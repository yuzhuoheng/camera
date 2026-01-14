from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.models.models import Share, Album, Photo, User
from app.schemas.share import ShareInfoResponse, AlbumSimpleResponse
from sqlalchemy import desc

router = APIRouter()

@router.get("/{token}", response_model=ShareInfoResponse)
def get_share_info(token: str, db: Session = Depends(get_db)):
    share = db.query(Share).filter(Share.token == token).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share link not found")
        
    if share.expires_at and share.expires_at < datetime.utcnow():
        raise HTTPException(status_code=404, detail="Share link expired")
        
    album = db.query(Album).filter(Album.id == share.album_id).first()
    if not album:
            raise HTTPException(status_code=404, detail="Album not found")

    # 获取最新一张照片作为封面
    latest_photo = db.query(Photo).filter(Photo.album_id == album.id).order_by(desc(Photo.created_at)).first()
    cover_url = latest_photo.thumbnail_url if latest_photo else None
    if latest_photo and not cover_url:
        cover_url = latest_photo.url
        
    owner = db.query(User).filter(User.id == album.owner_id).first()
    owner_nickname = owner.nickname if owner else "Unknown"

    album_info = AlbumSimpleResponse(
        id=album.id,
        name=album.name,
        owner_nickname=owner_nickname,
        cover_url=cover_url
    )
    
    return ShareInfoResponse(
        valid=True,
        album=album_info,
        permission=share.permission
    )
