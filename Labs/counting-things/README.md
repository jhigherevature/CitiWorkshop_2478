# Counting Things

We'll write the query shapes behind a typical set of analytical questions, first in plain SQL and then in SQLAlchemy, so we can read the two side by side. We'll cover `GROUP BY` with `COUNT`, a ratio per group filtered with `HAVING`, a join that compares two columns from different tables, and a table joined to itself.

## Prerequisites

| Software | Required Version |
|---|---|
| PostgreSQL | 14 or newer (18 is current) |
| A SQL client | `psql` (comes with PostgreSQL), pgAdmin, or DBeaver |
| Python | 3.10 or newer (3.14 is current) |
| SQLAlchemy | 2.0.54 |
| psycopg | 3.3.6 (the `binary` build) |

This lab needs a real PostgreSQL server. The earlier labs used SQLite because their subject was the Python plumbing around the database. This one's subject is the SQL itself, so we write it against the database the workshop uses.

### Getting it running

**1. Create and load the database.** From this folder, with PostgreSQL running:

```bash
psql -h localhost -U postgres -c "CREATE DATABASE library"
psql -h localhost -U postgres -d library -f sql/schema.sql
psql -h localhost -U postgres -d library -f sql/seed.sql
```

Each command asks for the `postgres` user's password. On Windows, if `psql` isn't found, add PostgreSQL's `bin` folder to the path for this PowerShell window (adjust `18` to your version):

```powershell
$env:Path += ";C:\Program Files\PostgreSQL\18\bin"
```

`schema.sql` drops and recreates every table, so running it and then `seed.sql` again always puts the data back exactly as it started.

**2. Run the SQL queries.**

```bash
psql -h localhost -U postgres -d library -f sql/queries.sql
```

This prints all four results one after another. In pgAdmin or DBeaver, open `sql/queries.sql` against the `library` database, highlight one query, and run just that selection. Running the whole file in pgAdmin only shows the last result.

**3. Run the SQLAlchemy queries.**

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/queries.py
```

Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src/queries.py
```

(If PowerShell refuses to run `Activate.ps1`, run `Set-ExecutionPolicy -Scope Process Bypass` first.)

The script connects as user `postgres` with password `postgres`. If yours differ, change the one `DATABASE_URL` line at the top of `src/queries.py`:

```python
DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/library"
```

### The data

Four small tables:

| Table | Columns | Points at |
|---|---|---|
| `libraries` | `id`, `name`, `city` | |
| `books` | `id`, `title`, `author`, `genre`, `pages`, `available` | |
| `members` | `id`, `name`, `home_library_id`, `referred_by_id` | `home_library_id` → `libraries`; `referred_by_id` → another row in `members` |
| `loans` | `id`, `member_id`, `book_id`, `library_id` | `member_id` → `members`; `book_id` → `books`; `library_id` → `libraries` |

A **loan** records that a member borrowed a book from a particular library. We need that fourth table because "which library did they borrow from" belongs to the borrowing, not to the member or the book.

The libraries are `1` Central, `2` Riverside, and `3` Hilltop. The seed data never changes, so every result below is an exact answer we can check against.

## Guided walkthrough

### How the SQLAlchemy side is set up

`src/queries.py` starts with a model for each table the queries touch (`Book`, `Member`, `Loan`). There's no `Library` class, because no query needs library names. The tables themselves were created by `schema.sql`, so the models just describe what's already there.

There's no `relationship()` anywhere. Every join spells out its `ON` condition, exactly like the SQL does, which is what lets the two versions line up clause for clause.

We use a plain synchronous `Session` because this is a script. The `select(...)` statements are exactly what we'd pass to `await db.execute(...)` inside a FastAPI endpoint. Building the statement doesn't depend on how it gets run.

For each query, the script prints **the SQL that SQLAlchemy generated** and then the rows. Keep an eye on that printed SQL as we go: it's the most direct evidence that the two versions say the same thing.

### Query 1: count per group

*How many books are in each genre?*

| SQL | SQLAlchemy |
|---|---|
| `SELECT genre, COUNT(*) AS book_count` | `select(Book.genre, func.count().label("book_count"))` |
| `FROM books` | *(worked out from `Book.genre`)* |
| `GROUP BY genre` | `.group_by(Book.genre)` |
| `ORDER BY genre;` | `.order_by(Book.genre)` |

`GROUP BY genre` collapses every row with the same genre into a single group, and `COUNT(*)` counts the rows in each group. Once we group, every column in the `SELECT` has to be either something we grouped by (`genre`) or an aggregate over the group (`COUNT(*)`). A book's `title` can't appear, because a group of six books has no single title.

On the Python side, `func.count()` becomes `count(*)`. `func.anything(...)` renders as the SQL function `anything(...)`, which is how we'll get `round` in a moment. We never write `FROM`: SQLAlchemy sees `Book.genre` and works out the table itself.

Expected result:

| genre | book_count |
|---|---|
| Fiction | 6 |
| History | 3 |
| Mystery | 5 |
| Poetry | 2 |
| Science Fiction | 4 |

