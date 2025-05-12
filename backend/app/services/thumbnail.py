from fastapi import UploadFile
import cloudinary.utils
import re

async def generate_thumbnail(video_url: str) -> str:
    """Generate thumbnail from video URL using Cloudinary"""
    # Extract the Cloudinary public ID from the URL
    # URL format: https://res.cloudinary.com/cloud_name/video/upload/v1234567890/folder/public_id.extension
    match = re.search(r'upload/v\d+/(.+)\.\w+$', video_url)
    if not match:
        # If we can't extract the public ID, just return the video URL
        return video_url
    
    public_id = match.group(1)
    
    # Create a thumbnail URL with Cloudinary transformations
    # This will extract a frame at 0 seconds and create a JPG thumbnail
    thumbnail_url = cloudinary.utils.cloudinary_url(
        public_id,
        resource_type="video",
        format="jpg",
        transformation=[
            {'width': 640, 'crop': 'fill'},
            {'start_offset': '0'}
        ]
    )[0]
    
    return thumbnail_url 