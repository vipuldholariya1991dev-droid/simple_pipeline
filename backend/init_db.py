"""
Initialize database - creates tables
Run this after creating the database
"""
from app.database import init_db, engine, Base
from app.database import ScrapedItem, ContentType

if __name__ == "__main__":
    print("Creating database tables...")
    init_db()
    print("✅ Database tables created successfully!")
    print("\nYou can now start the backend server with:")
    print("  uvicorn app.main:app --reload --port 8001")

