from typing import List, Dict
import asyncio
from app.scraper.base import BaseScraper
from app.config import settings

# Import Exa API (required for PDF search)
try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False
    print("⚠️  Exa API library not available. Please install: pip install exa-py")

class PDFScraper(BaseScraper):
    """Scraper for PDF files using Exa API"""
    
    def __init__(self):
        super().__init__()
        if EXA_AVAILABLE and settings.EXA_API_KEY:
            print(f"✅ PDF Scraper initialized - using Exa API")
        elif not EXA_AVAILABLE:
            print(f"⚠️  PDF Scraper: Exa API library not installed. Please install: pip install exa-py")
        elif not settings.EXA_API_KEY:
            print(f"⚠️  PDF Scraper: Exa API key not configured. Set EXA_API_KEY environment variable.")
    
    async def search(self, keyword: str, max_results: int = None) -> List[Dict]:
        """Search for PDF files using Exa API"""
        if max_results is None:
            max_results = settings.MAX_RESULTS_PER_KEYWORD
        
        print(f"  🔍 PDF Scraper: Searching for '{keyword}' (max_results={max_results})", flush=True)
        
        if not EXA_AVAILABLE:
            print(f"  ❌ Exa API library not available. Please install: pip install exa-py", flush=True)
            return []
        
        if not settings.EXA_API_KEY:
            print(f"  ❌ Exa API key not configured. Set EXA_API_KEY environment variable.", flush=True)
            return []
        
        # Use Exa API for PDF search
        print(f"  🔄 Using Exa API for PDF search...", flush=True)
        items = await self._search_with_exa(keyword, max_results)
        
        print(f"  ✅ PDF Scraper: Found {len(items)} PDFs for '{keyword}'", flush=True)
        return items[:max_results]
    
    async def _search_with_exa(self, keyword: str, max_results: int) -> List[Dict]:
        """Search PDFs using Exa API (high quality semantic search for PDFs)"""
        items = []
        
        if not EXA_AVAILABLE or not settings.EXA_API_KEY:
            if not EXA_AVAILABLE:
                print(f"    ⚠️  Exa API library not installed", flush=True)
            elif not settings.EXA_API_KEY:
                print(f"    ⚠️  Exa API key not configured (set EXA_API_KEY environment variable)", flush=True)
            return items
        
        try:
            print(f"    🔄 Using Exa API for '{keyword}'", flush=True)
            
            # Run Exa search in executor since it's synchronous
            loop = asyncio.get_event_loop()
            
            # Create Exa client
            exa = Exa(api_key=settings.EXA_API_KEY)
            
            # Try multiple query variations for better results
            queries = [
                f'{keyword} filetype:pdf',
                f'{keyword} PDF',
                f'{keyword} PDF document',
            ]
            
            urls = set()
            for query_idx, search_query in enumerate(queries, 1):
                if len(urls) >= max_results:
                    break
                
                print(f"    📝 Exa Query {query_idx}/{len(queries)}: '{search_query}'", flush=True)
                
                try:
                    # Run Exa search in executor
                    def run_exa_search(query, max_res):
                        # Search for PDFs using Exa API
                        # Note: Exa will search semantically - we filter results to PDFs only
                        results = exa.search(
                            query=query,
                            num_results=max_res * 3,  # Get more results to filter for PDFs
                        )
                        return results.results if results.results else []
                    
                    results = await loop.run_in_executor(
                        None,
                        run_exa_search,
                        search_query,
                        max_results
                    )
                    
                    found_count = 0
                    for result in results:
                        if len(urls) >= max_results:
                            break
                        
                        url = result.url if hasattr(result, 'url') else str(result)
                        if not url:
                            continue
                        
                        # Ensure it's a PDF URL
                        clean_url = url.split('?')[0].split('#')[0]
                        if clean_url.lower().endswith('.pdf') and clean_url.startswith('http'):
                            if clean_url not in urls:
                                urls.add(clean_url)
                                found_count += 1
                                title = result.title if hasattr(result, 'title') else result.text[:100] if hasattr(result, 'text') else clean_url.split('/')[-1]
                                items.append({
                                    "url": clean_url,
                                    "title": title[:200] if title else keyword,
                                    "description": result.text[:500] if hasattr(result, 'text') else f"PDF document for: {keyword}",
                                })
                                print(f"      ✅ Found PDF {found_count}: {clean_url[:80]}", flush=True)
                    
                    if found_count > 0:
                        print(f"    📊 Found {found_count} PDFs from Exa query", flush=True)
                    
                    # Small delay between queries
                    if query_idx < len(queries):
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    print(f"    ⚠️  Error with Exa query {query_idx}: {e}", flush=True)
                    continue
            
            print(f"    📊 Exa API: Total PDF URLs found: {len(items)}", flush=True)
            
        except Exception as e:
            print(f"    ❌ Error using Exa API: {e}", flush=True)
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
