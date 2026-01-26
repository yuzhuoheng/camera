from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    id: str

class UserUpdate(UserBase):
    pass

class User(UserBase):
    id: str
    created_at: datetime
    storage_used: int
    storage_limit: int

    class Config:
        from_attributes = True

class UserAdmin(User):
    storage_used: int
    storage_limit: int
