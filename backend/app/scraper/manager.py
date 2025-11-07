from typing import List, Dict, Optional
from app.scraper.youtube_scraper import YouTubeScraper
from app.scraper.image_scraper import ImageScraper
from app.scraper.pdf_scraper import PDFScraper
from app.database import ContentType, ScrapedItem
from sqlalchemy.orm import Session
from app.scraper.base import BaseScraper
from app.config import settings
# Import R2 storage - will be re-checked at runtime
from app.storage import r2_storage
import asyncio
import os

class ScraperManager:
    def __init__(self):
        self.scrapers: Dict[str, BaseScraper] = {
            "youtube": YouTubeScraper(),
            "image": ImageScraper(),
            "pdf": PDFScraper(),
        }
    
    async def scrape_keyword(
        self,
        keyword: str,
        db: Session,
        scrape_pdf: bool = True,
        scrape_image: bool = True,
        scrape_youtube: bool = True,
        task_id: Optional[str] = None,
        allowed_keywords: Optional[set] = None,
        source_file: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, int]:
        """Scrape all content types for a keyword"""
        # Validate keyword if allowed_keywords is provided
        if allowed_keywords is not None and keyword not in allowed_keywords:
            print(f"  ⚠️  SKIPPING: Keyword '{keyword}' is not in allowed keywords list!", flush=True)
            return {"pdf": 0, "image": 0, "youtube": 0}
        
        counts = {"pdf": 0, "image": 0, "youtube": 0}
        
        # Get existing URLs and content hashes from database for duplicate detection
        # Check URLs per content type to avoid false positives (PDF URLs won't match Image/YouTube URLs)
        existing_pdf_urls = {url[0] for url in db.query(ScrapedItem.url).filter(
            ScrapedItem.content_type == ContentType.PDF
        ).all()} if scrape_pdf else set()
        
        existing_image_urls = {url[0] for url in db.query(ScrapedItem.url).filter(
            ScrapedItem.content_type == ContentType.IMAGE
        ).all()} if scrape_image else set()
        
        existing_youtube_urls = {url[0] for url in db.query(ScrapedItem.url).filter(
            ScrapedItem.content_type == ContentType.YOUTUBE
        ).all()} if scrape_youtube else set()
        
        existing_hashes = {h[0] for h in db.query(ScrapedItem.content_hash).filter(
            ScrapedItem.content_hash.isnot(None)
        ).all() if h[0]}
        
        print(f"  Existing URLs in DB - PDFs: {len(existing_pdf_urls)}, Images: {len(existing_image_urls)}, YouTube: {len(existing_youtube_urls)}")
        
        # Track items found in this keyword to avoid duplicates within the keyword
        keyword_urls = set()
        
        try:
            # Scrape YouTube
            if scrape_youtube:
                youtube_items = await self.scrapers["youtube"].search(keyword, max_results=settings.MAX_RESULTS_PER_KEYWORD * 3)
                print(f"  YouTube scraper found {len(youtube_items)} items for '{keyword}'")
                for item in youtube_items:
                    url = item["url"]
                    # Check if URL already exists for YouTube content type AND within this keyword
                    if url in existing_youtube_urls:
                        print(f"    Skipping duplicate YouTube URL: {url[:60]}...")
                        continue
                    if url in keyword_urls:
                        print(f"    Skipping duplicate YouTube URL within keyword: {url[:60]}...")
                        continue
                    if url not in existing_youtube_urls and url not in keyword_urls:
                        # Validate keyword is in allowed list before saving
                        if allowed_keywords is not None and keyword not in allowed_keywords:
                            print(f"    ⚠️  SKIPPING: Keyword '{keyword}' not in allowed list - cannot save to DB", flush=True)
                            continue
                        
                        # For YouTube, use URL as hash (YouTube URLs are unique)
                        url_hash = url[:64]  # Truncate to 64 chars for hash field
                        db_item = ScrapedItem(
                            keyword=keyword,
                            url=url,
                            content_type=ContentType.YOUTUBE,
                            title=item.get("title", ""),
                            description=item.get("description", ""),
                            content_hash=url_hash,
                            task_id=task_id,
                            source_file=source_file
                        )
                        db.add(db_item)
                        db.flush()  # Ensure item is saved to get the item ID
                        db.refresh(db_item)  # Refresh to get the ID
                        
                        # Download and upload YouTube video to R2
                        # Re-import to ensure we have the latest R2 storage instance
                        from app.storage import r2_storage as current_r2_storage
                        print(f"    🔍 Checking R2 availability for YouTube video upload...", flush=True)
                        print(f"    🔍 R2 client exists: {current_r2_storage.client is not None if hasattr(current_r2_storage, 'client') else 'N/A'}", flush=True)
                        if current_r2_storage.is_available():
                            print(f"    ✅ R2 storage is available, downloading and uploading YouTube video...", flush=True)
                            try:
                                # Download video using yt-dlp
                                youtube_scraper = self.scrapers["youtube"]
                                video_path = await youtube_scraper.download_video(url)
                                
                                if video_path and os.path.exists(video_path):
                                    try:
                                        # Upload video file to R2 with video/mp4 content type
                                        r2_url, r2_key = await current_r2_storage.upload_file(
                                            url, 
                                            keyword, 
                                            "youtube", 
                                            task_id,
                                            item_id=db_item.id,
                                            file_path=video_path
                                        )
                                        
                                        if r2_key:  # Success if r2_key is set
                                            db_item.r2_url = r2_url  # May be None for presigned URLs
                                            db_item.r2_key = r2_key
                                            db.commit()
                                            if r2_url:
                                                print(f"    ☁️  YouTube video uploaded to R2: {r2_url[:80]}")
                                            else:
                                                print(f"    ☁️  YouTube video uploaded to R2: {r2_key} (video/mp4)")
                                    finally:
                                        # Clean up temporary video file and directory
                                        if video_path and os.path.exists(video_path):
                                            os.unlink(video_path)
                                            # Also remove parent directory if it's a temp dir
                                            video_dir = os.path.dirname(video_path)
                                            if video_dir and os.path.exists(video_dir):
                                                try:
                                                    os.rmdir(video_dir)
                                                except:
                                                    pass  # Directory might not be empty
                                            print(f"    🗑️  Cleaned up temporary video file: {video_path}")
                                else:
                                    print(f"    ⚠️  Failed to download YouTube video: {url[:80]}...")
                                    db.commit()  # Still save the URL even if download fails
                            except Exception as e:
                                print(f"    ⚠️  Failed to upload YouTube video to R2: {e}")
                                import traceback
                                traceback.print_exc()
                                db.commit()  # Still save the URL even if upload fails
                        else:
                            db.commit()  # Save URL if R2 is not available
                        
                        print(f"    ✅ YouTube video saved: {url[:80]}...")
                        existing_youtube_urls.add(url)
                        existing_hashes.add(url_hash)
                        keyword_urls.add(url)
                        counts["youtube"] += 1
                        
                        # Stop if we've reached max_results for this keyword
                        if counts["youtube"] >= settings.MAX_RESULTS_PER_KEYWORD:
                            break
            
            # Scrape Images
            if scrape_image:
                print(f"\n🔍 Starting Image scraping for '{keyword}'...")
                image_items = await self.scrapers["image"].search(keyword, max_results=settings.MAX_RESULTS_PER_KEYWORD * 3)
                print(f"  ✅ Image scraper returned {len(image_items)} items for '{keyword}'")
                if len(image_items) == 0:
                    print(f"    ⚠️  No Images found for '{keyword}'")
                else:
                    print(f"    🖼️  Image items to process: {len(image_items)}")
                for item in image_items:
                    url = item["url"]
                    # Check if URL already exists for Image content type AND within this keyword
                    if url in existing_image_urls:
                        print(f"    Skipping duplicate Image URL: {url[:60]}...")
                        continue
                    if url in keyword_urls:
                        print(f"    Skipping duplicate Image URL within keyword: {url[:60]}...")
                        continue
                    if url not in existing_image_urls and url not in keyword_urls:
                        # Validate keyword is in allowed list before saving
                        if allowed_keywords is not None and keyword not in allowed_keywords:
                            print(f"    ⚠️  SKIPPING: Keyword '{keyword}' not in allowed list - cannot save to DB", flush=True)
                            continue
                        
                        # Skip content hash for now - it's too slow and causes timeouts
                        # Use URL-based duplicate detection only
                        content_hash = None
                        
                        db_item = ScrapedItem(
                            keyword=keyword,
                            url=url,
                            content_type=ContentType.IMAGE,
                            title=item.get("title", ""),
                            description=item.get("description", ""),
                            content_hash=content_hash,
                            task_id=task_id,
                            source_file=source_file
                        )
                        db.add(db_item)
                        db.flush()  # Ensure item is saved before R2 upload
                        
                        # Upload image to R2
                        # Re-import to ensure we have the latest R2 storage instance
                        from app.storage import r2_storage as current_r2_storage
                        print(f"    🔍 Checking R2 availability for image upload...", flush=True)
                        print(f"    🔍 R2 client exists: {current_r2_storage.client is not None if hasattr(current_r2_storage, 'client') else 'N/A'}", flush=True)
                        if current_r2_storage.is_available():
                            print(f"    ✅ R2 storage is available, uploading image...", flush=True)
                            try:
                                r2_url, r2_key = await current_r2_storage.upload_file(url, keyword, "image", task_id)
                                if r2_key:  # Success if r2_key is set (r2_url may be None for presigned URLs)
                                    db_item.r2_url = r2_url  # May be None for presigned URLs
                                    db_item.r2_key = r2_key
                                    db.commit()
                                    if r2_url:
                                        print(f"    ☁️  Image uploaded to R2: {r2_url[:80]}")
                                    else:
                                        print(f"    ☁️  Image uploaded to R2: {r2_key}")
                                else:
                                    print(f"    ⚠️  Failed to upload image to R2, but saving URL to database")
                                    db.commit()  # Still save the item even if R2 upload fails
                            except Exception as e:
                                print(f"    ⚠️  Error uploading image to R2: {e}")
                                import traceback
                                traceback.print_exc()
                                db.commit()  # Still save the item even if R2 upload fails
                        else:
                            print(f"    ⚠️  R2 storage not available, saving image URL only", flush=True)
                            from app.storage import r2_storage as current_r2_storage
                            print(f"    🔍 R2 client status: {current_r2_storage.client is not None if hasattr(current_r2_storage, 'client') else 'N/A'}", flush=True)
                            db.commit()  # Save item even if R2 is not available
                        
                        existing_image_urls.add(url)
                        keyword_urls.add(url)
                        counts["image"] += 1
                        print(f"    Added image {counts['image']}/{settings.MAX_RESULTS_PER_KEYWORD}: {url[:80]}")
                        
                        # Stop if we've reached max_results for this keyword
                        if counts["image"] >= settings.MAX_RESULTS_PER_KEYWORD:
                            break
            
            # Scrape PDFs
            if scrape_pdf:
                print(f"\n🔍 Starting PDF scraping for '{keyword}'...")
                # Use higher limit for PDFs (MAX_PDF_RESULTS_PER_KEYWORD)
                pdf_items = await self.scrapers["pdf"].search(keyword, max_results=settings.MAX_PDF_RESULTS_PER_KEYWORD)
                print(f"  ✅ PDF scraper returned {len(pdf_items)} items for '{keyword}'")
                if len(pdf_items) == 0:
                    print(f"    ⚠️  No PDFs found for '{keyword}' - check DuckDuckGo search")
                else:
                    print(f"    📄 PDF items to process: {len(pdf_items)}")
                for item in pdf_items:
                    url = item.get("url", "")
                    if not url:
                        print(f"    ⚠️  Skipping PDF item with empty URL")
                        continue
                    
                    # Check if URL already exists for PDF content type AND within this keyword
                    if url in existing_pdf_urls:
                        print(f"    Skipping duplicate PDF URL: {url[:60]}...")
                        continue
                    if url in keyword_urls:
                        print(f"    Skipping duplicate PDF URL within keyword: {url[:60]}...")
                        continue
                    
                    # Skip content hash for now - it's too slow and causes timeouts
                    # Use URL-based duplicate detection only
                    content_hash = None
                    
                    # Validate keyword is in allowed list before saving
                    if allowed_keywords is not None and keyword not in allowed_keywords:
                        print(f"    ⚠️  SKIPPING: Keyword '{keyword}' not in allowed list - cannot save to DB", flush=True)
                        continue
                    
                    try:
                        db_item = ScrapedItem(
                            keyword=keyword,
                            url=url,
                            content_type=ContentType.PDF,
                            title=item.get("title", "")[:500] if item.get("title") else "",
                            description=item.get("description", "")[:1000] if item.get("description") else "",
                            file_size=item.get("file_size"),
                            content_hash=content_hash,
                            task_id=task_id,
                            source_file=source_file
                        )
                        db.add(db_item)
                        db.flush()  # Ensure item is saved before R2 upload
                        
                        # Upload PDF to R2
                        # Re-import to ensure we have the latest R2 storage instance
                        from app.storage import r2_storage as current_r2_storage
                        print(f"    🔍 Checking R2 availability for PDF upload...", flush=True)
                        print(f"    🔍 R2 client exists: {current_r2_storage.client is not None if hasattr(current_r2_storage, 'client') else 'N/A'}", flush=True)
                        if current_r2_storage.is_available():
                            print(f"    ✅ R2 storage is available, uploading PDF...", flush=True)
                            try:
                                r2_url, r2_key = await current_r2_storage.upload_file(url, keyword, "pdf", task_id)
                                if r2_key:  # Success if r2_key is set (r2_url may be None for presigned URLs)
                                    db_item.r2_url = r2_url  # May be None for presigned URLs
                                    db_item.r2_key = r2_key
                                    db.commit()
                                    if r2_url:
                                        print(f"    ☁️  PDF uploaded to R2: {r2_url[:80]}")
                                    else:
                                        print(f"    ☁️  PDF uploaded to R2: {r2_key}")
                                else:
                                    print(f"    ⚠️  Failed to upload PDF to R2, but saving URL to database")
                                    db.commit()  # Still save the item even if R2 upload fails
                            except Exception as e:
                                print(f"    ⚠️  Error uploading PDF to R2: {e}")
                                import traceback
                                traceback.print_exc()
                                db.commit()  # Still save the item even if R2 upload fails
                        else:
                            print(f"    ⚠️  R2 storage not available, saving PDF URL only", flush=True)
                            from app.storage import r2_storage as current_r2_storage
                            print(f"    🔍 R2 client status: {current_r2_storage.client is not None if hasattr(current_r2_storage, 'client') else 'N/A'}", flush=True)
                            db.commit()  # Save item even if R2 is not available
                        
                        existing_pdf_urls.add(url)
                        keyword_urls.add(url)
                        counts["pdf"] += 1
                        print(f"    ✅ Added PDF {counts['pdf']}/{settings.MAX_PDF_RESULTS_PER_KEYWORD}: {url[:80]}")
                        print(f"    📊 PDF count for keyword '{keyword}': {counts['pdf']}")
                        
                        # Stop if we've reached max_results for this keyword
                        if counts["pdf"] >= settings.MAX_PDF_RESULTS_PER_KEYWORD:
                            print(f"    ✅ Reached max PDFs ({settings.MAX_PDF_RESULTS_PER_KEYWORD}) for keyword '{keyword}'")
                            break
                    except Exception as e:
                        print(f"    ❌ Error adding PDF to database: {e}")
                        print(f"       URL: {url[:80]}")
                        import traceback
                        traceback.print_exc()
            
            db.commit()
            print(f"✅ Committed all items for keyword '{keyword}': PDF={counts['pdf']}, IMG={counts['image']}, YT={counts['youtube']}")
            
        except Exception as e:
            db.rollback()
            print(f"❌ Error scraping keyword '{keyword}': {e}")
            import traceback
            traceback.print_exc()
            raise
        
        print(f"📊 Final counts for keyword '{keyword}': PDF={counts['pdf']}, IMG={counts['image']}, YT={counts['youtube']}")
        return counts
    
    async def close_all(self):
        """Close all scraper clients"""
        for scraper in self.scrapers.values():
            await scraper.close()

