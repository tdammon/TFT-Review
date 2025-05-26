from fastapi import UploadFile
import cloudinary
import cloudinary.uploader
import os
import asyncio
from functools import partial

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

async def upload_to_cloud_storage(file: UploadFile) -> str:
    """
    Upload a file to Cloudinary and return its URL
    """
    try:
        # Check if Cloudinary is properly configured
        if not all([
            os.getenv('CLOUDINARY_CLOUD_NAME'),
            os.getenv('CLOUDINARY_API_KEY'),
            os.getenv('CLOUDINARY_API_SECRET')
        ]):
            raise Exception("Cloudinary credentials not configured. Please set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET environment variables.")
        
        # Create a partial function for the synchronous upload
        upload_func = partial(
            cloudinary.uploader.upload,
            file.file,
            resource_type="video",
            folder="league-review/videos"
        )
        
        # Run the synchronous upload in a thread pool with timeout
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, upload_func),
            timeout=60.0  # 60 second timeout
        )
        
        # Return the secure URL
        return result['secure_url']
        
    except asyncio.TimeoutError:
        raise Exception("Upload timed out after 60 seconds. Please check your Cloudinary configuration and try again.")
    except Exception as e:
        raise Exception(f"Error uploading file: {str(e)}") 