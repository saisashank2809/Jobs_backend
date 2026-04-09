import asyncio
import logging
from unittest.mock import MagicMock
from app.services.ingestion_service import IngestionService

# Simple mock objects
db = MagicMock()
ai = MagicMock()
emb = MagicMock()

async def test_location_logic():
    svc = IngestionService(db, ai, emb)
    
    # Mocking _db.find_job_by_external_id to return None (so it tries to ingest)
    db.find_job_by_external_id.return_value = asyncio.Future()
    db.find_job_by_external_id.return_value.set_result(None)
    
    # Mocking _db.insert_scraping_log
    db.insert_scraping_log.return_value = asyncio.Future()
    db.insert_scraping_log.return_value.set_result({"id": "test-log-id"})
    
    # Mocking _db.update_scraping_log
    db.update_scraping_log.return_value = asyncio.Future()
    db.update_scraping_log.return_value.set_result(None)

    # Mocking _db.create_job to just return a dummy
    db.create_job.return_value = asyncio.Future()
    db.create_job.return_value.set_result({"id": "dummy-id"})

    # Test Cases
    test_jobs = [
        {"title": "Software Engineer", "location": "Bengaluru, India", "external_id": "1", "company_name": "TestCorp", "description_raw": "Looking for devs."},
        {"title": "Remote Frontend Developer", "location": "New York, US", "external_id": "2", "company_name": "USACorp", "description_raw": "Global remote role."},
        {"title": "Backend Dev", "location": "Remote", "external_id": "3", "company_name": "RemoteCorp", "description_raw": "Join our distributed team."},
        {"title": "Office Manager", "location": "London, UK", "external_id": "4", "company_name": "UKCorp", "description_raw": "Join our London office."}, # Should be skipped
        {"title": "Java Dev", "location": "Mumbai", "external_id": "5", "company_name": "IndiaCorp", "description_raw": "In-office Mumbai."},
    ]

    scraper = MagicMock()
    scraper.COMPANY_NAME = "TestScraper"
    scraper.fetch_jobs.return_value = asyncio.Future()
    scraper.fetch_jobs.return_value.set_result(test_jobs)

    # We need to monkey-patch or just run the part of ingest_jobs that we want to test.
    # Since ingest_jobs is complex, I'll just check the logic in a small snippet 
    # that replicates the ingestion_service code logic to verify my regex and conditions.

    print("Running Logic Simulation...")
    stats = {"fetched": 0, "new": 0, "skipped": 0}
    
    import re
    
    for job_data in test_jobs:
        stats["fetched"] += 1
        title = job_data["title"]
        desc_raw = job_data["description_raw"]
        company = job_data["company_name"]
        
        # REPLICATED LOGIC FROM INGESTION_SERVICE
        loc = (job_data.get("location", "") or "India").lower()
        title_lower = title.lower()
        desc_lower = desc_raw.lower()
        
        is_remote = any("remote" in text for text in [loc, title_lower, desc_lower])
        
        india_keywords = ["india", "bengaluru", "bangalore", "mumbai", "delhi", "pune", "hyderabad", "chennai", "noida", "gurugram", "gurgaon", "kerala", "karnataka", "maharashtra", "gujarat", "ahmedabad", "kolkata"]
        foreign_keywords = ["usa", "united states", "uk", "united kingdom", "london", "new york", "california", "canada", "australia", "germany", "france", "singapore", "dubai", "uae", "mexico", "brazil", "japan", "china", "ireland", "washington", "texas", "florida"]
        
        is_india_eligible = False
        if any(kw in loc for kw in india_keywords) or loc == "" or loc == "india":
            is_india_eligible = True
        elif not any(kw in loc for kw in foreign_keywords):
            is_india_eligible = True
        
        if re.search(r",\s*(us|uk|ca|au)$", loc):
            is_india_eligible = False

        if not (is_remote or is_india_eligible):
            print(f"  [SKIPPED] {title} at {job_data['location']}")
            stats["skipped"] += 1
        else:
            print(f"  [ACCEPTED] {title} at {job_data['location']} (Remote: {is_remote}, India: {is_india_eligible})")
            stats["new"] += 1

    print(f"\nFinal Stats: {stats}")

if __name__ == "__main__":
    asyncio.run(test_location_logic())
