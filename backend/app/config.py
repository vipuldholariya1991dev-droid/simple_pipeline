from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/simple_scraping_db")
    
    # Application
    APP_NAME: str = "Simple Scraping Pipeline"
    DEBUG: bool = True
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"]
    
    # Scraping - Set to 2 items per keyword
    MAX_RESULTS_PER_KEYWORD: int = 2
    REQUEST_TIMEOUT: int = 30
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Storage
    DOWNLOADS_DIR: str = "downloads"
    MAX_DOWNLOAD_SIZE_MB: int = 500
    
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

