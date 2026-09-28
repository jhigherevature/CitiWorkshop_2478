# One Endpoint, One Table

We'll follow one request all the way through a FastAPI application: route, dependency, session, query, schema, response, with exactly one of each. Along the way we'll use an `APIRouter`, an async SQLAlchemy 2.0 declarative model, `select()`, an `AsyncSession` handed out by `Depends(get_db)`, Pydantic v2 schemas with `from_attributes`, status codes, and the OpenAPI docs FastAPI generates for free.

## Prerequisites

| Software | Required Version |
|---|---|
| Python | 3.10 or newer (3.14 is current) |
| FastAPI | 0.141.1 |
| Uvicorn | 0.53.0 |
| SQLAlchemy | 2.0.54, with the `asyncio` extra |
| aiosqlite | 0.22.1 |

Pydantic 2.13 comes along with FastAPI; there's nothing to install for it separately.

**We're using SQLite, not PostgreSQL.** The database is a single file, `library.db`, created the first time the app starts, so there's no server to install, start, or log in to. The connection URL in `src/database.py` is the only line that changes to point this lab at PostgreSQL (see [Pointing it at PostgreSQL](#pointing-it-at-postgresql) at the end). Everything else here is exactly what we'd write against PostgreSQL.

### Getting it running

From this folder (the one with this README in it):

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --app-dir src --reload
```

**Windows (PowerShell)**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --app-dir src --reload
```

If PowerShell refuses to run `Activate.ps1`, run `Set-ExecutionPolicy -Scope Process Bypass` in that window and try again. The change only lasts until the window closes.

`--app-dir src` tells Uvicorn to import from `src/`, which is why our files can import each other with plain `from database import Base`. We run from this folder (not from inside `src/`) so `library.db` lands here, next to the README.

When the terminal says `Application startup complete`, open **http://127.0.0.1:8000/docs**.

## Guided walkthrough

### The shape of the thing

There are four files, and each has one job:

| File | Its job | Imports from |
|---|---|---|
| `src/database.py` | Where the database is and how we talk to it: the engine, the session factory, `get_db` | nothing of ours |
| `src/models.py` | What a book looks like **in the table** | `database` |
| `src/schemas.py` | What a book looks like **on the wire**, in the JSON coming in and going out | nothing of ours |
| `src/main.py` | The endpoints, and the app that serves them | all three |

Imports only flow one way: `main.py` imports the other three, `models.py` imports `database.py`, and nothing imports `main.py`. We'll see why that matters as we go.

Here's the path a `POST /books` takes through those files:

```
POST /books  {"title": "Dune", ...}
   │
   ▼
main.py      create_book(payload: BookCreate, db = Depends(get_db))
   │           ├─ FastAPI checks the JSON body against BookCreate ........ schemas.py
   │           └─ FastAPI calls get_db() and passes in the session ....... database.py
   ▼
main.py      Book(**payload.model_dump())  →  add, commit, refresh ....... models.py
   │
   ▼
main.py      return book   →  response_model=BookRead turns it into JSON .. schemas.py
   │
   ▼
201 Created  {"id": 1, "title": "Dune", ...}
```

We'll take the files in dependency order, starting with the one that depends on nothing.

### 1. `database.py`: where the database is

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///./library.db"

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session
```

- **`DATABASE_URL`** is the only line in the whole lab that knows we're on SQLite. `sqlite+aiosqlite` reads as "the SQLite dialect, spoken through the `aiosqlite` async driver."
- **`engine`** owns the connections. There's one per application, created once at import time.
- **`SessionLocal`** is a *factory*: calling `SessionLocal()` gives us a fresh `AsyncSession`, our unit of work for one request. `expire_on_commit=False` stops SQLAlchemy from marking every object stale after a commit. In sync code a stale object quietly reloads itself the next time we read it, but in async code that hidden reload isn't allowed, so we switch it off.
- **`Base`** is what every model inherits from. As a side effect, `Base.metadata` ends up holding a description of every table, which is how `main.py` can create them all in one call.
- **`get_db`** is a *dependency*. FastAPI runs it up to the `yield`, hands the session to our endpoint, and once the response is sent it comes back and finishes the `async with`, closing the session. Each request gets exactly one session and never shares it with another.

Why is this its own file? Because both `models.py` (needs `Base`) and `main.py` (needs `engine` and `get_db`) depend on it. If we moved it into `main.py`, then `models.py` would have to import `main.py`, which already imports `models.py`, and Python would fail with a circular import at startup.

### 2. `models.py`: a book in the table

```python
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    author: Mapped[str]
    genre: Mapped[str]
    available: Mapped[bool] = mapped_column(default=True)
```

This is SQLAlchemy 2.0's typed declarative style: the Python type annotation *is* the column type. `Mapped[str]` becomes a `NOT NULL` text column, and an integer primary key gets filled in by the database on insert. We only reach for `mapped_column(...)` when there's something the annotation alone can't say, like "primary key" or "default to `True`."

A `Book` instance is a row the session is tracking. It knows which table it belongs to, whether it's been saved, and which of its attributes have changed since. We'll see that tracking directly in a minute.

### 3. `schemas.py`: a book on the wire

```python
from pydantic import BaseModel, ConfigDict


class BookCreate(BaseModel):
    title: str
    author: str
    genre: str
    available: bool = True


class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    genre: str
    available: bool
```

- **`BookCreate`** is what a client is allowed to *send*. There's no `id`, because the database picks that, not the caller.
- **`BookRead`** is what we *send back*. It has the `id`, and it's allowed to read its values off an object's attributes (`from_attributes`, more on that below).

### Why `models.py` and `schemas.py` are separate

They both describe a book, so it's fair to ask why we don't use one class for both. There are three reasons, and the last one we can see for ourselves.

1. **They disagree on purpose.** The table has an `id`. What the client sends must *not* have an `id`. What we send back *must* have one. That's three shapes of "book," and no single class can be all three.
2. **The table will always know more than the API should say.** In the next lab, `User` has a `hashed_password` column. Our table class needs it, and the response must never contain it. `BookRead` works as an allow-list: only the fields listed there leave the server.
3. **They're different kinds of object.** A model is a row tracked by a database session. A schema is plain data that Pydantic has checked. Let's look at both side by side.

#### Seeing `from_attributes` at work

We'll leave the server running, open a **second terminal** in this folder, activate the virtual environment again (`source .venv/bin/activate`, or `.venv\Scripts\Activate.ps1` on Windows), and start Python from inside `src/`:

```bash
cd src
python
```

First we'll build a `Book` by hand. No database is involved; it's just an object:

```python
>>> from models import Book
>>> from schemas import BookCreate, BookRead
>>> book = Book(id=1, title="Dune", author="Frank Herbert", genre="Science Fiction", available=True)
>>> vars(book)
{'_sa_instance_state': <sqlalchemy.orm.state.InstanceState object at 0x...>, 'id': 1, 'title': 'Dune', 'author': 'Frank Herbert', 'genre': 'Science Fiction', 'available': True}
```

There's our book data, and alongside it `_sa_instance_state`, SQLAlchemy's bookkeeping. That bookkeeping is what makes a model a model, and it's exactly what we don't want to send to a browser.

Now we'll hand that object to each schema:

```python
>>> BookRead.model_validate(book)
BookRead(id=1, title='Dune', author='Frank Herbert', genre='Science Fiction', available=True)

>>> BookCreate.model_validate(book)
Traceback (most recent call last):
  ...
pydantic_core._pydantic_core.ValidationError: 1 validation error for BookCreate
  Input should be a valid dictionary or instance of BookCreate [type=model_type, input_value=<models.Book object at 0x...>, input_type=Book]
```

Same object, two different outcomes. By default a Pydantic model only reads *dictionaries*: it looks up `data["title"]`. `BookCreate` never needs anything else, because what it receives is always parsed JSON, which is a dictionary. `from_attributes=True` lets `BookRead` read *attributes* instead: it looks up `book.title`, `book.author`, and so on, and copies out just the fields it declares. The result is plain data:

```python
>>> BookRead.model_validate(book).model_dump_json()
'{"id":1,"title":"Dune","author":"Frank Herbert","genre":"Science Fiction","available":true}'
```

This is what happens when an endpoint does `return book` with `response_model=BookRead`. FastAPI takes the ORM object, reads it through `BookRead`, and serializes the result. FastAPI's response handling actually switches attribute-reading on for itself, so the endpoint would still work without the `model_config` line. We keep it because as soon as we convert a model in our own code with `BookRead.model_validate(book)` (in a service function, a background job, a test), the setting is what makes that call succeed.

Type `exit()` to leave Python, `cd ..` to get back to the lab folder, and close the second terminal.

### 4. `main.py`: the router, the endpoints, the app

```python
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Base, engine, get_db
from models import Book
from schemas import BookCreate, BookRead


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


router = APIRouter(prefix="/books", tags=["books"])


@router.post("", response_model=BookRead, status_code=status.HTTP_201_CREATED)
async def create_book(payload: BookCreate, db: AsyncSession = Depends(get_db)):
    book = Book(**payload.model_dump())
    db.add(book)
    await db.commit()
    await db.refresh(book)
    return book


@router.get("", response_model=list[BookRead])
async def list_books(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Book))
    return result.scalars().all()


app = FastAPI(title="One Endpoint, One Table", lifespan=lifespan)
app.include_router(router)
```

**`lifespan`** runs once when the app starts. `create_all` creates any table in `Base.metadata` that doesn't exist yet. It *only* creates, and never alters a table that's already there. Changing an existing table is a migration tool's job (Alembic), and we'll bump into that limit shortly.

**`router`** groups every `/books` endpoint under one prefix and one tag (the tag is the heading they appear under in `/docs`). In a bigger app each router gets its own module (`routers/books.py`, `routers/members.py`) and `main.py` shrinks to creating the app and calling `include_router` for each. We have one router, so it lives here.

**`create_book`** is the request path from the diagram, one line at a time:

| Line | What happens |
|---|---|
| `payload: BookCreate` | FastAPI parses the JSON body and checks it against `BookCreate`. A missing field or wrong type never reaches our code: FastAPI answers `422` on its own. |
| `db: AsyncSession = Depends(get_db)` | FastAPI calls `get_db` and hands us the session it yields. |
| `Book(**payload.model_dump())` | Schema → model: the checked data becomes a row object. |
| `db.add(book)` / `await db.commit()` | Stage the insert, then run it. |
| `await db.refresh(book)` | Re-read the row, which picks up the `id` the database just assigned. |
| `return book` | We return the *model*. `response_model=BookRead` converts it on the way out. |
| `status_code=status.HTTP_201_CREATED` | "Created" rather than the default `200`, because a POST that makes something should say so. |

**`list_books`** builds a query with `select(Book)` (which runs nothing yet) and runs it with `await db.execute(...)`. The result comes back as rows. Each row holds one `Book`, so `.scalars()` unwraps them and `.all()` collects them into a list. `response_model=list[BookRead]` converts every one.

### 5. Following a request through `/docs`

With the server running, we'll open **http://127.0.0.1:8000/docs**.

First, scroll to the bottom and look at **Schemas**. `BookCreate` and `BookRead` are listed there, and `Book` is not. The docs describe the *wire* format, which comes from `schemas.py`. The table's layout never leaks into the API's contract.

Now we'll create a book. Open **POST /books**, click **Try it out**, set the request body to:

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "genre": "Science Fiction"
}
```

and click **Execute**. The response code is **201**, and the body has an `id` we never sent:

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "genre": "Science Fiction",
  "available": true
}
```

Now open **GET /books**, **Try it out**, **Execute**. The same book comes back, this time inside a list and read from the database rather than from the object we just made.

While we're here, we'll send POST a body with the `author` line deleted. The answer is **422**, with a `detail` saying `author` is a required field. We didn't write that check. It came from the type annotations in `BookCreate`.

### 6. Adding a field: `pages`

Now we'll give `Book` a page count and watch it appear in each place in turn. We'll do it in two passes, so we can see what each file controls.

**First, reset the database.** Stop the server with **Ctrl+C** and delete `library.db`. We need to because `create_all` won't add a column to a table that already exists. If we skip this step, the next POST returns `500` and the terminal shows `table books has no column named pages`.

**Pass one: the table and the input.** In `src/models.py`, add a `pages` column to `Book`, right under `genre`:

```python
    pages: Mapped[int]
