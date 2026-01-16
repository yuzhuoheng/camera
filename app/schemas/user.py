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
    storage_used: int = 0
    storage_limit: int = 524288000

    class Config:
        from_attributes = True
