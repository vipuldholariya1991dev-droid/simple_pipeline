from typing import List, Dict
import asyncio
import subprocess
import json
import re
from app.scraper.base import BaseScraper
from app.config import settings

class YouTubeScraper(BaseScraper):
    """Scraper for YouTube using yt-dlp"""
    
    async def search(self, keyword: str, max_results: int = None) -> List[Dict]:
        """Search YouTube videos using yt-dlp"""
        if max_results is None:
            max_results = settings.MAX_RESULTS_PER_KEYWORD
        
        try:
            # Use yt-dlp to search YouTube
            search_query = f"ytsearch{max_results}:{keyword}"
            
            # Run yt-dlp in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._run_ytdlp,
                search_query
            )
            
            items = []
            if result:
                for video in result:
                    items.append({
                        "url": video.get("webpage_url", ""),
                        "title": video.get("title", ""),
                        "description": video.get("description", "")[:500] if video.get("description") else "",  # Limit description
                        "thumbnail": video.get("thumbnail", ""),
                        "duration": video.get("duration", 0),
                    })
            
            return items
        
        except Exception as e:
            print(f"Error scraping YouTube for '{keyword}': {e}")
            return []
    
    def _run_ytdlp(self, search_query: str) -> List[Dict]:
        """Run yt-dlp command synchronously"""
        try:
            # yt-dlp command to search and extract JSON
            cmd = [
                "yt-dlp",
                search_query,
                "--dump-json",
                "--no-playlist",
                "--default-search", "ytsearch",
                "--quiet",
                "--no-warnings"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            
            if result.returncode == 0 and result.stdout:
                # Parse JSON output (one JSON object per line)
                videos = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            video_data = json.loads(line)
                            videos.append(video_data)
                        except json.JSONDecodeError:
                            continue
                return videos
            else:
                print(f"yt-dlp error: {result.stderr}")
                return []
        
        except subprocess.TimeoutExpired:
            print("yt-dlp search timed out")
            return []
        except FileNotFoundError:
            print("yt-dlp not found. Please install: pip install yt-dlp")
            return []
        except Exception as e:
            print(f"Error running yt-dlp: {e}")
            return []
