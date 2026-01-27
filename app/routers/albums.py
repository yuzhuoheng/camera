from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User, Album, Photo, Share
from app.schemas.album import AlbumCreate, AlbumResponse, AlbumUpdate
from app.schemas.share import ShareCreate, ShareResponse
from sqlalchemy import desc
import uuid
from datetime import datetime, timedelta

router = APIRouter()

def get_album_details(album: Album, db: Session) -> AlbumResponse:
    # 统计照片数量和总大小
    # 使用 func.sum 聚合查询
    from sqlalchemy.sql import func
    stats = db.query(
        func.count(Photo.id),
        func.sum(Photo.size)
    ).filter(Photo.album_id == album.id).first()
    
    photo_count = stats[0] or 0
    total_size = stats[1] or 0
    
    # 获取最新一张照片作为封面
    latest_photo = db.query(Photo).filter(Photo.album_id == album.id).order_by(desc(Photo.created_at)).first()
    cover_url = latest_photo.thumbnail_url if latest_photo else None
    
    # 如果 latest_photo 只有 url 没有 thumbnail_url，则使用 url
    if latest_photo and not cover_url:
        cover_url = latest_photo.url

    return AlbumResponse(
        id=album.id,
        name=album.name,
        owner_id=album.owner_id,
        created_at=album.created_at,
        cover_url=cover_url,
        photo_count=photo_count,
        size=int(total_size),
        is_default=album.is_default or 0
    )

@router.post("/", response_model=AlbumResponse, status_code=status.HTTP_201_CREATED)
def create_album(
    album_in: AlbumCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_album = Album(
        name=album_in.name,
        owner_id=current_user.id
    )
    db.add(new_album)
    db.commit()
    db.refresh(new_album)
    return get_album_details(new_album, db)

@router.get("/", response_model=List[AlbumResponse])
def get_albums(
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = None,
    start_date: Optional[datetime] = Query(None, description="Filter albums created after this date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter albums created before this date (ISO format)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Album).filter(Album.owner_id == current_user.id)
    
    if keyword:
        query = query.filter(Album.name.contains(keyword))
    
    if start_date:
        query = query.filter(Album.created_at >= start_date)
        
    if end_date:
        query = query.filter(Album.created_at <= end_date)
    
    # 按照创建时间倒序排列
    query = query.order_by(desc(Album.created_at))
    
    albums = query.offset(skip).limit(limit).all()
    
    # 填充详情（封面和数量）
    return [get_album_details(album, db) for album in albums]

@router.get("/{album_id}", response_model=AlbumResponse)
def get_album(
    album_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 先尝试获取属于自己的相册
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
        
    # 如果不是所有者，检查是否有有效的分享链接
    if album.owner_id != current_user.id:
        # 检查是否存在未过期的分享
        # 注意：这里我们放宽了权限，只要相册有有效的分享链接，就允许查看详情
        # 这是为了支持前端在不知道 token 的情况下（只知道 album_id）获取相册详情
        # 这是一个妥协方案，更严格的做法是要求请求头带上 share-token
        current_time = datetime.utcnow()
        share = db.query(Share).filter(
            Share.album_id == album.id,
            (Share.expires_at == None) | (Share.expires_at > current_time)
        ).first()
        
        if not share:
             raise HTTPException(status_code=403, detail="Not authorized to access this album")

    return get_album_details(album, db)

@router.put("/{album_id}", response_model=AlbumResponse)
def update_album(
    album_id: str,
    album_in: AlbumUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    album = db.query(Album).filter(Album.id == album_id, Album.owner_id == current_user.id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    if album_in.name is not None:
        album.name = album_in.name
    
    db.commit()
    db.refresh(album)
    return get_album_details(album, db)

from app.services.storage import minio_client
from app.core.config import get_settings

settings = get_settings()

@router.delete("/{album_id}", status_code=status.HTTP_200_OK)
def delete_album(
    album_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    album = db.query(Album).filter(Album.id == album_id, Album.owner_id == current_user.id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    if album.is_default:
        raise HTTPException(status_code=400, detail="Default album cannot be deleted")
    
    from sqlalchemy import update

    # 策略升级：级联删除照片（数据库记录 + 云存储文件）
    photos = db.query(Photo).filter(Photo.album_id == album_id).all()
    bucket_part = f"/{settings.MINIO_BUCKET_NAME}/"
    
    total_size_freed = 0

    for photo in photos:
        # Calculate size to free
        if photo.size:
            total_size_freed += photo.size

        # 1. Delete from MinIO
        try:
            if photo.url and bucket_part in photo.url:
                obj_name = photo.url.split(bucket_part)[-1]
                minio_client.delete_file(obj_name)
                
            if photo.thumbnail_url and bucket_part in photo.thumbnail_url:
                if photo.thumbnail_url != photo.url:
                    obj_name = photo.thumbnail_url.split(bucket_part)[-1]
                    minio_client.delete_file(obj_name)
        except Exception as e:
            print(f"Error deleting files for photo {photo.id}: {e}")
        
        # 2. Delete from DB
        db.delete(photo)
    
    # 3. Update User Quota
    if total_size_freed > 0:
        stmt = (
            update(User)
            .where(User.id == current_user.id)
            .values(storage_used=User.storage_used - total_size_freed)
        )
        db.execute(stmt)

    # 4. Delete Album
    db.delete(album)
    db.commit()
    
    return {"message": "Album and all its photos deleted successfully", "id": album_id}

@router.post("/{album_id}/share", response_model=ShareResponse)
def create_share(
    album_id: str,
    share_in: ShareCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    album = db.query(Album).filter(Album.id == album_id, Album.owner_id == current_user.id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    token = str(uuid.uuid4())
    expires_at = None
    if share_in.expires_in_hours:
        expires_at = datetime.utcnow() + timedelta(hours=share_in.expires_in_hours)
        
    new_share = Share(
        token=token,
        album_id=album.id,
        permission=share_in.permission,
        expires_at=expires_at
    )
    db.add(new_share)
    db.commit()
    db.refresh(new_share)
    
    # Construct share_url
    share_url = f"pages/share?token={token}" 
    
    return ShareResponse(
        token=new_share.token,
        share_url=share_url,
        permission=new_share.permission,
        expires_at=new_share.expires_at
    )

@router.get("/{album_id}/shares", response_model=List[ShareResponse])
def get_album_shares(
    album_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    album = db.query(Album).filter(Album.id == album_id, Album.owner_id == current_user.id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
        
    shares = db.query(Share).filter(Share.album_id == album.id).all()
    
    result = []
    for share in shares:
        share_url = f"pages/share?token={share.token}"
        result.append(ShareResponse(
            token=share.token,
            share_url=share_url,
            permission=share.permission,
            expires_at=share.expires_at
        ))
        
    return result

@router.delete("/shares/{token}", status_code=status.HTTP_200_OK)
def delete_share(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find share
    share = db.query(Share).filter(Share.token == token).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
        
    # Verify ownership through album
    album = db.query(Album).filter(Album.id == share.album_id).first()
    if not album or album.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this share")
        
    db.delete(share)
    db.commit()
    
    return {"message": "Share deleted successfully"}
