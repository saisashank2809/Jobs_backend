import sys
import os

# Add the project root to sys.path to import from app
sys.path.append(os.getcwd())

from app.dependencies import _get_supabase_client

def inspect_schema():
    client = _get_supabase_client()
    
    # Check if 'users' table exists and get columns
    print("Checking 'users' table...")
    try:
        response = client.rpc("get_table_columns", {"p_table_name": "users"}).execute()
        if response.data:
            print("Columns in 'users' table:")
            for col in response.data:
                print(f" - {col['column_name']} ({col['data_type']})")
        else:
            print("'users' table column info not found via RPC.")
    except Exception as e:
        print(f"Error checking 'users' table via RPC: {e}")
        
    # Fallback: Try a simple select to see if it exists
    try:
        response = client.table("users").select("*").limit(1).execute()
        print("'users' table exists.")
        if response.data:
            print("Sample data keys:", response.data[0].keys())
    except Exception as e:
        print(f"'users' table check failed: {e}")

    # Check 'users_jobs' for comparison
    print("\nChecking 'users_jobs' table...")
    try:
        response = client.table("users_jobs").select("*").limit(1).execute()
        print("'users_jobs' table exists.")
        if response.data:
            print("Sample data keys:", response.data[0].keys())
    except Exception as e:
        print(f"'users_jobs' table check failed: {e}")

if __name__ == "__main__":
    inspect_schema()
