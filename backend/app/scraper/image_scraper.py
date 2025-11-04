from typing import List, Dict
import httpx
from bs4 import BeautifulSoup
import json
from urllib.parse import quote, urlparse
import asyncio
from app.scraper.base import BaseScraper
from app.config import settings

class ImageScraper(BaseScraper):
    """Scraper for Bing Images API"""
    
    # Domains to exclude (gaming, entertainment, social media)
    EXCLUDED_DOMAINS = {
        'gamespot.com', 'steam.com', 'steampowered.com', 'gog.com', 
        'epicgames.com', 'twitch.tv', 'youtube.com', 'facebook.com',
        'twitter.com', 'x.com', 'instagram.com', 'reddit.com',
        'imgur.com', 'pinterest.com', 'flickr.com', 'deviantart.com',
        'tumblr.com', '9gag.com', 'memegenerator.net'
    }
    
    # Gaming/entertainment terms that indicate irrelevant content
    GAMING_KEYWORDS = {
        'game', 'gaming', 'gamer', 'video game', 'pc game', 'console',
        'playstation', 'xbox', 'nintendo', 'esports', 'twitch',
        'stream', 'livestream', 'esport'
    }
    
    def __init__(self):
        super().__init__()
        # Bing Images specific headers
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
    
    async def search(self, keyword: str, max_results: int = None) -> List[Dict]:
        """Search for images using Bing Images async API"""
        if max_results is None:
            max_results = settings.MAX_RESULTS_PER_KEYWORD
        
        items = []
        urls = set()
        
        try:
            # Calculate how many pages we need (Bing shows ~35 images per page)
            images_per_page = 35
            # Calculate pages needed to get at least max_results images
            # For small max_results (like 2), just fetch 1 page
            if max_results <= images_per_page:
                max_pages = 1
            else:
                pages_needed = (max_results // images_per_page) + 1
                max_pages = min(10, pages_needed)  # Max 10 pages (350 images)
            
            for page in range(max_pages):
                offset = page * images_per_page
                query = quote(keyword)
                url = f"https://www.bing.com/images/async?q={query}&first={offset}&count={images_per_page}&adlt=off"
                
                try:
                    response = await self.client.get(url, headers=self.headers, timeout=15)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Parse image JSON from "m" attribute
                        for a_tag in soup.select("a.iusc"):
                            m = a_tag.get("m")
                            if not m:
                                continue
                            
                            try:
                                m_json = json.loads(m)
                                img_url = m_json.get("murl")
                                if img_url and img_url not in urls:
                                    # Check if it's a valid image URL
                                    img_url_lower = img_url.lower()
                                    if any(img_url_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
                                        # Extract metadata from Bing's JSON
                                        page_title = m_json.get("t", "")  # Page title
                                        page_desc = m_json.get("desc", "")  # Page description
                                        page_url = m_json.get("purl", "")  # Source page URL
                                        
                                        # 1. Check domain exclusion (gaming, entertainment sites)
                                        if self._is_excluded_domain(img_url, page_url):
                                            continue
                                        
                                        # 2. Check for gaming/entertainment keywords
                                        if self._contains_gaming_keywords(page_title, page_desc, page_url):
                                            continue
                                        
                                        # 3. Relevance check: check if keyword terms appear in title/description
                                        keyword_lower = keyword.lower()
                                        keyword_terms = keyword_lower.split()
                                        
                                        title_lower = page_title.lower()
                                        desc_lower = page_desc.lower()
                                        page_url_lower = page_url.lower()
                                        
                                        # Count matches in title, description, and URL
                                        matches = sum(1 for term in keyword_terms 
                                                    if term in title_lower or term in desc_lower or term in page_url_lower)
                                        
                                        # For small max_results (like 2), be very lenient with filtering
                                        if max_results <= 2:
                                            # Only filter out obvious gaming/entertainment content
                                            # Accept any image that passed domain and gaming keyword checks
                                            urls.add(img_url)
                                        else:
                                            # For larger requests, apply relevance filtering
                                            # For ambiguous terms like "steam", require other boiler-related terms too
                                            if 'steam' in keyword_lower and matches == 1 and 'steam' in title_lower:
                                                # If only "steam" matches, check if other boiler terms appear
                                                boiler_terms = ['boiler', 'drum', 'foster', 'wheeler', 'leak', 'power', 'plant', 'turbine', 'industrial']
                                                has_boiler_context = any(term in title_lower or term in desc_lower for term in boiler_terms)
                                                if not has_boiler_context:
                                                    continue  # Skip if only "steam" matches without boiler context
                                            
                                            # Require at least 2 keyword terms (or 1 for short keywords)
                                            min_matches = 2 if len(keyword_terms) > 2 else 1
                                            if matches < min_matches and page_title:
                                                continue  # Skip if doesn't meet relevance threshold
                                            
                                            # Include the image
                                            urls.add(img_url)
                                        
                                        # Store metadata for this image
                                        if img_url in urls:
                                            if not hasattr(self, '_image_metadata'):
                                                self._image_metadata = {}
                                            self._image_metadata[img_url] = {
                                                "title": page_title or keyword,
                                                "description": page_desc or f"Image result for: {keyword}",
                                                "source_url": page_url or img_url
                                            }
                                            
                                            if len(urls) >= max_results:
                                                break
                            except (json.JSONDecodeError, KeyError):
                                continue
                        
                        if len(urls) >= max_results:
                            break
                        
                        # Be polite to Bing - small delay between pages
                        await asyncio.sleep(1.5)
                    
                except Exception as e:
                    print(f"Error fetching page {page + 1} for '{keyword}': {e}")
                    continue
            
            # Convert URLs to items with metadata
            metadata = getattr(self, '_image_metadata', {})
            for url in list(urls)[:max_results]:
                meta = metadata.get(url, {})
                items.append({
                    "url": url,
                    "title": meta.get("title", keyword),
                    "description": meta.get("description", f"Image result for: {keyword}"),
                    "source_url": meta.get("source_url", url)
                })
            
            # Clear metadata for next search
            if hasattr(self, '_image_metadata'):
                self._image_metadata = {}
        
        except Exception as e:
            print(f"Error scraping images for '{keyword}': {e}")
        
        return items
    
    def _is_excluded_domain(self, img_url: str, page_url: str) -> bool:
        """Check if URL is from an excluded domain (gaming, entertainment)"""
        for url in [img_url, page_url]:
            if url:
                try:
                    domain = urlparse(url).netloc.lower()
                    # Remove www. prefix
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    # Check if domain or subdomain matches excluded domains
                    for excluded in self.EXCLUDED_DOMAINS:
                        if domain == excluded or domain.endswith('.' + excluded):
                            return True
                except Exception:
                    pass
        return False
    
    def _contains_gaming_keywords(self, title: str, desc: str, page_url: str) -> bool:
        """Check if title/description/URL contains gaming/entertainment keywords"""
        text_to_check = ' '.join([title, desc, page_url]).lower()
        return any(keyword in text_to_check for keyword in self.GAMING_KEYWORDS)
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL is a valid image URL"""
        if not url:
            return False
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
        return any(ext in url.lower() for ext in image_extensions)
