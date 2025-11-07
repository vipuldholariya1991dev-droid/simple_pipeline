# Simple Scraping Pipeline

A modern, scalable web scraping pipeline that extracts PDFs, Images, and YouTube videos based on keyword CSV files. Features a clean React UI, FastAPI backend with PostgreSQL database, and automatic Cloudflare R2 storage for all scraped content.

## Features

### Scraping Capabilities
- 📄 **PDF Scraping** - Extract PDF documents using Exa API (high-quality semantic search)
- 🖼️ **Image Scraping** - Extract images using Bing Image API
- 🎥 **YouTube Scraping** - Extract YouTube videos using yt-dlp with multi-strategy retry system
- ✅ **Duplicate Detection** - Prevents duplicate items across scraping sessions
- 📁 **Multi-file Support** - Upload multiple CSV files at once

### Storage & Management
- ☁️ **Cloudflare R2 Storage** - Automatic upload of all scraped content (PDFs, Images, YouTube videos) to Cloudflare R2
- 📊 **Database Storage** - PostgreSQL with pgAdmin for data management and tracking
- 🔗 **Presigned URLs** - 7-day expiration presigned URLs for direct file access in CSV downloads
- 📋 **Source File Tracking** - Track which CSV file each scraped item came from

### User Interface
- 🎨 **Modern UI** - Clean, professional React interface
- 🔍 **Real-time Progress** - Live tracking of scraping progress with counts per content type
- 📥 **Bulk Downloads** - Download all items as ZIP (PDFs/Images) or CSV (YouTube)
- 📂 **Download by Source File** - Download CSV files filtered by specific input CSV file
- 📊 **Data Export** - Export scraped data with all metadata including R2 URLs and keys

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + Vite
- **Database**: PostgreSQL (Docker)
- **Scraping**: 
  - Exa API for PDF search (semantic search)
  - Bing Image API for image search
  - yt-dlp for YouTube video search and download
- **Storage**: Cloudflare R2 (S3-compatible object storage)
- **APIs**: Exa API, Bing Image API

## Quick Start

### Prerequisites

