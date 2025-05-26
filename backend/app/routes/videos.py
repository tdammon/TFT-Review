from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json
import os
import uuid
import shutil
from datetime import datetime
import time

from ..db.database import get_db
from ..models.comment import Comment
from ..models.user import User
from ..models.video import Video, VideoVisibility
from ..models.event import Event
from ..schemas.video import VideoCreate, VideoResponse, VideoDetailResponse, VideoUpdate
from ..schemas.comment import CommentCreate, CommentUpdate, CommentResponse
from ..schemas.event import EventResponse
from ..auth import get_current_user
# from ..services.storage import upload_to_cloud_storage  # Old Cloudinary service
from ..services.wasabi_storage import wasabi_storage  # New Wasabi service
from ..services.thumbnail import generate_thumbnail, generate_thumbnail_from_file

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
    game_version: Optional[str] = Form(None),
    rank: Optional[str] = Form(None),
    result: Optional[str] = Form(None),
    composition: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a new video file.
    The video will be stored on Wasabi and a record will be created in the database.
    """
    start_time = time.time()
    print(f"[VIDEO_UPLOAD] Starting upload at {time.time()}")
    print(f"[VIDEO_UPLOAD] User: {current_user.username if current_user else 'None'}")
    print(f"[VIDEO_UPLOAD] File: {file.filename}, Content-Type: {file.content_type}")
    print(f"[VIDEO_UPLOAD] Title: {title}")
    
    # Validate file type
    print(f"[VIDEO_UPLOAD] Validating file type...")
    if not file.content_type.startswith("video/"):
        print(f"[VIDEO_UPLOAD] Invalid file type: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be a video")
    
    try:
        print(f"[VIDEO_UPLOAD] Uploading to Wasabi...")
        upload_start = time.time()
        
        # Upload to Wasabi and get the file key
        file_key = await wasabi_storage.upload_video(file)
        
        upload_duration = time.time() - upload_start
        print(f"[VIDEO_UPLOAD] Wasabi upload completed in {upload_duration:.2f} seconds")
        print(f"[VIDEO_UPLOAD] Stored file key: {file_key}")
        
        # Generate thumbnail from the uploaded file
        print(f"[VIDEO_UPLOAD] Generating thumbnail...")
        thumbnail_start = time.time()
        thumbnail_url = await generate_thumbnail_from_file(file)
        thumbnail_end = time.time()
        if thumbnail_url:
            print(f"[VIDEO_UPLOAD] Thumbnail generated in {thumbnail_end - thumbnail_start:.2f}s")
        else:
            print(f"[VIDEO_UPLOAD] Thumbnail generation failed or skipped")
        
        # Parse composition if provided
        print(f"[VIDEO_UPLOAD] Parsing composition...")
        composition_list = None
        if composition:
            composition_list = [item.strip() for item in composition.split(",") if item.strip()]
        
        # Create video record in database with file key (not full URL)
        print(f"[VIDEO_UPLOAD] Creating database record...")
        db_start = time.time()
        new_video = Video(
            title=title,
            description=description,
            file_path="",  # Not needed with Wasabi
            video_url=file_key,  # Store the file key, not the full URL
            thumbnail_url=thumbnail_url,
            visibility=visibility,
            user_id=current_user.id,
            game_version=game_version,
            rank=rank,
            result=result,
            composition=composition_list
        )
        
        db.add(new_video)
        db.commit()
        db.refresh(new_video)
        
        db_end = time.time()
        print(f"[VIDEO_UPLOAD] Database operations completed in {db_end - db_start:.2f}s")
        
        total_time = time.time() - start_time
        print(f"[VIDEO_UPLOAD] Total upload completed in {total_time:.2f}s")
        
        # Generate fresh URLs for the response
        response_video = VideoResponse.model_validate(new_video)
        response_dict = response_video.model_dump()
        
        # Add fresh video URL
        if new_video.video_url:
            try:
                fresh_video_url = await wasabi_storage.get_video_url(new_video.video_url)
                response_dict["video_url"] = fresh_video_url
            except Exception as e:
                print(f"[VIDEO_UPLOAD] Error generating fresh video URL: {str(e)}")
        
        # Add fresh thumbnail URL
        if new_video.thumbnail_url:
            try:
                fresh_thumbnail_url = await wasabi_storage.get_video_url(new_video.thumbnail_url)
                response_dict["thumbnail_url"] = fresh_thumbnail_url
            except Exception as e:
                print(f"[VIDEO_UPLOAD] Error generating fresh thumbnail URL: {str(e)}")
        
        return VideoResponse.model_validate(response_dict)
        
    except Exception as e:
        error_time = time.time() - start_time
        print(f"[VIDEO_UPLOAD] Error after {error_time:.2f}s: {str(e)}")
        print(f"[VIDEO_UPLOAD] Exception type: {type(e).__name__}")
        import traceback
        print(f"[VIDEO_UPLOAD] Traceback: {traceback.format_exc()}")
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
    videos = db.query(Video).options(joinedload(Video.user)).filter(
        (Video.visibility == VideoVisibility.PUBLIC) | 
        (Video.user_id == current_user.id)
    ).offset(skip).limit(limit).all()
    
    # Generate fresh pre-signed URLs for all videos and thumbnails
    file_keys = [video.video_url for video in videos if video.video_url]
    thumbnail_keys = [video.thumbnail_url for video in videos if video.thumbnail_url]
    
    fresh_urls = await wasabi_storage.get_multiple_video_urls(file_keys) if file_keys else {}
    fresh_thumbnail_urls = await wasabi_storage.get_multiple_video_urls(thumbnail_keys) if thumbnail_keys else {}
    
    # Add username and fresh URLs to each video
    video_responses = []
    for video in videos:
        video_dict = VideoResponse.model_validate(video).model_dump()
        video_dict["user_username"] = video.user.username if video.user else "Unknown"
        # Replace stored file key with fresh pre-signed URL
        if video.video_url and video.video_url in fresh_urls:
            video_dict["video_url"] = fresh_urls[video.video_url]
        # Replace stored thumbnail key with fresh pre-signed URL
        if video.thumbnail_url and video.thumbnail_url in fresh_thumbnail_urls:
            video_dict["thumbnail_url"] = fresh_thumbnail_urls[video.thumbnail_url]
        video_responses.append(VideoResponse.model_validate(video_dict))
    
    return video_responses

@router.get("/my-videos", response_model=List[VideoResponse])
async def get_my_videos(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get videos uploaded by the current user"""
    videos = db.query(Video).filter(Video.user_id == current_user.id).offset(skip).limit(limit).all()
    
    # Generate fresh pre-signed URLs for all videos and thumbnails
    file_keys = [video.video_url for video in videos if video.video_url]
    thumbnail_keys = [video.thumbnail_url for video in videos if video.thumbnail_url]
    
    fresh_urls = await wasabi_storage.get_multiple_video_urls(file_keys) if file_keys else {}
    fresh_thumbnail_urls = await wasabi_storage.get_multiple_video_urls(thumbnail_keys) if thumbnail_keys else {}
    
    # Add username and fresh URLs to each video
    video_responses = []
    for video in videos:
        video_dict = VideoResponse.model_validate(video).model_dump()
        video_dict["user_username"] = current_user.username
        # Replace stored file key with fresh pre-signed URL
        if video.video_url and video.video_url in fresh_urls:
            video_dict["video_url"] = fresh_urls[video.video_url]
        # Replace stored thumbnail key with fresh pre-signed URL
        if video.thumbnail_url and video.thumbnail_url in fresh_thumbnail_urls:
            video_dict["thumbnail_url"] = fresh_thumbnail_urls[video.thumbnail_url]
        video_responses.append(VideoResponse.model_validate(video_dict))
    
    return video_responses

