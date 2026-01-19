from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import update
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import os
import math

from app.core.database import get_db
from app.core.config import get_settings
from app.models import models
from app.schemas.photo import PhotoResponse, PhotoListResponse
from app.core.deps import get_current_user
from app.services.storage import minio_client
from app.utils.image import create_thumbnail

router = APIRouter()
settings = get_settings()

@router.post("", response_model=PhotoResponse)
async def upload_photo(
    file: UploadFile = File(...),
    album_id: Optional[str] = Form(None),
    share_token: Optional[str] = Form(None), # 新增 share_token 参数
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Validate file
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    ext = os.path.splitext(file.filename)[1]
    if not ext:
        ext = ".jpg"
    
    # Calculate file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    # 2. Determine Album and Billable User (Album Owner)
    final_album_id = album_id
    billable_user_id = current_user.id
    
    if final_album_id:
        # 验证相册权限
        # 1. 尝试查找相册
        album = db.query(models.Album).filter(models.Album.id == final_album_id).first()
        
        if not album:
             # 如果指定了 ID 但找不到，抛出错误（或者回退到默认相册？这里选择抛错更严谨）
             raise HTTPException(status_code=404, detail="Album not found")

        # 2. 确定计费用户（相册拥有者）
        billable_user_id = album.owner_id
        
        # 3. 权限检查
        if album.owner_id != current_user.id:
             # 检查是否有上传权限的分享链接
             current_time = datetime.now(timezone.utc)
             
             # 优先使用前端传递的 share_token 进行验证
             if share_token:
                 share = db.query(models.Share).filter(models.Share.token == share_token).first()
                 
                 if not share:
                     raise HTTPException(status_code=403, detail="Invalid share token")
                 
                 if share.album_id != final_album_id:
                     raise HTTPException(status_code=403, detail="Share token does not match this album")
                     
                 if share.expires_at and share.expires_at < current_time:
                     raise HTTPException(status_code=403, detail="Share token expired")
                     
                 if share.permission != "upload":
                     raise HTTPException(status_code=403, detail="Insufficient permission: Upload access required")
                     
             else:
                raise HTTPException(status_code=403, detail="Permission denied: You need a valid share token to upload to this album")
    else:
        # Find or create default album for current_user
        default_album = db.query(models.Album).filter(
            models.Album.owner_id == current_user.id,
            models.Album.is_default == 1
        ).first()
        
        if not default_album:
            default_album = models.Album(
                name="默认相册",
                owner_id=current_user.id,
                is_default=1
            )
            db.add(default_album)
            db.commit()
            db.refresh(default_album)
        
        final_album_id = default_album.id
        billable_user_id = current_user.id

    # 3. Check Quota & Atomic Update for Billable User
    # Use atomic update to prevent race conditions
    stmt = (
        update(models.User)
        .where(models.User.id == billable_user_id)
        .where(models.User.storage_used + file_size <= models.User.storage_limit)
        .values(storage_used=models.User.storage_used + file_size)
    )
    result = db.execute(stmt)
    db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=403, detail="Storage limit exceeded for the album owner")

    photo_id = str(uuid.uuid4())
    object_name = f"photos/{billable_user_id}/{photo_id}{ext}" # Use billable_user_id for storage path? Or current_user? 
    # Usually files are stored under owner's path. So use billable_user_id (album owner).
    
    thumb_object_name = f"photos/{billable_user_id}/{photo_id}_thumb.jpg"
    
    try:
        file_data = await file.read()
        
        # 4. Upload Original
        url = minio_client.upload_file(
            file_data, 
            object_name, 
            content_type=file.content_type
        )
        
        # 5. Create and Upload Thumbnail
        thumbnail_url = None
        try:
            thumb_data = create_thumbnail(file_data)
            thumbnail_url = minio_client.upload_file(
                thumb_data,
                thumb_object_name,
                content_type="image/jpeg"
            )
        except Exception as e:
            print(f"Thumbnail generation failed: {e}")
            # Fallback: use original URL as thumbnail if generation fails
            thumbnail_url = url
            
        # 6. Save to DB
        photo = models.Photo(
            id=photo_id,
            url=url,
            thumbnail_url=thumbnail_url,
            filename=file.filename,
            size=file_size,
            owner_id=current_user.id, # The uploader is the owner of the photo record
            album_id=final_album_id
        )
        
        # Explicitly set owner to avoid extra query
        photo.owner = current_user
        
        db.add(photo)
        db.commit()
        db.refresh(photo)
        
        return photo

    except Exception as e:
        # Rollback storage usage if anything fails
        print(f"Upload failed, rolling back storage usage: {e}")
        # Only rollback if we haven't already raised the 403
        if "Storage limit exceeded" not in str(e):
             rollback_stmt = (
                update(models.User)
                .where(models.User.id == billable_user_id) # Rollback billable user
                .values(storage_used=models.User.storage_used - file_size)
            )
             db.execute(rollback_stmt)
             db.commit()
        
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("", response_model=PhotoListResponse)
def get_photos(
    page: int = 1,
    size: int = 20,
    album_id: Optional[str] = None,
    share_token: Optional[str] = None, # 新增 share_token 参数
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Photo)
    
    if album_id:
        # 场景1：查看特定相册
        
        # 优先检查 share_token
        if share_token:
            # 校验 Share Token
            share = db.query(models.Share).filter(models.Share.token == share_token).first()
            
            if not share:
                raise HTTPException(status_code=403, detail="Invalid share token")
            
            if share.album_id != album_id:
                raise HTTPException(status_code=403, detail="Share token does not match this album")
                
            current_time = datetime.now(timezone.utc)
            if share.expires_at and share.expires_at < current_time:
                raise HTTPException(status_code=403, detail="Share token expired")
            
            # Token 校验通过，允许访问该相册下的所有照片
            # 不再校验 owner_id
            
        else:
            # 没有 Token，走常规权限校验（是否是所有者）
            album = db.query(models.Album).filter(models.Album.id == album_id).first()
            if not album:
                 return {
                    "items": [],
                    "total": 0,
                    "page": page,
                    "size": size,
                    "pages": 0
                }
            
            if album.owner_id != current_user.id:
                # 再次检查数据库中是否有针对该用户的直接授权（如果有的话），或者是否是管理员
                # 目前只支持所有者访问，或者通过 Token 访问
                raise HTTPException(status_code=403, detail="Not authorized to access this album")
        
        # 过滤该相册下的所有照片
        query = query.filter(models.Photo.album_id == album_id)
        
    else:
        # 场景2：查看“所有照片”（时间线）
        # 仅限查看自己的照片
        query = query.filter(models.Photo.owner_id == current_user.id)
    
    # Order by created_at desc
    query = query.order_by(models.Photo.created_at.desc())
    
    if album_id and share_token:
        # 如果是分享相册，可能包含多人的照片，需要加载 owner 信息
        query = query.options(joinedload(models.Photo.owner))
        
    total = query.count()
    photos = query.offset((page - 1) * size).limit(size).all()
    
    # Optimization: Manually set owner if it's current user
    for photo in photos:
        if photo.owner_id == current_user.id:
            photo.owner = current_user
    
    pages = math.ceil(total / size) if size > 0 else 0
        
    return {
        "items": photos,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }

