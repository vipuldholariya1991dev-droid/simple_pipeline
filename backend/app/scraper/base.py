from abc import ABC, abstractmethod
from typing import List, Dict
import hashlib
import httpx
from app.config import settings

class BaseScraper(ABC):
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers={"User-Agent": settings.USER_AGENT},
            follow_redirects=True
        )
    
    @abstractmethod
    async def search(self, keyword: str, max_results: int = None) -> List[Dict]:
        """Search for items based on keyword"""
        pass
    
    def calculate_hash(self, content: bytes) -> str:
        """Calculate SHA256 hash of content for duplicate detection"""
        return hashlib.sha256(content).hexdigest()
    
    async def get_content_hash(self, url: str) -> str:
        """Download content and calculate hash"""
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                return self.calculate_hash(response.content)
        except Exception as e:
            print(f"Error getting content hash for {url}: {e}")
        return None
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

