"""Cloudflare R2 Storage Service"""
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import httpx
from typing import Optional, Tuple
from app.config import settings
import hashlib
from urllib.parse import urlparse
import os

class R2Storage:
    """Cloudflare R2 storage service using S3-compatible API"""
    
    def __init__(self):
        """Initialize R2 client"""
        if not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY:
            print("⚠️  R2 credentials not configured. Set R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY environment variables.")
            self.client = None
            return
        
        try:
            self.client = boto3.client(
                's3',
                endpoint_url=settings.R2_ENDPOINT_URL,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                config=Config(
                    signature_version='s3v4',
                    s3={
                        'addressing_style': 'path'
                    }
                )
            )
            self.bucket_name = settings.R2_BUCKET_NAME
            print(f"✅ R2 Storage initialized - Bucket: {self.bucket_name}")
        except Exception as e:
            print(f"❌ Failed to initialize R2 client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if R2 storage is available"""
        return self.client is not None
    
    def get_content_type(self, content_type: str, url: str) -> str:
        """Get appropriate content type based on content type and URL"""
        if content_type == "youtube":
            # YouTube videos are MP4 files
            return "video/mp4"
        elif content_type == "pdf":
            return "application/pdf"
        elif content_type == "image":
            # Check file extension to determine image type
            url_lower = url.lower()
            if url_lower.endswith('.png'):
                return "image/png"
            elif url_lower.endswith('.gif'):
                return "image/gif"
            elif url_lower.endswith('.webp'):
                return "image/webp"
            else:
                return "image/jpeg"  # Default to JPEG
        return "application/octet-stream"
    
    def get_file_extension(self, content_type: str, url: str) -> str:
        """Get file extension based on content type"""
        if content_type == "youtube":
            # YouTube videos are MP4 files
            return ".mp4"
        elif content_type == "pdf":
            return ".pdf"
        elif content_type == "image":
            # Try to get extension from URL
            url_lower = url.lower()
            if url_lower.endswith('.png'):
                return ".png"
            elif url_lower.endswith('.gif'):
                return ".gif"
            elif url_lower.endswith('.webp'):
                return ".webp"
            elif url_lower.endswith('.jpg') or url_lower.endswith('.jpeg'):
                return ".jpg"
            else:
                return ".jpg"  # Default to JPEG
        return ".bin"
    
    def generate_r2_key(self, keyword: str, content_type: str, url: str, task_id: str, item_id: Optional[int] = None) -> str:
        """Generate a unique R2 object key/path organized by content type"""
        # Create a hash from the original URL for uniqueness
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        
        # Sanitize keyword for use in path
        safe_keyword = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in keyword[:50])
        safe_keyword = safe_keyword.replace(' ', '_')
        
        # Get file extension
        ext = self.get_file_extension(content_type, url)
        
        # Map content type to directory name
        content_type_dir = {
            "pdf": "pdfs",
            "image": "images",
            "youtube": "youtube"
        }.get(content_type.lower(), "other")
        
        # Generate path: {content_type_dir}/item_{id}_{keyword}.ext or {content_type_dir}/keyword_type_urlhash.ext
        if item_id:
            path = f"{content_type_dir}/item_{item_id}_{safe_keyword}{ext}"
        else:
            path = f"{content_type_dir}/{safe_keyword}_{content_type}_{url_hash}{ext}"
        return path
    
    async def upload_file(self, 
                         url: str, 
                         keyword: str, 
                         content_type: str, 
                         task_id: str,
                         item_id: Optional[int] = None,
                         file_path: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Download file from URL and upload to R2
        
        Returns:
            Tuple of (r2_url, r2_key) or (None, None) if failed
        """
        if not self.is_available():
            print(f"  ⚠️  R2 storage not available, skipping upload")
            return None, None
        
        try:
            # Handle local file upload (for YouTube videos) or URL download
            if file_path and os.path.exists(file_path):
                # Upload from local file
                print(f"  📥 Reading local file: {file_path}", flush=True)
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                file_size = len(file_content)
                print(f"  ✅ Read {file_size} bytes from local file", flush=True)
            else:
                # Download file from original URL
                print(f"  📥 Downloading file from: {url[:80]}...", flush=True)
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    response = await client.get(url)
                    if response.status_code != 200:
                        print(f"  ❌ Failed to download file: HTTP {response.status_code}", flush=True)
                        return None, None
                    
                    file_content = response.content
                    file_size = len(file_content)
                    
                    print(f"  ✅ Downloaded {file_size} bytes", flush=True)
            
            # Check file size limit
            max_size = settings.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024
            if file_size > max_size:
                print(f"  ❌ File too large: {file_size} bytes (max {max_size})", flush=True)
                return None, None
            
            # Generate R2 key (use item_id if provided for YouTube videos)
            r2_key = self.generate_r2_key(keyword, content_type, url, task_id, item_id=item_id)
            
            # Get content type
            content_type_header = self.get_content_type(content_type, url)
            
            # Upload to R2 with proper headers for downloads
            print(f"  ☁️  Uploading to R2: {r2_key}", flush=True)
            
            # Extract filename from r2_key for Content-Disposition header
            filename = r2_key.split('/')[-1]  # Get just the filename
            
            # Prepare upload parameters
            upload_params = {
                'Bucket': self.bucket_name,
                'Key': r2_key,
                'Body': file_content,
                'ContentType': content_type_header,
                'Metadata': {
                    'original-url': url,
                    'keyword': keyword,
                    'task-id': task_id
                }
            }
            
            # Add Content-Disposition header for proper downloads
            # This ensures browsers download the file with the correct filename
            upload_params['ContentDisposition'] = f'attachment; filename="{filename}"'
            
            # Add Cache-Control for better caching behavior
            upload_params['CacheControl'] = 'public, max-age=31536000'  # 1 year cache
            
            self.client.put_object(**upload_params)
            
            # Generate public URL
            # Note: Store r2_key in database, generate presigned URLs on-demand for downloads
            # For public buckets, you can use direct URLs, but presigned URLs work for private buckets too
            if settings.R2_PUBLIC_URL:
                # Use custom domain if configured (public access)
                r2_url = f"{settings.R2_PUBLIC_URL.rstrip('/')}/{r2_key}"
            else:
                # Store r2_key only - we'll generate presigned URLs on-demand
                # This avoids expiration issues with presigned URLs
                # The r2_url will be generated when needed using get_public_url() or generate_presigned_url()
                r2_url = None  # Will be generated on-demand
            
            print(f"  ✅ Uploaded to R2: {r2_key}", flush=True)
            return r2_url, r2_key
            
        except ClientError as e:
            print(f"  ❌ R2 upload error: {e}", flush=True)
            return None, None
        except Exception as e:
            print(f"  ❌ Error uploading to R2: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return None, None
    
    def get_public_url(self, r2_key: str) -> str:
        """
        Generate public URL for an R2 object
        Uses R2_PUBLIC_URL if set (custom domain or Public Development URL)
        Otherwise falls back to endpoint URL (may require authentication)
        """
        if settings.R2_PUBLIC_URL:
            return f"{settings.R2_PUBLIC_URL.rstrip('/')}/{r2_key}"
        else:
            # Fallback - this may not work if bucket is private
            # Better to use get_download_url() which generates presigned URLs
            return f"{settings.R2_ENDPOINT_URL}/{self.bucket_name}/{r2_key}"
    
    def get_download_url(self, r2_key: str, expires_in: int = 86400) -> str:
        """
        Generate download URL (presigned if bucket is private, public if bucket is public)
        
        Args:
            r2_key: The R2 object key
            expires_in: Expiration time in seconds (default: 24 hours for better compatibility)
        """
        if not self.is_available():
            return None
        
        if settings.R2_PUBLIC_URL:
            # Use custom domain (public access)
            return f"{settings.R2_PUBLIC_URL.rstrip('/')}/{r2_key}"
        else:
            try:
                # Generate presigned URL (works for both public and private buckets)
                # Use longer expiration for video downloads (24 hours default)
                url = self.client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket_name, 
                        'Key': r2_key,
                        # Add response headers for proper download behavior
                        'ResponseContentDisposition': f'attachment; filename="{r2_key.split("/")[-1]}"',
                        'ResponseContentType': 'video/mp4'
                    },
                    ExpiresIn=expires_in
                )
                return url
            except Exception as e:
                # Fallback to direct URL (may not work if bucket is private)
                print(f"⚠️  Could not generate presigned URL: {e}")
                return f"{settings.R2_ENDPOINT_URL}/{self.bucket_name}/{r2_key}"
    
    def delete_file(self, r2_key: str) -> bool:
        """Delete a file from R2"""
        if not self.is_available():
            return False
        
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=r2_key)
            return True
        except Exception as e:
            print(f"❌ Error deleting R2 file {r2_key}: {e}")
            return False

# Global R2 storage instance
r2_storage = R2Storage()