@router.get("/{photo_id}", response_model=PhotoResponse)
def get_photo(
    photo_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Optimization: Remove joinedload since we filter by current_user.id
    photo = db.query(models.Photo).filter(
        models.Photo.id == photo_id,
        models.Photo.owner_id == current_user.id
    ).first()
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
        
    # Optimization: Manually set owner
    photo.owner = current_user
        
    return photo

@router.get("/user/{user_id}", response_model=PhotoListResponse)
def get_user_photos(
    user_id: str,
    page: int = 1,
    size: int = 20,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Optimization: Query user once instead of joining for every row
    target_user = None
    if user_id == current_user.id:
        target_user = current_user
    else:
        target_user = db.query(models.User).filter(models.User.id == user_id).first()
        if not target_user:
             # If user not found, we return empty list or 404. Here we return empty list to be safe or 404?
             # Let's return 404 as "User not found" makes sense
             raise HTTPException(status_code=404, detail="User not found")

    # TODO: Add privacy check (e.g., if album is public) or admin check here
    query = db.query(models.Photo).filter(models.Photo.owner_id == user_id)
    
    # Order by created_at desc
    query = query.order_by(models.Photo.created_at.desc())
        
    total = query.count()
    photos = query.offset((page - 1) * size).limit(size).all()
    
    # Optimization: Manually set owner
    for photo in photos:
        photo.owner = target_user

    pages = math.ceil(total / size) if size > 0 else 0
        
    return {
        "items": photos,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }

@router.delete("/{photo_id}", status_code=204)
def delete_photo(
    photo_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    photo = db.query(models.Photo).filter(
        models.Photo.id == photo_id,
        # models.Photo.owner_id == current_user.id # REMOVE THIS: Allow album owner to delete photos too
    ).first()
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Permission Check:
    # 1. Photo Owner can delete
    # 2. Album Owner can delete (if photo is in an album)
    can_delete = False
    if photo.owner_id == current_user.id:
        can_delete = True
    elif photo.album_id:
        album = db.query(models.Album).filter(models.Album.id == photo.album_id).first()
        if album and album.owner_id == current_user.id:
            can_delete = True
            
    if not can_delete:
        raise HTTPException(status_code=403, detail="Permission denied: You cannot delete this photo")
    
    photo_size = photo.size if photo.size else 0

    # Delete from MinIO
    try:
        bucket_part = f"/{settings.MINIO_BUCKET_NAME}/"
        
        if photo.url and bucket_part in photo.url:
            obj_name = photo.url.split(bucket_part)[-1]
            minio_client.delete_file(obj_name)
            
        if photo.thumbnail_url and bucket_part in photo.thumbnail_url:
            # Check if thumbnail is different from url (in case of fallback)
            if photo.thumbnail_url != photo.url:
                obj_name = photo.thumbnail_url.split(bucket_part)[-1]
                minio_client.delete_file(obj_name)
            
    except Exception as e:
        print(f"Error deleting files from MinIO: {e}")
        
    db.delete(photo)
    
    # Decrement storage usage (Restore quota to the album owner)
    billable_user_id = photo.owner_id # Default to photo owner
    if photo.album_id:
        album = db.query(models.Album).filter(models.Album.id == photo.album_id).first()
        if album:
            billable_user_id = album.owner_id
            
    if photo_size > 0:
        stmt = (
            update(models.User)
            .where(models.User.id == billable_user_id)
            .values(storage_used=models.User.storage_used - photo_size)
        )
        db.execute(stmt)
        
    db.commit()
    return
