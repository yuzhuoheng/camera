from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# 避免循环导入，这里定义一个简单的 Album Schema 用于 ShareInfo
class AlbumSimpleResponse(BaseModel):
    id: str
    name: str
    owner_nickname: Optional[str] = None
    cover_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class ShareCreate(BaseModel):
    expires_in_hours: Optional[int] = 72
    permission: str = "read_only"

class ShareResponse(BaseModel):
    token: str
    share_url: str
    permission: str
    expires_at: Optional[datetime]

class ShareInfoResponse(BaseModel):
    valid: bool
    album: Optional[AlbumSimpleResponse] = None
    permission: Optional[str] = None
