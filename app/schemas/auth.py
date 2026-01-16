from pydantic import BaseModel, Field
from typing import Optional

class WxUserInfo(BaseModel):
    nickName: str
    avatarUrl: str
    gender: Optional[int] = None
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None

class LoginRequest(BaseModel):
    code: str
    userInfo: Optional[WxUserInfo] = None
    invite_code: Optional[str] = None # Optional invite code (user_id of inviter)
