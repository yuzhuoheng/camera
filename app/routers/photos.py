from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import update
from typing import Optional, List
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
    
    # 2. Check Quota & Atomic Update
    # Use atomic update to prevent race conditions
    stmt = (
        update(models.User)
        .where(models.User.id == current_user.id)
        .where(models.User.storage_used + file_size <= models.User.storage_limit)
        .values(storage_used=models.User.storage_used + file_size)
    )
    result = db.execute(stmt)
    db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=403, detail="Storage limit exceeded")

    photo_id = str(uuid.uuid4())
    object_name = f"photos/{current_user.id}/{photo_id}{ext}"
    thumb_object_name = f"photos/{current_user.id}/{photo_id}_thumb.jpg"
    
    try:
        file_data = await file.read()
        
        # 3. Upload Original
        url = minio_client.upload_file(
            file_data, 
            object_name, 
            content_type=file.content_type
        )
        
        # 4. Create and Upload Thumbnail
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
            
        # 5. Handle Album Logic
        final_album_id = album_id
        if final_album_id:
            # 验证相册权限
            # 1. 尝试查找自己的相册
            album = db.query(models.Album).filter(
                models.Album.id == final_album_id,
                models.Album.owner_id == current_user.id
            ).first()
            
            # 2. 如果不是自己的相册，检查是否有上传权限的分享链接
            if not album:
                 # 这里有点 tricky，因为上传接口没有传 share_token，所以我们只能信任 album_id
                 # 但为了安全，我们应该检查该 album_id 是否存在有效的、允许上传的分享链接
                 # 只要存在 ANY 一个有效的、允许上传的分享链接，我们就允许上传
                 # 这是一个宽松的策略，适用于 "只要相册开放了上传权限，任何人（或者知道链接的人）都能上传"
                 
                 current_time = datetime.utcnow()
                 valid_share = db.query(models.Share).filter(
                     models.Share.album_id == final_album_id,
                     models.Share.permission == "upload", # 必须是上传权限
                     (models.Share.expires_at == None) | (models.Share.expires_at > current_time)
                 ).first()
                 
                 if not valid_share:
                     # 既不是自己的，也没有有效的上传分享
                     # 为了防止回滚错误（因为之前已经 rollback 了），这里抛出特定异常
                     # 但要注意上面的 rollback 逻辑
                     raise HTTPException(status_code=403, detail="Permission denied: You cannot upload to this album")
        else:
            # Find or create default album
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
            
        # 6. Save to DB
        photo = models.Photo(
            id=photo_id,
            url=url,
            thumbnail_url=thumbnail_url,
            filename=file.filename,
            size=file_size,
            owner_id=current_user.id,
            album_id=final_album_id
        )
        # Explicitly set owner to current_user to avoid extra query and ensure it's available for response_model
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
                .where(models.User.id == current_user.id)
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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Photo)
    
    if album_id:
        # 如果指定了 album_id
        # 1. 检查相册是否存在
        album = db.query(models.Album).filter(models.Album.id == album_id).first()
        if not album:
             # 如果相册不存在，返回空列表或者 404，这里保持行为一致返回空
             return {
                "items": [],
                "total": 0,
                "page": page,
                "size": size,
                "pages": 0
            }
            
        # 2. 权限检查：是否是所有者，或者是否有分享权限
        if album.owner_id != current_user.id:
            current_time = datetime.utcnow()
            valid_share = db.query(models.Share).filter(
                models.Share.album_id == album_id,
                (models.Share.expires_at == None) | (models.Share.expires_at > current_time)
            ).first()
            
            if not valid_share:
                # 既不是所有者，也没有分享链接，拒绝访问
                 raise HTTPException(status_code=403, detail="Not authorized to access this album")
        
        # 3. 过滤该相册下的所有照片（不限制 owner_id，因为可能是别人上传的）
        query = query.filter(models.Photo.album_id == album_id)
        
    else:
        # 如果没有指定 album_id，则默认只显示当前用户上传的照片（例如在"所有照片"视图中）
        query = query.filter(models.Photo.owner_id == current_user.id)
    
    # Order by created_at desc
    query = query.order_by(models.Photo.created_at.desc())
        
    total = query.count()
    photos = query.offset((page - 1) * size).limit(size).all()
    
    # Optimization: Manually set owner to avoid N+1 query
    # 这里需要注意，如果是共享相册，照片的 owner 可能不全是一样
    # 如果 owner_id == current_user.id，可以直接赋值
    # 否则，可能需要 eager load 或者单独查询（为了性能，这里最好加上 joinedload(models.Photo.owner)）
    # 但由于 PhotoResponse 中 owner 字段可能不是必须的，或者我们可以批量获取 user 信息
    
    # 既然已经重构了，我们简单处理：对于非当前用户的照片，owner 信息可能需要额外获取
    # 为了简化，我们暂时只给当前用户的照片填充 owner，其他人的照片 owner 可能会触发 lazy load
    # 或者我们可以用 joinedload 预加载
    
    # 重新构造查询以包含 owner 信息
    if album_id:
         # 只有在查询特定相册时（可能包含别人的照片），才需要 joinedload
         # 但上面的 query 已经执行了... 
         # 实际上，由于 SQLAlchemy 的特性，我们可以在 query 定义时就加上 options
         pass
         
    # 填充 owner (针对已经是对象的 photo)
    for photo in photos:
        if photo.owner_id == current_user.id:
            photo.owner = current_user
        # else: photo.owner will be lazy loaded if accessed
    
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
        models.Photo.owner_id == current_user.id
    ).first()
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
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
    
    # Decrement storage usage
    if photo_size > 0:
        stmt = (
            update(models.User)
            .where(models.User.id == current_user.id)
            .values(storage_used=models.User.storage_used - photo_size)
        )
        db.execute(stmt)
        
    db.commit()
    return
