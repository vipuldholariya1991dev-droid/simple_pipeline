"""Test R2 connection"""
import os
os.environ['R2_ACCESS_KEY_ID'] = '5068efe15645d5f08368a5b22a811746'
os.environ['R2_SECRET_ACCESS_KEY'] = 'f87a4caf85c89ada324027f17911e49dd66ea3e0953ce3c313960373d7a6a3a9'

from app.storage import r2_storage

print("=" * 60)
print("Testing Cloudflare R2 Connection")
print("=" * 60)

if r2_storage.is_available():
    print(f"✅ R2 Storage is available!")
    print(f"   Bucket: {r2_storage.bucket_name}")
    print(f"   Endpoint: https://4c9e60a2dc0dcf475cc907f3cd645f1d.r2.cloudflarestorage.com")
    
    # Test bucket access
    try:
        response = r2_storage.client.list_objects_v2(Bucket=r2_storage.bucket_name, MaxKeys=1)
        print(f"✅ Successfully connected to R2 bucket!")
        print(f"   Objects in bucket: {response.get('KeyCount', 'Unknown')}")
    except Exception as e:
        print(f"⚠️  Error accessing bucket: {e}")
else:
    print("❌ R2 Storage is NOT available")
    print("   Check your credentials in config.py or environment variables")

print("=" * 60)

