"""Lever Postings API adapter."""
import json
import logging
import os
from typing import Any, AsyncGenerator

import requests
from app.scraper.scraper_port import ScraperPort
from app.scraper.experience_filter import is_entry_level

logger = logging.getLogger(__name__)


class LeverAdapter(ScraperPort):
    """
    Fetches jobs from multiple companies using Lever via their public Postings API.
    API: https://api.lever.co/v0/postings/{company_id}
    """

    COMPANY_NAME = "Lever"

    def __init__(self):
        super().__init__()
        # Load tokens from ats_config.json
        config_path = os.path.join(os.getcwd(), "ats_config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.targets = config.get("lever", [])
            logger.info("Loaded %d Lever targets from ats_config.json", len(self.targets))
        except Exception as e:
            logger.error("Failed to load Lever targets from ats_config.json: %s", e)
            self.targets = []

    async def fetch_jobs(self) -> AsyncGenerator[list[dict[str, Any]], None]:
        """
        Fetches jobs for all Lever targets and yields them in batches per company.
        """
        if not self.targets:
            logger.warning("No Lever targets found to scrape.")
            return

        for target in self.targets:
            company_name = target.get("company_name", "Unknown Lever Partner")
            company_id = target.get("company_id")
            if not company_id:
                continue

            logger.info("🕸️ Fetching %s jobs from Lever API...", company_name)
            api_url = f"https://api.lever.co/v0/postings/{company_id}"

            try:
                resp = requests.get(api_url, timeout=20)
                if resp.status_code != 200:
                    logger.warning("⚠️ Lever API for %s returned %d", company_name, resp.status_code)
                    continue

                jobs_data = resp.json()
                if not jobs_data:
                    logger.info("  ↳ No jobs found for %s", company_name)
                    continue

                batch = []
                for job in jobs_data:
                    title = job.get("text", "")
                    description_raw = job.get("descriptionHtml", "") + "\n" + job.get("additionalHtml", "")
                    
                    # Apply entry-level filter
                    if not is_entry_level(title, description_raw):
                        continue

                    batch.append({
                        "external_id": str(job.get("id")),
                        "title": title,
                        "company_name": company_name,
                        "external_apply_url": job.get("hostedUrl"),
                        "description_raw": description_raw,
                        "skills_required": [],
                        "location": job.get("categories", {}).get("location", "Remote"),
                    })

                if batch:
                    logger.info("  ✅ Yielding %d entry-level jobs for %s", len(batch), company_name)
                    yield batch
                else:
                    logger.info("  ↳ No entry-level jobs matched for %s", company_name)

            except Exception as e:
                logger.error("❌ Failed to fetch Lever jobs for %s: %s", company_name, e)

        logger.info("✅ Lever scraping finished.")
