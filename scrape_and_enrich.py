import asyncio
import logging
import os
import sys
from typing import List, Dict, Any, cast, AsyncGenerator

# 1. Add CWD to sys.path BEFORE other imports
sys.path.insert(0, os.getcwd())

# 2. Add type ignores for environment-dependent imports
from dotenv import load_dotenv  # type: ignore
from supabase import create_client  # type: ignore

from app.scraper.deloitte_adapter import DeloitteAdapter  # type: ignore
from app.scraper.pwc_adapter import PwCAdapter  # type: ignore
from app.scraper.kpmg_adapter import KPMGAdapter  # type: ignore
from app.scraper.ey_adapter import EYAdapter  # type: ignore
from app.adapters.supabase_adapter import SupabaseAdapter  # type: ignore
from app.adapters.openai_adapter import OpenAIAdapter  # type: ignore
from app.adapters.openai_embedding import OpenAIEmbeddingAdapter  # type: ignore
from app.services.enrichment_service import EnrichmentService  # type: ignore

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s │ %(levelname)-8s │ %(message)s")
logger = logging.getLogger(__name__)

INGESTION_PROVIDER_ID = "00000000-0000-4000-a000-000000000001"


async def main():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if not all([url, key, openai_key]):
        print("❌ Error: Missing environment variables (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, or OPENAI_API_KEY).")
        return

    # url and key are checked above
    sb = create_client(cast(str, url), cast(str, key))
    db = SupabaseAdapter(sb)
    ai = OpenAIAdapter(api_key=cast(str, openai_key))
    emb = OpenAIEmbeddingAdapter(api_key=cast(str, openai_key))
    enricher = EnrichmentService(db=db, ai=ai, embeddings=emb)

    scrapers = [
        ("PwC", PwCAdapter()),
        ("KPMG", KPMGAdapter()),
        ("Deloitte", DeloitteAdapter()),
        ("EY", EYAdapter()),
    ]

    total_inserted: int = 0
    total_enriched: int = 0

    for company_name, scraper in scrapers:
        print(f"\n{'='*60}")
        print(f"  {company_name}")
        print(f"{'='*60}")

        try:
            # Handle both list and generator return types
            jobs_result = await scraper.fetch_jobs()
            jobs: List[Dict[str, Any]] = []
            
            if isinstance(jobs_result, list):
                jobs = cast(List[Dict[str, Any]], jobs_result)
            else:
                async for batch in cast(AsyncGenerator[List[Dict[str, Any]], None], jobs_result):
                    jobs.extend(batch)
                
            print(f"✅ Fetched {len(jobs)} jobs")
        except Exception as e:
            print(f"❌ Scraper failed: {e}")
            continue

        for job_data_raw in jobs:
            # Cast to Dict to satisfy IDE assignment checks
            job_data = cast(Dict[str, Any], job_data_raw)
            job_data.setdefault("company_name", company_name)
            job_data.setdefault("description_raw", "")
            job_data.setdefault("skills_required", [])
            job_data.setdefault("status", "processing")  # will become 'active' after enrichment
            job_data["provider_id"] = INGESTION_PROVIDER_ID

            # Skip jobs with no real description (can't enrich them clearly)
            desc = str(job_data.get("description_raw", ""))
            
            # Check for bad descriptions
            is_placeholder = (
                not desc 
                or len(desc) < 200 
                or "Visit the official career page" in desc
                or desc.startswith("Posted:")
            )

            if is_placeholder:
                # Insert but mark as 'active' without enrichment data
                job_data["status"] = "active"
            
            try:
                # Check if already exists
                existing = sb.table("jobs_jobs") \
                    .select("id") \
                    .eq("company_name", str(job_data["company_name"])) \
                    .eq("external_id", str(job_data.get("external_id", ""))) \
                    .maybe_single() \
                    .execute()

                if existing and existing.data:
                    logger.debug("Skipping duplicate: %s / %s",
                                 company_name, job_data.get("external_id"))
                    continue

                result = sb.table("jobs_jobs").insert(job_data).execute()
                created = result.data[0]
                total_inserted = total_inserted + 1  # type: ignore[operator]

                # Run enrichment ONLY if we have a real description
                if not is_placeholder:
                    try:
                        await enricher.enrich_job(created["id"])
                        await db.update_job(created["id"], {"status": "active"})
                        total_enriched = total_enriched + 1  # type: ignore[operator]
                        print(f"  ✅ {job_data['title'][:50]} — enriched (Desc len: {len(desc)})")
                    except Exception as e:
                        await db.update_job(created["id"], {"status": "active"})
                        print(f"  ⚠️ {job_data['title'][:50]} — enrichment failed: {e}")
                else:
                    print(f"  ➡️  {job_data['title'][:50]} — skipped enrichment (Low quality desc)")

            except Exception as e:
                print(f"  ❌ Failed: {job_data.get('title', '?')}: {e}")

    print(f"\n{'='*60}")
    print(f"  DONE! Inserted: {total_inserted} | Enriched: {total_enriched}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
