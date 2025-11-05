from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/scraping_pipeline_new")
    
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
    
    # Exa API (for PDF search - optional, get API key from https://exa.ai)
    EXA_API_KEY: str = os.getenv("EXA_API_KEY", "")
    
    # Cloudflare R2 Storage
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "4c9e60a2dc0dcf475cc907f3cd645f1d")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "assetblue")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_ENDPOINT_URL: str = os.getenv("R2_ENDPOINT_URL", "https://4c9e60a2dc0dcf475cc907f3cd645f1d.r2.cloudflarestorage.com")
    R2_PUBLIC_URL: str = os.getenv("R2_PUBLIC_URL", "")  # Public URL if using custom domain, otherwise will use R2 URL
    
    # Oxylabs Proxy (for YouTube scraping)
    OXYLABS_USERNAME: str = os.getenv("OXYLABS_USERNAME", "usrsh10151")
    OXYLABS_PASSWORD: str = os.getenv("OXYLABS_PASSWORD", "5vheo3r2m71rmoxkp0suwj82")
    OXYLABS_ENDPOINT: str = os.getenv("OXYLABS_ENDPOINT", "nam1bd158a6d4buib42a7xdx.hbproxy.net")
    OXYLABS_PORT: int = int(os.getenv("OXYLABS_PORT", "8000"))  # Default SOCKS5 port for Oxylabs
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

