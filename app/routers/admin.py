from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models import models
from app.schemas.user import UserAdmin

router = APIRouter()

@router.get("/users", response_model=List[UserAdmin])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    管理员接口：获取所有用户信息列表
    包含存储空间使用情况
    """
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users
