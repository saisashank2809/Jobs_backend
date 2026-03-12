import asyncio
from dotenv import load_dotenv

load_dotenv()

from app.dependencies import get_db

async def main():
    db = get_db()
    jobs = await db.list_active_jobs(limit=10000)
    
    # Check if there are any jobs with status archived
    result = db._client.table("jobs_jobs").select("id, status").eq("status", "archived").execute()
    archived_jobs = result.data or []
    
    print(f"Total active jobs: {len(jobs)}")
    print(f"Total archived jobs: {len(archived_jobs)}")

if __name__ == "__main__":
    asyncio.run(main())
