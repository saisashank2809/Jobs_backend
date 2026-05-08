import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

script_dir = os.path.dirname(os.path.abspath(__file__))
# Check both possible locations for .env
env_path = os.path.join(script_dir, ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(script_dir, "..", "jobs.backend", ".env")

load_dotenv(env_path)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def camel_to_snake(name):
    import re
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

def migrate_all():
    # Load companies from JSON
    # It's in the frontend dir, let's assume we run from backend and point to it
    json_path = "c:/jobs_frontend/jobs.frontend/companies_data.json"
    with open(json_path, 'r', encoding='utf-8') as f:
        companies = json.load(f)
    
    print(f"Loaded {len(companies)} companies.")
    
    for company in companies:
        # Map fields
        mapped_company = {}
        for k, v in company.items():
            if k == 'id': continue 
            if k == 'process': k = 'selectionProcess' # Normalize
            snake_k = camel_to_snake(k)
            mapped_company[snake_k] = v
        
        # Ensure some defaults or required fields
        if 'slug' not in mapped_company:
            mapped_company['slug'] = mapped_company['name'].lower().replace(' ', '-')
        
        print(f"Migrating {mapped_company['name']}...")
        try:
            result = supabase.table("playbooks").upsert(mapped_company, on_conflict="slug").execute()
            # print(f"Success: {mapped_company['name']}")
        except Exception as e:
            print(f"Error migrating {mapped_company['name']}: {e}")

if __name__ == "__main__":
    migrate_all()
