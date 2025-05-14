from sqlalchemy import Column, Integer, ForeignKey, Float, String
from sqlalchemy.orm import  Mapped, relationship
from typing import  TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User
    from .video import Video

from .base import Base


class Event(Base):
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("user.id"))
    video_id: Mapped[int] = Column(Integer, ForeignKey("video.id"))
    video_timestamp: Mapped[float] = Column(Float, nullable=False)
    title: Mapped[str] = Column(String(100), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="events")
    video: Mapped["Video"] = relationship("Video", back_populates="events")