from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import ContentType

class ScrapedItemResponse(BaseModel):
    id: int
    keyword: str
    url: str
    content_type: ContentType
    title: Optional[str]
    description: Optional[str]
    file_size: Optional[int]
    downloaded: Optional[str]
    r2_url: Optional[str]  # Cloudflare R2 storage URL
    r2_key: Optional[str]  # R2 object key
    source_file: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProgressUpdate(BaseModel):
    keyword: str
    total_keywords: int
    current_keyword_index: int
    pdf_count: int
    image_count: int
    youtube_count: int
    status: str

