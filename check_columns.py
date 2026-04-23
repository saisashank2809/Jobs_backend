import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client

async def check_columns():
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    # Try to fetch one row and see the keys
    res = supabase.table("jobs_jobs").select("*").limit(1).execute()
    if res.data:
        print("Columns in jobs_jobs:", res.data[0].keys())
    else:
        print("No jobs found in jobs_jobs")

if __name__ == "__main__":
    asyncio.run(check_columns())
