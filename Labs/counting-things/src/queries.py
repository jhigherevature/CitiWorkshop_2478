from sqlalchemy import Numeric, cast, create_engine, func, not_, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, aliased, mapped_column

DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/library"


class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    author: Mapped[str]
    genre: Mapped[str]
    pages: Mapped[int]
    available: Mapped[bool]


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    home_library_id: Mapped[int]
    referred_by_id: Mapped[int | None]


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int]
    book_id: Mapped[int]
    library_id: Mapped[int]


# 1. Count per group: how many books are in each genre?
books_per_genre = (
    select(Book.genre, func.count().label("book_count"))
    .group_by(Book.genre)
    .order_by(Book.genre)
)


# 2. Ratio per group above a threshold:
#    which genres have more than 30% of their books unavailable?
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


# 3. Comparing two locations:
#    which members borrowed a book from a library other than their home library?
members_borrowing_away = (
    select(Member.name, Member.home_library_id, Loan.library_id.label("borrowed_at_library_id"))
    .join(Loan, Loan.member_id == Member.id)
    .order_by(Member.name)
)


# 4. A table joined to itself: which members did Ada Park refer?
Referrer = aliased(Member, name="referrer")

referred_by_ada = (
    select(Member.name)
    .join(Referrer, Referrer.id == Member.referred_by_id)
    .where(Referrer.name == "Ada Park")
    .order_by(Member.name)
)


QUERIES = {
    "1. Books per genre": books_per_genre,
    "2. Genres with more than 30% unavailable": genres_mostly_unavailable,
    "3. Members who borrowed away from home": members_borrowing_away,
    "4. Members referred by Ada Park": referred_by_ada,
}

if __name__ == "__main__":
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        for title, statement in QUERIES.items():
            print(f"\n=== {title} ===\n")
            print(statement.compile(engine, compile_kwargs={"literal_binds": True}))
            print()
            for row in session.execute(statement):
                print("   ", " | ".join(str(value) for value in row))
