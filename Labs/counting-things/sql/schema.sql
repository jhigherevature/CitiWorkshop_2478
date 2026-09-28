DROP TABLE IF EXISTS loans;
DROP TABLE IF EXISTS members;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS libraries;

CREATE TABLE libraries (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL
);

CREATE TABLE books (
    id        SERIAL PRIMARY KEY,
    title     TEXT    NOT NULL,
    author    TEXT    NOT NULL,
    genre     TEXT    NOT NULL,
    pages     INTEGER NOT NULL,
    available BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE members (
    id              SERIAL PRIMARY KEY,
    name            TEXT    NOT NULL,
    home_library_id INTEGER NOT NULL REFERENCES libraries (id),
    referred_by_id  INTEGER REFERENCES members (id)
);

CREATE TABLE loans (
    id         SERIAL PRIMARY KEY,
    member_id  INTEGER NOT NULL REFERENCES members (id),
    book_id    INTEGER NOT NULL REFERENCES books (id),
    library_id INTEGER NOT NULL REFERENCES libraries (id)
);
