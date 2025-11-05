"""Database migration script to add R2 storage columns"""
from app.database import engine, Base, ScrapedItem
from sqlalchemy import text

def migrate_r2_columns():
    """Add r2_url and r2_key columns to scraped_items table"""
    print("🔄 Running database migration for R2 storage columns...")
    
    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='scraped_items' AND column_name IN ('r2_url', 'r2_key')
        """))
        existing_columns = [row[0] for row in result]
        
        # Add r2_url column if it doesn't exist
        if 'r2_url' not in existing_columns:
            print("  ✅ Adding r2_url column...")
            conn.execute(text("ALTER TABLE scraped_items ADD COLUMN r2_url TEXT"))
            conn.commit()
        else:
            print("  ℹ️  r2_url column already exists")
        
        # Add r2_key column if it doesn't exist
        if 'r2_key' not in existing_columns:
            print("  ✅ Adding r2_key column...")
            conn.execute(text("ALTER TABLE scraped_items ADD COLUMN r2_key VARCHAR(500)"))
            conn.commit()
        else:
            print("  ℹ️  r2_key column already exists")
    
    print("✅ Migration completed!")

if __name__ == "__main__":
    migrate_r2_columns()