```

In `src/schemas.py`, add the matching field to `BookCreate`, also under `genre`:

```python
    pages: int
```

Start the server again (`uvicorn main:app --app-dir src --reload`), refresh `/docs`, and POST this body:

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "genre": "Science Fiction",
  "pages": 412
}
```

It's a **201**, but look at the response: there's no `pages`. The value *was* saved (the column is `NOT NULL`, so the insert would have failed without it). We can check with a one-liner from a second terminal in the lab folder, with the virtual environment activated:

```bash
python -c "import sqlite3; print(sqlite3.connect('library.db').execute('SELECT * FROM books').fetchall())"
```

```
[(1, 'Dune', 'Frank Herbert', 'Science Fiction', 412, 1)]
```

It's in the table. It's missing from the response because `BookRead` doesn't list it, and only what `BookRead` lists goes out.

**Pass two: the output.** In `src/schemas.py`, add the same field to `BookRead`, under `genre`:

```python
    pages: int
```

Save. `--reload` restarts the server on its own. Now **GET /books** returns:

```json
[
  {
    "id": 1,
    "title": "Dune",
    "author": "Frank Herbert",
    "genre": "Science Fiction",
    "pages": 412,
    "available": true
  }
]
```

and the **Schemas** section at the bottom of `/docs` shows `pages` on both `BookCreate` and `BookRead`.

That one field touched three places, each for its own reason: the table has to store it, the input has to accept it, and the output has to allow it out.

## Pointing it at PostgreSQL

Everything above is exactly the code we'd write against PostgreSQL. To switch, we'd create an empty `library` database, install the async PostgreSQL driver in place of `aiosqlite`:

```bash
pip install asyncpg==0.31.0
```

and change the one line in `src/database.py`:

```python
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/library"
```

using our own username and password. No other file changes.

## What this lab leaves out

These are deliberate: authentication (that's the next lab), relationships between tables, filtering and pagination, error handling (there's no 404 path yet), configuration (the URL is written into the code), a frontend, and tests. Each one would be one more thing standing between us and the request path.
