"""Breezy.hr JSON feed adapter."""
import json
import logging
import os
from typing import Any, AsyncGenerator

import requests
from app.scraper.scraper_port import ScraperPort
from app.scraper.experience_filter import is_entry_level

logger = logging.getLogger(__name__)


class BreezyAdapter(ScraperPort):
    """
    Fetches jobs from Breezy.hr using their public .hr/json feed.
    API: https://{slug}.breezy.hr/json
    """

    COMPANY_NAME = "Breezy"

    def __init__(self):
        super().__init__()
        config_path = os.path.join(os.getcwd(), "ats_config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.targets = config.get("breezy", [])
            logger.info("Loaded %d Breezy targets from ats_config.json", len(self.targets))
        except Exception as e:
            logger.error("Failed to load Breezy targets: %s", e)
            self.targets = []

    async def fetch_jobs(self) -> AsyncGenerator[list[dict[str, Any]], None]:
        """Fetches and yields jobs in batches."""
        for target in self.targets:
            name = target.get("company_name", "Breezy Partner")
            slug = target.get("slug")
            if not slug:
                continue

            logger.info("🕸️ Fetching %s jobs from Breezy JSON feed...", name)
            api_url = f"https://{slug}.breezy.hr/json"

            try:
                resp = requests.get(api_url, timeout=20)
                if resp.status_code != 200:
                    continue

                jobs = resp.json()
                if not isinstance(jobs, list):
                    continue
                
                batch = []
                for job in jobs:
                    title = job.get("name", "")
                    description_raw = job.get("description", "")
                    
                    if not is_entry_level(title, description_raw):
                        continue

                    job_id = job.get("id")
                    external_url = f"https://{slug}.breezy.hr/p/{job_id}"

                    batch.append({
                        "external_id": str(job_id),
                        "title": title,
                        "company_name": name,
                        "external_apply_url": external_url,
                        "description_raw": description_raw,
                        "skills_required": [],
                        "location": job.get("location", {}).get("name", "Remote"),
                    })

                if batch:
                    yield batch
            except Exception as e:
                logger.error("❌ Breezy %s failed: %s", name, e)
