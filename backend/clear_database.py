#!/usr/bin/env python3
"""Script to clear all scraped items from the database"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, ScrapedItem
from app.config import settings

def clear_database():
    """Clear all scraped items"""
    print(f"\n🗑️  CLEARING DATABASE\n")
    print(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Use raw SQL to count and delete (works even if table structure is old)
        from sqlalchemy import text
        
        # Count items
        result = db.execute(text("SELECT COUNT(*) FROM scraped_items"))
        count = result.scalar()
        print(f"\n📊 Found {count} items in database")
        
        if count > 0:
            # Delete all items using raw SQL (simple and fast)
            print(f"\n🗑️  Deleting all {count} items...")
            db.execute(text("DELETE FROM scraped_items"))
            db.commit()
            print(f"\n✅ Deleted {count} items from database")
        else:
            print("\n✅ Database is already empty")
            
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error clearing database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    clear_database()
    print("\n✅ Done!\n")

