import asyncio
import logging
import sys
import os
from dotenv import load_dotenv  # type: ignore

# Path setup
sys.path.insert(0, os.getcwd())

# Setup logging to see everything
logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s")
logger = logging.getLogger(__name__)

async def main():
    load_dotenv()
    from app.scheduler import trigger_ingestion  # type: ignore
    
    print("🚀 Triggering all scrapers...")
    try:
        stats = await trigger_ingestion(scraper_name="all")
        print(f"✅ Full result: {stats}")
    except Exception as e:
        print(f"❌ Failed all: {e}")

if __name__ == "__main__":
    asyncio.run(main())
