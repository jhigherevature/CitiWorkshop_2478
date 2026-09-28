# Login and a Locked Door

We'll watch a request carry a token, and watch the same request get turned away without one. On the way we'll use bcrypt password hashing, issuing and decoding a JWT, FastAPI's `OAuth2PasswordBearer`, a `get_current_user` dependency, a `require_role` dependency, and the difference between a `401` and a `403`.

## Prerequisites

| Software | Required Version |
|---|---|
| Python | 3.10 or newer (3.14 is current) |
| FastAPI | 0.141.1 |
| Uvicorn | 0.53.0 |
| SQLAlchemy | 2.0.54, with the `asyncio` extra |
| aiosqlite | 0.22.1 |
| bcrypt | 5.0.0 |
| PyJWT | 2.14.0 |
| python-multipart | 0.0.32 |

**We're using SQLite, not PostgreSQL.** The database is a single file, `library.db`, created and seeded the first time the app starts, so there's no server to install or log in to. The connection URL in `src/database.py` is the only line that changes to point this lab at PostgreSQL (see [Pointing it at PostgreSQL](#pointing-it-at-postgresql) at the end). Everything else here is exactly what we'd write against PostgreSQL.

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

If PowerShell refuses to run `Activate.ps1`, run `Set-ExecutionPolicy -Scope Process Bypass` in that window and try again.

When the terminal says `Application startup complete`, open **http://127.0.0.1:8000/docs**.

On first start the app creates two users (and three books):

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | `admin` |
| `reader` | `reader123` | `reader` |

To start over at any point, stop the server, delete `library.db`, and start it again.

## Guided walkthrough

### The shape of the thing

This is the same layout as *One Endpoint, One Table*, plus two new files:

| File | Its job | Knows about HTTP? |
|---|---|---|
| `src/database.py` | The engine, the session factory, `Base` | no |
| `src/models.py` | `User` and `Book`, as tables | no |
| `src/schemas.py` | Book JSON in and out, plus the login response `Token` | no |
| `src/security.py` | **New.** Hash and check passwords; issue and decode tokens | no |
| `src/dependencies.py` | **New.** `get_db`, `get_current_user`, `require_role`: everything a route can ask for with `Depends` | yes |
| `src/main.py` | Seeding, the login endpoint, the book endpoints | yes |

`get_db` has moved from `database.py` into `dependencies.py`, because it's a dependency like the other two. `database.py` is now only about the connection.

Here's what happens to a request for a locked, admin-only route. Each step is a place it can be turned away:

```
POST /books   Authorization: Bearer eyJhbGciOi...
   │
   ▼
oauth2_scheme           pull the token out of the header ............ no header?          → 401
   │
   ▼
get_current_user        decode_access_token(token) → "reader" ........ bad or expired?     → 401
                        SELECT the user named "reader" ............... no such user?       → 401
   │
   ▼
require_role("admin")   is user.role "admin"? ......................... no?                 → 403
   │
   ▼
create_book runs
```

### 1. `security.py`: passwords and tokens

```python
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

SECRET_KEY = "lab-only-secret-key-never-use-this-one-in-production"
ALGORITHM = "HS256"
TOKEN_LIFETIME = timedelta(minutes=30)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


def create_access_token(username: str) -> str:
    claims = {"sub": username, "exp": datetime.now(timezone.utc) + TOKEN_LIFETIME}
    return jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return claims["sub"]
```

- **`hash_password`** runs bcrypt with a fresh random salt, so hashing `reader123` twice gives two different strings. The stored string (`$2b$12$...`) carries its own salt and cost factor inside it.
- **`verify_password`** hashes the attempt again using the salt from the stored string and compares the results. At no point do we turn a hash back into a password, because that can't be done.
- **`create_access_token`** builds the *claims* (`sub`, the subject, meaning who this is about, and `exp`, when it stops being valid) and signs them with `SECRET_KEY`.
- **`decode_access_token`** checks the signature and the expiry, and hands back the username. If either check fails, PyJWT raises `jwt.InvalidTokenError`.

The secret key is written straight into the code because configuration is out of scope here. In a real app it comes from the environment or a secret manager, and anyone who has it can mint tokens for any user.

This file has no FastAPI imports and no database. It's pure functions, strings in and strings out, so login, seeding, a test, or a one-off admin script can all use it without starting a web server.

### 2. `dependencies.py`: the locks

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
```

`oauth2_scheme` does two jobs. At request time it reads the `Authorization: Bearer <token>` header and returns the token string. If there's no such header, it answers `401 Not authenticated` without calling any of our code. In the docs, `tokenUrl` tells Swagger UI where to send a username and password, and that's what puts the **Authorize** button on `/docs`.

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        username = decode_access_token(token)
    except jwt.InvalidTokenError:
        raise unauthorized

    user = await db.scalar(select(User).where(User.username == username))
    if user is None:
        raise unauthorized
    return user
```

`get_current_user` is a dependency that has dependencies of its own. FastAPI resolves the whole chain: it gets the token from `oauth2_scheme` and a session from `get_db`, then calls this function. There are two ways out with a `401`. The token doesn't check out (tampered with, expired, or signed by someone else), or it checks out but names a user who isn't in the database. That second check is a database query, and it runs **on every request**. We'll come back to why that matters.

```python
def require_role(role: str):
    async def check_role(user: User = Depends(get_current_user)) -> User:
        if user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires the {role} role",
            )
        return user

    return check_role
```

`require_role` isn't a dependency itself. It's a function that *builds* one, which is how we get to write `require_role("admin")` at the route. The dependency it builds, `check_role`, depends on `get_current_user`, so any route that asks for a role gets authentication along with it. By the time `check_role` runs we already know who the caller is. All that's left to decide is whether this particular caller is allowed.

### 3. `models.py` and `schemas.py`

`User` has a `hashed_password` column, and `schemas.py` has no user schema at all. No endpoint returns a user, so that column has no path out of the server. This is the allow-list idea from the last lab, taken as far as it goes.

`Token` is the login response: `{"access_token": "...", "token_type": "bearer"}`. That exact shape is what the OAuth2 password flow specifies, and it's what Swagger UI expects to read back.

### 4. `main.py`: seed, login, books

`seed()` runs at startup, right after `create_all`, and does nothing if any user already exists. Passwords go in through `hash_password`, so the table only ever holds hashes.

```python
@auth_router.post("/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(select(User).where(User.username == form.username))
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    return Token(access_token=create_access_token(user.username))
```

`OAuth2PasswordRequestForm` reads `username` and `password` from a **form-encoded** body, not JSON. That's what the OAuth2 password flow specifies, and it's why `python-multipart` is in our requirements. An unknown username and a wrong password get the same answer, so the endpoint never tells a stranger which usernames exist.

```python
@books_router.get("", response_model=list[BookRead])
async def list_books(
    db: AsyncSession = Depends(get_db),
):
    ...


@books_router.post("", response_model=BookRead, status_code=status.HTTP_201_CREATED)
async def create_book(
    payload: BookCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    ...
```

`list_books` is open to anyone. `create_book` asks for `require_role("admin")`. We name the parameter `_` because we want the *check*, not the value: the endpoint never uses the user, it just can't run unless one was found with the right role.

### 5. Trying the doors

With the server running, open **http://127.0.0.1:8000/docs**. There's a padlock icon next to **POST /books** and none next to **GET /books**. Swagger worked that out from the dependencies: `require_role` leads to `get_current_user`, which leads to `oauth2_scheme`, so the docs know that route needs a token.

Open **GET /books**, **Try it out**, **Execute**: **200**, three books, no login needed.

Now open **POST /books**, **Try it out**, and send:

```json
{
  "title": "Kindred",
  "author": "Octavia E. Butler",
  "genre": "Science Fiction",
  "pages": 264
}
```

The answer is **401** with `{"detail": "Not authenticated"}`, and the response headers include `www-authenticate: Bearer`. That came from `oauth2_scheme`, which found no `Authorization` header and stopped the request before `create_book` could run.

### 6. Locking `GET /books`

Now we'll lock the open door. In `src/main.py`, we'll give `list_books` a second dependency so it needs to know who is calling. Add this line inside its parentheses, under the `db` line:

```python
    _: User = Depends(get_current_user),
```

so the signature reads:

```python
async def list_books(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
```

`get_current_user` and `User` are already imported at the top of the file. Save, and `--reload` restarts the server.

Refresh `/docs`. **GET /books** now has a padlock too. Run the exact request that worked a minute ago: it's **401**. The endpoint's own code didn't change. What changed is that FastAPI now has to resolve `get_current_user` before calling it, and it can't.

### 7. Logging in

Click **Authorize** at the top of `/docs`. Enter `reader` / `reader123`, leave `client_id` and `client_secret` empty, click **Authorize**, then **Close**. Swagger just posted that form to `/auth/login` and kept the `access_token` it got back.

Run **GET /books** again: **200**. Look at the **Curl** box Swagger shows above the response:

```
curl -X 'GET' \
  'http://127.0.0.1:8000/books' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
```

That header is the whole mechanism. Every request Swagger sends now carries it, and the server checks it every time.

### 8. The reader at the admin's door

Still logged in as `reader`, run **POST /books** with the Kindred body again. This time the answer is **403**, `{"detail": "Requires the admin role"}`, and there's no `www-authenticate` header.

Click **Authorize**, then **Logout**, and log in as `admin` / `admin123`. Run the same POST: **201**, and Kindred has an `id`.

### 401 versus 403

Both mean "no," but they are different answers:

- **401 Unauthorized** really means *unauthenticated*: "I don't know who you are." Logging in (again) fixes it. The `WWW-Authenticate: Bearer` header tells the client what kind of credential to come back with.
- **403 Forbidden** means "I know exactly who you are, and the answer is still no." Logging in again changes nothing.

In our code the split follows the dependency chain. Every `401` comes from `oauth2_scheme` (no token) or `get_current_user` (bad token, unknown user). The only `403` comes from `require_role`, and `require_role` can only run *after* `get_current_user` has succeeded. So a `403` always means the caller was authenticated. This is what a frontend relies on: a `401` sends the user to the login page, and a `403` shows them "you don't have access."

### The token is only a signed claim

We'll finish by looking inside a token, and then at what the server does with it.

Click **Authorize**, then **Logout**, and log back in as `reader`. Then open **POST /auth/login** in `/docs`, **Try it out**, enter `reader` / `reader123`, **Execute**, and copy the `access_token` value from the response.

Open a **second terminal** in this folder, activate the virtual environment, and start `python`:

```python
>>> import jwt
>>> jwt.decode("paste-the-token-here", options={"verify_signature": False})
{'sub': 'reader', 'exp': 1789745755}
```

We didn't need the secret key to read it. A JWT is encoded, not encrypted, so anyone holding one can read what's inside. The signature doesn't hide anything. What it proves is that *this server* issued these exact claims, and change one character of the token and the server answers `401 Could not validate credentials`.

Notice what isn't in there: the role. The token only says "this is `reader`." Every request, `get_current_user` takes that name and loads the user from the database, and `require_role` checks the role on *that* row. We can watch this happen by changing the reader's role in the database without touching the token. Type `exit()` to leave Python, then run this in the same terminal:

```bash
python -c "import sqlite3; c = sqlite3.connect('library.db'); c.execute('UPDATE users SET role = ? WHERE username = ?', ('admin', 'reader')); c.commit()"
```

Back in `/docs` (still logged in as `reader`, same token), run **POST /books** with any book: **201**. Now put the role back:

```bash
python -c "import sqlite3; c = sqlite3.connect('library.db'); c.execute('UPDATE users SET role = ? WHERE username = ?', ('reader', 'reader')); c.commit()"
```

and run it again: **403**. The token never changed, but the answer did, because the server doesn't trust the token for anything beyond *who*. What that person may do is looked up fresh every time. That's why removing someone's access takes effect on their very next request. If we'd put the role inside the token, it would stay frozen there until the token expired.

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

These are deliberate: refresh tokens, registration, password rules, expiry handling (tokens do expire after 30 minutes, and when one does, the answer is a plain `401`, so we just **Authorize** again), configuration (the secret key is written into the code), a frontend (that's the next lab), and tests.
