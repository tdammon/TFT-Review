from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json
import os
import uuid
import shutil
from datetime import datetime
import time
import asyncio

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

# In-memory storage for upload progress (in production, use Redis or database)
upload_progress = {}

@router.post("/start-upload")
async def start_video_upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Start video upload immediately and return an upload ID.
    This allows the frontend to begin upload while user fills out details.
    """
    start_time = time.time()
    upload_id = str(uuid.uuid4())
    
    print(f"[UPLOAD_START] Starting upload {upload_id} at {time.time()}")
    print(f"[UPLOAD_START] User: {current_user.username}")
    print(f"[UPLOAD_START] File: {file.filename}, Content-Type: {file.content_type}")
    
    # Validate file type
    if not file.content_type.startswith("video/"):
        print(f"[UPLOAD_START] Invalid file type: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be a video")
    
    # Initialize upload progress
    upload_progress[upload_id] = {
        "status": "uploading",
        "progress": 0,
        "file_key": None,
        "thumbnail_key": None,
        "error": None,
        "user_id": current_user.id,
        "filename": file.filename,
        "content_type": file.content_type,
        "started_at": time.time()
    }
    
    # Start upload in background
    asyncio.create_task(process_video_upload(upload_id, file))
    
    return {
        "upload_id": upload_id,
        "status": "uploading",
        "message": "Video upload started. You can now fill out the details while upload continues."
    }

async def process_video_upload(upload_id: str, file: UploadFile):
    """
    Process the video upload in the background and update progress.
    """
    try:
        print(f"[UPLOAD_PROCESS] Processing upload {upload_id}")
        
        # Update progress
        upload_progress[upload_id]["status"] = "uploading_video"
        upload_progress[upload_id]["progress"] = 10
        
        # Upload to Wasabi
        upload_start = time.time()
        file_key = await wasabi_storage.upload_video(file)
        upload_duration = time.time() - upload_start
        
        print(f"[UPLOAD_PROCESS] Upload {upload_id} completed in {upload_duration:.2f}s")
        
        # Update progress
        upload_progress[upload_id]["file_key"] = file_key
        upload_progress[upload_id]["status"] = "generating_thumbnail"
        upload_progress[upload_id]["progress"] = 70
        
        # Generate thumbnail in background
        thumbnail_key = await generate_thumbnail_from_file(file)
        
        # Update final progress
        upload_progress[upload_id]["thumbnail_key"] = thumbnail_key
        upload_progress[upload_id]["status"] = "completed"
        upload_progress[upload_id]["progress"] = 100
        upload_progress[upload_id]["completed_at"] = time.time()
        
        print(f"[UPLOAD_PROCESS] Upload {upload_id} fully completed")
        
    except Exception as e:
        print(f"[UPLOAD_PROCESS] Error in upload {upload_id}: {str(e)}")
        upload_progress[upload_id]["status"] = "error"
        upload_progress[upload_id]["error"] = str(e)
        upload_progress[upload_id]["progress"] = 0

@router.get("/upload-status/{upload_id}")
async def get_upload_status(
    upload_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of an ongoing upload.
    """
    if upload_id not in upload_progress:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    progress = upload_progress[upload_id]
    
    # Check if user owns this upload
    if progress["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    return {
        "upload_id": upload_id,
        "status": progress["status"],
        "progress": progress["progress"],
        "error": progress.get("error"),
        "filename": progress["filename"]
    }

