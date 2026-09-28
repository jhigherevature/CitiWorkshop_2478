from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

SECRET_KEY = "lab-only-secret-key-never-use-this-one-in-production"
ALGORITHM = "HS256"

USERS = {
    "reader": bcrypt.hashpw(b"reader123", bcrypt.gensalt()),
}

BOOKS = [
    {"id": 1, "title": "Dune", "author": "Frank Herbert", "genre": "Science Fiction", "pages": 412, "available": True},
    {"id": 2, "title": "Middlemarch", "author": "George Eliot", "genre": "Fiction", "pages": 880, "available": False},
    {"id": 3, "title": "The Big Sleep", "author": "Raymond Chandler", "genre": "Mystery", "pages": 231, "available": True},
    {"id": 4, "title": "Kindred", "author": "Octavia E. Butler", "genre": "Science Fiction", "pages": 264, "available": True},
    {"id": 5, "title": "SPQR", "author": "Mary Beard", "genre": "History", "pages": 608, "available": False},
]

app = FastAPI(title="Five Rows on a Page API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


@app.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    hashed = USERS.get(form.username)
    if hashed is None or not bcrypt.checkpw(form.password.encode(), hashed):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")
    claims = {"sub": form.username, "exp": datetime.now(timezone.utc) + timedelta(minutes=30)}
    return {"access_token": jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM), "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        username = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    except jwt.InvalidTokenError:
        raise unauthorized
    if username not in USERS:
        raise unauthorized
    return username


@app.get("/books")
def list_books(_: str = Depends(get_current_user)):
    return BOOKS
