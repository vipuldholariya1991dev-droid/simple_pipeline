from typing import List, Dict, Optional, Tuple
import asyncio
import subprocess
import json
import re
import sys
from app.scraper.base import BaseScraper
from app.config import settings

class YouTubeScraper(BaseScraper):
    """Scraper for YouTube using yt-dlp (URLs only, no download)"""
    
    async def search(self, keyword: str, max_results: int = None) -> List[Dict]:
        """Search YouTube videos using yt-dlp (URLs only, no download)"""
        if max_results is None:
            max_results = settings.MAX_RESULTS_PER_KEYWORD
        
        print(f"🔍 Starting YouTube scraping for '{keyword}'...", flush=True)
        print(f"  📝 Using yt-dlp to search YouTube for '{keyword}' (max_results={max_results})", flush=True)
        
        try:
            # Search without proxy (direct connection)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._run_ytdlp,
                keyword,
                max_results
            )
            
            items = []
            if result:
                print(f"  ✅ yt-dlp found {len(result)} videos for '{keyword}'", flush=True)
                # Filter videos to ensure relevance (check if title contains any keyword words)
                keyword_words = set(keyword.lower().split())
                relevant_videos = []
                
                for video in result[:max_results]:
                    video_title = video.get("title", "").lower()
                    video_description = video.get("description", "").lower()
                    
                    # Check if video title or description contains at least 2 words from keyword
                    video_text = f"{video_title} {video_description}"
                    matching_words = sum(1 for word in keyword_words if word in video_text and len(word) > 3)
                    
                    # Include video if it matches at least 2 significant words (words longer than 3 chars)
                    # or if keyword is short (1-2 words)
                    if matching_words >= min(2, len([w for w in keyword_words if len(w) > 3])) or len(keyword_words) <= 2:
                        relevant_videos.append(video)
                    else:
                        print(f"    ⚠️  Skipping irrelevant video: {video.get('title', '')[:60]}...", flush=True)
                
                # If we filtered out too many, use original results but warn
                if len(relevant_videos) < max_results and len(relevant_videos) < len(result):
                    print(f"    ℹ️  Filtered {len(result) - len(relevant_videos)} irrelevant videos", flush=True)
                    # If we still have some relevant videos, use them
                    if relevant_videos:
                        result = relevant_videos[:max_results]
                    # Otherwise, use original results but log warning
                    else:
                        print(f"    ⚠️  No videos matched keyword filter, using all results", flush=True)
                        result = result[:max_results]
                else:
                    result = relevant_videos[:max_results]
                
                for idx, video in enumerate(result, 1):
                    video_url = video.get("webpage_url") or video.get("url") or ""
                    video_title = video.get("title", keyword)
                    items.append({
                        "url": video_url,
                        "title": video_title,
                        "description": video.get("description", "")[:500] if video.get("description") else "",  # Limit description
                        "thumbnail": video.get("thumbnail", ""),
                        "duration": video.get("duration", 0),
                    })
                    print(f"    ✅ Video {idx}: {video_title[:60]}...", flush=True)
            else:
                print(f"  ⚠️  yt-dlp found 0 videos for '{keyword}'", flush=True)
            
            print(f"  📊 YouTube scraper returned {len(items)} items for '{keyword}'", flush=True)
            return items
        
        except Exception as e:
            print(f"  ❌ Error scraping YouTube for '{keyword}': {e}", flush=True)
            import traceback
            traceback.print_exc()
            return []
    
    def _run_ytdlp(self, keyword: str, max_results: int) -> List[Dict]:
        """Run yt-dlp command synchronously to search YouTube (URLs only, no proxy)"""
        try:
            # yt-dlp command to search YouTube and extract JSON
            # Format: ytsearch{number}:{query}
            # Add quotes around the keyword to make it an exact phrase search
            search_query = f'ytsearch{max_results}:"{keyword}"'
            
            # Build command - use --flat-playlist to avoid format extraction issues
            # This mode only gets basic info without requiring format extraction
            cmd = [
                sys.executable, "-m", "yt_dlp",
                search_query,
                "--flat-playlist",  # Get playlist info without downloading or extracting formats
                "--print", "%(id)s|%(title)s|%(url)s|%(duration)s",  # Print specific fields
                "--no-playlist",
                "--ignore-errors",  # Continue even if some videos fail
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--extractor-args", "youtube:player_client=web",  # Use web client
                "--socket-timeout", "30"
            ]
            
            # OXYLABS PROXY CODE COMMENTED OUT - Using direct connection only
            # if use_proxy:
            #     proxy_url = f"socks5://{settings.OXYLABS_USERNAME}:{settings.OXYLABS_PASSWORD}@{settings.OXYLABS_ENDPOINT}:{settings.OXYLABS_PORT}"
            #     cmd.extend(["--proxy", proxy_url])
            #     print(f"    🔄 Using Oxylabs proxy: {settings.OXYLABS_ENDPOINT}:{settings.OXYLABS_PORT}", flush=True)
            
            print(f"    🔄 Running yt-dlp search (direct connection, no proxy)", flush=True)
            print(f"    🔄 Running yt-dlp command: {' '.join(cmd[:5])}... [command truncated]", flush=True)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,  # 3 minute timeout
                check=False
            )
            
            # Debug: Print stderr first to see any errors
            if result.stderr:
                error_msg = result.stderr.strip()
                # Only show first part of stderr to avoid spam
                error_lines = error_msg.split('\n')
                # Filter out common warnings that don't affect search results
                important_errors = [line for line in error_lines if 'ERROR' in line or 'Unable to download' in line]
                if important_errors:
                    print(f"    📝 Important errors: {important_errors[0][:200]}...", flush=True)
            
            # Parse flat-playlist output format: id|title|url|duration
            videos = []
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if not line or line.startswith('ERROR') or line.startswith('WARNING'):
                        continue
                    
                    # Parse format: id|title|url|duration
                    parts = line.split('|', 3)
                    if len(parts) >= 2:
                        video_id = parts[0].strip()
                        video_title = parts[1].strip() if len(parts) > 1 else video_id
                        video_url = parts[2].strip() if len(parts) > 2 else f"https://www.youtube.com/watch?v={video_id}"
                        video_duration = parts[3].strip() if len(parts) > 3 else "0"
                        
                        # Ensure we have a valid YouTube URL
                        if not video_url.startswith('http'):
                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                        
                        videos.append({
                            'id': video_id,
                            'title': video_title,
                            'webpage_url': video_url,
                            'url': video_url,
                            'duration': int(video_duration) if video_duration.isdigit() else 0
                        })
                
                if videos:
                    print(f"    ✅ Successfully parsed {len(videos)} videos from search results", flush=True)
                    return videos
                else:
                    print(f"    ⚠️  No valid video data found in output", flush=True)
                    if result.returncode != 0:
                        print(f"    ⚠️  yt-dlp returned error code: {result.returncode}", flush=True)
                    # Debug: show first 500 chars of stdout if no videos found
                    if result.stdout:
                        print(f"    📝 Debug stdout preview: {result.stdout[:500]}...", flush=True)
                    # Also show stderr for debugging
                    if result.stderr:
                        stderr_lines = result.stderr.strip().split('\n')
                        if stderr_lines:
                            print(f"    📝 Last stderr line: {stderr_lines[-1][:200]}...", flush=True)
                    return []
            else:
                print(f"    ⚠️  yt-dlp returned no output (stdout empty)", flush=True)
                if result.stderr:
                    error_msg = result.stderr.strip()
                    # Check for connection errors
                    if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                        print(f"    ⚠️  Connection issue detected", flush=True)
                    # Show last few lines of stderr for debugging
                    stderr_lines = error_msg.split('\n')
                    if stderr_lines:
                        print(f"    📝 Last stderr line: {stderr_lines[-1][:200]}...", flush=True)
                return []
        
        except subprocess.TimeoutExpired:
            print(f"    ⚠️  yt-dlp search timed out after 3 minutes", flush=True)
            return []
        except FileNotFoundError:
            print(f"    ❌ Python or yt-dlp module not found. Please install: pip install yt-dlp", flush=True)
            return []
        except Exception as e:
            print(f"    ❌ Error running yt-dlp: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return []
    
    # VIDEO DOWNLOAD FUNCTIONALITY COMMENTED OUT - Only scraping URLs now
    # async def download_video(self, video_url: str) -> Optional[str]:
    #     """
    #     Download YouTube video using yt-dlp (without proxy for better reliability)
    #     
    #     Returns:
    #         Path to downloaded video file or None if failed
    #     """
    #     # Download code commented out - only scraping URLs now
    #     pass
