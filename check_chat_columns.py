import asyncio
from app.dependencies import get_db

async def check_columns():
    db = get_db()
    # Supabase doesn't have a direct "describe table" but we can try to fetch one row
    result = db._client.table("chat_sessions_jobs").select("*").limit(1).execute()
    if result.data:
        print(f"Columns in chat_sessions_jobs: {list(result.data[0].keys())}")
    else:
        print("No sessions found to check columns.")

if __name__ == "__main__":
    asyncio.run(check_columns())
