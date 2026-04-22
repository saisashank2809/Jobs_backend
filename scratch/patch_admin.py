import sys
import os

path = 'app/routers/admin.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """    result = (
        db._client.table("jobs_jobs")
        .select("id, title, company_name, prep_guide_generated, resume_guide_generated, embedding, status")
        .execute()
    )"""

new = """    def _get_jobs():
        return (
            db._client.table("jobs_jobs")
            .select("id, title, company_name, prep_guide_generated, resume_guide_generated, embedding, status")
            .execute()
        )
    result = await run_in_threadpool(_get_jobs)"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Success: File updated.")
else:
    print("Error: Target content not found.")
    # Debug: print the first 100 chars around where it should be
    idx = content.find("Query all jobs missing")
    if idx != -1:
        print("Snippet found at:", idx)
        print(repr(content[idx:idx+200]))
