"""Greenhouse Job Board API adapter."""
import json
import logging
import os
from typing import Any, AsyncGenerator

import requests
from app.scraper.scraper_port import ScraperPort
from app.scraper.experience_filter import is_entry_level

logger = logging.getLogger(__name__)


class GreenhouseAdapter(ScraperPort):
    """
    Fetches jobs from multiple companies using Greenhouse via their public Job Board API.
    API: https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
    """

    COMPANY_NAME = "Greenhouse"

    def __init__(self):
        super().__init__()
        # Load tokens from ats_config.json
        config_path = os.path.join(os.getcwd(), "ats_config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.targets = config.get("greenhouse", [])
            logger.info("Loaded %d Greenhouse targets from ats_config.json", len(self.targets))
        except Exception as e:
            logger.error("Failed to load Greenhouse targets from ats_config.json: %s", e)
            self.targets = []

    async def fetch_jobs(self) -> AsyncGenerator[list[dict[str, Any]], None]:
        """
        Fetches jobs for all Greenhouse targets and yields them in batches per company.
        """
        if not self.targets:
            logger.warning("No Greenhouse targets found to scrape.")
            return

        for target in self.targets:
            company_name = target.get("company_name", "Unknown Greenhouse Partner")
            token = target.get("token")
            if not token:
                continue

            logger.info("🕸️ Fetching %s jobs from Greenhouse API...", company_name)
            api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"

            try:
                resp = requests.get(api_url, timeout=20)
                if resp.status_code != 200:
                    logger.warning("⚠️ Greenhouse API for %s returned %d", company_name, resp.status_code)
                    continue

                data = resp.json()
                jobs_data = data.get("jobs", [])
                if not jobs_data:
                    logger.info("  ↳ No jobs found for %s", company_name)
                    continue

                batch = []
                for job in jobs_data:
                    title = job.get("title", "")
                    description_raw = job.get("content", "")
                    # Greenhouse description is HTML; AI handles it fine.
                    
                    # Apply entry-level filter
                    if not is_entry_level(title, description_raw):
                        continue

                    batch.append({
                        "external_id": str(job.get("id")),
                        "title": title,
                        "company_name": company_name,
                        "external_apply_url": job.get("absolute_url"),
                        "description_raw": description_raw,
                        "skills_required": [],
                        "location": job.get("location", {}).get("name", "Remote"),
                    })

                if batch:
                    logger.info("  ✅ Yielding %d entry-level jobs for %s", len(batch), company_name)
                    yield batch
                else:
                    logger.info("  ↳ No entry-level jobs matched for %s", company_name)

            except Exception as e:
                logger.error("❌ Failed to fetch Greenhouse jobs for %s: %s", company_name, e)

        logger.info("✅ Greenhouse scraping finished.")
