from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class EventBase(BaseModel):
    """Base event attributes"""
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    video_timestamp: float = Field(..., ge=0.1)  # Timestamp in seconds, minimum 0.1s
    event_type: Optional[str] = Field(None, min_length=1, max_length=50)

class EventCreate(EventBase):
    """Schema for creating a new event"""
    video_id: uuid.UUID

class EventUpdate(BaseModel):
    """Schema for updating event"""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    video_timestamp: float = Field(None, ge=0.1)  # Minimum 0.1s
    event_type: Optional[str] = Field(None, min_length=1, max_length=50)

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
    video_timestamp: float
    event_type: Optional[str] = None
    user_id: uuid.UUID
    video_id: uuid.UUID
    user_username: str
    user_profile_picture: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    
    

