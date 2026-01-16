from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, BigInteger, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True) # openid
    nickname = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Storage quota
    storage_used = Column(BigInteger, default=0) # bytes
    storage_limit = Column(BigInteger, default=524288000) # 500MB in bytes

    albums = relationship("Album", back_populates="owner")
    photos = relationship("Photo", back_populates="owner")
    quota_logs = relationship("UserQuotaLog", back_populates="user")
    invites_sent = relationship("UserInvite", foreign_keys="[UserInvite.inviter_id]", back_populates="inviter")
    invites_received = relationship("UserInvite", foreign_keys="[UserInvite.invitee_id]", back_populates="invitee")

class UserQuotaLog(Base):
    __tablename__ = "user_quota_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    change_amount = Column(BigInteger, nullable=False) # Positive or negative
    current_limit = Column(BigInteger, nullable=False) # Snapshot after change
    reason = Column(String, nullable=False) # initial_default, invite_reward, purchase
    reference_id = Column(String, nullable=True) # invited_user_id, order_id
    operator = Column(String, nullable=True) # system, admin_id
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="quota_logs")

class UserInvite(Base):
    __tablename__ = "user_invites"

    id = Column(String, primary_key=True, default=generate_uuid)
    inviter_id = Column(String, ForeignKey("users.id"), index=True)
    invitee_id = Column(String, ForeignKey("users.id"), unique=True, index=True)
    status = Column(String, default="completed") # completed, fraud
    reward_granted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    inviter = relationship("User", foreign_keys=[inviter_id], back_populates="invites_sent")
    invitee = relationship("User", foreign_keys=[invitee_id], back_populates="invites_received")

class Album(Base):
    __tablename__ = "albums"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, index=True)
    owner_id = Column(String, ForeignKey("users.id"))
    cover_url = Column(String, nullable=True)
    is_default = Column(Integer, default=0) # 0: normal, 1: default
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="albums")
    photos = relationship("Photo", back_populates="album")
    shares = relationship("Share", back_populates="album")

class Photo(Base):
    __tablename__ = "photos"

    id = Column(String, primary_key=True, default=generate_uuid)
    url = Column(String)
    thumbnail_url = Column(String, nullable=True)
    filename = Column(String)
    size = Column(Integer, default=0) # bytes
    
    owner_id = Column(String, ForeignKey("users.id"))
    album_id = Column(String, ForeignKey("albums.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="photos")
    album = relationship("Album", back_populates="photos")

    @property
    def download_url(self):
        return self.url

class Share(Base):
    __tablename__ = "shares"

    id = Column(String, primary_key=True, default=generate_uuid)
    token = Column(String, unique=True, index=True)
    album_id = Column(String, ForeignKey("albums.id"))
    permission = Column(String, default="read_only") # read_only, allow_upload
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    album = relationship("Album", back_populates="shares")
