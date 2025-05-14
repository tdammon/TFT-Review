from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class EventBase(BaseModel):
    """Base event attributes"""
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    video_timestamp: int = Field(..., ge=0)  # Timestamp in seconds
    event_type: str = Field(..., min_length=1, max_length=50)
    tags: Optional[List[str]] = None

class EventCreate(EventBase):
    """Schema for creating a new event"""
    video_id: uuid.UUID

class EventUpdate(BaseModel):
    """Schema for updating event"""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    video_timestamp: Optional[int] = Field(None, ge=0)
    event_type: Optional[str] = Field(None, min_length=1, max_length=50)
    tags: Optional[List[str]] = None

class EventInDB(EventBase):
    """Schema for event as stored in database"""
    id: uuid.UUID
    user_id: uuid.UUID
    video_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EventResponse(BaseModel):
    """Schema for event responses"""
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    video_timestamp: int
    event_type: str
    tags: Optional[List[str]] = None
    user_id: uuid.UUID
    video_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    
    

