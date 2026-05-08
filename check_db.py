import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

res = supabase.table('jobs').select('company_name, company_logo').ilike('company_name', '%micron%').execute()
print("JOBS:", res.data)

res2 = supabase.table('playbooks').select('name, slug, logo').ilike('name', '%micron%').execute()
print("PLAYBOOKS:", res2.data)
