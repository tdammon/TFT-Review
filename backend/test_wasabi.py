#!/usr/bin/env python3
"""
Test script for Wasabi integration
Run this to verify your Wasabi credentials and bucket are set up correctly
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_wasabi_config():
    """Test if Wasabi environment variables are configured"""
    print("🔍 Testing Wasabi Configuration...")
    
    required_vars = [
        'WASABI_ACCESS_KEY_ID',
        'WASABI_SECRET_ACCESS_KEY', 
        'WASABI_BUCKET_NAME'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {'*' * (len(value) - 4) + value[-4:]}")  # Hide most of the value
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please add these to your .env file")
        return False
    
    print("✅ All required environment variables are set!")
    return True

def test_wasabi_connection():
    """Test connection to Wasabi"""
    print("\n🔗 Testing Wasabi Connection...")
    
    try:
        from app.services.wasabi_storage import wasabi_storage
        print("✅ Wasabi storage service imported successfully")
        
        # Test bucket access by listing objects (this will fail if credentials are wrong)
        import boto3
        from botocore.exceptions import ClientError
        
        s3_client = wasabi_storage.s3_client
        bucket_name = wasabi_storage.bucket_name
        
        print(f"🪣 Testing access to bucket: {bucket_name}")
        
        # Try to list objects in the bucket
        response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
        print("✅ Successfully connected to Wasabi bucket!")
        
        # Check if bucket is public
        try:
            bucket_acl = s3_client.get_bucket_acl(Bucket=bucket_name)
            print("✅ Bucket ACL retrieved successfully")
        except ClientError as e:
            print(f"⚠️  Could not retrieve bucket ACL: {e}")
            print("This might be okay if bucket permissions are set differently")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import Wasabi service: {e}")
        print("Make sure boto3 is installed: pip install boto3")
        return False
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            print(f"❌ Bucket '{bucket_name}' does not exist")
            print("Please create the bucket in your Wasabi console")
        elif error_code == 'AccessDenied':
            print("❌ Access denied - check your credentials")
        else:
            print(f"❌ AWS Error: {error_code} - {e.response['Error']['Message']}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Wasabi Integration Test\n")
    
    # Test 1: Environment variables
    config_ok = test_wasabi_config()
    if not config_ok:
        print("\n❌ Configuration test failed. Please fix environment variables first.")
        sys.exit(1)
    
    # Test 2: Connection
    connection_ok = test_wasabi_connection()
    if not connection_ok:
        print("\n❌ Connection test failed. Please check your credentials and bucket.")
        sys.exit(1)
    
    print("\n🎉 All tests passed! Wasabi integration is ready to use.")
    print("\nNext steps:")
    print("1. Start your FastAPI server: uvicorn main:app --host 0.0.0.0 --port 3001 --reload")
    print("2. Try uploading a video through your frontend")
    print("3. Check the logs for [WASABI] messages")

if __name__ == "__main__":
    main() 