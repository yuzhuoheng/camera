from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import models
from typing import List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class InviteHistoryItem(BaseModel):
    invitee_nickname: str
    invitee_avatar: str
    reward_amount: int
    created_at: datetime

class InviteStatsResponse(BaseModel):
    total_reward: int
    invite_count: int
    history: List[InviteHistoryItem]

@router.get("", response_model=InviteStatsResponse)
def get_my_invites(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    获取当前用户的邀请统计信息
    """
    # 1. Total Reward from invites
    total_reward = db.query(func.sum(models.UserQuotaLog.change_amount)).filter(
        models.UserQuotaLog.user_id == current_user.id,
        models.UserQuotaLog.reason == "invite_reward_inviter"
    ).scalar() or 0

    # 2. Invite Count (Successful invites)
    invite_count = db.query(models.UserInvite).filter(
        models.UserInvite.inviter_id == current_user.id,
        models.UserInvite.status == "completed"
    ).count()

    # 3. History
    # Join UserInvite with User (invitee) and UserQuotaLog to get exact reward amount per invite
    # Note: One invite -> One quota log (reason=invite_reward_inviter)
    
    results = db.query(
        models.UserInvite,
        models.User,
        models.UserQuotaLog.change_amount
    ).join(
        models.User, models.UserInvite.invitee_id == models.User.id
    ).outerjoin(
        models.UserQuotaLog, 
        (models.UserQuotaLog.reference_id == models.UserInvite.id) & 
        (models.UserQuotaLog.user_id == current_user.id)
    ).filter(
        models.UserInvite.inviter_id == current_user.id
    ).order_by(models.UserInvite.created_at.desc()).all()

    history = []
    for invite, invitee, amount in results:
        # Desensitize nickname if needed (e.g., "User***") - keeping it simple for now
        history.append(InviteHistoryItem(
            invitee_nickname=invitee.nickname or "Unknown",
            invitee_avatar=invitee.avatar_url or "",
            reward_amount=amount or 0, # Could be 0 if limit reached
            created_at=invite.created_at
        ))

    return InviteStatsResponse(
        total_reward=int(total_reward),
        invite_count=invite_count,
        history=history
    )