That's 20 books in all.

### Query 2: a ratio per group, above a threshold

*Which genres have more than 30% of their books unavailable?*

This is the shape behind any "flag the groups where too many members are in some state" question. As provided, the query computes the ratio for every genre but doesn't filter yet:

```sql
SELECT genre,
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE NOT available) AS unavailable,
       ROUND(CAST(COUNT(*) FILTER (WHERE NOT available) AS NUMERIC) / COUNT(*), 2) AS unavailable_ratio
FROM books
GROUP BY genre
ORDER BY genre;
```

```python
unavailable = func.count().filter(not_(Book.available))
unavailable_ratio = cast(unavailable, Numeric) / func.count()

genres_mostly_unavailable = (
    select(
        Book.genre,
        func.count().label("total"),
        unavailable.label("unavailable"),
        func.round(unavailable_ratio, 2).label("unavailable_ratio"),
    )
    .group_by(Book.genre)
    .order_by(Book.genre)
)
```

Three new pieces:

- **`COUNT(*) FILTER (WHERE NOT available)`** counts only the rows in each group that match the condition, so we get the total and the unavailable count from the same pass over the data. SQLAlchemy spells it `func.count().filter(not_(Book.available))`.
- **`CAST(... AS NUMERIC)`** matters more than it looks. In PostgreSQL, an integer divided by an integer is an integer, with the fraction thrown away. Try it:

  ```sql
  SELECT 2 / 5 AS integer_division, CAST(2 AS NUMERIC) / 5 AS numeric_division;
  ```

  ```
   integer_division |    numeric_division
  ------------------+------------------------
                  0 | 0.40000000000000000000
  ```

  Without the cast, every ratio here would be `0` and no genre would ever cross 30%. (If you look at the SQL the script prints, SQLAlchemy's `/` goes one step further and casts the right-hand side as well. The answer is the same.)
- **`ROUND(..., 2)`** is only for display, turning `0.40000000000000000000` into `0.40`.

Run it now, from `psql` or with `python src/queries.py`, and all five genres appear:

| genre | total | unavailable | unavailable_ratio |
|---|---|---|---|
| Fiction | 6 | 1 | 0.17 |
| History | 3 | 1 | 0.33 |
| Mystery | 5 | 2 | 0.40 |
| Poetry | 2 | 0 | 0.00 |
| Science Fiction | 4 | 1 | 0.25 |

#### Why `HAVING` and not `WHERE`

We want to keep only the genres above `0.3`. The instinct is to write `WHERE`, but it helps to know the order PostgreSQL works through a query in, which isn't the order we write it in:

```
FROM books          start with every row in the table
WHERE ...           keep or drop individual ROWS         ← no groups exist yet
GROUP BY genre      collapse the surviving rows into groups
HAVING ...          keep or drop whole GROUPS            ← aggregates exist now
SELECT ...          compute the output columns and give them names
ORDER BY ...        sort
```

"30% of the books are unavailable" is a fact about a *group*. A single row has no ratio. `WHERE` runs before any groups exist, so it can't see one, and PostgreSQL says so if we try:

```
ERROR:  aggregate functions are not allowed in WHERE
```

`HAVING` runs after grouping, when each group's counts exist. It's a `WHERE` for groups.

The same list explains why we can't write `HAVING unavailable_ratio > 0.3`. The name `unavailable_ratio` is handed out in `SELECT`, which runs *after* `HAVING`, so at that point PostgreSQL reports `column "unavailable_ratio" does not exist`. In SQL we write the expression out again. In Python we built it once as the variable `unavailable_ratio` and simply use it twice, and SQLAlchemy writes it out twice for us.

The two clauses aren't rivals, either. A query can have both: `WHERE pages > 300` would first drop the short books, and `HAVING` would then judge the groups made from the rows that are left.

Now we'll add the filter. In `sql/queries.sql`, in query 2, add this line **between `GROUP BY genre` and `ORDER BY genre`**:

```sql
HAVING CAST(COUNT(*) FILTER (WHERE NOT available) AS NUMERIC) / COUNT(*) > 0.3
```

In `src/queries.py`, in `genres_mostly_unavailable`, add this **between `.group_by(Book.genre)` and `.order_by(Book.genre)`**:

```python
    .having(unavailable_ratio > 0.3)
```

Run both again. Two genres remain:

| genre | total | unavailable | unavailable_ratio |
|---|---|---|---|
| History | 3 | 1 | 0.33 |
| Mystery | 5 | 2 | 0.40 |

History only just makes it, and Science Fiction at `0.25` doesn't. Side by side, the finished query reads:

| SQL | SQLAlchemy |
|---|---|
| `SELECT genre,` | `select(Book.genre,` |
| `COUNT(*) AS total,` | `func.count().label("total"),` |
| `COUNT(*) FILTER (WHERE NOT available) AS unavailable,` | `unavailable.label("unavailable"),` |
| `ROUND(CAST(...) / COUNT(*), 2) AS unavailable_ratio` | `func.round(unavailable_ratio, 2).label("unavailable_ratio"))` |
| `FROM books` | *(worked out from `Book`)* |
| `GROUP BY genre` | `.group_by(Book.genre)` |
| `HAVING CAST(...) / COUNT(*) > 0.3` | `.having(unavailable_ratio > 0.3)` |
| `ORDER BY genre;` | `.order_by(Book.genre)` |

### Query 3: comparing two locations

*Which members borrowed a book from a library other than their home library?*

This is the shape behind any "these two things should be in the same place, and where aren't they?" question. The two locations live in different tables: a member's home is `members.home_library_id`, and where a loan happened is `loans.library_id`. A comparison can only look at one row at a time, so the first job is to get both columns onto the same row. That's what the join does:

```sql
SELECT members.name, members.home_library_id, loans.library_id AS borrowed_at_library_id
FROM members
JOIN loans ON loans.member_id = members.id
ORDER BY members.name;
```

```python
members_borrowing_away = (
    select(Member.name, Member.home_library_id, Loan.library_id.label("borrowed_at_library_id"))
    .join(Loan, Loan.member_id == Member.id)
    .order_by(Member.name)
)
```

Run it as provided and we get **12 rows**, one per loan, each showing the member's home library next to the library the loan came from. In most rows the two numbers match. We want the rows where they don't.

Now that both columns sit on the same row, comparing them is an ordinary condition. In `sql/queries.sql`, in query 3, add this line **between the `JOIN` line and `ORDER BY`**:

```sql
WHERE loans.library_id <> members.home_library_id
```

In `src/queries.py`, in `members_borrowing_away`, add this **between `.join(...)` and `.order_by(...)`**:

```python
    .where(Loan.library_id != Member.home_library_id)
```

`<>` is standard SQL for "not equal". PostgreSQL also accepts `!=`, which is what SQLAlchemy writes. Run both again. **3 rows** remain:

| name | home_library_id | borrowed_at_library_id |
|---|---|---|
| Cleo Martin | 2 | 1 |
| Esme Lindqvist | 3 | 1 |
| Grace Kim | 1 | 3 |

For an inner join like this one, the comparison could also be written into the `ON` clause with an `AND`, and it would return the same rows. We keep `ON` for *how the tables connect* and `WHERE` for *which rows we want*, so each clause does one job.

| SQL | SQLAlchemy |
|---|---|
| `SELECT members.name, members.home_library_id,` | `select(Member.name, Member.home_library_id,` |
| `loans.library_id AS borrowed_at_library_id` | `Loan.library_id.label("borrowed_at_library_id"))` |
| `FROM members` | *(worked out from `Member`)* |
| `JOIN loans ON loans.member_id = members.id` | `.join(Loan, Loan.member_id == Member.id)` |
| `WHERE loans.library_id <> members.home_library_id` | `.where(Loan.library_id != Member.home_library_id)` |
| `ORDER BY members.name;` | `.order_by(Member.name)` |

### Query 4: a table joined to itself

*Which members did Ada Park refer?*

This is the shape behind any "who reports to whom" question. `members.referred_by_id` points at *another row in the same table*. To put a member next to the person who referred them, we need the `members` table in the query twice, and each copy needs its own name so we can say which one we mean:

```sql
SELECT members.name
FROM members
JOIN members AS referrer ON referrer.id = members.referred_by_id
WHERE referrer.name = 'Ada Park'
ORDER BY members.name;
```

```python
Referrer = aliased(Member, name="referrer")

referred_by_ada = (
    select(Member.name)
    .join(Referrer, Referrer.id == Member.referred_by_id)
    .where(Referrer.name == "Ada Park")
    .order_by(Member.name)
)
```

Read the join as: for each member, find the row whose `id` equals this member's `referred_by_id`, and call that row `referrer`. `aliased(Member)` gives SQLAlchemy a second, separately named handle on the same table. The `name="referrer"` only makes the generated SQL say `AS referrer`, just like ours. Without it, SQLAlchemy would invent a name like `members_1`.

This one is provided complete. Expected result, **3 rows**:

| name |
|---|
| Ben Okafor |
| Cleo Martin |
| Esme Lindqvist |

| SQL | SQLAlchemy |
|---|---|
| *(a second name for `members`)* | `Referrer = aliased(Member, name="referrer")` |
| `SELECT members.name` | `select(Member.name)` |
| `FROM members` | *(worked out from `Member`)* |
| `JOIN members AS referrer ON referrer.id = members.referred_by_id` | `.join(Referrer, Referrer.id == Member.referred_by_id)` |
| `WHERE referrer.name = 'Ada Park'` | `.where(Referrer.name == "Ada Park")` |
| `ORDER BY members.name;` | `.order_by(Member.name)` |

## What this lab leaves out

These are deliberate: the API, the frontend, `relationship()` configuration, and tests. In an application, each of these statements would live in an endpoint or a service function and run with `await db.execute(...)`. The statement itself wouldn't change.
