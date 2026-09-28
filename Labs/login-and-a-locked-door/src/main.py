from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Base, SessionLocal, engine
from dependencies import get_current_user, get_db, require_role
from models import Book, User
from schemas import BookCreate, BookRead, Token
from security import create_access_token, hash_password, verify_password


async def seed():
    async with SessionLocal() as db:
        if await db.scalar(select(User)) is not None:
            return
        db.add_all([
            User(username="admin", hashed_password=hash_password("admin123"), role="admin"),
            User(username="reader", hashed_password=hash_password("reader123"), role="reader"),
            Book(title="Dune", author="Frank Herbert", genre="Science Fiction", pages=412),
            Book(title="Middlemarch", author="George Eliot", genre="Fiction", pages=880),
            Book(title="The Big Sleep", author="Raymond Chandler", genre="Mystery", pages=231),
        ])
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed()
    yield


auth_router = APIRouter(prefix="/auth", tags=["auth"])


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


books_router = APIRouter(prefix="/books", tags=["books"])


@books_router.get("", response_model=list[BookRead])
async def list_books(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Book))
    return result.scalars().all()


@books_router.post("", response_model=BookRead, status_code=status.HTTP_201_CREATED)
async def create_book(
    payload: BookCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    book = Book(**payload.model_dump())
    db.add(book)
    await db.commit()
    await db.refresh(book)
    return book


app = FastAPI(title="Login and a Locked Door", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(books_router)