@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific video by ID with its comments and events"""
    video = db.query(Video).options(joinedload(Video.user)).filter(Video.id == video_id).first()
    
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
    events = db.query(Event).options(joinedload(Event.user)).filter(Event.video_id == video_id).order_by(Event.video_timestamp.asc()).all()
    event_responses = []
    for event in events:
      # Get the username from the user relationship
      user_username = event.user.username if event.user else "Unknown"
      user_profile_picture = event.user.profile_picture if event.user else None
    
      # Create an EventResponse object
      event_response = EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        event_type=event.event_type,
        user_id=event.user_id,
        video_id=event.video_id,
        user_username=user_username,
        user_profile_picture=user_profile_picture,
        created_at=event.created_at,
        updated_at=event.updated_at,
        video_timestamp=event.video_timestamp
      )
      event_responses.append(event_response)
    
    # Create video response with username and fresh URLs
    video_dict = VideoResponse.model_validate(video).model_dump()
    video_dict["user_username"] = video.user.username if video.user else "Unknown"
    
    # Generate fresh pre-signed URLs for video and thumbnail
    if video.video_url:
        try:
            fresh_video_url = await wasabi_storage.get_video_url(video.video_url)
            video_dict["video_url"] = fresh_video_url
        except Exception as e:
            print(f"[VIDEO_DETAIL] Error generating fresh video URL: {str(e)}")
            # Keep the original key as fallback
    
    if video.thumbnail_url:
        try:
            fresh_thumbnail_url = await wasabi_storage.get_video_url(video.thumbnail_url)
            video_dict["thumbnail_url"] = fresh_thumbnail_url
        except Exception as e:
            print(f"[VIDEO_DETAIL] Error generating fresh thumbnail URL: {str(e)}")
            # Keep the original key as fallback
    
    video_data = VideoResponse.model_validate(video_dict)
    
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
    
    # Generate fresh pre-signed URL from the stored file key
    try:
        print(f"[VIDEO_STREAM] Generating fresh pre-signed URL for: {video.video_url}")
        fresh_url = await wasabi_storage.get_video_url(video.video_url)
        print(f"[VIDEO_STREAM] Generated fresh URL")
        return {"url": fresh_url}
    except Exception as e:
        print(f"[VIDEO_STREAM] Error generating fresh URL: {str(e)}")
        # Fallback to stored URL (might be expired but better than nothing)
        return {"url": video.video_url}

@router.patch("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: uuid.UUID,
    video_data: VideoUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update video details"""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized to update this video")
    
    # Update video fields from the request data
    for key, value in video_data.model_dump(exclude_unset=True).items():
        setattr(video, key, value)
    
    db.commit()
    db.refresh(video)
    
    # Add username to the response
    video_dict = VideoResponse.model_validate(video).model_dump()
    video_dict["user_username"] = current_user.username
    
    return VideoResponse.model_validate(video_dict)


