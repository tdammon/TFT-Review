from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid
from .comment import CommentResponse
from .event import EventResponse

class VideoVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"

class VideoBase(BaseModel):
    """Base video attributes"""
    title: str = Field(..., max_length=100)
    description: Optional[str] = None
    visibility: VideoVisibility = VideoVisibility.PRIVATE

class VideoCreate(VideoBase):
    """Schema for creating a new video metadata"""
    pass

class VideoUpdate(BaseModel):
    """Schema for updating video metadata"""
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    game_version: Optional[str] = Field(None, max_length=20)
    composition: Optional[List[str]] = None
    rank: Optional[str] = Field(None, max_length=20)
    result: Optional[str] = Field(None, max_length=20)
    visibility: Optional[VideoVisibility] = None

class VideoInDB(VideoBase):
    """Schema for video as stored in database"""
    id: uuid.UUID
    user_id: uuid.UUID
    file_path: str
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None
    game_version: Optional[str] = None
    composition: Optional[List[str]] = None
    rank: Optional[str] = None
    result: Optional[str] = None
    views: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VideoResponse(BaseModel):
    """Schema for video responses"""
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    game_version: Optional[str] = None
    composition: Optional[List[str]] = None
    rank: Optional[str] = None
    result: Optional[str] = None
    views: int
    user_id: uuid.UUID
    user_username: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VideoDetailResponse(VideoResponse):
    """Schema for detailed video responses including comments and events"""
    comments: List[CommentResponse] = []
    events: List[EventResponse] = []

    class Config:
        from_attributes = True