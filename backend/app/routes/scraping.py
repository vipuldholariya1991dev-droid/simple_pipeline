from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, Response
from fastapi.encoders import jsonable_encoder
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
from app.storage import r2_storage

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
            
            # Preserve resumable mode info if it exists
            resumable_mode = current_progress.get("resumable_mode", False)
            new_keywords_count = current_progress.get("new_keywords_count", 0)
            skipped_keywords_count = current_progress.get("skipped_keywords_count", 0)
            all_keywords_scraped = current_progress.get("all_keywords_scraped", False)
            
            scraping_progress[task_id] = {
                **current_progress,  # Preserve all existing fields
                "keyword": keyword,
                "total_keywords": total,
                "current_keyword_index": idx + 1,
                "pdf_count": current_pdf_count,
                "image_count": current_image_count,
                "youtube_count": current_youtube_count,
                "status": "processing",
                "resumable_mode": resumable_mode,
                "new_keywords_count": new_keywords_count,
                "skipped_keywords_count": skipped_keywords_count,
                "all_keywords_scraped": all_keywords_scraped
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
            
            # Debug: Log the counts returned from scraper
            print(f"  🔍 DEBUG: Scraper returned counts: {counts}", flush=True)
            print(f"  🔍 DEBUG: Extracted counts - PDF={pdf_added}, IMG={image_added}, YT={youtube_added}", flush=True)
            
            new_pdf_count = current_pdf_count + pdf_added
            new_image_count = current_image_count + image_added
            new_youtube_count = current_youtube_count + youtube_added
            
            scraping_progress[task_id]["pdf_count"] = new_pdf_count
            scraping_progress[task_id]["image_count"] = new_image_count
            scraping_progress[task_id]["youtube_count"] = new_youtube_count
            
            # Debug: Verify progress was updated
            updated_progress = scraping_progress.get(task_id, {})
            print(f"  🔍 DEBUG: Progress after update - PDF={updated_progress.get('pdf_count', 0)}, IMG={updated_progress.get('image_count', 0)}, YT={updated_progress.get('youtube_count', 0)}", flush=True)
            
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
    
    # RESUMABLE MODE: Check which keywords have already been scraped
    # A keyword is considered "already scraped" if it has ANY items in the database
    # from the same source_file
    already_scraped_keywords = set()
    new_keywords = []
    
    for keyword in unique_keywords:
        source_file = keyword_to_file.get(keyword, "unknown")
        # Check if this keyword from this source_file has any items in database
        existing_items = db.query(ScrapedItem).filter(
            ScrapedItem.keyword == keyword,
            ScrapedItem.source_file == source_file
        ).first()
        
        if existing_items:
            already_scraped_keywords.add(keyword)
        else:
            new_keywords.append(keyword)
    
    # Use resumable mode if there are any already-scraped keywords
    # If all keywords are already scraped, still enable resumable mode but keywords_to_process will be empty
    resumable_mode = len(already_scraped_keywords) > 0
    keywords_to_process = new_keywords if resumable_mode else unique_keywords
    
    # If all keywords are already scraped, warn user
    if resumable_mode and len(new_keywords) == 0:
        print(f"\n⚠️  ALL KEYWORDS ALREADY SCRAPED", flush=True)
        print(f"   ⏭️  All {len(already_scraped_keywords)} keywords from this CSV have already been scraped.", flush=True)
        print(f"   💡 No new keywords to process. Task will complete immediately.", flush=True)
    
    if resumable_mode:
        print(f"\n🔄 RESUMABLE MODE ACTIVATED", flush=True)
        print(f"   ✅ {len(new_keywords)} new keywords will be scraped", flush=True)
        print(f"   ⏭️  {len(already_scraped_keywords)} already-scraped keywords skipped: {sorted(already_scraped_keywords)}", flush=True)
    
    # Cancel all old running tasks (but keep old items in database)
    # IMPORTANT: We keep ALL items from ALL scraping sessions in the database.
    # The frontend filters by task_id to show only the current session.
    # Duplicate detection checks against ALL items across ALL sessions.
    print(f"\n⚠️  Cancelling all old running tasks (keeping all items in database)...", flush=True)
    for old_task_id in list(scraping_progress.keys()):
        if scraping_progress[old_task_id].get("status") == "processing":
            cancelled_tasks.add(old_task_id)
            scraping_progress[old_task_id]["status"] = "cancelled"
            print(f"   ✅ Cancelled old task: {old_task_id}", flush=True)
    
    # Keep all old items in database - don't delete them
    # All scraping sessions will accumulate items in the database
    total_items_count = db.query(ScrapedItem).count()
    print(f"   ℹ️  Total items in database (kept from all sessions): {total_items_count}", flush=True)
    
    # Create task ID
    task_id = f"task_{datetime.now().timestamp()}"
    
    # Store allowed keywords for validation (use all keywords, not just new ones)
    allowed_keywords_set = set(unique_keywords)
    
    # Initialize progress
    scraping_progress[task_id] = {
        "keyword": "",
        "total_keywords": len(keywords_to_process),  # Only new keywords to process
        "current_keyword_index": 0,
        "pdf_count": 0,
        "image_count": 0,
        "youtube_count": 0,
        "status": "processing",
        "files": file_names,  # Track which files were used
        "allowed_keywords": allowed_keywords_set,  # Store allowed keywords for validation
        "keyword_to_file": keyword_to_file,  # Map keyword to source file
        "resumable_mode": resumable_mode,  # Track if resumable mode is active
        "new_keywords_count": len(new_keywords),  # Number of new keywords to scrape
        "skipped_keywords_count": len(already_scraped_keywords) if resumable_mode else 0,  # Number of skipped keywords
        "all_keywords_scraped": resumable_mode and len(new_keywords) == 0  # Flag when all keywords are already scraped
    }
    
    # Start background task
    print(f"\n🚀 Starting NEW scraping task {task_id}", flush=True)
    print(f"   📄 Files: {', '.join(file_names)}", flush=True)
    print(f"   📋 Total keywords in CSV: {len(unique_keywords)}", flush=True)
    print(f"   📋 Keywords to process: {len(keywords_to_process)}", flush=True)
    if resumable_mode:
        print(f"   🔄 Resumable mode: {len(new_keywords)} new, {len(already_scraped_keywords)} skipped", flush=True)
    print(f"   📋 Content types: PDF={scrape_pdf_bool}, Image={scrape_image_bool}, YouTube={scrape_youtube_bool}", flush=True)
    background_tasks.add_task(
        background_scrape_task,
        keywords_to_process, scrape_pdf_bool, scrape_image_bool, scrape_youtube_bool, task_id, db, keyword_to_file
    )
    
    return {
        "task_id": task_id, 
        "total_keywords": len(keywords_to_process),
        "files_processed": len(files),
        "resumable_mode": resumable_mode,
        "new_keywords_count": len(new_keywords),
        "skipped_keywords_count": len(already_scraped_keywords) if resumable_mode else 0,
        "all_keywords_scraped": resumable_mode and len(new_keywords) == 0  # Flag when all keywords are already scraped
    }

@router.get("/progress/{task_id}")
async def get_progress(task_id: str):
    """Get scraping progress"""
    if task_id not in scraping_progress:
        raise HTTPException(status_code=404, detail="Task not found")
    
    progress_data = scraping_progress[task_id]
    # Debug: Log what we're returning
    print(f"  🔍 DEBUG: Progress endpoint returning for task {task_id}: PDF={progress_data.get('pdf_count', 0)}, IMG={progress_data.get('image_count', 0)}, YT={progress_data.get('youtube_count', 0)}", flush=True)
    
    return progress_data

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

@router.get("/items")
async def get_items(
    task_id: Optional[str] = None,
    all_items: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get scraped items - filter by task_id if provided, or return all items if all_items=True
    
    Returns:
        {
            "items": List[ScrapedItemResponse],
            "total": int,
            "limit": int,
            "offset": int
        }
    """
    from typing import List

    print(
        f"ℹ️ get_items called with task_id={task_id}, all_items={all_items}, "
        f"limit={limit}, offset={offset}"
    )

    # Normalize all_items flag (handles bool or string values from query params)
    if isinstance(all_items, str):
        all_items_flag = all_items.strip().lower() in {"true", "1", "yes", "on"}
    else:
        all_items_flag = bool(all_items)
    print(f"ℹ️ all_items_flag evaluated to {all_items_flag} (type={type(all_items)})")

    # If all_items=True, return all items from database (for download page)
    if all_items_flag:
        query = db.query(ScrapedItem)
        total = query.count()

        # Allow limit <= 0 to fetch all items without pagination
        if limit and limit > 0:
            items_query = (
                query.order_by(ScrapedItem.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        else:
            items_query = query.order_by(ScrapedItem.created_at.desc())

        items = items_query.all()

        if limit and limit > 0:
            print(
                f"🔍 Fetching ALL items: {len(items)} items "
                f"(offset={offset}, limit={limit}, total={total})"
            )
        else:
            print(
                f"🔍 Fetching ALL items without pagination: {len(items)} items "
                f"(total={total})"
            )
        print(
            f"🔍 Fetching ALL items: {len(items)} items "
            f"(offset={offset}, limit={limit}, total={total})"
        )

        # Serialize items and generate presigned URLs for R2 items
        serialized_items = []
        for item in items:
            item_dict = ScrapedItemResponse.model_validate(item).model_dump()
            # Generate presigned URL (7 days = 604800 seconds) if r2_key exists
            if item.r2_key and r2_storage.is_available():
                try:
                    presigned_url = r2_storage.get_download_url(
                        item.r2_key, 
                        expires_in=604800,  # 7 days
                        force_presigned=True
                    )
                    if presigned_url:
                        item_dict['r2_url'] = presigned_url
                except Exception as e:
                    print(f"⚠️  Could not generate presigned URL for item {item.id}: {e}")
            serialized_items.append(item_dict)
        
        return jsonable_encoder(
            {
                "items": serialized_items,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        )

    # If task_id provided, filter by task_id (backward compatibility)
    if task_id:
        query = (
            db.query(ScrapedItem)
            .filter(ScrapedItem.task_id == task_id)
            .filter(ScrapedItem.task_id.isnot(None))
        )
        total = query.count()
        items = (
            query.order_by(ScrapedItem.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        print(f"🔍 Filtering items by task_id: {task_id}")
        print(f"📊 Found {len(items)} items for task_id: {task_id} (total={total})")

        # Debug: Check if any items have different task_id
        if len(items) > 0:
            task_ids = {item.task_id for item in items if item.task_id}
            if len(task_ids) > 1 or (task_ids and task_id not in task_ids):
                print(f"⚠️  WARNING: Found items with different task_ids: {task_ids}")

        # Serialize items and generate presigned URLs for R2 items
        serialized_items = []
        for item in items:
            item_dict = ScrapedItemResponse.model_validate(item).model_dump()
            # Generate presigned URL (7 days = 604800 seconds) if r2_key exists
            if item.r2_key and r2_storage.is_available():
                try:
                    presigned_url = r2_storage.get_download_url(
                        item.r2_key, 
                        expires_in=604800,  # 7 days
                        force_presigned=True
                    )
                    if presigned_url:
                        item_dict['r2_url'] = presigned_url
                except Exception as e:
                    print(f"⚠️  Could not generate presigned URL for item {item.id}: {e}")
            serialized_items.append(item_dict)
        # Return as list for backward compatibility (old frontend code expects list)
        return jsonable_encoder(serialized_items)

    # No task_id and all_items=False - return empty list
    print("⚠️  No task_id provided and all_items=False, returning empty list")
    return []

@router.get("/download/{item_id}")
async def download_item(item_id: int, db: Session = Depends(get_db)):
    """Download an item - use R2 URL if available, otherwise proxy from original URL"""
    import httpx
    from app.storage import r2_storage
    
    item = db.query(ScrapedItem).filter(ScrapedItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.content_type == ContentType.YOUTUBE:
        raise HTTPException(status_code=400, detail="YouTube videos cannot be downloaded directly through this API")
    
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            # Prefer R2 URL if available - generate presigned URL if needed
            download_url = None
            if item.r2_key:
                from app.storage import r2_storage
                download_url = r2_storage.get_download_url(item.r2_key)
            elif item.r2_url:
                download_url = item.r2_url
            else:
                download_url = item.url
            
            # Fetch the file from R2 or original URL
            response = await client.get(download_url)
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
                # Use R2 storage helper if R2 URL is available
                if item.r2_url:
                    ext = r2_storage.get_file_extension("image", item.url)
                    media_type = r2_storage.get_content_type("image", item.url)
                else:
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

@router.get("/source-files")
async def get_source_files(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Get unique source files (CSV files) for a task"""
    if not task_id:
        return {"source_files": []}
    
    # First, try to get source files from progress tracking (files that were uploaded)
    if task_id in scraping_progress:
        progress_data = scraping_progress[task_id]
        uploaded_files = progress_data.get("files", [])
        if uploaded_files:
            # Return the files that were uploaded, even if they don't have items yet
            return {"source_files": uploaded_files}
    
    # Fallback: Get distinct source files from database (files that have items)
    # This handles cases where progress tracking might not be available
    source_files = db.query(ScrapedItem.source_file).filter(
        ScrapedItem.task_id == task_id,
        ScrapedItem.source_file.isnot(None)
    ).distinct().all()
    
    # Extract file names from tuples
    file_names = [file[0] for file in source_files if file[0]]
    
    return {"source_files": file_names}

@router.get("/download-source-file-csv")
async def download_source_file_csv(
    source_file: str,
    task_id: Optional[str] = None,  # Optional - kept for backward compatibility but not used
    db: Session = Depends(get_db)
):
    """Download all items for a specific source file as CSV with all columns
    Filters items to only include keywords that match the current CSV file content.
    If task_id is provided, uses keywords from that task. Otherwise, uses keywords from the most recent task.
    """
    from app.storage import r2_storage
    
    if not source_file:
        raise HTTPException(status_code=400, detail="source_file is required")
    
    # First, get the keywords that were actually scraped for this source_file
    # We'll use the most recent task_id for this source_file, or the provided task_id
    target_task_id = task_id
    
    if not target_task_id:
        # Find the most recent task_id that used this source_file
        most_recent_task = db.query(ScrapedItem.task_id).filter(
            ScrapedItem.source_file == source_file,
            ScrapedItem.task_id.isnot(None)
        ).order_by(ScrapedItem.created_at.desc()).first()
        
        if most_recent_task:
            target_task_id = most_recent_task[0]
            print(f"📋 Using most recent task_id for {source_file}: {target_task_id}", flush=True)
    
    # Get unique keywords from the target task (these are the keywords that match the current CSV)
    valid_keywords = set()
    if target_task_id:
        keyword_rows = db.query(ScrapedItem.keyword).filter(
            ScrapedItem.source_file == source_file,
            ScrapedItem.task_id == target_task_id
        ).distinct().all()
        valid_keywords = {row[0] for row in keyword_rows if row[0]}
        print(f"📋 Found {len(valid_keywords)} unique keywords in task {target_task_id} for {source_file}", flush=True)
    
    # Get all items for this source file, but filter by valid keywords if we have them
    query = db.query(ScrapedItem).filter(
        ScrapedItem.source_file == source_file
    )
    
    # Filter by valid keywords if we found them (to match current CSV content)
    if valid_keywords:
        query = query.filter(ScrapedItem.keyword.in_(valid_keywords))
        print(f"🔍 Filtering items to match {len(valid_keywords)} keywords from current CSV", flush=True)
    
    items = query.order_by(ScrapedItem.created_at.asc()).all()
    
    # Log breakdown for debugging
    if items:
        unique_keywords = set(item.keyword for item in items)
        unique_task_ids = set(item.task_id for item in items if item.task_id)
        content_type_counts = {}
        for item in items:
            ct = item.content_type.value if hasattr(item.content_type, 'value') else str(item.content_type)
            content_type_counts[ct] = content_type_counts.get(ct, 0) + 1
        
        print(f"📊 CSV Download for {source_file}:", flush=True)
        print(f"   Total items: {len(items)}", flush=True)
        print(f"   Unique keywords: {len(unique_keywords)}", flush=True)
        print(f"   Scraping sessions (task_ids): {len(unique_task_ids)}", flush=True)
        print(f"   Content type breakdown: {content_type_counts}", flush=True)
    
    if not items:
        raise HTTPException(status_code=404, detail=f"No items found for source file: {source_file}")
    
    # Create CSV content
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header with all required columns
    writer.writerow([
        'id',
        'keyword',
        'scraped_url',
        'content_type',
        'title',
        'task_id',
        'source_file',
        'created_at',
        'cloudflarer2_dashboard_url',  # Dashboard URL - click to navigate to Cloudflare dashboard (shows objects list filtered by prefix)
        'cloudflarer2_download_url',  # Presigned URL (7 days) - click to download/view file directly
        'cloudflarer2_key'
    ])
    
    # Write data rows
    for item in items:
        # Generate dashboard URL for Cloudflare dashboard navigation
        # Note: Cloudflare R2 dashboard doesn't support direct deep-linking to object details pages
        # Dashboard URL will show objects list filtered by prefix, where user can find the specific item
        r2_dashboard_url = None
        if item.r2_key:
            if r2_storage.is_available():
                r2_dashboard_url = r2_storage.get_dashboard_url(item.r2_key)
        
        # Generate presigned URL for direct file download/view (7 days expiration)
        # This URL allows direct file access but cannot navigate to dashboard
        r2_presigned_url = None
        if item.r2_key:
            if r2_storage.is_available():
                # Generate presigned URL for 7 days (604800 seconds)
                r2_presigned_url = r2_storage.get_download_url(item.r2_key, expires_in=604800, force_presigned=True)
        
        writer.writerow([
            item.id,
            item.keyword,
            item.url,
            item.content_type.value if hasattr(item.content_type, 'value') else str(item.content_type),
            item.title or '',
            item.task_id or '',
            item.source_file or '',
            item.created_at.isoformat() if item.created_at else '',
            r2_dashboard_url or '',  # Dashboard URL - navigates to Cloudflare dashboard objects list
            r2_presigned_url or '',  # Presigned URL - direct file download/view (7 days)
            item.r2_key or ''
        ])
    
    csv_content = output.getvalue()
    output.close()
    
    # Generate filename (remove .csv extension if present, then add it back)
    safe_filename = source_file.replace('.csv', '') if source_file.endswith('.csv') else source_file
    csv_filename = f"{safe_filename}_scraped_data.csv"
    
    # Return CSV file
    return Response(
        content=csv_content,
        media_type='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{csv_filename}"',
            'Content-Length': str(len(csv_content.encode('utf-8')))
        }
    )

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
    from app.storage import r2_storage
    
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
    import tempfile
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    temp_zip.close()
    
    try:
        downloaded_count = 0
        skipped_count = 0
        
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                for item in items:
                    try:
                        # Prefer R2 URL if available - generate presigned URL if needed
                        download_url = None
                        if item.r2_key:
                            from app.storage import r2_storage
                            download_url = r2_storage.get_download_url(item.r2_key)
                        elif item.r2_url:
                            download_url = item.r2_url
                        else:
                            download_url = item.url
                        
                        # Fetch the file from R2 or original URL
                        response = await client.get(download_url)
                        if response.status_code != 200:
                            print(f"⚠️  Failed to fetch {download_url}: HTTP {response.status_code}")
                            skipped_count += 1
                            continue
                        
                        # Check file size
                        content_length = len(response.content)
                        max_size = settings.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024
                        if content_length > max_size:
                            print(f"⚠️  File too large for {download_url}: {content_length} bytes")
                            skipped_count += 1
                            continue
                        
                        # Determine file extension using R2 storage helper
                        ext = r2_storage.get_file_extension(
                            "pdf" if item.content_type == ContentType.PDF else "image",
                            item.url
                        )
                        
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

