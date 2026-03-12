import asyncio
from app.scheduler import trigger_ingestion
from dotenv import load_dotenv

load_dotenv()

async def main():
    print("Manually triggering global ingestion...")
    results = await trigger_ingestion(scraper_name="all")
    print(f"Ingestion results: {results}")

if __name__ == "__main__":
    asyncio.run(main())
