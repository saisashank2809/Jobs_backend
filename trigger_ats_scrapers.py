import asyncio
import logging
from app.dependencies import get_db, get_ai_service, get_embedding_service, get_scraper, get_telegram_channel_service
from app.services.ingestion_service import IngestionService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def manual_trigger():
    print("Manually triggering Greenhouse and Lever ingestion...")
    
    db = get_db()
    ai = get_ai_service()
    emb = get_embedding_service()
    telegram = get_telegram_channel_service()
    
    svc = IngestionService(db, ai, emb, telegram)
    
    # Trigger Greenhouse
    try:
        gh = get_scraper("greenhouse")
        print("\n--- Ingesting from Greenhouse ---")
        gh_stats = await svc.ingest_jobs(gh)
        print(f"Greenhouse Results: {gh_stats}")
    except Exception as e:
        print(f"Greenhouse Failed: {e}")

    # Trigger Lever
    try:
        lv = get_scraper("lever")
        print("\n--- Ingesting from Lever ---")
        lv_stats = await svc.ingest_jobs(lv)
        print(f"Lever Results: {lv_stats}")
    except Exception as e:
        print(f"Lever Failed: {e}")

    print("\nManual trigger complete.")

if __name__ == "__main__":
    asyncio.run(manual_trigger())
