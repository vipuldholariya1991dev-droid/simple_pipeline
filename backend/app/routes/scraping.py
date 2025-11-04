from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import io
import os
import zipfile
import tempfile
from datetime import datetime
import httpx

from app.database import get_db, ScrapedItem, ContentType
from app.models import ScrapedItemResponse, ProgressUpdate
from app.scraper.manager import ScraperManager
from app.config import settings

router = APIRouter(prefix="/api/scraping", tags=["scraping"])

# Global state for progress tracking
scraping_progress = {}
# Global flag to track cancelled tasks
cancelled_tasks = set()

async def background_scrape_task(
    keywords: List[str],
    scrape_pdf: bool,
    scrape_image: bool,
    scrape_youtube: bool,
    task_id: str,
    db: Session,
    keyword_to_file: dict = None
):
    """Background task for scraping - validates keywords are from allowed list"""
    import sys
    sys.stdout.flush()  # Force flush output
    
    # Get allowed keywords and keyword_to_file mapping from task metadata FIRST
    task_metadata = scraping_progress.get(task_id, {})
    allowed_keywords = task_metadata.get("allowed_keywords", set())
    keyword_to_file = keyword_to_file or task_metadata.get("keyword_to_file", {})
    
    # If not found, create from keywords list (should match CSV files)
    if not allowed_keywords:
        allowed_keywords = set(keywords)
        print(f"⚠️  WARNING: allowed_keywords not found in task metadata, using keywords list", flush=True)
    
    print(f"\n{'='*80}", flush=True)
    print(f"🚀 STARTING SCRAPING TASK: {task_id}", flush=True)
    print(f"{'='*80}\n", flush=True)
    print(f"📋 ALLOWED KEYWORDS ({len(allowed_keywords)}): {sorted(allowed_keywords)}", flush=True)
    
    manager = ScraperManager()
    total = len(keywords)
    print(f"📋 Total keywords to process: {total}", flush=True)
    print(f"📋 Keywords list: {keywords}", flush=True)
    print(f"📋 Content types: PDF={scrape_pdf}, Image={scrape_image}, YouTube={scrape_youtube}\n", flush=True)
    
    # Validate ALL keywords before processing
    invalid_keywords = [kw for kw in keywords if kw not in allowed_keywords]
    if invalid_keywords:
        print(f"❌ ERROR: Found {len(invalid_keywords)} invalid keywords that are NOT in allowed list!", flush=True)
        print(f"   Invalid keywords: {invalid_keywords}", flush=True)
        print(f"   These will be SKIPPED!", flush=True)
    
    try:
        for idx, keyword in enumerate(keywords):
            # Check if task was cancelled
            if task_id in cancelled_tasks:
                print(f"\n⚠️  TASK CANCELLED: {task_id}", flush=True)
                scraping_progress[task_id]["status"] = "cancelled"
                break
            
            keyword = keyword.strip()
            if not keyword:
                continue
            
            # STRICT VALIDATION: keyword MUST be in allowed list
            if keyword not in allowed_keywords:
                print(f"\n❌ SKIPPING keyword '{keyword}' - NOT in allowed keywords list!", flush=True)
                print(f"   Allowed keywords: {sorted(allowed_keywords)}", flush=True)
                print(f"   This keyword will NOT be scraped or saved to database!", flush=True)
                continue
            
            print(f"\n{'='*80}", flush=True)
            print(f"📝 Processing keyword {idx + 1}/{total}: '{keyword}'", flush=True)
            print(f"{'='*80}", flush=True)
            
            # Preserve existing counts when updating progress
            current_progress = scraping_progress.get(task_id, {})
            current_pdf_count = current_progress.get("pdf_count", 0)
            current_image_count = current_progress.get("image_count", 0)
            current_youtube_count = current_progress.get("youtube_count", 0)
            
            scraping_progress[task_id] = {
                "keyword": keyword,
                "total_keywords": total,
                "current_keyword_index": idx + 1,
                "pdf_count": current_pdf_count,
                "image_count": current_image_count,
                "youtube_count": current_youtube_count,
                "status": "processing"
            }
            
            # Get source file for this keyword
            source_file = keyword_to_file.get(keyword, "unknown")
            
            counts = await manager.scrape_keyword(
                keyword, db, scrape_pdf, scrape_image, scrape_youtube, 
                task_id=task_id, allowed_keywords=allowed_keywords, source_file=source_file
            )
            
            # Update counts - use the actual counts returned from scraper
            pdf_added = counts.get("pdf", 0)
            image_added = counts.get("image", 0)
            youtube_added = counts.get("youtube", 0)
            
            new_pdf_count = current_pdf_count + pdf_added
            new_image_count = current_image_count + image_added
            new_youtube_count = current_youtube_count + youtube_added
            
            scraping_progress[task_id]["pdf_count"] = new_pdf_count
            scraping_progress[task_id]["image_count"] = new_image_count
            scraping_progress[task_id]["youtube_count"] = new_youtube_count
            
            print(f"\n✅ COMPLETED keyword '{keyword}'", flush=True)
            print(f"📊 Items added this keyword: PDF={pdf_added}, IMG={image_added}, YT={youtube_added}", flush=True)
            print(f"📊 Total progress so far: PDF={new_pdf_count} (was {current_pdf_count} + {pdf_added}), IMG={new_image_count} (was {current_image_count} + {image_added}), YT={new_youtube_count} (was {current_youtube_count} + {youtube_added})", flush=True)
        
        scraping_progress[task_id]["status"] = "completed"
        print(f"✅ Task {task_id} completed successfully")
        print(f"   Final counts: PDF={scraping_progress[task_id]['pdf_count']}, IMG={scraping_progress[task_id]['image_count']}, YT={scraping_progress[task_id]['youtube_count']}")
    except Exception as e:
        scraping_progress[task_id]["status"] = f"error: {str(e)}"
        print(f"❌ Task {task_id} failed with error: {str(e)}")
    finally:
        await manager.close_all()
        print(f"🔒 Task {task_id} cleanup complete - no more items will be added")

