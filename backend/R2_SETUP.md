# Cloudflare R2 Storage Configuration

## ✅ Setup Complete!

Your R2 credentials have been configured in `restart_backend.ps1`. The backend will automatically use these credentials when you restart it.

### Current Configuration

- **Account ID**: `4c9e60a2dc0dcf475cc907f3cd645f1d`
- **Bucket Name**: `assetblue`
- **Endpoint URL**: `https://4c9e60a2dc0dcf475cc907f3cd645f1d.r2.cloudflarestorage.com`
- **Access Key ID**: Configured in `restart_backend.ps1`
- **Secret Access Key**: Configured in `restart_backend.ps1`

## Setup Instructions

1. **Database Migration** ✅ (Already completed)
   ```bash
   python migrate_r2_columns.py
   ```

2. **Install Dependencies** ✅ (Already completed)
   ```bash
   pip install boto3>=1.34.0
   ```

3. **Restart Backend**:
   ```bash
   .\restart_backend.ps1
   ```

   The script will automatically set R2 credentials and start the server.

## How It Works

- **PDFs**: Uploaded to R2 with content type `application/pdf` → stored in `pdfs/` directory
- **Images**: Uploaded with proper content types (`image/jpeg`, `image/png`, `image/gif`, `image/webp`) → stored in `images/` directory
- **YouTube**: Only metadata is stored (URLs stored, videos not downloaded) → stored in `youtube/` directory
- **Storage**: All scraped data accumulates in three dedicated directories in R2 bucket `assetblue`
- **Access**: Downloads use presigned URLs (valid 1 hour) or public URLs if configured

## File Organization

Files are stored in R2 organized by content type in dedicated directories:
```
pdfs/keyword_type_hash.pdf
images/keyword_type_hash.jpg
youtube/keyword_type_hash.mp4
```

Example:
```
pdfs/Boiler_Product_pdf_a1b2c3d4.pdf
images/Boiler_Product_image_e5f6g7h8.jpg
youtube/Boiler_Video_youtube_x9y8z7w6.mp4
```

All scraped data from all sessions accumulates in these three directories:
- **pdfs/** - All PDF files
- **images/** - All image files  
- **youtube/** - All YouTube metadata/files

## Accessing Files

- Files are accessible via presigned URLs generated on-demand
- The download endpoints automatically prefer R2 URLs if available
- Original URLs are preserved for fallback

## Testing

To test R2 connection:
```bash
python test_r2_connection.py
```

## Manual Credential Setup (Alternative)

If you prefer to set credentials via environment variables instead of the restart script:

Create a `.env` file in the `backend` directory:
```bash
# Required R2 Credentials
R2_ACCESS_KEY_ID=5068efe15645d5f08368a5b22a811746
R2_SECRET_ACCESS_KEY=f87a4caf85c89ada324027f17911e49dd66ea3e0953ce3c313960373d7a6a3a9

# Optional (already configured with defaults)
R2_ACCOUNT_ID=4c9e60a2dc0dcf475cc907f3cd645f1d
R2_BUCKET_NAME=assetblue
R2_ENDPOINT_URL=https://4c9e60a2dc0dcf475cc907f3cd645f1d.r2.cloudflarestorage.com

# Optional: Custom public domain (if you have one configured)
# R2_PUBLIC_URL=https://your-custom-domain.com
```
