from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

INGESTION_PROVIDER_ID = "00000000-0000-4000-a000-000000000001"
res = sb.table("jobs_jobs").update({"salary_range": None}).eq("provider_id", INGESTION_PROVIDER_ID).execute()
print(f"Cleared {len(res.data)} salaries")