@router.post("/upload-csv")
async def upload_csv(
    files: List[UploadFile] = File(..., alias="files"),
    scrape_pdf: str = Form("false"),
    scrape_image: str = Form("false"),
    scrape_youtube: str = Form("false"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """Upload multiple CSV files and start scraping"""
    all_keywords = []
    keyword_to_file = {}  # Map keyword to source file
    
    # Process all CSV files
    file_names = []
    for file in files:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail=f"File {file.filename} must be a CSV file")
        
        file_names.append(file.filename)
        content = await file.read()
        text_content = content.decode('utf-8')
        
        # Parse CSV
        csv_reader = csv.reader(io.StringIO(text_content))
        keywords = [row[0].strip() for row in csv_reader if row and row[0].strip()]
        # Map each keyword to its source file
        for keyword in keywords:
            keyword_to_file[keyword] = file.filename
        all_keywords.extend(keywords)
        print(f"📄 Processed file: {file.filename} - Found {len(keywords)} keywords", flush=True)
    
    if not all_keywords:
        raise HTTPException(status_code=400, detail="No keywords found in CSV files")
    
    # Remove duplicates while preserving order, but keep first file assignment
    seen = set()
    unique_keywords = []
    for keyword in all_keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)
    
    # Convert string form data to boolean
    scrape_pdf_bool = scrape_pdf.lower() in ("true", "1", "yes", "on")
    scrape_image_bool = scrape_image.lower() in ("true", "1", "yes", "on")
    scrape_youtube_bool = scrape_youtube.lower() in ("true", "1", "yes", "on")
    
    # Cancel all old running tasks AND delete old items from database
    print(f"\n⚠️  Cancelling all old tasks and clearing old items...", flush=True)
    old_items_count = 0
    for old_task_id in list(scraping_progress.keys()):
        if scraping_progress[old_task_id].get("status") == "processing":
            cancelled_tasks.add(old_task_id)
            scraping_progress[old_task_id]["status"] = "cancelled"
            print(f"   ✅ Cancelled old task: {old_task_id}", flush=True)
    
    # Delete all old items from database (items without task_id or with old task_ids)
    try:
        # Count items to delete
        old_items_count = db.query(ScrapedItem).count()
        
        if old_items_count > 0:
            # Delete all items from database
            db.query(ScrapedItem).delete()
            db.commit()
            print(f"   ✅ Deleted {old_items_count} old items from database", flush=True)
        else:
            print(f"   ✅ Database is already empty", flush=True)
    except Exception as e:
        db.rollback()
        print(f"   ⚠️  Warning: Could not clear old items: {e}", flush=True)
    
    # Create task ID
    task_id = f"task_{datetime.now().timestamp()}"
    
    # Store allowed keywords for validation
    allowed_keywords_set = set(unique_keywords)
    
    # Initialize progress
    scraping_progress[task_id] = {
        "keyword": "",
        "total_keywords": len(unique_keywords),
        "current_keyword_index": 0,
        "pdf_count": 0,
        "image_count": 0,
        "youtube_count": 0,
        "status": "processing",
        "files": file_names,  # Track which files were used
        "allowed_keywords": allowed_keywords_set,  # Store allowed keywords for validation
        "keyword_to_file": keyword_to_file  # Map keyword to source file
    }
    
    # Start background task
    print(f"\n🚀 Starting NEW scraping task {task_id}", flush=True)
    print(f"   📄 Files: {', '.join(file_names)}", flush=True)
    print(f"   📋 Total keywords: {len(unique_keywords)}", flush=True)
    print(f"   📋 Allowed keywords: {sorted(unique_keywords)}", flush=True)
    print(f"   📋 Content types: PDF={scrape_pdf_bool}, Image={scrape_image_bool}, YouTube={scrape_youtube_bool}", flush=True)
    background_tasks.add_task(
        background_scrape_task,
        unique_keywords, scrape_pdf_bool, scrape_image_bool, scrape_youtube_bool, task_id, db, keyword_to_file
    )
    
    return {
        "task_id": task_id, 
        "total_keywords": len(unique_keywords),
        "files_processed": len(files)
    }

