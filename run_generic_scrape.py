"""
Trigger Generic Ingestion safely (non-destructive).
"""
import asyncio
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.getcwd())

async def main():
    from app.dependencies import _get_supabase_client, get_ai_service, get_embedding_service
    from app.adapters.supabase_adapter import SupabaseAdapter
    from app.services.ingestion_service import IngestionService
    from app.scraper.generic_adapter import GenericAdapter

    client = _get_supabase_client()
    db = SupabaseAdapter(client)
    ai = get_ai_service()
    emb = get_embedding_service()
    service = IngestionService(db, ai, emb)
    
    scraper = GenericAdapter()
    
    # Optional: Limiting to a few URLs for the very first live test if you want to be quick
    # scraper.target_urls = scraper.target_urls[:5] 

    print(f"🚀 Starting Generic Scraper for {len(scraper.target_urls)} sites...")
    try:
        stats = await service.ingest_jobs(scraper)
        print(f"\n✅ Stats: {stats}")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
