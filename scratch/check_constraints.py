import sys
import os

# Add the project root to sys.path to import from app
sys.path.append(os.getcwd())

from app.dependencies import _get_supabase_client

def check_strictness():
    client = _get_supabase_client()
    
    # Try to insert a dummy user with minimal info to see what fails
    print("Testing 'users' table constraints...")
    try:
        dummy_data = {"user_id": "00000000-0000-0000-0000-000000000000", "email": "test_constraint@example.com"}
        response = client.table("users").insert(dummy_data).execute()
        print("Insert succeeded (unexpectedly).")
    except Exception as e:
        print(f"Insert failed as expected: {e}")

if __name__ == "__main__":
    check_strictness()
