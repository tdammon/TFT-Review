from sqlalchemy import Column, Integer, String, ForeignKey, ARRAY, Float, DateTime
from sqlalchemy.orm import relationship, Mapped
from typing import List, TYPE_CHECKING, Optional
from datetime import datetime

if TYPE_CHECKING:
    from .user import User
    from .video import Video

from .base import Base

class Comment(Base):
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("user.id"))
    video_id: Mapped[int] = Column(Integer, ForeignKey("video.id"))
    parent_id: Mapped[Optional[int]] = Column(Integer, ForeignKey("comment.id"), nullable=True)
    content: Mapped[str] = Column(String, nullable=False)
    
    # Timestamp indicating the position in the video (in seconds) where the comment refers to
    # Should only be set for top-level comments (parent_id is None)
    video_timestamp: Mapped[Optional[float]] = Column(Float, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="comments")
    video: Mapped["Video"] = relationship("Video", back_populates="comments")
    
    # Self-referential relationship
    parent: Mapped[Optional["Comment"]] = relationship(
        "Comment", 
        remote_side=[id],  # This defines which side is the "parent"
        back_populates="replies",
        foreign_keys=[parent_id]
    )
    replies: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="parent",
        foreign_keys=[parent_id],
        cascade="all, delete-orphan"
    )
    
    @property
    def effective_timestamp(self) -> Optional[float]:
        """
        Returns the effective timestamp for this comment.
        For top-level comments, this is their own timestamp.
        For replies, it returns the parent comment's timestamp.
        """
        if self.parent_id is None:
            return self.video_timestamp
        elif self.parent is not None:
            return self.parent.effective_timestamp
        return None

# Helper functions for route-level validation
def validate_comment_data(parent_id: Optional[int], video_timestamp: Optional[float]) -> dict:
    """
    Validates comment data according to our business rules:
    - Top-level comments (no parent_id) must have a video_timestamp
    - Reply comments (with parent_id) should not have a video_timestamp
    
    Returns:
        dict: Cleaned/validated data or raises ValueError with explanation
    """
    errors = {}
    
    # Handle top-level comments
    if parent_id is None:
        if video_timestamp is None:
            errors["video_timestamp"] = "Top-level comments must have a timestamp"
    # Handle replies
    else:
        if video_timestamp is not None:
            # For replies, we ignore the timestamp rather than error
            video_timestamp = None
    
    if errors:
        raise ValueError(errors)
        
    return {
        "parent_id": parent_id,
        "video_timestamp": video_timestamp
    }
    