import asyncio
import sys
import os
from dotenv import load_dotenv  # type: ignore

load_dotenv()

from app.dependencies import get_ai_service, get_db, get_embedding_service  # type: ignore
from app.services.enrichment_service import EnrichmentService  # type: ignore

async def main():
    db = get_db()
    ai = get_ai_service()
    emb = get_embedding_service()
    enricher = EnrichmentService(db=db, ai=ai, embeddings=emb)
    
    jobs = await db.list_active_jobs(limit=100)
    print(f"Total active jobs found: {len(jobs)}")
    
    missing_enrichment = [
        j for j in jobs 
        if not j.get('prep_guide_generated') or not j.get('resume_guide_generated') or not j.get('skills_required')
    ]
    
    print(f"Jobs missing enrichment: {len(missing_enrichment)}")
    if not missing_enrichment:
        print("All jobs are enriched!")
        return

    print(f"Re-enriching {len(missing_enrichment)} missing jobs...")
    
    sem = asyncio.Semaphore(5)
    
    async def _enrich_job(j):
        async with sem:
            print(f"Enriching: {j['company_name']} - {j['title']} (ID: {j['id']})")
            try:
                await enricher.enrich_job(j['id'])
                print(f"Finished enriching {j['id']}")
            except Exception as e:
                print(f"Failed to enrich {j['id']}: {e}")

    tasks = [_enrich_job(j) for j in missing_enrichment]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
