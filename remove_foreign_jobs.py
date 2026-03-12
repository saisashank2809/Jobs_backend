import asyncio
import re
from dotenv import load_dotenv

load_dotenv()

from app.dependencies import get_db

async def main():
    db = get_db()
    jobs = await db.list_active_jobs(limit=10000)
    print(f"Total active jobs found: {len(jobs)}")
    
    to_remove = []

    for job in jobs:
        title = job.get("title", "")
        desc_raw = job.get("description_raw", "")
        combo_text = title + " " + desc_raw
        
        has_cjk = bool(re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', combo_text))
        
        if has_cjk:
            to_remove.append(job)

    print(f"Found {len(to_remove)} jobs with Japanese/Chinese characters.")
    
    for job in to_remove:
        # Delete the job
        print(f"Removing [{job['company_name']}] {job['title']} - {job.get('location')}")
        db._client.table("jobs_jobs").delete().eq("id", job["id"]).execute()

    print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(main())
