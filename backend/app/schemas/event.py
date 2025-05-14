from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EventBase(BaseModel):
    """Base event attributes"""
    title: str = Field(..., min_length=1, max_length=100)  
    video_id: int
    

class EventCreate(EventBase):
    """Schema for creating a new event"""
    video_timestamp: float
    pass

class EventUpdate(EventBase):
    """Schema for updating an event"""
    title: Optional[str] = Field(None, max_length=100)
    video_timestamp: Optional[float] = None
    pass

class EventInDB(EventBase):
    """Schema for event as stored in database"""
    id: int 
    user_id: int
    video_id: int
    video_timestamp: float
    title: str
    created_at: datetime
    updated_at: datetime

class EventResponse(BaseModel):
    """Schema for comment responses, including user info"""
    id: int
    title: str
    user_username: Optional[str] = None  # Just the username for display
    user_profile_picture: Optional[str] = None  # Maybe useful for UI
    created_at: datetime
    updated_at: datetime
    video_timestamp: float # Timestamp in the video where the event refers to
    class Config:
        from_attributes = True

    
    

