"""
Ingestion service — orchestrates the scrape → dedup → insert → enrich pipeline.
Single Responsibility: only handles external job ingestion logic.

Production hardening:
  - Fail-fast per-scraper: if fetch_jobs() throws, log to scraping_logs and move on.
  - SHA-256 dedup: skip AI enrichment for duplicate job descriptions.
"""

import asyncio
import hashlib
import logging
import re
import traceback
from datetime import datetime, timezone
from typing import Any

from app.ports.ai_port import AIPort  # type: ignore
from app.ports.database_port import DatabasePort  # type: ignore
from app.ports.embedding_port import EmbeddingPort  # type: ignore
from app.scraper.scraper_port import ScraperPort  # type: ignore
from app.services.enrichment_service import EnrichmentService  # type: ignore

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.services.telegram_channel_service import TelegramChannelService  # type: ignore

logger = logging.getLogger(__name__)

# System user UUID that "owns" all scraped/ingested jobs.
# Must match the UUID inserted by external_ingestion_migration.sql.
INGESTION_PROVIDER_ID = "00000000-0000-4000-a000-000000000001"


class IngestionService:
    """
    Fetches jobs from a scraper, deduplicates against existing records,
    inserts new ones, and triggers AI enrichment for each.
    """

    def __init__(
        self,
        db: DatabasePort,
        ai: AIPort,
        embeddings: EmbeddingPort,
        telegram: "TelegramChannelService | None" = None,
    ) -> None:
        self._db = db
        self._ai = ai
        self._emb = embeddings
        self._telegram = telegram

    async def ingest_jobs(self, scraper: ScraperPort) -> dict[str, Any]:
        """
        Full ingestion pipeline with resilience:
        1. Create a scraping_log entry (status='running')
        2. Fetch jobs from the external scraper (fail-fast on error)
        3. Deduplicate by (company_name, external_id)
        4. SHA-256 hash dedup for AI enrichment cost savings
        5. Insert new jobs and trigger enrichment
        6. Finalize scraping_log with results

        Returns a stats dict: {fetched, new, skipped, errors, dedup_hits}
        """
        source_name = scraper.COMPANY_NAME.lower()
        started_at = datetime.now(timezone.utc).isoformat()

        # Create log entry at the start of the run
        log_entry = await self._db.insert_scraping_log({
            "source_name": source_name,
            "status": "running",
            "started_at": started_at,
        })
        log_id = log_entry["id"]

        stats: dict[str, Any] = {
            "fetched": 0, "new": 0, "skipped": 0,
            "errors": 0, "dedup_hits": 0,
        }

        # Queue to collect all enriched/new jobs for rapid Telegram broadcasting at the end
        telegram_queue = []

        # ── Step 1 & 2: Fetch and Process (Incremental Support) ──────
        active_ids_by_company = {}

        enrichment_tasks = []
        enrichment_sem = asyncio.Semaphore(5)

        async def _run_enrichment(job_id: str, company: str, ext_id: str):
            async with enrichment_sem:
                enricher = EnrichmentService(db=self._db, ai=self._ai, embeddings=self._emb)
                try:
                    enrichment = await enricher.enrich_job(job_id)
                    logger.info("Background enrichment finished: %s / %s", company, ext_id)

                    # ── Queue for Telegram Channel ──────────────────
                    if self._telegram:
                        job_data = await self._db.get_job(job_id)
                        if job_data:
                            # Overlay enrichment fields that may not yet be persisted
                            if enrichment:
                                if enrichment.estimated_salary_range:
                                    job_data["salary_range"] = enrichment.estimated_salary_range
                                if enrichment.qualification:
                                    job_data["qualification"] = enrichment.qualification
                                if enrichment.experience:
                                    job_data["experience"] = enrichment.experience
                            telegram_queue.append(job_data)
                except Exception as e:
                    logger.warning("Background enrichment failed for %s: %s", job_id, e)

        async def _process_job_batch(batch: Any):
            for job_data in batch:
                company = job_data["company_name"]
                ext_id = job_data["external_id"]
                
                if company not in active_ids_by_company:
                    active_ids_by_company[company] = []
                active_ids_by_company[company].append(ext_id)

                try:
                    # Strict CJK / Foreign Language Filter
                    # If the job title or description contains Japanese, Chinese, or Korean,
                    # drop it immediately. Many "Remote" AWS jobs are actually Japan-only.
                    title = job_data.get("title", "")
                    desc_raw = job_data.get("description_raw", "")
                    combo_text = title + " " + desc_raw
                    
                    if re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', combo_text):
                        logger.info("Skipping foreign job (CJK characters detected): %s in %s", title, company)
                        stats["skipped"] += 1
                        continue

                    # --- Location & Remote Logic ---
                    loc = (job_data.get("location", "") or "India").lower()
                    title_lower = title.lower()
                    desc_lower = desc_raw.lower()
                    
                    # 1. Higher-fidelity Remote detection (Title, Location, or Body)
                    is_remote = any("remote" in text for text in [loc, title_lower, desc_lower])
                    
                    # 2. India-only location check (only applies if NOT remote)
                    india_keywords = ["india", "bengaluru", "bangalore", "mumbai", "delhi", "pune", "hyderabad", "chennai", "noida", "gurugram", "gurgaon", "kerala", "karnataka", "maharashtra", "gujarat", "ahmedabad", "kolkata"]
                    foreign_keywords = ["usa", "united states", "uk", "united kingdom", "london", "new york", "california", "canada", "australia", "germany", "france", "singapore", "dubai", "uae", "mexico", "brazil", "japan", "china", "ireland", "washington", "texas", "florida"]
                    
                    is_india_eligible = False
                    if any(kw in loc for kw in india_keywords) or loc == "" or loc == "india":
                        is_india_eligible = True
                    elif not any(kw in loc for kw in foreign_keywords):
                        # If no foreign keywords, and no specific India keywords, we assume India for non-US/UK sites
                        is_india_eligible = True
                    
                    # Country code check (e.g. , US)
                    if re.search(r",\s*(us|uk|ca|au)$", loc):
                        is_india_eligible = False

                    # Final Logic: Allow if it's explicitly Remote OR if it's in India
                    if not (is_remote or is_india_eligible):
                        logger.info("Skipping non-remote foreign job: %s in %s", company, loc)
                        stats["skipped"] += 1
                        continue

                    # Dedup check
                    existing = await self._db.find_job_by_external_id(company, ext_id)
                    if existing:
                        stats["skipped"] += 1
                        continue

                    desc_hash = hashlib.sha256(desc_raw.encode()).hexdigest() if desc_raw else None

                    created = await self._db.create_job({
                        "provider_id": INGESTION_PROVIDER_ID,
                        "title": job_data["title"],
                        "description_raw": desc_raw,
                        "skills_required": job_data.get("skills_required", []),
                        "external_id": ext_id,
                        "external_apply_url": job_data.get("external_apply_url"),
                        "company_name": company,
                        "description_hash": desc_hash,
                        "status": "active",  # Mark as active immediately for frontend visibility
                        "location": loc,
                    })

                    # Dedup enrichment
                    if desc_hash:
                        donor = await self._db.find_job_by_description_hash(desc_hash)
                        if donor:
                            await self._db.update_job(created["id"], {
                                "resume_guide_generated": donor["resume_guide_generated"],
                                "prep_guide_generated": donor["prep_guide_generated"],
                                "embedding": donor["embedding"],
                            })
                            stats["new"] += 1
                            stats["dedup_hits"] += 1
                            if self._telegram:
                                job_data = await self._db.get_job(created["id"])
                                if job_data:
                                    telegram_queue.append(job_data)
                            continue

                    # Run enrichment (updates the fields, status remains active)
                    task = asyncio.create_task(_run_enrichment(created["id"], company, ext_id))
                    enrichment_tasks.append(task)

                    stats["new"] += 1
                    logger.info("Ingested and active: %s / %s", company, ext_id)

                except Exception:
                    logger.exception("Failed to ingest: %s / %s", company, ext_id)
                    stats["errors"] += 1

        try:
            # Note: Do NOT await here yet, as it might be an async generator
            fetch_result = scraper.fetch_jobs()
            
            if hasattr(fetch_result, "__aiter__"):
                # It's an async generator (Incremental batches)
                async for batch in fetch_result:
                    stats["fetched"] += len(batch)
                    await _process_job_batch(batch)
            else:
                # It's a regular coroutine/list
                raw_jobs = await fetch_result
                stats["fetched"] = len(raw_jobs)
                await _process_job_batch(raw_jobs)

        except Exception as exc:
            tb = traceback.format_exc()
            logger.error("Scraper %s failed: %s", source_name, exc)
            await self._db.update_scraping_log(log_id, {
                "status": "failed",
                "error_message": str(exc),
                "traceback": tb,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            })
            return {**stats, "error": str(exc)}

        # ── Step 3: Cleanup outdated jobs ─────────────────────
        # Note: If the scraper fails entirely (e.g. timeout), it won't hit this block.
        # But if it returns 0 jobs cleanly, we assume they removed all jobs.
        archived_count = 0
        for company, active_ids in active_ids_by_company.items():
            count = await self._db.archive_jobs_not_in(company, active_ids)
            archived_count += count
        
        stats["archived_outdated"] = archived_count

        # Wait for all background enrichment tasks to finish
        if enrichment_tasks:
            logger.info("Waiting for %d background enrichment tasks to finish...", len(enrichment_tasks))
            await asyncio.gather(*enrichment_tasks, return_exceptions=True)

        # ── Fast Telegram Broadcasting ────────────────────────
        if self._telegram and telegram_queue:
            logger.info("Blasting %d jobs to Telegram channel...", len(telegram_queue))
            for i, job in enumerate(telegram_queue):
                await self._telegram.post_job(job)
                if i < len(telegram_queue) - 1:
                    await asyncio.sleep(0.1)

        # ── Step 5: Finalize log ──────────────────────────────
        final_status = "success"
        if stats["errors"] > 0 and stats["new"] > 0:
            final_status = "partial"
        elif stats["errors"] > 0 and stats["new"] == 0:
            final_status = "failed"

        await self._db.update_scraping_log(log_id, {
            "status": final_status,
            "jobs_found": stats["fetched"],
            "jobs_new": stats["new"],
            "jobs_skipped": stats["skipped"],
            "error_count": stats["errors"],
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })

        logger.info("Ingestion complete for %s. Stats: %s", source_name, stats)
        return stats

