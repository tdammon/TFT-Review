from sqlalchemy import Column, Integer, String, ForeignKey, ARRAY, Enum as SQLAlchemyEnum, Text
from sqlalchemy.orm import relationship, Mapped
from typing import List, Optional, TYPE_CHECKING

from .base import Base

from enum import Enum

if TYPE_CHECKING:
    from .user import User
    from .comment import Comment


class VideoVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"

class Video(Base):
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("user.id"))
    
    # Basic info
    title: Mapped[str] = Column(String(100), nullable=False)
    description: Mapped[Optional[str]] = Column(Text, nullable=True)
    
    # Storage Info
    file_path: Mapped[Optional[str]] = Column(String, nullable=True)  # Local file path (not used with Cloudinary)
    video_url: Mapped[Optional[str]] = Column(String, nullable=True)  # URL for streaming
    thumbnail_url: Mapped[Optional[str]] = Column(String, nullable=True)
    duration: Mapped[Optional[int]] = Column(Integer, nullable=True)

    # TFT specific (optional)
    game_version: Mapped[Optional[str]] = Column(String(20), nullable=True)  # TFT patch
    composition: Mapped[Optional[List[str]]] = Column(ARRAY(String), nullable=True)  # Team comp used
    rank: Mapped[Optional[str]] = Column(String(20), nullable=True)  # Rank of the team
    result: Mapped[Optional[str]] = Column(String(20), nullable=True)  # Result of the game

    # Metadata
    views: Mapped[int] = Column(Integer, default=0)
    visibility: Mapped[VideoVisibility] = Column(SQLAlchemyEnum(VideoVisibility), default=VideoVisibility.PRIVATE)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="videos")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="video", cascade="all, delete-orphan")
    
    
    