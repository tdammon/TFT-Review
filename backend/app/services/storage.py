from fastapi import UploadFile
import cloudinary
import cloudinary.uploader
import os

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
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file.file,
            resource_type="video",
            folder="league-review/videos"
        )
        
        # Return the secure URL
        return result['secure_url']
        
    except Exception as e:
        raise Exception(f"Error uploading file: {str(e)}") 