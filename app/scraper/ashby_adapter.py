"""Ashby Job Board API adapter."""
import json
import logging
import os
from typing import Any, AsyncGenerator

import requests
from app.scraper.scraper_port import ScraperPort
from app.scraper.experience_filter import is_entry_level

logger = logging.getLogger(__name__)


class AshbyAdapter(ScraperPort):
    """
    Fetches jobs from Ashby using their public Job Board API.
    API: https://api.ashbyhq.com/posting-api/job-board/{slug}
    """

    COMPANY_NAME = "Ashby"

    def __init__(self):
        super().__init__()
        config_path = os.path.join(os.getcwd(), "ats_config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.targets = config.get("ashby", [])
            logger.info("Loaded %d Ashby targets from ats_config.json", len(self.targets))
        except Exception as e:
            logger.error("Failed to load Ashby targets: %s", e)
            self.targets = []

    async def fetch_jobs(self) -> AsyncGenerator[list[dict[str, Any]], None]:
        """Fetches and yields jobs in batches."""
        for target in self.targets:
            name = target.get("company_name", "Ashby Partner")
            slug = target.get("slug")
            if not slug:
                continue

            logger.info("🕸️ Fetching %s jobs from Ashby API...", name)
            api_url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"

            try:
                resp = requests.get(api_url, timeout=20)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                jobs = data.get("jobs", [])
                
                batch = []
                for job in jobs:
                    title = job.get("title", "")
                    description_raw = job.get("descriptionHtml", "")
                    
                    if not is_entry_level(title, description_raw):
                        continue

                    batch.append({
                        "external_id": str(job.get("id")),
                        "title": title,
                        "company_name": name,
                        "external_apply_url": job.get("jobUrl"),
                        "description_raw": description_raw,
                        "skills_required": [],
                        "location": job.get("location", "Remote"),
                    })

                if batch:
                    yield batch
            except Exception as e:
                logger.error("❌ Ashby %s failed: %s", name, e)
