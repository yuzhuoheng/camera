from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import create_access_token
from app.models import models
from app.schemas.auth import LoginRequest
from app.schemas.token import Token
from app.schemas.user import User, UserUpdate
from app.core.deps import get_current_user
from app.services.storage import minio_client
from app.utils.random_utils import generate_random_nickname, get_animal_avatar_url
import uuid
import os
import httpx

router = APIRouter()
settings = get_settings()

@router.post("/avatar", response_model=User)
async def update_user_avatar(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    用户头像上传接口
    1. 接收文件
    2. 上传到 MinIO
    3. 更新用户 avatar_url
    """
    # 1. 校验文件
    ext = os.path.splitext(file.filename)[1]
    if not ext:
        ext = ".jpg"
    
    # 2. 生成文件名 (users/{user_id}/avatar.jpg)
    object_name = f"users/{current_user.id}/avatar{ext}"
    
    try:
        # 3. 检查并删除旧头像（如果存在且不是当前新文件）
        if current_user.avatar_url:
            # 简单判断是否为 MinIO 的 URL
            bucket_part = f"/{settings.MINIO_BUCKET_NAME}/"
            if bucket_part in current_user.avatar_url:
                old_object_name = current_user.avatar_url.split(bucket_part)[-1]
                # 只有当新旧文件名不一致时才需要显式删除（MinIO会自动覆盖同名文件）
                if old_object_name != object_name:
                    try:
                        minio_client.delete_file(old_object_name)
                    except Exception as e:
                        # 删除旧文件失败不应阻止新文件上传，记录日志即可
                        print(f"Warning: Failed to delete old avatar {old_object_name}: {e}")

        file_data = await file.read()
        
        # 4. 上传到 MinIO
        url = minio_client.upload_file(
            file_data, 
            object_name, 
            content_type=file.content_type
        )
        
        # 5. 更新用户信息
        current_user.avatar_url = url
        db.commit()
        db.refresh(current_user)
        
        return current_user
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Avatar upload failed: {str(e)}")

@router.put("/me", response_model=User)
def update_user_me(
    user_update: UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新当前用户的信息（昵称、头像等）
    """
    if user_update.nickname is not None:
        current_user.nickname = user_update.nickname
    if user_update.avatar_url is not None:
        current_user.avatar_url = user_update.avatar_url
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/me", response_model=User)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    """
    获取当前用户信息
    """
    return current_user

from datetime import datetime
from sqlalchemy import func

@router.post("/login", response_model=Token)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    微信小程序登录接口
    1. 接收小程序端的 code
    2. 调用微信 API 获取 openid 和 session_key
    3. 如果用户不存在则创建，存在则更新
    4. 颁发 JWT Token
    5. 处理邀请奖励逻辑
    """
    
    # 1. 向微信服务器换取 openid
    wx_url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.WECHAT_APP_ID,
        "secret": settings.WECHAT_APP_SECRET,
        "js_code": request.code,
        "grant_type": "authorization_code"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(wx_url, params=params)
        wx_data = response.json()
    
    if "errcode" in wx_data and wx_data["errcode"] != 0:
        raise HTTPException(
            status_code=400, 
            detail=f"WeChat API Error: {wx_data.get('errmsg')}"
        )
    
    openid = wx_data["openid"]
    # session_key = wx_data["session_key"] # 如果需要解密敏感数据会用到
    
    # 2. 查找或创建用户
    user = db.query(models.User).filter(models.User.id == openid).first()
    is_new_user = False
    
    if not user:
        is_new_user = True
        user = models.User(id=openid)
        user.last_login_at = datetime.utcnow()
        
        # 初始化默认值
        # 1. 随机生成昵称
        random_nickname = generate_random_nickname()
        user.nickname = random_nickname
        
        # 2. 根据昵称中的动物名，生成对应的随机头像
        user.avatar_url = get_animal_avatar_url(random_nickname)
        
        if request.userInfo:
            if request.userInfo.nickName:
                user.nickname = request.userInfo.nickName
            # 只有当 avatarUrl 存在且不是临时地址时才使用
            if request.userInfo.avatarUrl and not request.userInfo.avatarUrl.startswith(("http://tmp", "wxfile://")):
                user.avatar_url = request.userInfo.avatarUrl
                
        db.add(user)
        
        # Record initial quota log
        initial_limit = 524288000 # 500MB
        quota_log = models.UserQuotaLog(
            user_id=openid,
            change_amount=initial_limit,
            current_limit=initial_limit,
            reason="initial_default",
            operator="system"
        )
        db.add(quota_log)
        
        # --- Invite Logic Start ---
        if request.invite_code and request.invite_code != openid:
            # Check if inviter exists
            inviter = db.query(models.User).filter(models.User.id == request.invite_code).first()
            if inviter:
                # Create invite record
                invite_record = models.UserInvite(
                    inviter_id=inviter.id,
                    invitee_id=openid,
                    status="completed",
                    reward_granted=False
                )
                db.add(invite_record)
                db.flush() # Get ID

                # 1. Reward Invitee (+100MB)
                reward_amount = 104857600 # 100MB
                user.storage_limit += reward_amount
                
                invitee_log = models.UserQuotaLog(
                    user_id=openid,
                    change_amount=reward_amount,
                    current_limit=user.storage_limit,
                    reason="invite_reward_invitee",
                    reference_id=invite_record.id,
                    operator="system"
                )
                db.add(invitee_log)

                # 2. Reward Inviter (+100MB, with limits)
                # Check daily limit (1GB) and total limit (5GB) for inviter from invites
                # Total gained from invites
                total_invite_reward = db.query(func.sum(models.UserQuotaLog.change_amount)).filter(
                    models.UserQuotaLog.user_id == inviter.id,
                    models.UserQuotaLog.reason == "invite_reward_inviter"
                ).scalar() or 0
                
                # Today gained from invites
                today_invite_reward = db.query(func.sum(models.UserQuotaLog.change_amount)).filter(
                    models.UserQuotaLog.user_id == inviter.id,
                    models.UserQuotaLog.reason == "invite_reward_inviter",
                    func.date(models.UserQuotaLog.created_at) == datetime.utcnow().date()
                ).scalar() or 0

                daily_limit = 1073741824 # 1GB
                total_limit = 5368709120 # 5GB
                
                # Calculate actual reward allowed
                remaining_daily = max(0, daily_limit - today_invite_reward)
                remaining_total = max(0, total_limit - total_invite_reward)
                
                actual_reward = min(reward_amount, remaining_daily, remaining_total)
                
                if actual_reward > 0:
                    inviter.storage_limit += actual_reward
                    inviter_log = models.UserQuotaLog(
                        user_id=inviter.id,
                        change_amount=actual_reward,
                        current_limit=inviter.storage_limit,
                        reason="invite_reward_inviter",
                        reference_id=invite_record.id,
                        operator="system"
                    )
                    db.add(inviter_log)
                    invite_record.reward_granted = True

        # --- Invite Logic End ---
        
        # Create Default Album
        default_album = models.Album(
            name="默认相册",
            owner_id=user.id,
            is_default=1
        )
        db.add(default_album)
        
        db.commit()
        db.refresh(user)
    else:
        # 这里的逻辑可优化：每次登录是否更新头像昵称？
        # 目前简单处理：如果传了且不一致则更新
        user.last_login_at = datetime.utcnow()
        if request.userInfo:
            if request.userInfo.nickName != user.nickname:
                user.nickname = request.userInfo.nickName
            if request.userInfo.avatarUrl != user.avatar_url:
                user.avatar_url = request.userInfo.avatarUrl
        db.commit()

    # 3. 生成 JWT Token
    access_token = create_access_token(data={"sub": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "is_new_user": is_new_user
    }