- Docker Desktop
- Python 3.8+
- Node.js 16+ and npm
- **Note**: Default R2 credentials and Exa API key are included in `backend/app/config.py` - the system works out of the box! You can override these with your own credentials if desired.

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd simple_pipeline
   ```

2. **Start Database**
   ```bash
   cd backend
   docker-compose up -d
   ```

3. **Setup Backend**
   ```bash
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1  # Windows
   # or: source venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   python init_db.py
   
   # Note: Default credentials are included in config.py - system works out of the box!
   # To use your own credentials, update config.py or set environment variables:
   # - EXA_API_KEY for PDF search (get from https://exa.ai)
   # - R2 credentials for Cloudflare R2 storage
   
   # Start backend server
   uvicorn app.main:app --reload --port 8001
   # Or use the restart script:
   .\restart_backend.ps1  # Windows
   ```

4. **Setup Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Access the Application**
   - Frontend: http://localhost:5174
   - Backend API: http://localhost:8001
   - API Docs: http://localhost:8001/docs
   - pgAdmin: http://localhost:5050

## Usage

### Basic Workflow

1. **Upload CSV Files**: Select one or more CSV files containing keywords (one keyword per line)
2. **Select Content Types**: Check PDF, Image, and/or YouTube checkboxes
3. **Start Scraping**: Click "Start Scraping" and monitor real-time progress
   - System automatically finds and downloads content
   - All content is automatically uploaded to Cloudflare R2
   - Progress updates in real-time showing PDF, Image, and YouTube counts
4. **View Results**: See scraped items in the table with all metadata
   - Each item shows: title, URL, content type, source file, and R2 storage info
5. **Download Results**: 
   - **Download All**: Click "Download Scraped Data" to download all items from current session
   - **Download by Source File**: 
     - Go to "Download Scraped Data" page
     - Select a source CSV file from dropdown menu
     - Click download button to get CSV with all items for that file
     - CSV includes presigned URLs (7-day expiration) for direct file access
     - Includes items from all scraping sessions for that source file
     - Automatically filters to match current CSV file keywords

### Features Explained

- **Automatic R2 Storage**: 
  - All scraped content (PDFs, Images, YouTube videos) is automatically uploaded to Cloudflare R2
  - Files are organized by type: `pdfs/`, `images/`, `youtube/`
  - Each file gets a unique R2 key and public URL
  - R2 credentials are configured by default (can be overridden)
  - Proper error handling ensures items are saved even if R2 upload fails

- **Presigned URLs**: 
  - CSV downloads include presigned URLs (7-day expiration) for direct file access
  - URLs work directly in browsers - no authentication needed
  - Valid for 7 days from generation
  - Includes proper Content-Disposition headers for downloads
  - Works even if R2 bucket is private

- **Source File Tracking**: 
  - Each scraped item is tagged with its source CSV file (`source_file` column)
  - Download CSV files filtered by specific input CSV file
  - Includes items from all scraping sessions for that source file
  - Automatically filters by keywords from the most recent scraping session
  - Ensures downloaded CSV matches current CSV file content

- **Resumable Scraping**: 
  - Re-uploading the same CSV file will skip already-scraped keywords
  - Prevents duplicate work across sessions
  - Tracks by URL and content hash

- **PDF Search with Exa API**:
  - High-quality semantic search (understands meaning, not just keywords)
  - Multiple query variations for better results
  - Automatically filters for PDF file types
  - Default API key included (can be overridden)

- **YouTube Video Download**:
  - Multi-strategy retry system for reliable downloads
  - Tries different formats and player clients automatically
  - Downloads videos as MP4 files
  - Filters out shorts, music videos, and irrelevant content

## Project Structure

```
simple_pipeline/
├── backend/
│   ├── app/
│   │   ├── config.py          # Configuration settings
│   │   ├── database.py         # Database models
│   │   ├── main.py            # FastAPI application
│   │   ├── models.py          # Pydantic models
│   │   ├── routes/
│   │   │   └── scraping.py    # API endpoints
│   │   └── scraper/
│   │       ├── base.py         # Base scraper class
│   │       ├── manager.py      # Scraper manager
│   │       ├── pdf_scraper.py  # PDF scraper
│   │       ├── image_scraper.py # Image scraper
│   │       └── youtube_scraper.py # YouTube scraper
│   ├── docker-compose.yml     # Docker services
│   ├── requirements.txt      # Python dependencies
│   ├── init_db.py            # Database initialization
│   └── clear_database.py     # Database clearing script
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Main React component
│   │   ├── index.css         # Styles
│   │   └── main.jsx          # React entry point
│   └── package.json          # Node dependencies
│
├── backend/
│   ├── app/
│   │   ├── storage/
│   │   │   └── r2_storage.py  # Cloudflare R2 storage integration
│   │   └── ...
│   └── ...
├── keywords1.csv            # Sample input file (not in repo - gitignored)
├── keywords2.csv            # Sample input file (not in repo - gitignored)
├── SETUP_GUIDE.md          # Detailed setup instructions
├── QUICK_START.md          # Quick start guide
└── README.md               # This file
```

## Configuration

### Scraping Limits

Edit `backend/app/config.py`:
```python
MAX_RESULTS_PER_KEYWORD: int = 2  # Items per keyword per content type
```

### Database

Default connection: `postgresql://postgres:postgres@localhost:5432/scraping_pipeline_new`

Edit `backend/app/config.py` to change database settings.

### Cloudflare R2 Storage

**Default credentials are included in `backend/app/config.py`** - the system works out of the box!

To use your own R2 bucket:

1. Create a Cloudflare R2 bucket
2. Generate R2 API tokens (Access Key ID and Secret Access Key)
3. Enable "Public Access" in R2 bucket settings (or use custom domain)
4. Get your Public Development URL (if using public access)
5. Update `backend/app/config.py` or set environment variables:
   - `R2_ACCOUNT_ID` - Your Cloudflare account ID
   - `R2_BUCKET_NAME` - Your R2 bucket name
   - `R2_ACCESS_KEY_ID` - R2 access key
   - `R2_SECRET_ACCESS_KEY` - R2 secret key
   - `R2_ENDPOINT_URL` - R2 endpoint URL (default: `https://{ACCOUNT_ID}.r2.cloudflarestorage.com`)
   - `R2_PUBLIC_URL` - Public development URL (e.g., `https://pub-xxxxx.r2.dev`) - Optional but recommended

**Note**: All scraped content (PDFs, Images, YouTube videos) is automatically uploaded to R2. Files are organized in folders: `pdfs/`, `images/`, `youtube/`.

### Exa API (for PDF Search)

**Default API key is included in `backend/app/config.py`** - PDF search works out of the box!

To use your own Exa API key:

1. Get API key from https://exa.ai
2. Update `backend/app/config.py` or set environment variable:
   - `EXA_API_KEY` - Your Exa API key

**Note**: The Exa API provides high-quality semantic search for PDFs, finding documents based on meaning rather than just keyword matching. This results in more relevant PDF results.

## API Endpoints

