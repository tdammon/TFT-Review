from fastapi import UploadFile
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config
import os
import asyncio
from functools import partial
import time
import uuid
from typing import Optional, Dict

class WasabiStorageService:
    def __init__(self):
        """Initialize Wasabi storage service with credentials from environment variables"""
        self.access_key_id = os.getenv('WASABI_ACCESS_KEY_ID')
        self.secret_access_key = os.getenv('WASABI_SECRET_ACCESS_KEY')
        self.bucket_name = os.getenv('WASABI_BUCKET_NAME')
        self.region = os.getenv('WASABI_REGION', 'us-central-1')
        
        # Use region-specific endpoint to avoid redirect errors
        region_endpoints = {
            'us-east-1': 'https://s3.us-east-1.wasabisys.com',
            'us-east-2': 'https://s3.us-east-2.wasabisys.com', 
            'us-central-1': 'https://s3.us-central-1.wasabisys.com',
            'us-west-1': 'https://s3.us-west-1.wasabisys.com',
            'eu-central-1': 'https://s3.eu-central-1.wasabisys.com',
            'ap-northeast-1': 'https://s3.ap-northeast-1.wasabisys.com'
        }
        
        # Get region-specific endpoint or fall back to environment variable
        self.endpoint_url = region_endpoints.get(self.region, os.getenv('WASABI_ENDPOINT_URL', 'https://s3.wasabisys.com'))
        
        print(f"[WASABI] Using endpoint: {self.endpoint_url} for region: {self.region}")
        
        # Validate required environment variables
        if not all([self.access_key_id, self.secret_access_key, self.bucket_name]):
            missing = []
            if not self.access_key_id: missing.append('WASABI_ACCESS_KEY_ID')
            if not self.secret_access_key: missing.append('WASABI_SECRET_ACCESS_KEY')
            if not self.bucket_name: missing.append('WASABI_BUCKET_NAME')
            raise ValueError(f"Missing required Wasabi environment variables: {', '.join(missing)}")
        
        # Initialize S3 client for Wasabi
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region,
            config=Config(
                retries={'max_attempts': 3, 'mode': 'adaptive'},
                max_pool_connections=50,
                region_name=self.region
            )
        )
        
        print(f"[WASABI] Initialized with bucket: {self.bucket_name}, region: {self.region}")

    async def upload_video(self, file: UploadFile) -> str:
        """
        Upload a video file to Wasabi and return its public URL
        """
        start_time = time.time()
        print(f"[WASABI] Starting video upload at {time.time()}")
        
        try:
            # Generate unique filename
            file_extension = self._get_file_extension(file.filename)
            unique_filename = f"videos/{uuid.uuid4()}{file_extension}"
            
            print(f"[WASABI] Uploading file: {file.filename} -> {unique_filename}")
            print(f"[WASABI] Content type: {file.content_type}")
            
            # Reset file pointer to beginning
            await file.seek(0)
            
            # Check file size to determine upload method
            file_size = 0
            try:
                # Try to get file size
                current_pos = file.file.tell()
                file.file.seek(0, 2)  # Seek to end
                file_size = file.file.tell()
                file.file.seek(current_pos)  # Reset to original position
                print(f"[WASABI] File size: {file_size / (1024*1024):.2f} MB")
            except:
                print(f"[WASABI] Could not determine file size")
            
            # Use multipart upload for files larger than 100MB
            if file_size > 100 * 1024 * 1024:  # 100MB
                print(f"[WASABI] Using multipart upload for large file")
                return await self._upload_multipart(file, unique_filename, file_size)
            else:
                print(f"[WASABI] Using standard upload")
                return await self._upload_standard(file, unique_filename)
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"[WASABI] ERROR after {duration:.2f} seconds: {str(e)}")
            print(f"[WASABI] Error type: {type(e).__name__}")
            raise Exception(f"Failed to upload to Wasabi: {str(e)}")
        
        finally:
            # Reset file pointer
            try:
                await file.seek(0)
            except:
                pass

    async def _upload_standard(self, file: UploadFile, unique_filename: str) -> str:
        """Standard upload for smaller files"""
        # Prepare upload parameters (remove ACL since public access not allowed)
        upload_params = {
            'ContentType': file.content_type or 'video/mp4'
        }
        
        # Upload with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"[WASABI] Upload attempt {attempt + 1}/{max_retries}")
                upload_start = time.time()
                
                # Reset file pointer before each attempt
                await file.seek(0)
                
                # Use asyncio to run the blocking upload in a thread
                loop = asyncio.get_event_loop()
                upload_func = partial(
                    self.s3_client.upload_fileobj,
                    file.file,  # File object as second argument
                    self.bucket_name,  # Bucket as third argument
                    unique_filename,  # Key as fourth argument
                    ExtraArgs=upload_params  # Extra args separately
                )
                
                await asyncio.wait_for(
                    loop.run_in_executor(None, upload_func),
                    timeout=120.0  # Reduced to 2 minutes for faster failure detection
                )
                
                upload_duration = time.time() - upload_start
                print(f"[WASABI] Upload completed in {upload_duration:.2f} seconds")
                
                return unique_filename  # Return the key, not a pre-signed URL
                
            except (ClientError, Exception) as e:
                attempt_duration = time.time() - upload_start if 'upload_start' in locals() else 0
                print(f"[WASABI] Attempt {attempt + 1} failed after {attempt_duration:.2f}s: {str(e)}")
                
                if attempt == max_retries - 1:  # Last attempt
                    raise e
                    
                # Wait before retry (exponential backoff)
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                print(f"[WASABI] Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)

    async def _upload_multipart(self, file: UploadFile, unique_filename: str, file_size: int) -> str:
        """Multipart upload for larger files"""
        print(f"[WASABI] Starting multipart upload")
        
        try:
            # Initiate multipart upload
            loop = asyncio.get_event_loop()
            
            create_func = partial(
                self.s3_client.create_multipart_upload,
                Bucket=self.bucket_name,
                Key=unique_filename,
                ContentType=file.content_type or 'video/mp4'
            )
            
            response = await loop.run_in_executor(None, create_func)
            upload_id = response['UploadId']
            print(f"[WASABI] Multipart upload initiated: {upload_id}")
            
            # Upload parts (5MB each)
            part_size = 5 * 1024 * 1024  # 5MB
            parts = []
            part_number = 1
            
            await file.seek(0)
            
            while True:
                chunk = await file.read(part_size)
                if not chunk:
                    break
                
                print(f"[WASABI] Uploading part {part_number} ({len(chunk)} bytes)")
                
                # Upload this part
                upload_part_func = partial(
                    self.s3_client.upload_part,
                    Bucket=self.bucket_name,
                    Key=unique_filename,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=chunk
                )
                
                part_response = await loop.run_in_executor(None, upload_part_func)
                parts.append({
                    'ETag': part_response['ETag'],
                    'PartNumber': part_number
                })
                
                part_number += 1
            
            # Complete multipart upload
            complete_func = partial(
                self.s3_client.complete_multipart_upload,
                Bucket=self.bucket_name,
                Key=unique_filename,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )
            
            await loop.run_in_executor(None, complete_func)
            print(f"[WASABI] Multipart upload completed")
            
            return unique_filename
            
        except Exception as e:
            # Abort multipart upload on error
            try:
                abort_func = partial(
                    self.s3_client.abort_multipart_upload,
                    Bucket=self.bucket_name,
                    Key=unique_filename,
                    UploadId=upload_id
                )
                await loop.run_in_executor(None, abort_func)
                print(f"[WASABI] Aborted multipart upload due to error")
            except:
                pass
            raise e

    def _get_file_extension(self, filename: Optional[str]) -> str:
        """Extract file extension from filename"""
        if not filename:
            return '.mp4'  # Default extension
        
        if '.' in filename:
            return '.' + filename.split('.')[-1].lower()
        return '.mp4'  # Default extension

    async def delete_video(self, file_url_or_key: str) -> bool:
        """
        Delete a video file from Wasabi given its URL or file key
        """
        try:
            # Check if it's a file key (doesn't contain http) or URL
            if file_url_or_key.startswith('http'):
                # Extract key from URL
                key = self._extract_key_from_url(file_url_or_key)
                if not key:
                    print(f"[WASABI] Could not extract key from URL: {file_url_or_key}")
                    return False
            else:
                # Assume it's already a file key
                key = file_url_or_key
            
            print(f"[WASABI] Deleting file: {key}")
            
            # Delete the object
            loop = asyncio.get_event_loop()
            delete_func = partial(
                self.s3_client.delete_object,
                Bucket=self.bucket_name,
                Key=key
            )
            
            await loop.run_in_executor(None, delete_func)
            print(f"[WASABI] Successfully deleted: {key}")
            return True
            
        except Exception as e:
            print(f"[WASABI] Error deleting file: {str(e)}")
            return False

    async def delete_file_by_key(self, file_key: str) -> bool:
        """
        Delete a file from Wasabi by its key (path in bucket)
        """
        try:
            print(f"[WASABI] Deleting file by key: {file_key}")
            
            loop = asyncio.get_event_loop()
            delete_func = partial(
                self.s3_client.delete_object,
                Bucket=self.bucket_name,
                Key=file_key
            )
            
            await loop.run_in_executor(None, delete_func)
            print(f"[WASABI] Successfully deleted file: {file_key}")
            return True
            
        except Exception as e:
            print(f"[WASABI] Error deleting file by key {file_key}: {str(e)}")
            return False

    def _extract_key_from_url(self, url: str) -> Optional[str]:
        """Extract the object key from a Wasabi URL"""
        try:
            # New URL format: https://bucket-name.s3.region.wasabisys.com/path/to/file.ext
            # or https://bucket-name.s3.wasabisys.com/path/to/file.ext (for us-east-1)
            if f"{self.bucket_name}.s3" in url and "wasabisys.com" in url:
                # Split on the domain and get the path part
                parts = url.split(".wasabisys.com/")
                if len(parts) > 1:
                    return parts[1]
            
            # Fallback for old URL format: https://s3.region.wasabisys.com/bucket-name/path/to/file.ext
            if self.bucket_name in url:
                parts = url.split(f"/{self.bucket_name}/")
                if len(parts) > 1:
                    return parts[1]
            return None
        except:
            return None

    async def get_video_url(self, file_key: str, expires_in: int = 604800) -> str:
        """
        Generate a fresh pre-signed URL for an existing video file
        
        Args:
            file_key: The object key (path) in the bucket
            expires_in: URL expiration time in seconds (default: 7 days)
        
        Returns:
            Pre-signed URL for the video
        """
        try:
            print(f"[WASABI] Generating fresh pre-signed URL for: {file_key}")
            
            loop = asyncio.get_event_loop()
            url_func = partial(
                self.s3_client.generate_presigned_url,
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expires_in
            )
            
            file_url = await loop.run_in_executor(None, url_func)
            print(f"[WASABI] Generated fresh URL (expires in {expires_in} seconds)")
            return file_url
            
        except Exception as e:
            print(f"[WASABI] Error generating pre-signed URL: {str(e)}")
            raise Exception(f"Failed to generate video URL: {str(e)}")

    async def get_multiple_video_urls(self, file_keys: list, expires_in: int = 604800) -> dict:
        """
        Generate fresh pre-signed URLs for multiple video files at once
        
        Args:
            file_keys: List of object keys (paths) in the bucket
            expires_in: URL expiration time in seconds (default: 7 days)
        
        Returns:
            Dictionary mapping file_key -> pre-signed URL
        """
        try:
            print(f"[WASABI] Generating {len(file_keys)} pre-signed URLs...")
            
            loop = asyncio.get_event_loop()
            
            # Create tasks for all URL generations
            tasks = []
            for file_key in file_keys:
                url_func = partial(
                    self.s3_client.generate_presigned_url,
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': file_key},
                    ExpiresIn=expires_in
                )
                tasks.append(loop.run_in_executor(None, url_func))
            
            # Execute all tasks concurrently
            urls = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Build result dictionary
            result = {}
            for i, file_key in enumerate(file_keys):
                if isinstance(urls[i], Exception):
                    print(f"[WASABI] Error generating URL for {file_key}: {urls[i]}")
                    result[file_key] = file_key  # Fallback to original key
                else:
                    result[file_key] = urls[i]
            
            print(f"[WASABI] Generated {len([u for u in urls if not isinstance(u, Exception)])} URLs successfully")
            return result
            
        except Exception as e:
            print(f"[WASABI] Error generating multiple URLs: {str(e)}")
            # Return fallback mapping
            return {key: key for key in file_keys}

    async def create_multipart_upload(self, file_key: str, content_type: str) -> dict:
        """
        Initiate a multipart upload and return the upload ID
        """
        try:
            print(f"[WASABI] Initiating multipart upload for {file_key}")
            
            loop = asyncio.get_event_loop()
            create_func = partial(
                self.s3_client.create_multipart_upload,
                Bucket=self.bucket_name,
                Key=file_key,
                ContentType=content_type or 'video/mp4'
            )
            
            response = await loop.run_in_executor(None, create_func)
            print(f"[WASABI] Multipart upload initiated with ID: {response['UploadId']}")
            
            return response
            
        except Exception as e:
            print(f"[WASABI] Error initiating multipart upload: {str(e)}")
            raise Exception(f"Failed to initiate multipart upload: {str(e)}")

    async def get_chunk_upload_urls(self, file_key: str, upload_id: str, total_chunks: int) -> Dict[int, str]:
        """
        Generate presigned URLs for uploading each chunk
        """
        try:
            print(f"[WASABI] Generating presigned URLs for {total_chunks} chunks")
            
            urls = {}
            loop = asyncio.get_event_loop()
            
            for chunk_number in range(1, total_chunks + 1):
                url_func = partial(
                    self.s3_client.generate_presigned_url,
                    'upload_part',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': file_key,
                        'UploadId': upload_id,
                        'PartNumber': chunk_number
                    },
                    ExpiresIn=3600  # URL valid for 1 hour
                )
                
                presigned_url = await loop.run_in_executor(None, url_func)
                urls[chunk_number] = presigned_url
            
            print(f"[WASABI] Generated {len(urls)} presigned URLs")
            return urls
            
        except Exception as e:
            print(f"[WASABI] Error generating chunk upload URLs: {str(e)}")
            raise Exception(f"Failed to generate chunk upload URLs: {str(e)}")

    async def complete_multipart_upload(self, file_key: str, upload_id: str, etags: Dict[int, str]) -> str:
        """
        Complete a multipart upload with the ETags from all chunks
        """
        try:
            print(f"[WASABI] Completing multipart upload for {file_key}")
            print(f"[WASABI] ETags received: {etags}")
            
            # Prepare parts list in correct order
            parts = []
            for part_num in sorted(etags.keys()):
                etag = etags[part_num]
                # Add quotes back if they're not present
                if not etag.startswith('"'):
                    etag = f'"{etag}"'
                if not etag.endswith('"'):
                    etag = f'{etag}"'
                parts.append({
                    'ETag': etag,
                    'PartNumber': part_num
                })
            
            print(f"[WASABI] Parts prepared: {parts}")
            
            loop = asyncio.get_event_loop()
            complete_func = partial(
                self.s3_client.complete_multipart_upload,
                Bucket=self.bucket_name,
                Key=file_key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )
            
            await loop.run_in_executor(None, complete_func)
            print(f"[WASABI] Multipart upload completed successfully")
            
            return file_key
            
        except Exception as e:
            print(f"[WASABI] Error completing multipart upload: {str(e)}")
            raise Exception(f"Failed to complete multipart upload: {str(e)}")

    async def abort_multipart_upload(self, file_key: str, upload_id: str):
        """
        Abort a multipart upload and clean up any uploaded parts
        """
        try:
            print(f"[WASABI] Aborting multipart upload for {file_key}")
            
            loop = asyncio.get_event_loop()
            abort_func = partial(
                self.s3_client.abort_multipart_upload,
                Bucket=self.bucket_name,
                Key=file_key,
                UploadId=upload_id
            )
            
            await loop.run_in_executor(None, abort_func)
            print(f"[WASABI] Multipart upload aborted successfully")
            
        except Exception as e:
            print(f"[WASABI] Error aborting multipart upload: {str(e)}")
            raise Exception(f"Failed to abort multipart upload: {str(e)}")

# Global instance
wasabi_storage = WasabiStorageService() 