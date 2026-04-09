"""Workable Widget API adapter."""
import json
import logging
import os
from typing import Any, AsyncGenerator

import requests
from app.scraper.scraper_port import ScraperPort
from app.scraper.experience_filter import is_entry_level

logger = logging.getLogger(__name__)


class WorkableAdapter(ScraperPort):
    """
    Fetches jobs from Workable using their public Widget API.
    API: https://apply.workable.com/api/v1/widget/accounts/{subdomain}
    """

    COMPANY_NAME = "Workable"

    def __init__(self):
        super().__init__()
        config_path = os.path.join(os.getcwd(), "ats_config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.targets = config.get("workable", [])
            logger.info("Loaded %d Workable targets from ats_config.json", len(self.targets))
        except Exception as e:
            logger.error("Failed to load Workable targets: %s", e)
            self.targets = []

    async def fetch_jobs(self) -> AsyncGenerator[list[dict[str, Any]], None]:
        """Fetches and yields jobs in batches."""
        for target in self.targets:
            name = target.get("company_name", "Workable Partner")
            subdomain = target.get("subdomain")
            if not subdomain:
                continue

            logger.info("🕸️ Fetching %s jobs from Workable Widget API...", name)
            api_url = f"https://apply.workable.com/api/v1/widget/accounts/{subdomain}"

            try:
                resp = requests.get(api_url, timeout=20)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                jobs = data.get("jobs", [])
                
                batch = []
                for job in jobs:
                    title = job.get("title", "")
                    description_raw = job.get("description", "")
                    # Note: Widget API often provides a preview; full detail might need another call
                    # but usually it's enough for filtering.
                    
                    if not is_entry_level(title, description_raw):
                        continue

                    shortcode = job.get("shortcode")
                    external_url = f"https://apply.workable.com/{subdomain}/j/{shortcode}"

                    batch.append({
                        "external_id": str(shortcode),
                        "title": title,
                        "company_name": name,
                        "external_apply_url": external_url,
                        "description_raw": description_raw,
                        "skills_required": [],
                        "location": job.get("location", {}).get("city", "Remote"),
                    })

                if batch:
                    yield batch
            except Exception as e:
                logger.error("❌ Workable %s failed: %s", name, e)
