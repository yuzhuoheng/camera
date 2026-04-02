from typing import Optional
from urllib.parse import urlparse
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.admin_deps import verify_admin_credentials, create_admin_token, get_current_admin
from app.core.config import get_settings
from app.models.models import User, Album, Photo, UserQuotaLog

router = APIRouter(prefix="/cs-server/admin-api", tags=["admin-ui"])
settings = get_settings()


class AdminLoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def admin_login(payload: AdminLoginRequest):
    if not verify_admin_credentials(payload.username, payload.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"access_token": create_admin_token(), "token_type": "bearer"}


@router.get("/users")
def list_users(
    keyword: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    _: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = (
        db.query(
            User.id.label("id"),
            User.nickname.label("nickname"),
            User.email.label("email"),
            User.avatar_url.label("avatar_url"),
            User.created_at.label("created_at"),
            User.last_login_at.label("last_login_at"),
            User.storage_used.label("storage_used"),
            User.storage_limit.label("storage_limit"),
            func.count(func.distinct(Album.id)).label("album_count"),
            func.count(func.distinct(Photo.id)).label("photo_count"),
        )
        .outerjoin(Album, Album.owner_id == User.id)
        .outerjoin(Photo, Photo.album_id == Album.id)
    )

    if keyword:
        like_keyword = f"%{keyword}%"
        query = query.filter((User.id.like(like_keyword)) | (User.nickname.like(like_keyword)))

    total = query.with_entities(func.count(func.distinct(User.id))).scalar()

    rows = (
        query.group_by(
            User.id,
            User.nickname,
            User.email,
            User.avatar_url,
            User.created_at,
            User.last_login_at,
            User.storage_used,
            User.storage_limit,
        )
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "items": [
            {
                "id": row.id,
                "nickname": row.nickname,
                "email": row.email,
                "avatar_url": row.avatar_url,
                "created_at": row.created_at,
                "last_login_at": row.last_login_at,
                "album_count": int(row.album_count or 0),
                "photo_count": int(row.photo_count or 0),
                "storage_used": int(row.storage_used or 0),
                "storage_limit": int(row.storage_limit or 0),
            }
            for row in rows
        ]
    }


@router.get("/albums")
def list_albums(
    keyword: Optional[str] = None,
    sort_by: str = "created_at",
    order: str = "desc",
    skip: int = 0,
    limit: int = 100,
    _: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = (
        db.query(
            Album.id.label("id"),
            Album.name.label("name"),
            Album.owner_id.label("owner_id"),
            User.nickname.label("owner_nickname"),
            Album.is_default.label("is_default"),
            Album.created_at.label("created_at"),
            func.count(Photo.id).label("photo_count"),
        )
        .outerjoin(User, User.id == Album.owner_id)
        .outerjoin(Photo, Photo.album_id == Album.id)
    )
    if keyword:
        like_keyword = f"%{keyword}%"
        query = query.filter(
            (Album.id.like(like_keyword))
            | (Album.name.like(like_keyword))
            | (Album.owner_id.like(like_keyword))
        )

    total = query.with_entities(func.count(func.distinct(Album.id))).scalar()

    grouped_query = query.group_by(
        Album.id,
        Album.name,
        Album.owner_id,
        User.nickname,
        Album.is_default,
        Album.created_at,
    )

    if sort_by == "photo_count":
        if order == "asc":
            grouped_query = grouped_query.order_by(func.count(Photo.id).asc(), Album.created_at.desc())
        else:
            grouped_query = grouped_query.order_by(func.count(Photo.id).desc(), Album.created_at.desc())
    else:
        if order == "asc":
            grouped_query = grouped_query.order_by(Album.created_at.asc())
        else:
            grouped_query = grouped_query.order_by(Album.created_at.desc())

    rows = (
        grouped_query
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "items": [
            {
                "id": row.id,
                "name": row.name,
                "owner_id": row.owner_id,
                "owner_nickname": row.owner_nickname,
                "is_default": row.is_default,
                "created_at": row.created_at,
                "photo_count": int(row.photo_count or 0),
            }
            for row in rows
        ]
    }


@router.get("/albums/{album_id}/photos")
def list_album_photos(
    album_id: str,
    skip: int = 0,
    limit: int = 200,
    _: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    photos = (
        db.query(
            Photo.id.label("id"),
            Photo.filename.label("filename"),
            Photo.url.label("url"),
            Photo.thumbnail_url.label("thumbnail_url"),
            Photo.size.label("size"),
            Photo.owner_id.label("owner_id"),
            Photo.album_id.label("album_id"),
            Photo.created_at.label("created_at"),
            User.nickname.label("owner_nickname"),
            User.avatar_url.label("owner_avatar_url"),
        )
        .outerjoin(User, User.id == Photo.owner_id)
        .filter(Photo.album_id == album_id)
        .order_by(Photo.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": photo.id,
            "filename": photo.filename,
            "url": photo.url,
            "thumbnail_url": photo.thumbnail_url,
            "size": photo.size,
            "owner_id": photo.owner_id,
            "owner_nickname": photo.owner_nickname,
            "owner_avatar_url": photo.owner_avatar_url,
            "album_id": photo.album_id,
            "created_at": photo.created_at,
        }
        for photo in photos
    ]


@router.get("/users/{user_id}/quota-logs")
def list_user_quota_logs(
    user_id: str,
    skip: int = 0,
    limit: int = 200,
    _: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    logs = (
        db.query(UserQuotaLog)
        .filter(UserQuotaLog.user_id == user_id)
        .order_by(UserQuotaLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "change_amount": log.change_amount,
            "current_limit": log.current_limit,
            "reason": log.reason,
            "reference_id": log.reference_id,
            "operator": log.operator,
            "created_at": log.created_at,
        }
        for log in logs
    ]


@router.get("/media-proxy")
def media_proxy(
    url: str = Query(...),
    _: str = Depends(get_current_admin),
):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="无效媒体地址")

    allowed_hosts = set()
    if settings.MINIO_EXTERNAL_ENDPOINT:
        ext_parsed = urlparse(settings.MINIO_EXTERNAL_ENDPOINT)
        if ext_parsed.hostname:
            allowed_hosts.add(ext_parsed.hostname)
    minio_parsed = urlparse(
        settings.MINIO_ENDPOINT
        if settings.MINIO_ENDPOINT.startswith(("http://", "https://"))
        else f"http://{settings.MINIO_ENDPOINT}"
    )
    if minio_parsed.hostname:
        allowed_hosts.add(minio_parsed.hostname)
        
    # 添加内网常用IP段或允许所有的内部IP进行代理
    # 因为用户的照片可能存在 192.168.x.x, 10.x.x.x, 127.0.0.1 等
    if parsed.hostname not in allowed_hosts and not (
        parsed.hostname.startswith("192.168.") or 
        parsed.hostname.startswith("10.") or 
        parsed.hostname.startswith("127.") or 
        parsed.hostname == "localhost"
    ):
        raise HTTPException(status_code=403, detail=f"不允许的媒体地址: {parsed.hostname}")

    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            resp = client.get(url)
    except Exception:
        raise HTTPException(status_code=502, detail="媒体拉取失败")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail="媒体不可访问")

    media_type = resp.headers.get("content-type", "application/octet-stream")
    return Response(
        content=resp.content,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=300"},
    )
