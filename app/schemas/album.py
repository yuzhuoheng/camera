from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AlbumBase(BaseModel):
    name: str

class AlbumCreate(AlbumBase):
    pass

class AlbumUpdate(BaseModel):
    name: Optional[str] = None

class AlbumResponse(AlbumBase):
    id: str
    owner_id: str
    cover_url: Optional[str] = None
    photo_count: int = 0
    size: int = 0 # bytes
    is_default: int = 0
    created_at: datetime

    class Config:
        from_attributes = True
