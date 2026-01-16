from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PhotoBase(BaseModel):
    pass

class PhotoCreate(PhotoBase):
    album_id: Optional[str] = None

class PhotoOwner(BaseModel):
    id: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

class PhotoResponse(PhotoBase):
    id: str
    url: str
    thumbnail_url: Optional[str] = None
    download_url: str 
    filename: str
    size: int = 0
    owner_id: str
    owner: PhotoOwner
    album_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PhotoListResponse(BaseModel):
    items: List[PhotoResponse]
    total: int
    page: int
    size: int
    pages: int