@router.post("/complete-upload", response_model=VideoResponse)
async def complete_video_upload(
    upload_id: str = Form(...),
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
    Complete the video upload by creating the database record with game details.
    This can be called while upload is still in progress - it will wait for completion.
    """
    start_time = time.time()
    print(f"[UPLOAD_COMPLETE] Completing upload {upload_id}")
    
    if upload_id not in upload_progress:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    progress = upload_progress[upload_id]
    
    # Check if user owns this upload
    if progress["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Wait for upload to complete if still in progress
    max_wait = 300  # 5 minutes max wait
    wait_start = time.time()
    
    while progress["status"] not in ["completed", "error"] and (time.time() - wait_start) < max_wait:
        print(f"[UPLOAD_COMPLETE] Waiting for upload {upload_id} to complete... Status: {progress['status']}")
        await asyncio.sleep(1)
    
    if progress["status"] == "error":
        error_msg = progress.get("error", "Unknown upload error")
        # Clean up
        del upload_progress[upload_id]
        raise HTTPException(status_code=500, detail=f"Upload failed: {error_msg}")
    
    if progress["status"] != "completed":
        raise HTTPException(status_code=408, detail="Upload timed out")
    
    file_key = progress["file_key"]
    thumbnail_key = progress.get("thumbnail_key")
    
    if not file_key:
        # Clean up
        del upload_progress[upload_id]
        raise HTTPException(status_code=500, detail="Upload completed but no file key found")
    
    try:
        # Parse composition if provided
        composition_list = None
        if composition:
            composition_list = [item.strip() for item in composition.split(",") if item.strip()]
        
        # Create video record in database
        print(f"[UPLOAD_COMPLETE] Creating database record for upload {upload_id}")
        new_video = Video(
            title=title,
            description=description,
            file_path="",  # Not needed with Wasabi
            video_url=file_key,  # Store the file key
            thumbnail_url=thumbnail_key,  # Store the thumbnail key
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
        
        # Clean up upload progress
        del upload_progress[upload_id]
        
        total_time = time.time() - start_time
        print(f"[UPLOAD_COMPLETE] Upload {upload_id} completed in {total_time:.2f}s")
        
        # Generate fresh URLs for the response
        response_video = VideoResponse.model_validate(new_video)
        response_dict = response_video.model_dump()
        
        # Add fresh video URL
        if new_video.video_url:
            try:
                fresh_video_url = await wasabi_storage.get_video_url(new_video.video_url)
                response_dict["video_url"] = fresh_video_url
            except Exception as e:
                print(f"[UPLOAD_COMPLETE] Error generating fresh video URL: {str(e)}")
        
        # Add fresh thumbnail URL
        if new_video.thumbnail_url:
            try:
                fresh_thumbnail_url = await wasabi_storage.get_video_url(new_video.thumbnail_url)
                response_dict["thumbnail_url"] = fresh_thumbnail_url
            except Exception as e:
                print(f"[UPLOAD_COMPLETE] Error generating fresh thumbnail URL: {str(e)}")
        
        return VideoResponse.model_validate(response_dict)
        
    except Exception as e:
        # Clean up on error
        if upload_id in upload_progress:
            del upload_progress[upload_id]
        
        error_time = time.time() - start_time
        print(f"[UPLOAD_COMPLETE] Error after {error_time:.2f}s: {str(e)}")
        import traceback
        print(f"[UPLOAD_COMPLETE] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to complete video upload: {str(e)}")

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
    Original upload endpoint - uploads video and creates record in one step.
    For better UX, use /start-upload and /complete-upload instead.
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
            thumbnail_url=None,  # Will be updated asynchronously
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
        
        # Start thumbnail generation in the background (don't wait for it)
        print(f"[VIDEO_UPLOAD] Starting background thumbnail generation...")
        asyncio.create_task(generate_thumbnail_async(file, new_video.id))
        
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
        
        # Thumbnail will be None initially, but will be generated in background
        response_dict["thumbnail_url"] = None
        
        return VideoResponse.model_validate(response_dict)
        
    except Exception as e:
        error_time = time.time() - start_time
        print(f"[VIDEO_UPLOAD] Error after {error_time:.2f}s: {str(e)}")
        print(f"[VIDEO_UPLOAD] Exception type: {type(e).__name__}")
        import traceback
        print(f"[VIDEO_UPLOAD] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to upload video: {str(e)}")

async def generate_thumbnail_async(file: UploadFile, video_id: uuid.UUID):
    """
    Generate thumbnail asynchronously in the background and update the database.
    This doesn't block the main upload response.
    """
    try:
        print(f"[THUMBNAIL_ASYNC] Starting background thumbnail generation for video {video_id}")
        
        # Generate thumbnail from the uploaded file
        thumbnail_key = await generate_thumbnail_from_file(file)
        
        if thumbnail_key:
            print(f"[THUMBNAIL_ASYNC] Thumbnail generated: {thumbnail_key}")
            
            # Create a new database session for this background task
            from ..db.database import SessionLocal
            db = SessionLocal()
            
            try:
                # Update the video record with the thumbnail
                video = db.query(Video).filter(Video.id == video_id).first()
                if video:
                    video.thumbnail_url = thumbnail_key
                    db.commit()
                    print(f"[THUMBNAIL_ASYNC] Updated video {video_id} with thumbnail")
                else:
                    print(f"[THUMBNAIL_ASYNC] Video {video_id} not found in database")
            finally:
                db.close()
        else:
            print(f"[THUMBNAIL_ASYNC] Thumbnail generation failed for video {video_id}")
            
    except Exception as e:
        print(f"[THUMBNAIL_ASYNC] Error in background thumbnail generation: {str(e)}")
        import traceback
        print(f"[THUMBNAIL_ASYNC] Traceback: {traceback.format_exc()}")

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

@router.delete("/upload/{upload_id}")
async def cancel_upload(
    upload_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Cancel an ongoing upload and clean up resources.
    """
    if upload_id not in upload_progress:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    progress = upload_progress[upload_id]
    
    # Check if user owns this upload
    if progress["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Clean up
    del upload_progress[upload_id]
    
    return {"message": "Upload cancelled successfully"}

@router.get("/cleanup-uploads")
async def cleanup_old_uploads(current_user: User = Depends(get_current_user)):
    """
    Clean up uploads older than 1 hour (for development/testing).
    In production, this should be a background task.
    """
    current_time = time.time()
    old_uploads = []
    
    for upload_id, progress in list(upload_progress.items()):
        # Remove uploads older than 1 hour
        if current_time - progress["started_at"] > 3600:
            old_uploads.append(upload_id)
            del upload_progress[upload_id]
    
    return {
        "message": f"Cleaned up {len(old_uploads)} old uploads",
        "cleaned_uploads": old_uploads
    }