### Scraping
- `POST /api/scraping/upload-csv` - Upload CSV files and start scraping
- `GET /api/scraping/progress/{task_id}` - Get scraping progress (PDF, Image, YouTube counts)
- `GET /api/scraping/items` - Get scraped items (filtered by task_id)

### Downloads
- `GET /api/scraping/download-bulk` - Download items as ZIP (PDF/Image)
- `GET /api/scraping/download-youtube-csv` - Download YouTube items as CSV
- `GET /api/scraping/download-source-file-csv` - Download all items for a specific source CSV file
  - Parameters: `source_file` (required), `task_id` (optional)
  - Returns CSV with all columns including presigned URLs (7-day expiration)
  - Filters items by keywords from most recent scraping session
  - Includes items from all scraping sessions for that source file
- `GET /api/scraping/download/{item_id}` - Download a single item

### Source Files
- `GET /api/scraping/source-files` - Get list of source CSV files for a task

### Management
- `POST /api/scraping/clear-database` - Clear all items from database

## Key Features Details

### Cloudflare R2 Storage
- **Automatic Upload**: All scraped content (PDFs, Images, YouTube videos) is automatically uploaded to R2
- **File Organization**: Files are organized by content type:
  - `pdfs/keyword_pdf_hash.pdf`
  - `images/keyword_image_hash.jpg`
  - `youtube/item_XXX_keyword_video.mp4`
- **R2 Keys**: Each file gets a unique R2 key stored in database
- **Public URLs**: Public URLs are generated if `R2_PUBLIC_URL` is configured
- **Presigned URLs**: Generated on-demand for CSV downloads (7-day expiration)
- **Error Handling**: Items are saved to database even if R2 upload fails
- **Content Headers**: Proper Content-Disposition and Cache-Control headers for browser downloads

### CSV Download with Presigned URLs
- **Source File Filtering**: Download CSV files filtered by specific input CSV file
- **Keyword Matching**: Automatically filters items to match keywords from most recent scraping session
- **All Sessions**: Includes items from all scraping sessions for that source file
- **Presigned URLs**: Includes presigned URLs (7-day expiration) for direct file access
  - Click URLs directly in CSV to download/view files
  - No authentication needed for 7 days
  - Works even if R2 bucket is private
- **Complete Metadata**: Includes all columns:
  - `id` - Database ID
  - `keyword` - Search keyword
  - `scraped_url` - Original URL
  - `content_type` - PDF, IMAGE, or YOUTUBE
  - `title` - Item title
  - `task_id` - Scraping session ID
  - `source_file` - Source CSV file name
  - `created_at` - Timestamp
  - `cloudflarer2_url` - Presigned URL (7-day expiration) for direct file access
  - `cloudflarer2_key` - R2 storage key

### PDF Scraping with Exa API
- Uses Exa API for high-quality semantic PDF search
- Finds relevant PDFs based on keyword meaning, not just text matching
- Automatically filters for PDF file types
- Multiple query variations for better results

### YouTube Video Download
- Multi-strategy retry system for reliable downloads
- Tries different formats (worst, best, auto-select) and player clients (web, android, ios)
- Downloads videos as MP4 files
- Automatically uploads to R2 storage

### Source File Tracking
- **Automatic Tagging**: Each scraped item is tagged with its source CSV file (`source_file` column)
- **Multi-File Support**: Upload multiple CSV files in one session - each item tracks its source
- **Filtered Downloads**: Download CSV files filtered by specific input CSV file
- **All Sessions**: Includes items from all scraping sessions for a given source file
- **Smart Filtering**: Automatically filters by keywords from the most recent scraping session
  - Ensures downloaded CSV matches current CSV file content
  - Prevents old items from different CSV versions from appearing

## Troubleshooting

### PDFs Not Found
- Ensure Exa API key is configured in `backend/app/config.py`
- Check that `exa-py` package is installed: `pip install exa-py`

### R2 Upload Failures
- **Default Credentials**: Default R2 credentials are included in `backend/app/config.py` - should work out of the box
- **Check Credentials**: Verify R2 credentials are set correctly in `backend/app/config.py` if using custom bucket
- **Bucket Permissions**: Check that R2 bucket exists and credentials have write permissions
- **Package Installation**: Ensure `boto3` package is installed: `pip install boto3`
- **Public Access**: If using public URLs, enable "Public Access" in R2 bucket settings
- **Error Handling**: Items are still saved to database even if R2 upload fails - check logs for details

### YouTube Downloads Failing
- Check internet connection
- Some videos may be region-restricted or unavailable
- System tries multiple strategies automatically

See `SETUP_GUIDE.md` for detailed troubleshooting steps.

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