@router.get("/progress/{task_id}")
async def get_progress(task_id: str):
    """Get scraping progress"""
    if task_id not in scraping_progress:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return scraping_progress[task_id]

@router.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a running scraping task"""
    if task_id not in scraping_progress:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if scraping_progress[task_id].get("status") in ("completed", "cancelled", "error"):
        return {"message": f"Task {task_id} is already {scraping_progress[task_id].get('status')}"}
    
    cancelled_tasks.add(task_id)
    scraping_progress[task_id]["status"] = "cancelled"
    print(f"⚠️  Task {task_id} cancelled by user", flush=True)
    return {"message": f"Task {task_id} cancelled successfully"}

@router.get("/tasks")
async def list_tasks():
    """List all tasks and their status"""
    return {
        "tasks": {
            task_id: {
                "status": progress.get("status"),
                "total_keywords": progress.get("total_keywords"),
                "current_keyword_index": progress.get("current_keyword_index"),
                "files": progress.get("files", []),
                "pdf_count": progress.get("pdf_count", 0),
                "image_count": progress.get("image_count", 0),
                "youtube_count": progress.get("youtube_count", 0),
            }
            for task_id, progress in scraping_progress.items()
        }
    }

@router.post("/clear-database")
async def clear_database_endpoint(db: Session = Depends(get_db)):
    """Clear all items from the database"""
    try:
        # Cancel all running tasks first
        print(f"\n⚠️  Cancelling all running tasks before clearing database...", flush=True)
        for task_id in list(scraping_progress.keys()):
            if scraping_progress[task_id].get("status") == "processing":
                cancelled_tasks.add(task_id)
                scraping_progress[task_id]["status"] = "cancelled"
                print(f"   ✅ Cancelled task: {task_id}", flush=True)
        
        # Count items before deletion
        total_count = db.query(ScrapedItem).count()
        
        if total_count > 0:
            # Delete all items
            db.query(ScrapedItem).delete()
            db.commit()
            print(f"✅ Deleted {total_count} items from database", flush=True)
            return {
                "message": f"Successfully deleted {total_count} items from database",
                "deleted_count": total_count
            }
        else:
            return {
                "message": "Database is already empty",
                "deleted_count": 0
            }
    except Exception as e:
        db.rollback()
        print(f"❌ Error clearing database: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Error clearing database: {str(e)}")

@router.get("/items", response_model=List[ScrapedItemResponse])
async def get_items(
    task_id: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get scraped items - filter by task_id if provided"""
    # ALWAYS require task_id - never show items without task_id (old items)
    if not task_id:
        print("⚠️  No task_id provided, returning empty list")
        return []
    
    # Only show items from the specified task_id
    # This explicitly excludes NULL task_id items (old items from before task_id was added)
    query = db.query(ScrapedItem).filter(
        ScrapedItem.task_id == task_id
    ).filter(
        ScrapedItem.task_id.isnot(None)  # Explicitly exclude NULL task_id items
    )
    
    items = query.order_by(ScrapedItem.created_at.desc()).offset(offset).limit(limit).all()
    print(f"🔍 Filtering items by task_id: {task_id}")
    print(f"📊 Found {len(items)} items for task_id: {task_id}")
    
    # Debug: Check if any items have different task_id
    if len(items) > 0:
        task_ids = {item.task_id for item in items if item.task_id}
        if len(task_ids) > 1 or (task_ids and task_id not in task_ids):
            print(f"⚠️  WARNING: Found items with different task_ids: {task_ids}")
    
    return items

