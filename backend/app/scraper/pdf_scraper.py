from typing import List, Dict
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import re
from app.scraper.base import BaseScraper
from app.config import settings

class PDFScraper(BaseScraper):
    """Scraper for PDF files using DuckDuckGo Search"""
    
    def __init__(self):
        super().__init__()
        print(f"✅ PDF Scraper initialized - using DuckDuckGo for PDF search")
    
    async def search(self, keyword: str, max_results: int = None) -> List[Dict]:
        """Search for PDF files using DuckDuckGo Search"""
        if max_results is None:
            max_results = settings.MAX_RESULTS_PER_KEYWORD
        
        print(f"  🔍 PDF Scraper: Searching for '{keyword}' (max_results={max_results})", flush=True)
        print(f"  🔄 Using DuckDuckGo for PDF search", flush=True)
        result = await self._search_with_duckduckgo(keyword, max_results)
        print(f"  📊 DuckDuckGo returned {len(result)} PDFs", flush=True)
        return result
    
    async def _search_with_duckduckgo(self, keyword: str, max_results: int) -> List[Dict]:
        """Search PDFs using DuckDuckGo Search"""
        items = []
        urls = set()
        
        try:
            print(f"    🔄 DuckDuckGo: Starting PDF search for '{keyword}'", flush=True)
            # Try multiple query variations
            queries = [
                f'{keyword} filetype:pdf',
                f'{keyword} PDF',
                f'{keyword} PDF document',
            ]
            
            # Create a custom client with better headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Try multiple query variations
            for query_idx, search_query_text in enumerate(queries, 1):
                if len(urls) >= max_results:
                    break
                    
                search_query = quote_plus(search_query_text)
                search_url = f"https://html.duckduckgo.com/html/?q={search_query}"
                print(f"    📝 DuckDuckGo: Query {query_idx}/{len(queries)} - '{search_query_text}'", flush=True)
            
                try:
                    async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
                        response = await client.get(search_url)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                        
                            # Method 1: DuckDuckGo result links are in <a class="result__a"> tags
                            found_in_links = 0
                            for link in soup.find_all('a', class_='result__a', href=True):
                                href = link.get('href', '')
                                if href:
                                    # DuckDuckGo uses redirect URLs, extract actual URL
                                    if 'uddg=' in href:
                                        import urllib.parse
                                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                                        if 'uddg' in parsed:
                                            href = urllib.parse.unquote(parsed['uddg'][0])
                                    
                                    # Only accept direct PDF URLs that end with .pdf
                                    if href.endswith('.pdf') and href not in urls:
                                        if href.startswith('http'):
                                            urls.add(href)
                                            found_in_links += 1
                                            print(f"      ✅ Found PDF {found_in_links}: {href[:80]}", flush=True)
                                            if len(urls) >= max_results:
                                                break
                            
                            # Method 2: Check for any PDF links in the page
                            found_in_all_links = 0
                            for link in soup.find_all('a', href=True):
                                if len(urls) >= max_results:
                                    break
                                href = link.get('href', '')
                                if href:
                                    # Only accept direct PDF URLs that end with .pdf
                                    if href.endswith('.pdf'):
                                        # Clean up the URL
                                        if href.startswith('/'):
                                            continue  # Skip relative URLs
                                        if href.startswith('http') and href not in urls:
                                            urls.add(href)
                                            found_in_all_links += 1
                                            print(f"      ✅ Found PDF (all links) {found_in_all_links}: {href[:80]}", flush=True)
                                            if len(urls) >= max_results:
                                                break
                            
                            # Method 3: Extract from page text using regex
                            found_in_text = 0
                            page_text = response.text
                            # Only extract URLs that end with .pdf (direct PDF links)
                            pdf_urls = re.findall(r'https?://[^\s<>"\'\)]+\.pdf(?:\?|$|"|\'|\)|,|;|\.|!|\s)', page_text)
                            for pdf_url in pdf_urls:
                                if len(urls) >= max_results:
                                    break
                                # Clean trailing punctuation and ensure it ends with .pdf
                                pdf_url = pdf_url.rstrip('.,;!?"\')\s')
                                # Only accept if it ends with .pdf (not .pdf? or .pdf#)
                                if pdf_url.endswith('.pdf') and pdf_url not in urls:
                                    if pdf_url.startswith('http'):
                                        urls.add(pdf_url)
                                        found_in_text += 1
                                        print(f"      ✅ Found PDF (text) {found_in_text}: {pdf_url[:80]}", flush=True)
                                        if len(urls) >= max_results:
                                            break
                            
                            print(f"    📊 DuckDuckGo: Found {len(urls)} PDF URLs from this query", flush=True)
                        else:
                            print(f"    ⚠️  DuckDuckGo: HTTP {response.status_code} for query {query_idx}", flush=True)
                            
                except Exception as e:
                    print(f"    ⚠️  Error fetching DuckDuckGo results for query {query_idx}: {e}", flush=True)
                    continue  # Try next query
            
            # Process collected URLs - filter to only direct PDF URLs
            print(f"    📊 DuckDuckGo: Total unique PDF URLs found: {len(urls)}", flush=True)
            filtered_urls = []
            for url in list(urls)[:max_results]:
                # Only accept URLs that end with .pdf (direct PDF links)
                if url and url.endswith('.pdf') and (url.startswith('http://') or url.startswith('https://')):
                    # Remove query parameters but keep .pdf extension
                    clean_url = url.split('?')[0].split('#')[0]
                    if clean_url.endswith('.pdf') and clean_url not in filtered_urls:
                        filtered_urls.append(clean_url)
                        filename = clean_url.split('/')[-1]
                        items.append({
                            "url": clean_url,
                            "title": filename or keyword,
                            "description": f"PDF document for: {keyword}",
                        })
            
            print(f"    📊 DuckDuckGo: Filtered to {len(items)} direct PDF URLs (removed non-PDF links)", flush=True)
            
            print(f"    📊 DuckDuckGo found {len(items)} PDFs for '{keyword}'", flush=True)
            if len(items) == 0:
                print(f"    ⚠️  No PDFs found via DuckDuckGo for '{keyword}'", flush=True)
        
        except Exception as e:
            print(f"    ❌ Error scraping PDFs with DuckDuckGo for '{keyword}': {e}", flush=True)
            import traceback
            traceback.print_exc()
        
        return items[:max_results]
    
    def is_pdf_url(self, url: str) -> bool:
        """Check if URL is a direct PDF link - only accepts URLs ending with .pdf"""
        if not url:
            return False
        
        # Remove query parameters and fragments
        clean_url = url.split('?')[0].split('#')[0]
        
        # Only accept URLs that end with .pdf (direct PDF links)
        return clean_url.lower().endswith('.pdf')
        
        # Old code below - not executed
        url_lower = url.lower()
        # Exclude common non-PDF hosting sites
        excluded_domains = [
            'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
            'imgur.com', 'flickr.com', 'pinterest.com', 'instagram.com',
            'facebook.com', 'twitter.com', 'x.com', 'linkedin.com',
            'reddit.com', 'tumblr.com', 'snapchat.com', 'tiktok.com',
            'twitch.tv', 'soundcloud.com', 'spotify.com', 'apple.com/music',
            'amazon.com', 'ebay.com', 'etsy.com', 'shopify.com',
            'github.com', 'gitlab.com', 'bitbucket.org', 'stackoverflow.com',
            'wikipedia.org', 'wikimedia.org', 'wikia.com', 'fandom.com',
            'google.com', 'googleapis.com', 'gstatic.com', 'googletagmanager.com',
            'doubleclick.net', 'googlesyndication.com', 'google-analytics.com',
            'adobe.com', 'adobesc.com', 'adobelogin.com', 'adobedtm.com',
            'microsoft.com', 'office.com', 'office365.com', 'live.com',
            'cloudflare.com', 'cloudflareinsights.com', 'cfanalytics.com',
            'amazonaws.com', 's3.amazonaws.com', 'cloudfront.net',
            'akamai.com', 'akamaized.net', 'fastly.com', 'fastlylb.net',
            'cdnjs.cloudflare.com', 'cdn.jsdelivr.net', 'unpkg.com',
            'jquery.com', 'bootstrapcdn.com', 'fontawesome.com',
            'gravatar.com', 'wp.com', 'wordpress.com', 'wordpress.org',
            'tumblr.com', 'blogger.com', 'blogspot.com', 'medium.com',
            'substack.com', 'ghost.org', 'typepad.com', 'livejournal.com',
            'myspace.com', 'friendster.com', 'orkut.com', 'bebo.com',
            'hi5.com', 'tagged.com', 'meetup.com', 'nextdoor.com',
            'clubhouse.com', 'discord.com', 'telegram.org', 'whatsapp.com',
            'signal.org', 'wechat.com', 'line.me', 'kakao.com',
            'weibo.com', 'qq.com', 'baidu.com', 'sina.com.cn',
            'naver.com', 'daum.net', 'yahoo.com', 'yahoo.co.jp',
            'aol.com', 'msn.com', 'bing.com', 'duckduckgo.com',
            'ask.com', 'yandex.com', 'ecosia.org', 'startpage.com',
            'brave.com', 'opera.com', 'safari.com', 'firefox.com',
            'chrome.com', 'edge.com', 'internetexplorer.com',
            'netscape.com', 'mozilla.org', 'webkit.org', 'chromium.org',
        ]
        
        # Check if URL contains excluded domain
        for domain in excluded_domains:
            if domain in url_lower:
                return False
        
        # Check if URL ends with .pdf or contains .pdf
        return url_lower.endswith('.pdf') or '.pdf' in url_lower or 'filetype:pdf' in url_lower
