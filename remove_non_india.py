import asyncio
import re
from dotenv import load_dotenv

load_dotenv()

from app.dependencies import get_db

async def main():
    db = get_db()
    jobs = await db.list_active_jobs(limit=10000)
    print(f"Total active jobs found: {len(jobs)}")
    
    india_keywords = ["india", "bengaluru", "bangalore", "mumbai", "delhi", "pune", "hyderabad", "chennai", "noida", "gurugram", "gurgaon", "kerala", "karnataka", "maharashtra", "gujarat", "ahmedabad", "kolkata"]
    foreign_keywords = ["usa", "united states", "uk", "united kingdom", "london", "new york", "california", "canada", "australia", "germany", "france", "singapore", "dubai", "uae", "mexico", "brazil", "japan", "china", "ireland", "washington", "texas", "florida"]

    to_remove = []

    for job in jobs:
        loc = job.get("location") or "India"
        loc_lower = loc.lower()
        
        is_india = False
        if any(kw in loc_lower for kw in india_keywords) or "remote" in loc_lower or loc_lower == "":
            is_india = True
        elif any(kw in loc_lower for kw in foreign_keywords):
            is_india = False
        else:
            is_india = True
            
        if re.search(r",\s*(us|uk|ca|au)$", loc_lower):
            is_india = False
            
        if not is_india:
            to_remove.append(job)

    print(f"Found {len(to_remove)} jobs outside of India.")
    
    for job in to_remove:
        # Delete the job
        print(f"Removing [{job['company_name']}] {job['title']} - {job.get('location')}")
        db._client.table("jobs_jobs").delete().eq("id", job["id"]).execute()

    print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(main())
