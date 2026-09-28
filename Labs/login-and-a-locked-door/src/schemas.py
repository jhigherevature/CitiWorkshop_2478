from pydantic import BaseModel, ConfigDict


class BookCreate(BaseModel):
    title: str
    author: str
    genre: str
    pages: int
    available: bool = True


class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    genre: str
    pages: int
    available: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
