import asyncio
from app.dependencies import _get_supabase_client
from app.config import settings

async def check_jobs():
    print(f"Checking Supabase at {settings.supabase_url}")
    client = _get_supabase_client()
    
    # 1. Total jobs count
    res = client.table("jobs_jobs").select("*", count="exact").limit(0).execute()
    print(f"Total jobs in 'jobs_jobs': {res.count}")
    
    # 2. Count by status
    res = client.table("jobs_jobs").select("status").execute()
    statuses = {}
    for row in res.data:
        s = row.get("status", "unknown")
        statuses[s] = statuses.get(s, 0) + 1
    print(f"Statuses: {statuses}")
    
    # 3. Sample of 'active' jobs
    res = client.table("jobs_jobs").select("*").eq("status", "active").limit(5).execute()
    print(f"Found {len(res.data)} active jobs.")
    if res.data:
        print("Sample active job titles:")
        for job in res.data:
            print(f"- {job.get('title')} ({job.get('company_name')})")
    else:
        print("No active jobs found in the database.")

if __name__ == "__main__":
    asyncio.run(check_jobs())
