from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict
import json
import os
import uuid
import shutil
from datetime import datetime
import time
import asyncio
import io
import tempfile
import psutil
import math

from ..db.database import get_db
from ..models.comment import Comment
from ..models.user import User
from ..models.video import Video, VideoVisibility
from ..models.event import Event
from ..schemas.video import (
    VideoCreate, VideoResponse, VideoDetailResponse, VideoUpdate,
    ChunkedUploadInit, ChunkedUploadInitResponse, ChunkedUploadComplete,
    ChunkedUploadStatus
)
from ..schemas.comment import CommentCreate, CommentUpdate, CommentResponse
from ..schemas.event import EventResponse
from ..auth import get_current_user
# from ..services.storage import upload_to_cloud_storage  # Old Cloudinary service
from ..services.wasabi_storage import wasabi_storage  # New Wasabi service
from ..services.thumbnail import generate_thumbnail, generate_thumbnail_from_file, generate_thumbnail_from_file_key

router = APIRouter(
    prefix="/videos",
    tags=["videos"]
)

# Create upload directory if it doesn't exist
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory storage for upload progress (in production, use Redis or database)
upload_progress = {}

# Storage for chunked upload progress
chunked_uploads = {}

def get_memory_usage():
    """Get current memory usage of the process"""
    process = psutil.Process(os.getpid())
    mem = process.memory_info()
    return {
        'rss': mem.rss / (1024 * 1024),  # RSS in MB
        'vms': mem.vms / (1024 * 1024),  # VMS in MB
    }

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
    print(f"[UPLOAD_START] File object type: {type(file.file)}")
    print(f"[UPLOAD_START] File size: {file.size if hasattr(file, 'size') else 'Unknown'}")
    
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
    Uses streaming with temporary files to avoid memory issues.
    """
    temp_file = None
    try:
        print(f"[UPLOAD_PROCESS] Processing upload {upload_id}")
        print(f"[UPLOAD_PROCESS] Initial file object state: {file.file.closed=}")
        
        # Log initial memory usage
        mem_start = get_memory_usage()
        print(f"[MEMORY] Initial memory usage: RSS={mem_start['rss']:.1f}MB, VMS={mem_start['vms']:.1f}MB")
        
        # Update progress
        upload_progress[upload_id]["status"] = "uploading_video"
        upload_progress[upload_id]["progress"] = 10
        
        # Read the entire file content first
        print(f"[UPLOAD_PROCESS] Reading file content")
        file_content = await file.read()
        total_size = len(file_content)
        print(f"[UPLOAD_PROCESS] Read {total_size} bytes")
        
        # Log memory after reading file
        mem_after_read = get_memory_usage()
        print(f"[MEMORY] After reading file: RSS={mem_after_read['rss']:.1f}MB, VMS={mem_after_read['vms']:.1f}MB")
        print(f"[MEMORY] Memory increase: RSS={mem_after_read['rss'] - mem_start['rss']:.1f}MB")
        
        # Create a SpooledTemporaryFile with a larger max_size
        temp_file = tempfile.SpooledTemporaryFile(max_size=10*1024*1024)  # 10MB before spilling to disk
        
        try:
            # Write content in chunks to show progress
            chunk_size = 8192  # 8KB chunks
            total_written = 0
            
            print(f"[UPLOAD_PROCESS] Writing to temporary file")
            
            while total_written < total_size:
                # Calculate chunk size
                current_chunk_size = min(chunk_size, total_size - total_written)
                # Write chunk
                chunk = file_content[total_written:total_written + current_chunk_size]
                temp_file.write(chunk)
                total_written += current_chunk_size
                
                # Update progress
                progress = min(30, 10 + (total_written / (1024 * 1024)))
                upload_progress[upload_id]["progress"] = progress
            
            print(f"[UPLOAD_PROCESS] All data written to temp file: {total_written} bytes")
            
            # Log memory after writing to temp file
            mem_after_write = get_memory_usage()
            print(f"[MEMORY] After writing to temp file: RSS={mem_after_write['rss']:.1f}MB, VMS={mem_after_write['vms']:.1f}MB")
            
            # Reset file pointer for reading
            temp_file.flush()
            temp_file.seek(0)
            
            print(f"[UPLOAD_PROCESS] Temp file ready for upload")
            
            # Create a file-like object that wraps our temporary file
            class TempFileWrapper:
                def __init__(self, temp_file, filename: str, content_type: str):
                    self.temp_file = temp_file
                    self.filename = filename
                    self.content_type = content_type
                    
                async def seek(self, position: int):
                    self.temp_file.seek(position)
                    
                async def read(self, size: int = -1):
                    return self.temp_file.read(size)
                
                @property
                def file(self):
                    return self.temp_file
                
                def close(self):
                    try:
                        self.temp_file.close()
                    except:
                        pass
            
            # Create wrapper around our temp file
            temp_upload = TempFileWrapper(temp_file, file.filename, file.content_type)
            
            # Upload to Wasabi
            upload_start = time.time()
            try:
                file_key = await wasabi_storage.upload_video(temp_upload)
                upload_duration = time.time() - upload_start
                print(f"[UPLOAD_PROCESS] Upload {upload_id} completed in {upload_duration:.2f}s")
                
                # Log memory after Wasabi upload
                mem_after_upload = get_memory_usage()
                print(f"[MEMORY] After Wasabi upload: RSS={mem_after_upload['rss']:.1f}MB, VMS={mem_after_upload['vms']:.1f}MB")
            except Exception as e:
                print(f"[UPLOAD_PROCESS] Wasabi upload failed for {upload_id}: {str(e)}")
                raise e
            finally:
                temp_upload.close()
            
            # Update progress
            upload_progress[upload_id]["file_key"] = file_key
            upload_progress[upload_id]["status"] = "generating_thumbnail"
            upload_progress[upload_id]["progress"] = 70
            
            # Generate thumbnail
            try:
                print(f"[UPLOAD_PROCESS] Starting thumbnail generation for {upload_id}")
                
                # Create new temporary file for thumbnail generation
                thumb_temp_file = tempfile.SpooledTemporaryFile(max_size=10*1024*1024)
                thumb_temp_file.write(file_content)  # Write the content we already have
                thumb_temp_file.seek(0)
                
                # Create wrapper for thumbnail generation
                thumb_upload = TempFileWrapper(thumb_temp_file, file.filename, file.content_type)
                
                try:
                    thumbnail_key = await generate_thumbnail_from_file(thumb_upload)
                    
                    # Log memory after thumbnail generation
                    mem_after_thumb = get_memory_usage()
                    print(f"[MEMORY] After thumbnail generation: RSS={mem_after_thumb['rss']:.1f}MB, VMS={mem_after_thumb['vms']:.1f}MB")
                finally:
                    thumb_upload.close()
                
                upload_progress[upload_id]["thumbnail_key"] = thumbnail_key
                print(f"[UPLOAD_PROCESS] Thumbnail generation completed for {upload_id}")
            except Exception as e:
                print(f"[UPLOAD_PROCESS] Thumbnail generation failed for {upload_id}: {str(e)}")
                import traceback
                print(f"[UPLOAD_PROCESS] Thumbnail error traceback: {traceback.format_exc()}")
                # Continue without thumbnail - not critical
                upload_progress[upload_id]["thumbnail_key"] = None
            
            # Update final progress
            upload_progress[upload_id]["status"] = "completed"
            upload_progress[upload_id]["progress"] = 100
            upload_progress[upload_id]["completed_at"] = time.time()
            
            print(f"[UPLOAD_PROCESS] Upload {upload_id} fully completed")
            
            # Log final memory usage
            mem_final = get_memory_usage()
            print(f"[MEMORY] Final memory usage: RSS={mem_final['rss']:.1f}MB, VMS={mem_final['vms']:.1f}MB")
            print(f"[MEMORY] Total memory increase: RSS={mem_final['rss'] - mem_start['rss']:.1f}MB")
            
        except Exception as e:
            print(f"[UPLOAD_PROCESS] Error in file processing: {str(e)}")
            print(f"[UPLOAD_PROCESS] Error type: {type(e)}")
            import traceback
            print(f"[UPLOAD_PROCESS] Traceback: {traceback.format_exc()}")
            raise e
        
    except Exception as e:
        print(f"[UPLOAD_PROCESS] Error in upload {upload_id}: {str(e)}")
        import traceback
        print(f"[UPLOAD_PROCESS] Error traceback: {traceback.format_exc()}")
        upload_progress[upload_id]["status"] = "error"
        upload_progress[upload_id]["error"] = str(e)
        upload_progress[upload_id]["progress"] = 0
        
    finally:
        # Clean up temporary file
        if temp_file:
            try:
                temp_file.close()
            except:
                pass
        
        # Log memory after cleanup
        mem_cleanup = get_memory_usage()
        print(f"[MEMORY] After cleanup: RSS={mem_cleanup['rss']:.1f}MB, VMS={mem_cleanup['vms']:.1f}MB")

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
        asyncio.create_task(generate_thumbnail_async(new_video.id, file_key))
        
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

async def generate_thumbnail_async(video_id: uuid.UUID, file_key: str):
    """
    Generate thumbnail asynchronously in the background and update the database.
    This doesn't block the main upload response.
    """
    try:
        print(f"[THUMBNAIL_ASYNC] Starting background thumbnail generation for video {video_id}")
        
        # Generate thumbnail from the file key
        thumbnail_key = await generate_thumbnail_from_file_key(file_key)
        
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
    This prevents orphaned files in Wasabi when users exit before completing.
    """
    if upload_id not in upload_progress:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    progress = upload_progress[upload_id]
    
    # Check if user owns this upload
    if progress["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Clean up uploaded file from Wasabi if it exists
    file_key = progress.get("file_key")
    thumbnail_key = progress.get("thumbnail_key")
    
    cleanup_tasks = []
    
    if file_key:
        print(f"[UPLOAD_CANCEL] Cleaning up video file from Wasabi: {file_key}")
        try:
            # Delete the video file from Wasabi
            await wasabi_storage.delete_video(file_key)
            print(f"[UPLOAD_CANCEL] Successfully deleted video file: {file_key}")
        except Exception as e:
            print(f"[UPLOAD_CANCEL] Error deleting video file {file_key}: {str(e)}")
    
    if thumbnail_key:
        print(f"[UPLOAD_CANCEL] Cleaning up thumbnail file from Wasabi: {thumbnail_key}")
        try:
            # Delete the thumbnail file from Wasabi
            await wasabi_storage.delete_video(thumbnail_key)  # Same method works for any file
            print(f"[UPLOAD_CANCEL] Successfully deleted thumbnail file: {thumbnail_key}")
        except Exception as e:
            print(f"[UPLOAD_CANCEL] Error deleting thumbnail file {thumbnail_key}: {str(e)}")
    
    # Clean up from memory
    del upload_progress[upload_id]
    
    return {"message": "Upload cancelled and resources cleaned up successfully"}

@router.get("/cleanup-uploads")
async def cleanup_old_uploads(current_user: User = Depends(get_current_user)):
    """
    Clean up uploads older than 1 hour and their associated Wasabi files.
    This prevents orphaned files from abandoned uploads.
    In production, this should be a background task.
    """
    current_time = time.time()
    old_uploads = []
    cleanup_summary = {
        "cleaned_uploads": 0,
        "deleted_video_files": 0,
        "deleted_thumbnail_files": 0,
        "errors": []
    }
    
    for upload_id, progress in list(upload_progress.items()):
        # Remove uploads older than 1 hour
        if current_time - progress["started_at"] > 3600:
            print(f"[CLEANUP] Processing old upload: {upload_id}")
            
            # Clean up files from Wasabi
            file_key = progress.get("file_key")
            thumbnail_key = progress.get("thumbnail_key")
            
            if file_key:
                try:
                    await wasabi_storage.delete_video(file_key)
                    cleanup_summary["deleted_video_files"] += 1
                    print(f"[CLEANUP] Deleted video file: {file_key}")
                except Exception as e:
                    error_msg = f"Failed to delete video file {file_key}: {str(e)}"
                    cleanup_summary["errors"].append(error_msg)
                    print(f"[CLEANUP] {error_msg}")
            
            if thumbnail_key:
                try:
                    await wasabi_storage.delete_video(thumbnail_key)
                    cleanup_summary["deleted_thumbnail_files"] += 1
                    print(f"[CLEANUP] Deleted thumbnail file: {thumbnail_key}")
                except Exception as e:
                    error_msg = f"Failed to delete thumbnail file {thumbnail_key}: {str(e)}"
                    cleanup_summary["errors"].append(error_msg)
                    print(f"[CLEANUP] {error_msg}")
            
            old_uploads.append(upload_id)
            del upload_progress[upload_id]
            cleanup_summary["cleaned_uploads"] += 1
    
    cleanup_summary["upload_ids"] = old_uploads
    
    return {
        "message": f"Cleaned up {len(old_uploads)} old uploads and associated files",
        "summary": cleanup_summary
    }

@router.post("/initiate-chunked-upload", response_model=ChunkedUploadInitResponse)
async def initiate_chunked_upload(
    upload_info: ChunkedUploadInit,
    current_user: User = Depends(get_current_user)
):
    """
    Initiate a chunked upload and get presigned URLs for each chunk.
    """
    try:
        # Generate unique upload ID
        upload_id = str(uuid.uuid4())
        
        # Calculate number of chunks
        total_chunks = math.ceil(upload_info.total_size / upload_info.chunk_size)
        
        # Generate unique filename
        file_extension = os.path.splitext(upload_info.filename)[1].lower()
        if not file_extension:
            file_extension = '.mp4'  # Default extension
        unique_filename = f"videos/{upload_id}{file_extension}"
        
        print(f"[CHUNKED_UPLOAD] Initiating upload {upload_id}")
        print(f"[CHUNKED_UPLOAD] File: {upload_info.filename} -> {unique_filename}")
        print(f"[CHUNKED_UPLOAD] Size: {upload_info.total_size} bytes")
        print(f"[CHUNKED_UPLOAD] Chunks: {total_chunks} ({upload_info.chunk_size} bytes each)")
        
        # Initiate multipart upload in Wasabi
        multipart_upload = await wasabi_storage.create_multipart_upload(
            unique_filename,
            upload_info.content_type
        )
        
        # Get presigned URLs for each chunk
        presigned_urls = await wasabi_storage.get_chunk_upload_urls(
            unique_filename,
            multipart_upload['UploadId'],
            total_chunks
        )
        
        # Store upload information
        chunked_uploads[upload_id] = {
            "status": "initialized",
            "started_at": time.time(),
            "filename": upload_info.filename,
            "content_type": upload_info.content_type,
            "total_size": upload_info.total_size,
            "chunk_size": upload_info.chunk_size,
            "total_chunks": total_chunks,
            "uploaded_chunks": set(),
            "file_key": unique_filename,
            "wasabi_upload_id": multipart_upload['UploadId'],
            "user_id": current_user.id,
            "etags": {},
            "error": None
        }
        
        return ChunkedUploadInitResponse(
            upload_id=upload_id,
            chunk_size=upload_info.chunk_size,
            total_chunks=total_chunks,
            presigned_urls=presigned_urls
        )
        
    except Exception as e:
        print(f"[CHUNKED_UPLOAD] Error initiating upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate upload: {str(e)}")

@router.post("/complete-chunked-upload")
async def complete_chunked_upload(
    completion_info: ChunkedUploadComplete,
    current_user: User = Depends(get_current_user)
):
    """
    Complete a chunked upload after all chunks have been uploaded.
    """
    try:
        print(f"[CHUNKED_UPLOAD_COMPLETE] Received completion info: {completion_info}")
        print(f"[CHUNKED_UPLOAD_COMPLETE] ETags type: {type(completion_info.etags)}")
        print(f"[CHUNKED_UPLOAD_COMPLETE] ETags keys: {list(completion_info.etags.keys())}")
        print(f"[CHUNKED_UPLOAD_COMPLETE] ETags values: {list(completion_info.etags.values())}")
        print(f"[CHUNKED_UPLOAD_COMPLETE] ETags key types: {[type(k) for k in completion_info.etags.keys()]}")
        print(f"[CHUNKED_UPLOAD_COMPLETE] ETags value types: {[type(v) for v in completion_info.etags.values()]}")
        
        upload_id = completion_info.upload_id
        if upload_id not in chunked_uploads:
            print(f"[CHUNKED_UPLOAD_COMPLETE] Upload {upload_id} not found in chunked_uploads")
            print(f"[CHUNKED_UPLOAD_COMPLETE] Available uploads: {list(chunked_uploads.keys())}")
            raise HTTPException(status_code=404, detail="Upload not found")
        
        upload_info = chunked_uploads[upload_id]
        print(f"[CHUNKED_UPLOAD_COMPLETE] Upload info: {upload_info}")
        
        # Verify user owns this upload
        if upload_info["user_id"] != current_user.id:
            print(f"[CHUNKED_UPLOAD_COMPLETE] User {current_user.id} not authorized for upload {upload_id}")
            raise HTTPException(status_code=403, detail="Not authorized to complete this upload")
        
        # Verify all chunks are present
        if len(completion_info.etags) != upload_info["total_chunks"]:
            print(f"[CHUNKED_UPLOAD_COMPLETE] Chunk count mismatch:")
            print(f"  Expected: {upload_info['total_chunks']}")
            print(f"  Received: {len(completion_info.etags)}")
            print(f"  ETags: {completion_info.etags}")
            raise HTTPException(
                status_code=400,
                detail=f"Missing chunks. Expected {upload_info['total_chunks']}, got {len(completion_info.etags)}"
            )
        
        print(f"[CHUNKED_UPLOAD_COMPLETE] Completing upload {upload_id}")
        
        # Complete multipart upload in Wasabi
        try:
            file_key = await wasabi_storage.complete_multipart_upload(
                upload_info["file_key"],
                upload_info["wasabi_upload_id"],
                completion_info.etags
            )
            
            print(f"[CHUNKED_UPLOAD_COMPLETE] Upload completed: {file_key}")
            
            # Update upload status
            upload_info["status"] = "completed"
            upload_info["completed_at"] = time.time()
            
            return {"status": "success", "file_key": file_key}
            
        except Exception as e:
            print(f"[CHUNKED_UPLOAD_COMPLETE] Error completing upload: {str(e)}")
            print(f"[CHUNKED_UPLOAD_COMPLETE] Error type: {type(e)}")
            import traceback
            print(f"[CHUNKED_UPLOAD_COMPLETE] Traceback: {traceback.format_exc()}")
            
            # Attempt to abort the multipart upload
            try:
                await wasabi_storage.abort_multipart_upload(
                    upload_info["file_key"],
                    upload_info["wasabi_upload_id"]
                )
            except Exception as abort_error:
                print(f"[CHUNKED_UPLOAD_COMPLETE] Error aborting upload: {str(abort_error)}")
            
            raise HTTPException(status_code=500, detail=f"Failed to complete upload: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"[CHUNKED_UPLOAD_COMPLETE] Unexpected error: {str(e)}")
        print(f"[CHUNKED_UPLOAD_COMPLETE] Error type: {type(e)}")
        import traceback
        print(f"[CHUNKED_UPLOAD_COMPLETE] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/chunked-upload-status/{upload_id}", response_model=ChunkedUploadStatus)
async def get_chunked_upload_status(
    upload_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of a chunked upload.
    """
    if upload_id not in chunked_uploads:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    upload_info = chunked_uploads[upload_id]
    
    # Verify user owns this upload
    if upload_info["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this upload")
    
    # Calculate progress
    total_chunks = upload_info["total_chunks"]
    uploaded_chunks = list(upload_info["uploaded_chunks"])
    remaining_chunks = [i for i in range(1, total_chunks + 1) if i not in upload_info["uploaded_chunks"]]
    progress = (len(uploaded_chunks) / total_chunks) * 100 if total_chunks > 0 else 0
    
    return ChunkedUploadStatus(
        upload_id=upload_id,
        status=upload_info["status"],
        progress=progress,
        uploaded_chunks=uploaded_chunks,
        remaining_chunks=remaining_chunks,
        error=upload_info.get("error")
    )

@router.post("/complete-chunked-upload-details", response_model=VideoResponse)
async def complete_chunked_upload_details(
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
    Complete a chunked upload by creating the database record with game details.
    This is called after the chunks have been uploaded and combined.
    """
    print(f"[CHUNKED_UPLOAD_DETAILS] Completing upload {upload_id}")
    
    if upload_id not in chunked_uploads:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    upload_info = chunked_uploads[upload_id]
    
    # Check if user owns this upload
    if upload_info["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to complete this upload")
    
    # Check if upload is completed
    if upload_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="Upload is not completed")
    
    file_key = upload_info["file_key"]
    if not file_key:
        raise HTTPException(status_code=500, detail="Upload completed but no file key found")
    
    try:
        # Parse composition if provided
        composition_list = None
        if composition:
            composition_list = [item.strip() for item in composition.split(",") if item.strip()]
        
        # Create video record in database
        print(f"[CHUNKED_UPLOAD_DETAILS] Creating database record for upload {upload_id}")
        new_video = Video(
            title=title,
            description=description,
            file_path="",  # Not needed with Wasabi
            video_url=file_key,  # Store the file key
            thumbnail_url=None,  # Will be generated asynchronously
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
        
        # Clean up upload info
        del chunked_uploads[upload_id]
        
        # Generate fresh URLs for the response
        response_video = VideoResponse.model_validate(new_video)
        response_dict = response_video.model_dump()
        
        # Add fresh video URL
        if new_video.video_url:
            try:
                fresh_video_url = await wasabi_storage.get_video_url(new_video.video_url)
                response_dict["video_url"] = fresh_video_url
            except Exception as e:
                print(f"[CHUNKED_UPLOAD_DETAILS] Error generating fresh video URL: {str(e)}")
        
        # Start thumbnail generation in the background
        asyncio.create_task(generate_thumbnail_async(new_video.id, file_key))
        
        return VideoResponse.model_validate(response_dict)
        
    except Exception as e:
        print(f"[CHUNKED_UPLOAD_DETAILS] Error completing upload: {str(e)}")
        import traceback
        print(f"[CHUNKED_UPLOAD_DETAILS] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to complete upload: {str(e)}")