@router.get("/download/{item_id}")
async def download_item(item_id: int, db: Session = Depends(get_db)):
    """Download an item - proxy through backend to avoid CORS"""
    import httpx
    
    item = db.query(ScrapedItem).filter(ScrapedItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.content_type == ContentType.YOUTUBE:
        raise HTTPException(status_code=400, detail="YouTube videos cannot be downloaded directly through this API")
    
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            # Fetch the file from the original URL
            response = await client.get(item.url)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch file: {response.status_code}")
            
            # Check file size
            content_length = len(response.content)
            max_size = settings.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024
            if content_length > max_size:
                raise HTTPException(status_code=413, detail=f"File too large (max {settings.MAX_DOWNLOAD_SIZE_MB}MB)")
            
            # Determine file extension and content type
            ext = ""
            media_type = 'application/octet-stream'
            if item.content_type == ContentType.PDF:
                ext = ".pdf"
                media_type = 'application/pdf'
            elif item.content_type == ContentType.IMAGE:
                content_type_header = response.headers.get('content-type', '').lower()
                url_lower = item.url.lower()
                if '.jpg' in url_lower or '.jpeg' in url_lower or 'jpeg' in content_type_header or 'jpg' in content_type_header:
                    ext = ".jpg"
                    media_type = 'image/jpeg'
                elif '.png' in url_lower or 'png' in content_type_header:
                    ext = ".png"
                    media_type = 'image/png'
                elif '.gif' in url_lower or 'gif' in content_type_header:
                    ext = ".gif"
                    media_type = 'image/gif'
                elif '.webp' in url_lower or 'webp' in content_type_header:
                    ext = ".webp"
                    media_type = 'image/webp'
                else:
                    ext = ".jpg"
                    media_type = 'image/jpeg'
            
            # Generate filename
            safe_keyword = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in item.keyword[:50])
            filename = f"{item.id}_{safe_keyword.replace(' ', '_')}{ext}"
            
            # Return the file directly as a streaming response
            from fastapi.responses import Response
            return Response(
                content=response.content,
                media_type=media_type,
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Length': str(content_length)
                }
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Download timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading: {str(e)}")

