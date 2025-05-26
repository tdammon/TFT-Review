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
            # Reset file pointer and save video to temp file
            await video_file.seek(0)
            video_content = await video_file.read()
            
            with open(temp_video_path, 'wb') as f:
                f.write(video_content)
            
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
            
            # Generate pre-signed URL for thumbnail (valid for 7 days)
            # Actually, let's return the key so we can generate fresh URLs on demand
            # thumbnail_url = wasabi_storage.s3_client.generate_presigned_url(
            #     'get_object',
            #     Params={'Bucket': wasabi_storage.bucket_name, 'Key': thumbnail_key},
            #     ExpiresIn=604800  # 7 days
            # )
            
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
        # Reset video file pointer
        try:
            await video_file.seek(0)
        except:
            pass 