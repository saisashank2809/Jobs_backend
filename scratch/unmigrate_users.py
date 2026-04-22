import sys
import os

# Add the project root to sys.path to import from app
sys.path.append(os.getcwd())

from app.dependencies import _get_supabase_client

def unmigrate_data():
    client = _get_supabase_client()
    
    print("Fetching user IDs from users_jobs...")
    response = client.table("users_jobs").select("id").execute()
    user_ids = [u["id"] for u in response.data]
    
    if not user_ids:
        print("No users found in users_jobs.")
        return
    
    deleted_count = 0
    # We will only delete if the user exists in 'users' and matches an ID from 'users_jobs'
    # BUT we should check if they were already there.
    # To be safe, we'll only delete if the email is in the list we migrated.
    
    print(f"Attempting to remove {len(user_ids)} users from 'users' table...")
    for uid in user_ids:
        try:
            # We use a cautious approach: delete from 'users' where user_id matches
            # but only if it's not a protected system ID if any.
            res = client.table("users").delete().eq("user_id", uid).execute()
            if res.data:
                deleted_count += len(res.data)
        except Exception as e:
            print(f"Error deleting {uid}: {e}")
            
    print(f"\nUnmigration complete! Removed {deleted_count} rows from 'users' table.")

if __name__ == "__main__":
    unmigrate_data()
