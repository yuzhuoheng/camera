from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.database import get_db
from app.models.models import Share, Album, Photo, User
from app.schemas.share import ShareInfoResponse, AlbumSimpleResponse
from sqlalchemy import desc

router = APIRouter()

@router.get("/{token}", response_model=ShareInfoResponse)
def get_share_info(token: str, db: Session = Depends(get_db)):
    share = db.query(Share).filter(Share.token == token).first()
    if not share:
        # 区分撤回（找不到记录）
        raise HTTPException(status_code=404, detail="分享链接已撤销或不存在")
        
    # Fix: Compare timezone-aware datetime with timezone-aware datetime
    now = datetime.now(timezone.utc)
    
    if share.expires_at and share.expires_at < now:
        # 区分过期
        raise HTTPException(status_code=410, detail="分享链接已过期")
        
    album = db.query(Album).filter(Album.id == share.album_id).first()
    if not album:
            raise HTTPException(status_code=404, detail="相册不存在")

    # 获取最新一张照片作为封面
    latest_photo = db.query(Photo).filter(Photo.album_id == album.id).order_by(desc(Photo.created_at)).first()
    cover_url = latest_photo.thumbnail_url if latest_photo else None
    if latest_photo and not cover_url:
        cover_url = latest_photo.url
        
    owner = db.query(User).filter(User.id == album.owner_id).first()
    owner_nickname = owner.nickname if owner else "Unknown"
    owner_avatar_url = owner.avatar_url if owner else None

    album_info = AlbumSimpleResponse(
        id=album.id,
        name=album.name,
        owner_nickname=owner_nickname,
        owner_avatar_url=owner_avatar_url,
        cover_url=cover_url
    )
    
    return ShareInfoResponse(
        valid=True,
        album=album_info,
        permission=share.permission
    )
