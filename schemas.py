from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class UserBase(BaseModel):
    login: str = Field(
        ..., 
        min_length=3, 
        max_length=30, 
        regex=r'^[a-zA-Z0-9_]+$', 
        description="Логін користувача (латинські літери, цифри, підкреслення)"
    )

class UserCreate(UserBase):
    password: str = Field(
        ..., 
        min_length=6, 
        max_length=128, 
        description="Пароль користувача"
    )
    avatar: Optional[str] = Field(
        None, 
        description="Шлях до зображення"
    )

class UserOut(UserBase):
    id: int

    class Config:
        orm_mode = True


class AuthorBase(BaseModel):
    name: str = Field(
        ..., 
        min_length=2, 
        max_length=50, 
        description="Ім'я автора"
    )
    avatar: Optional[str] = Field(
        None, 
        description="Шлях до зображення"
    )

class AuthorCreate(AuthorBase):
    pass

class AuthorOut(AuthorBase):
    id: int

    class Config:
        orm_mode = True



class TrackBase(BaseModel):
    title: str = Field(
        ..., 
        min_length=1, 
        max_length=100, 
        description="Назва треку"
    )

    file_url: str = Field(
        ..., 
        description="Шлях до файлу"
    )

    avatar: Optional[str] = Field(
        None, 
        description="Шлях до зображення"
    )

    author_id: int = Field(
        ..., 
        description="ID автора треку"
    )

class TrackCreate(TrackBase):
    user_id: int

class TrackOut(TrackBase):
    id: int
    author: AuthorOut

    class Config:
        orm_mode = True


class PlaylistBase(BaseModel):
    title: str = Field(
        ..., 
        min_length=1, 
        max_length=100, 
        description="Назва плейлиста"
    )
    avatar: Optional[str] = Field(
        None, 
        description="Шлях до зображення"
    )
    user_id: int = Field(
        ..., 
        description="ID користувача"
    )

class PlaylistCreate(PlaylistBase):
    pass

class PlaylistOut(PlaylistBase):
    id: int
    user: UserOut
    tracks: List[TrackOut] = []

    class Config:
        orm_mode = True
