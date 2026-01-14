from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    is_new_user: bool

class TokenPayload(BaseModel):
    sub: Optional[str] = None
