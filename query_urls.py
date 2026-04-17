from dotenv import load_dotenv
import os

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

from supabase import create_client
sb = create_client(url, key)

res = sb.table("jobs_jobs").select("id, company_name, external_apply_url").limit(5).execute()
for job in res.data:
    print(f"{job['company_name']} -> {job['external_apply_url']}")
