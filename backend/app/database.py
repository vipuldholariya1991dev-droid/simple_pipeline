from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum as SQLEnum, Index, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum
from app.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=settings.DEBUG)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ContentType(enum.Enum):
    PDF = "pdf"
    IMAGE = "image"
    YOUTUBE = "youtube"

class ScrapedItem(Base):
    __tablename__ = "scraped_items"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(500), index=True, nullable=False)
    url = Column(Text, nullable=False)
    content_type = Column(SQLEnum(ContentType), nullable=False, index=True)
    title = Column(String(1000), nullable=True)
    description = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)
    content_hash = Column(String(64), index=True, nullable=True)
    downloaded = Column(String(500), nullable=True)
    r2_url = Column(Text, nullable=True)  # Cloudflare R2 storage URL
    r2_key = Column(String(500), nullable=True)  # R2 object key/path
    task_id = Column(String(100), index=True, nullable=True)  # Track which scraping task created this item
    source_file = Column(String(255), nullable=True)  # Track which CSV file the keyword came from
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_keyword_type', 'keyword', 'content_type'),
        Index('idx_content_hash', 'content_hash'),
        Index('idx_url', 'url'),
        Index('idx_task_id', 'task_id'),
    )

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

