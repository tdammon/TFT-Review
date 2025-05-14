from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json
import os
import uuid
import shutil
from datetime import datetime

from ..db.database import get_db
from ..models.comment import Comment
from ..models.user import User
from ..models.video import Video, VideoVisibility
from ..models.event import Event
from ..schemas.video import VideoCreate, VideoResponse, VideoDetailResponse
from ..schemas.comment import CommentCreate, CommentUpdate, CommentResponse
from ..schemas.event import EventResponse
from ..auth import get_current_user
from ..services.storage import upload_to_cloud_storage
from ..services.thumbnail import generate_thumbnail

router = APIRouter(
    prefix="/videos",
    tags=["videos"]
)

# Create upload directory if it doesn't exist
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=VideoResponse)
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    visibility: VideoVisibility = Form(VideoVisibility.PRIVATE),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a new video file.
    The video will be stored on Cloudinary and a record will be created in the database.
    """
    # Validate file type
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video")
    
    try:
        # Upload to Cloudinary
        video_url = await upload_to_cloud_storage(file)
        
        # Generate thumbnail
        thumbnail_url = await generate_thumbnail(video_url)
        
        # Create video record in database
        new_video = Video(
            title=title,
            description=description,
            file_path="",  # Not needed with Cloudinary
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            visibility=visibility,
            user_id=current_user.id
        )
        
        db.add(new_video)
        db.commit()
        db.refresh(new_video)
        
        return new_video
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload video: {str(e)}")

@router.get("/", response_model=List[VideoResponse])
async def get_videos(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    print('running')
    """Get a list of videos accessible to the current user"""
    # Get public videos and user's own videos
    videos = db.query(Video).filter(
        (Video.visibility == VideoVisibility.PUBLIC) | 
        (Video.user_id == current_user.id)
    ).offset(skip).limit(limit).all()
    
    return videos

@router.get("/my-videos", response_model=List[VideoResponse])
async def get_my_videos(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get videos uploaded by the current user"""
    videos = db.query(Video).filter(Video.user_id == current_user.id).offset(skip).limit(limit).all()
    return videos

@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific video by ID with its comments and events"""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if user has access to this video
    if video.visibility != VideoVisibility.PUBLIC and video.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have access to this video")
    
    # Get comments for this video
    comments = db.query(Comment).options(joinedload(Comment.user)).filter(Comment.video_id == video_id).all()
    comment_responses = []
    for comment in comments:
      # Get the username from the user relationship
      user_username = comment.user.username if comment.user else "Unknown"
      user_profile_picture = comment.user.profile_picture if comment.user else None
    
      # Create a CommentResponse object
      comment_response = CommentResponse(
        id=comment.id,
        content=comment.content,
        user_username=user_username,
        user_profile_picture=user_profile_picture,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        parent_id=comment.parent_id,
        event_id=comment.event_id,
        video_timestamp=comment.video_timestamp
      )
      comment_responses.append(comment_response)
    
    # Get events for this video
    events = db.query(Event).options(joinedload(Event.user)).filter(Event.video_id == video_id).all()
    event_responses = []
    for event in events:
      # Get the username from the user relationship
      user_username = event.user.username if event.user else "Unknown"
      user_profile_picture = event.user.profile_picture if event.user else None
    
      # Create an EventResponse object
      event_response = EventResponse(
        id=event.id,
        title=event.title,
        user_username=user_username,
        user_profile_picture=user_profile_picture,
        created_at=event.created_at,
        updated_at=event.updated_at,
        video_timestamp=event.video_timestamp
      )
      event_responses.append(event_response)
    
    video_data = VideoResponse.from_orm(video)
    # Create the detailed response with comments and events
    return VideoDetailResponse(
        **video_data.model_dump(),
        comments=comment_responses,
        events=event_responses
    )

@router.delete("/{video_id}", status_code=204)
async def delete_video(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized to delete this video")
    
    db.delete(video)
    db.commit()
    return {"message": "Video deleted successfully"}

@router.get("/{video_id}/stream")
async def stream_video(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the streaming URL for a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if user has access to this video
    if video.visibility != VideoVisibility.PUBLIC and video.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have access to this video")
    
    if not video.video_url:
        raise HTTPException(status_code=404, detail="Video URL not found")
    
    # Increment view count
    video.views += 1
    db.commit()
    
    # Return the streaming URL
    return {"url": video.video_url}


