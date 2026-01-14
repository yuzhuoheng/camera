from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
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

    albums = relationship("Album", back_populates="owner")
    photos = relationship("Photo", back_populates="owner")

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
