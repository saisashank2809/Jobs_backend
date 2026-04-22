import sys
import os

# Add the project root to sys.path to import from app
sys.path.append(os.getcwd())

from app.dependencies import _get_supabase_client

def migrate_data():
    client = _get_supabase_client()
    
    print("Fetching users from users_jobs...")
    response = client.table("users_jobs").select("*").execute()
    users_jobs = response.data
    
    if not users_jobs:
        print("No users found in users_jobs.")
        return
    
    migrated_count = 0
    
    for u in users_jobs:
        user_id = u["id"]
        email = u["email"]
        
        # Prepare data for 'users' table
        user_data = {
            "user_id": user_id,
            "email": email,
            "full_name": u.get("full_name"),
            "phone": u.get("phone"),
            "password_hash": u.get("password"),
            "role": u.get("role"),
            "created_at": u.get("created_at")
        }
        
        print(f"Migrating {email} to 'users' table...")
        try:
            # Upsert into 'users'
            client.table("users").upsert(user_data, on_conflict="user_id").execute()
            migrated_count += 1
        except Exception as e:
            print(f"Error migrating {email}: {e}")
            
    print(f"\nMigration complete! Migrated {migrated_count} users.")

if __name__ == "__main__":
    migrate_data()
