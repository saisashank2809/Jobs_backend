"""Quick test: run GenericAdapter on 3 URLs to verify improved filtering."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.scraper.generic_adapter import GenericAdapter

async def test_scraper():
    adapter = GenericAdapter()
    
    # Test on a mix of URLs
    adapter.target_urls = [
        "https://careers.slb.com",
        "https://careers.epam.com",
        "https://careers.activisionblizzard.com"
    ]
    
    print(f"Testing generic scraper on: {adapter.target_urls}")
    
    jobs = await adapter.fetch_jobs()
    print(f"\n{'='*60}")
    print(f"Scrape completed! Found {len(jobs)} jobs.")
    print(f"{'='*60}")
    for j in jobs:
        print(f"\n [{j['company_name']}] {j['title']}")
        print(f"   URL: {j['external_apply_url']}")
        print(f"   Desc length: {len(j.get('description_raw', ''))}")

if __name__ == "__main__":
    asyncio.run(test_scraper())
