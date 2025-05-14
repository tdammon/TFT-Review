from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CommentBase(BaseModel):
    """Base comment attributes"""
    content: str = Field(..., min_length=1, max_length=1000)  # Prevent empty/huge comments

class CommentCreate(CommentBase):
    """Schema for creating a new comment"""
    video_id: int  # Which video this comment is for
    parent_id: Optional[int] = None  # ID of the parent comment (for nested comments)

class CommentUpdate(BaseModel):
    """Schema for updating a comment"""
    content: str = Field(..., min_length=1, max_length=1000)  # Only content can be updated

class CommentInDB(CommentBase):
    """Schema for comment as stored in database"""
    id: int
    user_id: int
    video_id: int
    parent_id: Optional[int] = None  # ID of the parent comment (for nested comments)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CommentResponse(BaseModel):
    """Schema for comment responses, including user info"""
    id: int
    content: str
    user_username: str  # Just the username for display
    user_profile_picture: Optional[str] = None  # Maybe useful for UI
    created_at: datetime
    updated_at: datetime
    parent_id: Optional[int] = None  # ID of the parent comment (for nested comments)
    video_timestamp: float # Timestamp in the video where the comment refers to
    class Config:
        from_attributes = True
