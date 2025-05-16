from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
import uuid

from ..models.event import Event
from ..models.video import Video
from ..models.user import User
from ..schemas.event import EventResponse, EventCreate, EventUpdate
from ..db.database import get_db
from ..auth import get_current_user

router = APIRouter(
    prefix="/events", 
    tags=["events"]
)

@router.get("/{video_id}", response_model=List[EventResponse])
async def get_events(
    video_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get all events for a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    events = db.query(Event).options(joinedload(Event.user)).filter(Event.video_id == video_id).order_by(Event.video_timestamp.asc()).all()
    
    # Create event responses with usernames
    event_responses = []
    for event in events:
        event_dict = {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "video_timestamp": event.video_timestamp,
            "event_type": event.event_type,
            "user_id": event.user_id,
            "video_id": event.video_id,
            "user_username": event.user.username if event.user else "Unknown",
            "user_profile_picture": event.user.profile_picture if event.user else None,
            "created_at": event.created_at,
            "updated_at": event.updated_at
        }
        event_responses.append(event_dict)
    
    return event_responses

@router.post("/", response_model=EventResponse)
async def create_event(
    event_data: EventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    print(event_data)
    """Create a new event"""
    video = db.query(Video).filter(Video.id == event_data.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized to create event for this video")
    
    event = Event(
        **event_data.model_dump(),
        user_id=current_user.id
    )

    db.add(event)
    db.commit()
    db.refresh(event)
    
    # Create response with username
    response = {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "video_timestamp": event.video_timestamp,
        "event_type": event.event_type,
        "user_id": event.user_id,
        "video_id": event.video_id,
        "user_username": current_user.username,
        "user_profile_picture": current_user.profile_picture,
        "created_at": event.created_at,
        "updated_at": event.updated_at
    }
    
    return response

@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: uuid.UUID,
    event_data: EventUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if not event.user_id == current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized to update this event")
    
    for key, value in event_data.model_dump(exclude_unset=True).items():
        setattr(event, key, value)
    
    db.commit()
    db.refresh(event)
    
    # Create response with username
    response = {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "video_timestamp": event.video_timestamp,
        "event_type": event.event_type,
        "user_id": event.user_id,
        "video_id": event.video_id,
        "user_username": current_user.username,
        "user_profile_picture": current_user.profile_picture,
        "created_at": event.created_at,
        "updated_at": event.updated_at
    }
    
    return response

@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if not event.user_id == current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized to delete this event")
    
    db.delete(event)
    db.commit()
    return {"message": "Event deleted successfully"}
        