from sqlalchemy import Column, ForeignKey, Float, String
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.dialects.postgresql import UUID
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .user import User
    from .video import Video
    from .comment import Comment

from .base import Base


class Event(Base):
    id: Mapped[str] = Column(UUID(as_uuid=True), primary_key=True, index=True, default=Base.generate_uuid)
    user_id: Mapped[str] = Column(UUID(as_uuid=True), ForeignKey("user.id"))
    video_id: Mapped[str] = Column(UUID(as_uuid=True), ForeignKey("video.id"))
    video_timestamp: Mapped[float] = Column(Float, nullable=False)
    title: Mapped[str] = Column(String(100), nullable=False)
    description: Mapped[str] = Column(String(500), nullable=True)
    event_type: Mapped[str] = Column(String(50), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="events")
    video: Mapped["Video"] = relationship("Video", back_populates="events")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="event", cascade="all, delete-orphan")