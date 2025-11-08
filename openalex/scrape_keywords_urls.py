
from openalex_scraper import OpenAlexScraper
import csv
import os

def scrape_keywords_urls(keywords, output_file="keywords_urls.csv", max_results_per_keyword=50):
    
    # Initialize scraper
    scraper = OpenAlexScraper(email="vipuldholariya1991dev@gmail.com")
    
    # Prepare data for CSV
    csv_data = []
    
    print(f"=== Scraping OpenAlex for {len(keywords)} keywords ===\n")
    
    for idx, keyword in enumerate(keywords, 1):
        print(f"\n{'='*60}")
        print(f"[{idx}/{len(keywords)}] Keyword: '{keyword}'")
        print(f"{'='*60}")
        
        try:
            # Search for works - try the full keyword first, then try broader searches
            print(f"Searching OpenAlex for documents related to '{keyword}' (English only)...")
            works = scraper.get_all_works(
                query=keyword,
                filter_params={'language': 'en'},
                max_results=max_results_per_keyword,
                use_cursor=True
            )
            
            # If no results, try broader search with main terms
            if len(works) == 0:
                # Extract main terms from keyword
                words = keyword.split()
                # Try combinations of main terms
                if len(words) > 3:
                    # Try first 3-4 words
                    broader_query = " ".join(words[:4])
                    print(f"  No results, trying broader search: '{broader_query}'...")
                    works = scraper.get_all_works(
                        query=broader_query,
                        filter_params={'language': 'en'},
                        max_results=max_results_per_keyword,
                        use_cursor=True
                    )
                
                # If still no results, try with just boiler-related terms
                if len(works) == 0:
                    boiler_terms = [w for w in words if w.lower() in ['boiler', 'drum', 'tube', 'steam', 'pressure', 'vessel', 'rupture', 'leak', 'failure', 'explosion', 'overheating', 'accident']]
                    if boiler_terms:
                        broader_query = " ".join(boiler_terms[:3])
                        print(f"  Still no results, trying: '{broader_query}'...")
                        works = scraper.get_all_works(
                            query=broader_query,
                            filter_params={'language': 'en'},
                            max_results=max_results_per_keyword,
                            use_cursor=True
                        )
            
            print(f"✓ Found {len(works)} documents/works")
            
            # Filter works to only boiler-related ones
            # Primary boiler terms (must have at least one)
            primary_boiler_terms = ['boiler', 'steam drum', 'steam generator', 'heat exchanger', 
                                   'waste heat', 'whrb', 'hrsg', 'power plant', 'thermal power']
            
            # Secondary boiler terms (help identify boiler context)
            secondary_boiler_terms = ['drum', 'tube', 'pressure vessel', 'turbine', 'generator', 
                                     'furnace', 'combustion', 'rupture', 'leak', 'failure', 
                                     'explosion', 'overheating', 'accident', 'alstom', 
                                     'foster wheeler', 'b&w', 'babcock', 'subcritical', 'supercritical',
                                     'steam', 'thermal', 'heat recovery', 'boiler tube']

            
            filtered_works = []
            for work in works:
                if not work:
                    continue
                
                # Check title and abstract for boiler-related terms
                title = work.get('title', '').lower()
                abstract = ''
                if work.get('abstract_inverted_index'):
                    # Reconstruct abstract from inverted index
                    abstract = ' '.join(work.get('abstract_inverted_index', {}).keys()).lower()
                
                work_text = f"{title} {abstract}"
                
                # Must have at least one primary boiler term
                has_primary_term = any(term in work_text for term in primary_boiler_terms)
                
                # Check for medical terms (if present, need stronger boiler context)
                has_medical_term = any(term in work_text for term in medical_exclusion_terms)
                
                # Count secondary boiler terms
                secondary_count = sum(1 for term in secondary_boiler_terms if term in work_text)
                
                # Include if:
                # 1. Has primary boiler term AND (no medical terms OR has multiple secondary terms)
                # 2. OR has multiple secondary boiler terms (at least 2) and no medical terms
                is_boiler_related = False
                if has_primary_term:
                    if not has_medical_term or secondary_count >= 2:
                        is_boiler_related = True
                elif secondary_count >= 2 and not has_medical_term:
                    is_boiler_related = True
                
                if is_boiler_related:
                    filtered_works.append(work)
            
            if len(filtered_works) < len(works):
                print(f"  Filtered to {len(filtered_works)} boiler-related documents")
            
            # Extract all URLs for each boiler-related document (PDF, landing page, DOI, etc.)
            url_count = 0
            for work in filtered_works:
                if not work:
                    continue
                
                # Get all possible URLs (prioritize PDF URLs, then landing pages, then DOI)
                url = None
                
                # Priority 1: PDF URLs
                best_oa = work.get('best_oa_location')
                if best_oa and best_oa.get('pdf_url'):
                    url = best_oa['pdf_url']
                
                # Check all locations for PDF URLs if not found yet
                if not url:
                    locations = work.get('locations', [])
                    if locations:
                        for location in locations:
                            if location and location.get('pdf_url'):
                                url = location['pdf_url']
                                break
                
                # Check primary location for PDF URL if not found yet
                if not url:
                    primary_location = work.get('primary_location')
                    if primary_location and primary_location.get('pdf_url'):
                        url = primary_location['pdf_url']
                
                # Priority 2: Landing page URLs if no PDF found
                if not url:
                    if best_oa and best_oa.get('landing_page_url'):
                        url = best_oa['landing_page_url']
                
                if not url:
                    locations = work.get('locations', [])
                    if locations:
                        for location in locations:
                            if location and location.get('landing_page_url'):
                                url = location['landing_page_url']
                                break
                
                if not url:
                    primary_location = work.get('primary_location')
                    if primary_location and primary_location.get('landing_page_url'):
                        url = primary_location['landing_page_url']
                
                # Priority 3: Open access URL
                if not url:
                    oa_url = work.get('open_access', {}).get('oa_url')
                    if oa_url:
                        url = oa_url
                
                # Priority 4: DOI
                if not url:
                    doi = work.get('doi')
                    if doi:
                        # Format DOI as URL
                        if doi.startswith('http'):
                            url = doi
                        else:
                            url = f"https://doi.org/{doi}"
                
                # Add row with keyword and URL (blank if no URL found)
                csv_data.append({
                    'keyword': keyword,
                    'url': url if url else ''
                })
                
                if url:
                    url_count += 1
            
            print(f"✓ Extracted {url_count} URLs out of {len(filtered_works)} boiler-related documents")
            
        except Exception as e:
            print(f"✗ Error scraping '{keyword}': {e}")
            # Still add the keyword with empty URL
            csv_data.append({
                'keyword': keyword,
                'url': ''
            })
    
    # Write to CSV
    print(f"\n{'='*60}")
    print(f"Writing results to {output_file}...")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['keyword', 'url'])
        writer.writeheader()
        writer.writerows(csv_data)
    
    print(f"✓ Saved {len(csv_data)} records to {output_file}")
    print(f"{'='*60}\n")
    
    return csv_data


def main():
    """Main function to scrape the 5 keywords"""
    
    keywords = [
        "Boiler tube rupture Subcritical Drum Alstom",
        "Steam drum leak Foster Wheeler boiler",
        "Pressure vessel failure B&W drum boiler",
        "Subcritical boiler explosion case study",
        "Boiler overheating accident analysis"
    ]
    
    # Scrape keywords and extract URLs
    results = scrape_keywords_urls(
        keywords=keywords,
        output_file="keywords_urls.csv",
        max_results_per_keyword=50
    )
    
    # Print summary
    print("\n=== SUMMARY ===")
    keyword_counts = {}
    for row in results:
        keyword = row['keyword']
        if keyword not in keyword_counts:
            keyword_counts[keyword] = 0
        if row['url']:  # Count non-empty URLs
            keyword_counts[keyword] += 1
    
    for keyword, count in keyword_counts.items():
        print(f"  {keyword}: {count} URLs")
    
    print(f"\n✓ Results saved to: keywords_urls.csv")


if __name__ == "__main__":
    main()

