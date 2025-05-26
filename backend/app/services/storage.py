from fastapi import UploadFile
import cloudinary
import cloudinary.uploader
import os
import asyncio
from functools import partial
import time
import urllib3
from urllib3.util.retry import Retry
import requests

# Disable SSL warnings for debugging
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure Cloudinary with better connection settings
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True,
    # Add connection pool settings
    api_proxy=None
)

async def upload_to_cloud_storage(file: UploadFile) -> str:
    """
    Upload a file to Cloudinary and return its URL with retry logic
    """
    start_time = time.time()
    print(f"[CLOUDINARY] Starting upload_to_cloud_storage at {time.time()}")
    
    try:
        # Check if Cloudinary is properly configured
        print(f"[CLOUDINARY] Checking configuration...")
        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
        api_key = os.getenv('CLOUDINARY_API_KEY')
        api_secret = os.getenv('CLOUDINARY_API_SECRET')
        
        print(f"[CLOUDINARY] Cloud name: {'SET' if cloud_name else 'NOT SET'}")
        print(f"[CLOUDINARY] API key: {'SET' if api_key else 'NOT SET'}")
        print(f"[CLOUDINARY] API secret: {'SET' if api_secret else 'NOT SET'}")
        
        if not all([cloud_name, api_key, api_secret]):
            missing = []
            if not cloud_name: missing.append('CLOUDINARY_CLOUD_NAME')
            if not api_key: missing.append('CLOUDINARY_API_KEY')
            if not api_secret: missing.append('CLOUDINARY_API_SECRET')
            
            error_msg = f"Missing Cloudinary credentials: {', '.join(missing)}. Please set these environment variables."
            print(f"[CLOUDINARY] ERROR: {error_msg}")
            raise Exception(error_msg)
        
        print(f"[CLOUDINARY] Configuration OK, proceeding with upload...")
        
        # Get file info without reading entire content into memory
        print(f"[CLOUDINARY] Getting file info...")
        print(f"[CLOUDINARY] Filename: {file.filename}")
        print(f"[CLOUDINARY] Content type: {file.content_type}")
        
        # Reset file pointer to beginning
        await file.seek(0)
        
        # Retry logic for network issues
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"[CLOUDINARY] Upload attempt {attempt + 1}/{max_retries}")
                upload_start = time.time()
                
                # Reset file pointer before each attempt
                await file.seek(0)
                
                # Use asyncio to run the blocking upload in a thread with timeout
                loop = asyncio.get_event_loop()
                upload_func = partial(
                    cloudinary.uploader.upload,
                    file.file,  # Pass file object directly, not content
                    resource_type="video",
                    folder="league-reviews",
                    use_filename=True,
                    unique_filename=True,
                    timeout=180  # 3 minute timeout per attempt
                )
                
                print(f"[CLOUDINARY] Executing upload with 3-minute timeout...")
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, upload_func),
                    timeout=180.0  # 3 minute timeout
                )
                
                upload_duration = time.time() - upload_start
                print(f"[CLOUDINARY] Upload completed in {upload_duration:.2f} seconds")
                print(f"[CLOUDINARY] Result URL: {result.get('secure_url', 'NO_URL')}")
                
                total_duration = time.time() - start_time
                print(f"[CLOUDINARY] Total function duration: {total_duration:.2f} seconds")
                
                return result["secure_url"]
                
            except (asyncio.TimeoutError, Exception) as e:
                attempt_duration = time.time() - upload_start if 'upload_start' in locals() else 0
                print(f"[CLOUDINARY] Attempt {attempt + 1} failed after {attempt_duration:.2f}s: {str(e)}")
                
                if attempt == max_retries - 1:  # Last attempt
                    raise e
                    
                # Wait before retry (exponential backoff)
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                print(f"[CLOUDINARY] Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
        
    except asyncio.TimeoutError:
        duration = time.time() - start_time
        print(f"[CLOUDINARY] TIMEOUT after {duration:.2f} seconds")
        raise Exception(f"Cloudinary upload timed out after multiple attempts. This may be due to network issues or file size.")
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"[CLOUDINARY] ERROR after {duration:.2f} seconds: {str(e)}")
        print(f"[CLOUDINARY] Error type: {type(e).__name__}")
        
        # Provide more specific error messages
        error_str = str(e)
        if "SSL" in error_str or "EOF occurred" in error_str:
            raise Exception(f"Network/SSL connection issue with Cloudinary. This often happens with large files. Try with a smaller file or check your internet connection. Error: {str(e)}")
        elif "Max retries exceeded" in error_str:
            raise Exception(f"Cloudinary upload failed after multiple retry attempts. This may be due to network issues or file size. Error: {str(e)}")
        elif "Unsupported" in error_str and "format" in error_str:
            raise Exception(f"Video format not supported by Cloudinary. Supported formats: MP4, MOV, AVI, MKV, WebM. Error: {str(e)}")
        else:
            raise Exception(f"Failed to upload to Cloudinary: {str(e)}")
    
    finally:
        # Reset file pointer
        try:
            await file.seek(0)
        except:
            pass 