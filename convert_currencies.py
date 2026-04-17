from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

from supabase import create_client
sb = create_client(url, key)

from app.services.job_summary_service import mine_salary_from_text

# Fetch jobs with salary
res = sb.table("jobs_jobs").select("id, salary_range, description_raw").neq("salary_range", "null").execute()
jobs = res.data

updated_count = 0

for job in jobs:
    old_salary = str(job.get("salary_range", ""))
    desc = job.get("description_raw", "")
    
    # If the old salary had $ or £, let's try to remine it from description
    if "$" in old_salary or "£" in old_salary:
        new_salary = mine_salary_from_text(desc)
        if new_salary and "₹" in new_salary:
            sb.table("jobs_jobs").update({"salary_range": new_salary}).eq("id", job["id"]).execute()
            print(f"Updated {old_salary} -> {new_salary}")
            updated_count += 1

print(f"Updated {updated_count} salaries to INR format.")
