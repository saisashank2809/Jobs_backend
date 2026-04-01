import asyncio
import os
from app.dependencies import _get_supabase_client
from app.config import settings

async def check_user_columns():
    print(f"Checking Supabase at {settings.supabase_url}")
    client = _get_supabase_client()
    
    try:
        # Fetch one user to check columns
        res = client.table("users_jobs").select("*").limit(1).execute()
        if res.data:
            user = res.data[0]
            print("Columns in 'users_jobs':")
            for key in user.keys():
                print(f"- {key}")
            
            if "skills" in user and "interests" in user:
                print("\n✅ 'skills' and 'interests' columns exist.")
            else:
                missing = []
                if "skills" not in user: missing.append("skills")
                if "interests" not in user: missing.append("interests")
                print(f"\n❌ Missing columns: {', '.join(missing)}")
        else:
            print("No users found in 'users_jobs' table.")
    except Exception as e:
        print(f"Error checking table: {e}")

if __name__ == "__main__":
    asyncio.run(check_user_columns())
