#!/usr/bin/env python3
"""Script to check database contents"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, ScrapedItem, ContentType

def check_database():
    """Check database contents"""
    db = SessionLocal()
    try:
        print("\n📊 DATABASE ANALYSIS\n")
        print("=" * 80)
        
        # Total counts
        total = db.query(ScrapedItem).count()
        print(f"Total items: {total}")
        
        # By type
        for content_type in ContentType:
            count = db.query(ScrapedItem).filter(ScrapedItem.content_type == content_type).count()
            print(f"{content_type.name}: {count}")
        
        # By keyword
        print("\n" + "=" * 80)
        print("Items per keyword:\n")
        keywords = db.query(ScrapedItem.keyword).distinct().all()
        for (keyword,) in keywords:
            pdf_count = db.query(ScrapedItem).filter(
                ScrapedItem.keyword == keyword,
                ScrapedItem.content_type == ContentType.PDF
            ).count()
            image_count = db.query(ScrapedItem).filter(
                ScrapedItem.keyword == keyword,
                ScrapedItem.content_type == ContentType.IMAGE
            ).count()
            youtube_count = db.query(ScrapedItem).filter(
                ScrapedItem.keyword == keyword,
                ScrapedItem.content_type == ContentType.YOUTUBE
            ).count()
            
            total = pdf_count + image_count + youtube_count
            expected = 6  # 2 PDFs + 2 Images + 2 YouTube
            status = "✅" if total == expected else "⚠️"
            print(f"{status} {keyword[:55]:55} | PDF:{pdf_count:2} IMG:{image_count:2} YT:{youtube_count:2} | Total:{total} (expected {expected})")
        
        print("\n" + "=" * 80)
        print("\nExpected: 10 keywords × 2 items × 3 types = 60 items")
        print(f"Actual:   {total} items")
        print(f"Missing:  {60 - total} items")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_database()