@router.get("/download-youtube-csv")
async def download_youtube_csv(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Download YouTube items as a CSV file"""
    # Get all YouTube items for this task
    items = db.query(ScrapedItem).filter(
        ScrapedItem.task_id == task_id,
        ScrapedItem.content_type == ContentType.YOUTUBE
    ).all()
    
    if not items:
        raise HTTPException(status_code=404, detail="No YouTube items found for this task")
    
    # Create CSV content
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header (ID, Keyword, URL as requested)
    writer.writerow(['ID', 'Keyword', 'URL'])
    
    # Write data rows (ID first, then Keyword, then URL)
    for item in items:
        writer.writerow([item.id, item.keyword, item.url])
    
    csv_content = output.getvalue()
    output.close()
    
    # Generate filename
    csv_filename = f"YouTube_{task_id}_{len(items)}items.csv"
    
    # Return CSV file
    return Response(
        content=csv_content,
        media_type='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{csv_filename}"',
            'Content-Length': str(len(csv_content.encode('utf-8')))
        }
    )

@router.get("/download-bulk")
async def download_bulk(
    task_id: str,
    content_type: str,
    db: Session = Depends(get_db)
):
    """Download all items of a specific content type for a task as a ZIP file"""
    import aiofiles
    
    # Validate content type - enum values are lowercase
    content_type_lower = content_type.lower()
    try:
        if content_type_lower == "pdf":
            content_type_enum = ContentType.PDF
        elif content_type_lower == "image":
            content_type_enum = ContentType.IMAGE
        elif content_type_lower == "youtube":
            content_type_enum = ContentType.YOUTUBE
        else:
            raise ValueError(f"Invalid content_type: {content_type}")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid content_type: {content_type}. Must be PDF, IMAGE, or YOUTUBE")
    
    if content_type_enum == ContentType.YOUTUBE:
        raise HTTPException(status_code=400, detail="YouTube videos cannot be downloaded as ZIP files")
    
    # Get all items for this task and content type
    items = db.query(ScrapedItem).filter(
        ScrapedItem.task_id == task_id,
        ScrapedItem.content_type == content_type_enum
    ).all()
    
    if not items:
        raise HTTPException(status_code=404, detail=f"No {content_type} items found for this task")
    
    # Create a temporary ZIP file
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    temp_zip.close()
    
    try:
        downloaded_count = 0
        skipped_count = 0
        
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                for item in items:
                    try:
                        # Fetch the file
                        response = await client.get(item.url)
                        if response.status_code != 200:
                            print(f"⚠️  Failed to fetch {item.url}: HTTP {response.status_code}")
                            skipped_count += 1
                            continue
                        
                        # Check file size
                        content_length = len(response.content)
                        max_size = settings.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024
                        if content_length > max_size:
                            print(f"⚠️  File too large for {item.url}: {content_length} bytes")
                            skipped_count += 1
                            continue
                        
                        # Determine file extension
                        ext = ""
                        if item.content_type == ContentType.PDF:
                            ext = ".pdf"
                        elif item.content_type == ContentType.IMAGE:
                            content_type_header = response.headers.get('content-type', '').lower()
                            url_lower = item.url.lower()
                            if '.jpg' in url_lower or '.jpeg' in url_lower or 'jpeg' in content_type_header or 'jpg' in content_type_header:
                                ext = ".jpg"
                            elif '.png' in url_lower or 'png' in content_type_header:
                                ext = ".png"
                            elif '.gif' in url_lower or 'gif' in content_type_header:
                                ext = ".gif"
                            elif '.webp' in url_lower or 'webp' in content_type_header:
                                ext = ".webp"
                            else:
                                ext = ".jpg"
                        
                        # Generate safe filename
                        safe_keyword = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in item.keyword[:50])
                        filename = f"{item.id}_{safe_keyword.replace(' ', '_')}{ext}"
                        
                        # Add file to ZIP
                        zipf.writestr(filename, response.content)
                        downloaded_count += 1
                        print(f"✅ Added {filename} to ZIP")
                        
                    except httpx.TimeoutException:
                        print(f"⚠️  Timeout downloading {item.url}")
                        skipped_count += 1
                        continue
                    except Exception as e:
                        print(f"⚠️  Error downloading {item.url}: {e}")
                        skipped_count += 1
                        continue
        
        if downloaded_count == 0:
            os.unlink(temp_zip.name)
            raise HTTPException(status_code=500, detail="Failed to download any files")
        
        # Generate ZIP filename
        zip_filename = f"{content_type}_{task_id}_{downloaded_count}files.zip"
        
        # Read the ZIP file
        with open(temp_zip.name, 'rb') as f:
            zip_content = f.read()
        
        # Clean up temp file
        os.unlink(temp_zip.name)
        
        # Return ZIP file
        return Response(
            content=zip_content,
            media_type='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename="{zip_filename}"',
                'Content-Length': str(len(zip_content))
            }
        )
        
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_zip.name):
            os.unlink(temp_zip.name)
        raise HTTPException(status_code=500, detail=f"Error creating ZIP file: {str(e)}")

