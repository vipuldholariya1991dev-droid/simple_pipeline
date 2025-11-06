from typing import List, Dict, Optional, Tuple
import asyncio
import subprocess
import json
import re
import sys
import tempfile
import os
from app.scraper.base import BaseScraper
from app.config import settings

# Music filter patterns - use word boundaries to avoid false positives
MUSIC_PATTERNS = [
    r'\bmusic\b', r'\bsong\b', r'\bsongs\b', r'\bmusical\b', 
    r'\balbum\b', r'\blyrics\b', r'\bmv\b', r'\bmusic video\b',
    r'\bofficial music\b', r'\bofficial video\b', r'\bofficial audio\b'
]

class YouTubeScraper(BaseScraper):
    """Scraper for YouTube using yt-dlp (downloads videos and uploads to R2)"""
    
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
                # Filter out YouTube Shorts, music, and songs - only process regular videos
                regular_videos = []
                for video in result:
                    video_url = video.get("webpage_url") or video.get("url") or ""
                    video_title = video.get("title", "").lower()
                    video_description = video.get("description", "").lower()
                    
                    # Skip YouTube Shorts (shorts URLs)
                    if "/shorts/" in video_url.lower():
                        print(f"    ⏭️  Skipping YouTube Short: {video.get('title', '')[:60]}...", flush=True)
                        continue
                    
                    # Skip music/songs - check title and description with word boundaries
                    video_text = f"{video_title} {video_description}"
                    is_music = any(re.search(pattern, video_text, re.IGNORECASE) for pattern in MUSIC_PATTERNS)
                    if is_music:
                        print(f"    ⏭️  Skipping music/song: {video.get('title', '')[:60]}...", flush=True)
                        continue
                    
                    regular_videos.append(video)
                
                if not regular_videos:
                    print(f"  ⚠️  No regular videos found (only Shorts/music/songs were returned)", flush=True)
                    return []
                
                # Filter videos to ensure relevance (check if title contains any keyword words)
                keyword_words = set(keyword.lower().split())
                relevant_videos = []
                
                for video in regular_videos[:max_results * 2]:  # Check more videos since we're filtering shorts
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
                
                # If we filtered out too many, use original regular videos but warn
                if len(relevant_videos) < max_results and len(relevant_videos) < len(regular_videos):
                    print(f"    ℹ️  Filtered {len(regular_videos) - len(relevant_videos)} irrelevant videos", flush=True)
                    # If we still have some relevant videos, use them
                    if relevant_videos:
                        result = relevant_videos[:max_results]
                    # Otherwise, use original regular videos but log warning
                    else:
                        print(f"    ⚠️  No videos matched keyword filter, using all regular videos", flush=True)
                        result = regular_videos[:max_results]
                else:
                    result = relevant_videos[:max_results]
                
                for idx, video in enumerate(result, 1):
                    video_url = video.get("webpage_url") or video.get("url") or ""
                    video_title = video.get("title", keyword)
                    video_description = video.get("description", "").lower()
                    
                    # Double-check: skip shorts URLs (shouldn't happen, but safety check)
                    if "/shorts/" in video_url.lower():
                        print(f"    ⏭️  Skipping YouTube Short (safety check): {video_title[:60]}...", flush=True)
                        continue
                    
                    # Double-check: skip music/songs (shouldn't happen, but safety check)
                    video_text = f"{video_title.lower()} {video_description}"
                    is_music = any(re.search(pattern, video_text, re.IGNORECASE) for pattern in MUSIC_PATTERNS)
                    if is_music:
                        print(f"    ⏭️  Skipping music/song (safety check): {video_title[:60]}...", flush=True)
                        continue
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
                        
                        # Skip YouTube Shorts - only process regular videos
                        if "/shorts/" in video_url.lower():
                            continue
                        
                        # Skip music/songs - check title with word boundaries
                        video_title_lower = video_title.lower()
                        is_music = any(re.search(pattern, video_title_lower, re.IGNORECASE) for pattern in MUSIC_PATTERNS)
                        if is_music:
                            continue
                        
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
    
    async def download_video(self, video_url: str) -> Optional[str]:
        """
        Download YouTube video using yt-dlp (direct connection for better reliability)
        
        Returns:
            Path to downloaded video file or None if failed
        """
        # Skip YouTube Shorts - they have format issues
        if "/shorts/" in video_url.lower():
            print(f"    ⏭️  Skipping YouTube Short (format issues): {video_url[:80]}...", flush=True)
            return None
        
        try:
            # Create temp directory and file for download
            temp_dir = tempfile.mkdtemp()
            temp_output = os.path.join(temp_dir, "video.%(ext)s")  # yt-dlp will determine extension
            
            print(f"    📥 Downloading video: {video_url[:80]}...", flush=True)
            print(f"    🔄 Using direct connection (no proxy) for better reliability", flush=True)
            
            # Try multiple format strategies and player clients in order of compatibility
            format_strategies = [
                "worst",  # Most compatible, always available
                "best",   # Best quality if available
                None,     # No format selector - let yt-dlp auto-select
            ]
            
            # Try different player clients - some videos work better with different clients
            player_clients = ["web", "android", "ios"]
            
            result = None
            downloaded_file = None
            total_attempts = len(format_strategies) * len(player_clients)
            attempt_num = 0
            
            for format_idx, format_strategy in enumerate(format_strategies, 1):
                if downloaded_file:
                    break  # Success, stop trying
                
                for client_idx, player_client in enumerate(player_clients, 1):
                    if downloaded_file:
                        break  # Success, stop trying
                    
                    attempt_num += 1
                    
                    # Build command with current format strategy and player client
                    cmd = [
                        sys.executable, "-m", "yt_dlp",
                        video_url,
                        "--output", temp_output,
                        "--no-playlist",
                        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "--quiet",
                        "--no-warnings",
                        "--extractor-args", f"youtube:player_client={player_client}",
                    ]
                    
                    # Add format selector if specified
                    if format_strategy:
                        cmd.insert(-3, format_strategy)  # Insert before --output
                        cmd.insert(-3, "--format")
                        strategy_name = f"{format_strategy} (client: {player_client})"
                    else:
                        strategy_name = f"auto-select (client: {player_client})"
                    
                    if attempt_num > 1:
                        print(f"    🔄 Retry {attempt_num}/{total_attempts}: Trying '{strategy_name}'...", flush=True)
                    else:
                        print(f"    🔄 Strategy 1/{total_attempts}: Trying '{strategy_name}'...", flush=True)
                
                    # Run download in executor
                    loop = asyncio.get_event_loop()
                    def run_download():
                        return subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=300,  # 5 minute timeout for video downloads
                            check=False
                        )
                    result = await loop.run_in_executor(None, run_download)
                    
                    # Check if download succeeded
                    if result.returncode == 0:
                        # Look for downloaded video file (could be any format: mp4, webm, mkv, etc.)
                        video_extensions = ['.mp4', '.webm', '.mkv', '.flv', '.mov', '.avi']
                        for file in os.listdir(temp_dir):
                            file_path = os.path.join(temp_dir, file)
                            if os.path.isfile(file_path):
                                # Check if it's a video file
                                file_ext = os.path.splitext(file)[1].lower()
                                if file_ext in video_extensions or file.startswith("video."):
                                    downloaded_file = file_path
                                    break
                        
                        if downloaded_file and os.path.exists(downloaded_file):
                            file_size = os.path.getsize(downloaded_file)
                            file_ext = os.path.splitext(downloaded_file)[1].lower()
                            print(f"    ✅ Video downloaded: {downloaded_file} ({file_size} bytes, format: {file_ext})", flush=True)
                            
                            # Check file size limit
                            max_size = settings.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024
                            if file_size > max_size:
                                print(f"    ⚠️  Video file too large: {file_size} bytes (max {max_size})", flush=True)
                                os.unlink(downloaded_file)
                                os.rmdir(temp_dir)
                                return None
                            
                            # Convert to MP4 if needed (for consistency, but keep original if conversion fails)
                            if file_ext != '.mp4':
                                try:
                                    # Try to rename to .mp4 (works if it's already MP4-compatible)
                                    mp4_path = downloaded_file.rsplit('.', 1)[0] + '.mp4'
                                    os.rename(downloaded_file, mp4_path)
                                    downloaded_file = mp4_path
                                    print(f"    ℹ️  Renamed video to MP4 format", flush=True)
                                except Exception as e:
                                    # Keep original format if rename fails
                                    print(f"    ℹ️  Keeping original format {file_ext} (rename to MP4 failed: {e})", flush=True)
                            
                            break  # Success! Exit both loops
                    else:
                        # Download failed with this strategy/client combo, try next one
                        # Don't log every failure to avoid spam - only log if it's the last attempt for this format
                        if client_idx == len(player_clients) and format_idx < len(format_strategies):
                            if result.stderr:
                                error_msg = result.stderr.strip()
                                if "format is not available" in error_msg.lower() or "requested format" in error_msg.lower():
                                    print(f"    ⚠️  Format '{format_strategy or 'auto-select'}' failed with all clients, trying next format...", flush=True)
                        # Continue to next client or format
                        continue
            
            # Return downloaded file if successful
            if downloaded_file:
                return downloaded_file
            
            # All strategies failed
            print(f"    ❌ Failed to download video after trying {total_attempts} combinations (3 formats × 3 clients)", flush=True)
            if result and result.stderr:
                error_msg = result.stderr.strip()
                print(f"    📝 Last error: {error_msg[:500]}", flush=True)
            # Clean up temp directory
            if os.path.exists(temp_dir):
                try:
                    for file in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, file)
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    os.rmdir(temp_dir)
                except Exception as e:
                    print(f"    ⚠️  Warning: Could not clean up temp directory: {e}", flush=True)
            return None
                
        except subprocess.TimeoutExpired:
            print(f"    ⚠️  Video download timed out after 5 minutes", flush=True)
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                for file in os.listdir(temp_dir):
                    os.unlink(os.path.join(temp_dir, file))
                os.rmdir(temp_dir)
            return None
        except Exception as e:
            print(f"    ❌ Error downloading video: {e}", flush=True)
            import traceback
            traceback.print_exc()
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                for file in os.listdir(temp_dir):
                    os.unlink(os.path.join(temp_dir, file))
                os.rmdir(temp_dir)
            return None
