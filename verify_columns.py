import asyncio
import os
from app.dependencies import _get_supabase_client

async def verify():
    client = _get_supabase_client()
    try:
        # Try to update a dummy record with the suspicious columns
        # If columns are missing, this will throw an error
        client.table("users_jobs").update({"skills": ["test"], "interests": "test"}).eq("id", "00000000-0000-0000-0000-000000000000").execute()
        print("COLUMNS_EXIST")
    except Exception as e:
        print(f"COLUMNS_MISSING_ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
