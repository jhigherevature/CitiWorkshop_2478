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
