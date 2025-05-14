from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class CommentBase(BaseModel):
    """Base comment attributes"""
    content: str = Field(..., min_length=1, max_length=1000)  # Prevent empty/huge comments
    timestamp: Optional[int] = None  # Video timestamp in seconds
    event_id: Optional[uuid.UUID] = None  # Link to an event

class CommentCreate(CommentBase):
    """Schema for creating a new comment"""
    video_id: uuid.UUID  # Which video this comment is for
    parent_id: Optional[uuid.UUID] = None  # ID of the parent comment (for nested comments)
    video_timestamp: Optional[float] = None  # Timestamp in the video

class CommentUpdate(BaseModel):
    """Schema for updating a comment"""
    content: Optional[str] = Field(None, min_length=1, max_length=1000)  # Only content can be updated

class CommentInDB(CommentBase):
    """Schema for comment as stored in database"""
    id: uuid.UUID
    user_id: uuid.UUID
    video_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None  # ID of the parent comment (for nested comments)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CommentResponse(BaseModel):
    """Schema for comment responses, including user info"""
    id: uuid.UUID
    content: str
    user_username: str  # Just the username for display
    user_profile_picture: Optional[str] = None  # Maybe useful for UI
    created_at: datetime
    updated_at: datetime
    parent_id: Optional[uuid.UUID] = None  # ID of the parent comment (for nested comments)
    event_id: Optional[uuid.UUID] = None  # Optional link to an event
    video_timestamp: Optional[float] = None  # Timestamp in the video where the comment refers to
    replies: List['CommentResponse'] = []
    effective_timestamp: Optional[int] = None

    class Config:
        from_attributes = True
