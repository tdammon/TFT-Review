# Wasabi Setup Guide

## Requirements

- **FFmpeg**: Required for video thumbnail generation
  - macOS: `brew install ffmpeg`
  - Ubuntu: `sudo apt install ffmpeg`
  - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## 1. Create a Wasabi Account

1. Go to [wasabi.com](https://wasabi.com) and sign up for an account
2. Choose a plan (they have a free tier with 5GB storage for 30 days)

## 2. Create Access Keys

1. Log into your Wasabi console
2. Go to "Access Keys" in the left sidebar
3. Click "Create New Access Key"
4. Save both the **Access Key ID** and **Secret Access Key** (you won't see the secret again!)

## 3. Create a Bucket

1. In the Wasabi console, go to "Buckets"
2. Click "Create Bucket"
3. Choose a unique bucket name (e.g., `your-app-name-videos`)
4. Select a region (us-central-1 is recommended for best performance)
5. **Note**: You don't need to make the bucket public - we use pre-signed URLs instead

## Important: Pre-signed URLs

Since many Wasabi accounts don't allow public object access, this integration uses **pre-signed URLs** instead of public URLs. This means:

✅ **Works with all account types** - No need for public access permissions  
✅ **Secure** - URLs expire after 7 days by default  
✅ **No additional setup** - Works out of the box  
✅ **Always fresh** - New URLs generated on-demand when videos are accessed  
✅ **No expiration issues** - URLs are created fresh each time you view videos

## How It Works:

1. **Upload**: Video file key is stored in database (not the full URL)
2. **Thumbnails**: FFmpeg extracts a frame at 1 second, uploads to Wasabi as thumbnail
3. **Access**: Fresh pre-signed URLs generated when videos are requested
4. **Lists**: Multiple URLs (videos + thumbnails) generated efficiently in parallel
5. **Streaming**: New URLs created each time video is played

The generated URLs will look like:

```
https://your-bucket.s3.us-central-1.wasabisys.com/videos/uuid.mp4?AWSAccessKeyId=...&Expires=...&Signature=...
https://your-bucket.s3.us-central-1.wasabisys.com/thumbnails/uuid.jpg?AWSAccessKeyId=...&Expires=...&Signature=...
```

**No URL expiration problems!** Since URLs are generated fresh each time, they're always valid.

## 4. Update Your Environment Variables

Add these variables to your `.env` file in the backend directory:

```bash
# Wasabi Configuration
WASABI_ACCESS_KEY_ID="your_access_key_id_here"
WASABI_SECRET_ACCESS_KEY="your_secret_access_key_here"
WASABI_BUCKET_NAME="your_bucket_name_here"
WASABI_REGION="us-central-1"
WASABI_ENDPOINT_URL="https://s3.us-central-1.wasabisys.com"
```

**Note**: The endpoint URL should match your region:

- `us-central-1`: `https://s3.us-central-1.wasabisys.com`
- `us-east-1`: `https://s3.us-east-1.wasabisys.com`
- `us-east-2`: `https://s3.us-east-2.wasabisys.com`
- `us-west-1`: `https://s3.us-west-1.wasabisys.com`
- `eu-central-1`: `https://s3.eu-central-1.wasabisys.com`
- `ap-northeast-1`: `https://s3.ap-northeast-1.wasabisys.com`

## 5. Test the Integration

Once you've added the credentials, restart your FastAPI server:

```bash
uvicorn main:app --host 0.0.0.0 --port 3001 --reload
```

Try uploading a video through your frontend. You should see logs like:

```
[WASABI] Initialized with bucket: your-bucket-name, region: us-central-1
[WASABI] Starting video upload...
[WASABI] Upload completed in X.XX seconds
```

## 6. Wasabi Regions Available

- `us-central-1` (Central US) - Default, good performance for central US
- `us-east-1` (N. Virginia) - US East Coast
- `us-east-2` (N. Virginia) - Alternative US East
- `us-west-1` (Oregon) - US West Coast
- `eu-central-1` (Amsterdam) - Europe
- `ap-northeast-1` (Tokyo) - Asia Pacific

## Benefits of Wasabi vs Cloudinary

✅ **No file size limits** - Upload videos of any size  
✅ **No egress fees** - Free downloads and streaming  
✅ **No API request fees** - Unlimited API calls  
✅ **80% cheaper** than AWS S3  
✅ **Fast performance** - Built for media companies  
✅ **Simple pricing** - $6/TB/month, no surprises

## Troubleshooting

### "Missing required Wasabi environment variables"

- Make sure all environment variables are set in your `.env` file
- Restart your FastAPI server after adding variables

### "Wasabi bucket does not exist"

- Double-check your bucket name in the Wasabi console
- Make sure the bucket name matches exactly (case-sensitive)

### "Access denied to Wasabi bucket"

- Verify your access key and secret key are correct
- Make sure the bucket is set to public for video streaming
- Check that your access key has permissions to the bucket

### "Public use of objects is not allowed by this account"

- This is normal for many Wasabi accounts (especially free/trial accounts)
- The integration automatically uses pre-signed URLs instead
- No action needed - videos will still work with pre-signed URLs
- Pre-signed URLs expire after 7 days but can be regenerated

### "PermanentRedirect - The bucket you are attempting to access must be addressed using the specified endpoint"

- This means your bucket is in a different region than configured
- Check your bucket's region in the Wasabi console
- Update your `WASABI_REGION` environment variable to match
- The code will automatically use the correct region-specific endpoint
- Restart your server after updating the region

### "Upload timeout"

- This usually happens with very large files
- The timeout is set to 5 minutes per attempt with 3 retries
- Consider compressing your video if it's extremely large

## Need Help?

If you run into issues, check the FastAPI logs for detailed error messages. All Wasabi operations are logged with `[WASABI]` prefix for easy debugging.
