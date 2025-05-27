from fastapi import UploadFile
import ffmpeg
import os
import tempfile
import uuid
import asyncio
from functools import partial
from typing import Optional
from .wasabi_storage import wasabi_storage

async def generate_thumbnail(video_url: str) -> Optional[str]:
    """
    Generate thumbnail from video URL.
    
    Since we're using Wasabi (which doesn't have video processing),
    we'll return None for now. In the future, this could be enhanced to:
    1. Download the video temporarily
    2. Use FFmpeg to extract a frame
    3. Upload the thumbnail image to Wasabi
    4. Return the thumbnail URL
    
    For now, the frontend should handle missing thumbnails gracefully.
    """
    print(f"[THUMBNAIL] Skipping thumbnail generation for Wasabi video: {video_url}")
    print(f"[THUMBNAIL] Thumbnail generation not yet implemented for Wasabi storage")
    
    # Return None - frontend should show a default video placeholder
    return None

async def generate_thumbnail_from_file(video_file: UploadFile) -> Optional[str]:
    """
    Generate thumbnail directly from uploaded video file using FFmpeg.
    
    This extracts a frame at 1 second, saves it as a JPEG,
    uploads it to Wasabi, and returns the thumbnail URL.
    """
    try:
        print(f"[THUMBNAIL] Starting thumbnail generation for: {video_file.filename}")
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_thumb:
                temp_video_path = temp_video.name
                temp_thumb_path = temp_thumb.name
        
        try:
            # Reset file pointer and stream video to temp file (avoid loading entire file into memory)
            await video_file.seek(0)
            
            print(f"[THUMBNAIL] Streaming video to temporary file...")
            with open(temp_video_path, 'wb') as f:
                # Stream the file in chunks instead of reading all at once
                chunk_size = 1024 * 1024  # 1MB chunks
                while True:
                    chunk = await video_file.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
            
            # Reset file pointer for any subsequent operations
            try:
                await video_file.seek(0)
            except Exception as e:
                print(f"[THUMBNAIL] Warning: Could not reset file pointer: {e}")
                # Continue anyway, as the temp file has the data we need
            
            print(f"[THUMBNAIL] Extracting frame using FFmpeg...")
            
            # Extract frame at 1 second using FFmpeg
            loop = asyncio.get_event_loop()
            extract_func = partial(
                ffmpeg.input(temp_video_path, ss=1)
                .output(temp_thumb_path, vframes=1, format='image2', vcodec='mjpeg')
                .overwrite_output()
                .run,
                quiet=True
            )
            
            await loop.run_in_executor(None, extract_func)
            
            # Check if thumbnail was created
            if not os.path.exists(temp_thumb_path) or os.path.getsize(temp_thumb_path) == 0:
                print(f"[THUMBNAIL] Failed to extract frame")
                return None
            
            print(f"[THUMBNAIL] Frame extracted, uploading to Wasabi...")
            
            # Upload thumbnail to Wasabi (without ACL since public access not allowed)
            thumbnail_key = f"thumbnails/{uuid.uuid4()}.jpg"
            
            # Create a file-like object for upload
            with open(temp_thumb_path, 'rb') as thumb_file:
                upload_func = partial(
                    wasabi_storage.s3_client.upload_fileobj,
                    thumb_file,
                    wasabi_storage.bucket_name,
                    thumbnail_key,
                    ExtraArgs={
                        'ContentType': 'image/jpeg'
                        # Removed ACL since account doesn't allow public access
                    }
                )
                
                await loop.run_in_executor(None, upload_func)
            
            print(f"[THUMBNAIL] Thumbnail uploaded successfully, returning key: {thumbnail_key}")
            return thumbnail_key  # Return the key, not the full URL
            
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(temp_video_path):
                    os.unlink(temp_video_path)
                if os.path.exists(temp_thumb_path):
                    os.unlink(temp_thumb_path)
            except:
                pass
                
    except Exception as e:
        print(f"[THUMBNAIL] Error generating thumbnail: {str(e)}")
        return None
    
    finally:
        # Reset video file pointer if possible
        try:
            await video_file.seek(0)
        except Exception as e:
            print(f"[THUMBNAIL] Warning: Could not reset file pointer in finally block: {e}")
            # This is not critical, just log and continue

async def generate_thumbnail_from_file_key(file_key: str) -> Optional[str]:
    """
    Generate thumbnail from a video file stored in Wasabi.
    Downloads the video temporarily, generates the thumbnail, and uploads it back to Wasabi.
    """
    try:
        print(f"[THUMBNAIL] Starting thumbnail generation for file key: {file_key}")
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_thumb:
                temp_video_path = temp_video.name
                temp_thumb_path = temp_thumb.name
        
        try:
            # Download video from Wasabi
            print(f"[THUMBNAIL] Downloading video from Wasabi...")
            loop = asyncio.get_event_loop()
            download_func = partial(
                wasabi_storage.s3_client.download_file,
                wasabi_storage.bucket_name,
                file_key,
                temp_video_path
            )
            await loop.run_in_executor(None, download_func)
            
            print(f"[THUMBNAIL] Extracting frame using FFmpeg...")
            
            # Extract frame at 1 second using FFmpeg
            extract_func = partial(
                ffmpeg.input(temp_video_path, ss=1)
                .output(temp_thumb_path, vframes=1, format='image2', vcodec='mjpeg')
                .overwrite_output()
                .run,
                quiet=True
            )
            
            await loop.run_in_executor(None, extract_func)
            
            # Check if thumbnail was created
            if not os.path.exists(temp_thumb_path) or os.path.getsize(temp_thumb_path) == 0:
                print(f"[THUMBNAIL] Failed to extract frame")
                return None
            
            print(f"[THUMBNAIL] Frame extracted, uploading to Wasabi...")
            
            # Upload thumbnail to Wasabi
            thumbnail_key = f"thumbnails/{uuid.uuid4()}.jpg"
            
            # Create a file-like object for upload
            with open(temp_thumb_path, 'rb') as thumb_file:
                upload_func = partial(
                    wasabi_storage.s3_client.upload_fileobj,
                    thumb_file,
                    wasabi_storage.bucket_name,
                    thumbnail_key,
                    ExtraArgs={
                        'ContentType': 'image/jpeg'
                    }
                )
                
                await loop.run_in_executor(None, upload_func)
            
            print(f"[THUMBNAIL] Thumbnail uploaded successfully, returning key: {thumbnail_key}")
            return thumbnail_key
            
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(temp_video_path):
                    os.unlink(temp_video_path)
                if os.path.exists(temp_thumb_path):
                    os.unlink(temp_thumb_path)
            except:
                pass
                
    except Exception as e:
        print(f"[THUMBNAIL] Error generating thumbnail from file key: {str(e)}")
        import traceback
        print(f"[THUMBNAIL] Traceback: {traceback.format_exc()}")
        return None 