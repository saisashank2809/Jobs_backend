"""SmartRecruiters Posting API adapter."""
import json
import logging
import os
from typing import Any, AsyncGenerator

import requests
from app.scraper.scraper_port import ScraperPort
from app.scraper.experience_filter import is_entry_level

logger = logging.getLogger(__name__)


class SmartRecruitersAdapter(ScraperPort):
    """
    Fetches jobs from SmartRecruiters using their public Posting API.
    API: https://api.smartrecruiters.com/v1/companies/{id}/postings
    """

    COMPANY_NAME = "SmartRecruiters"

    def __init__(self):
        super().__init__()
        config_path = os.path.join(os.getcwd(), "ats_config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.targets = config.get("smartrecruiters", [])
            logger.info("Loaded %d SmartRecruiters targets from ats_config.json", len(self.targets))
        except Exception as e:
            logger.error("Failed to load SmartRecruiters targets: %s", e)
            self.targets = []

    async def fetch_jobs(self) -> AsyncGenerator[list[dict[str, Any]], None]:
        """Fetches and yields jobs in batches."""
        for target in self.targets:
            name = target.get("company_name", "SR Partner")
            comp_id = target.get("id")
            if not comp_id:
                continue

            logger.info("🕸️ Fetching %s jobs from SmartRecruiters API...", name)
            # Use basic endpoint. Note: sometimes /postings needs certain params for full data, 
            # but usually it returns enough for a summary.
            api_url = f"https://api.smartrecruiters.com/v1/companies/{comp_id}/postings"

            try:
                resp = requests.get(api_url, timeout=20)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                content = data.get("content", [])
                
                batch = []
                for item in content:
                    title = item.get("name", "")
                    # Fetching full description usually requires another call per job in SR
                    # Endpoint: https://api.smartrecruiters.com/v1/companies/{id}/postings/{jobId}
                    job_id = item.get("id")
                    external_url = f"https://jobs.smartrecruiters.com/{comp_id}/{job_id}"
                    
                    # Basic detail fetch
                    detail_url = f"https://api.smartrecruiters.com/v1/companies/{comp_id}/postings/{job_id}"
                    desc_raw = ""
                    try:
                        d_resp = requests.get(detail_url, timeout=10)
                        if d_resp.status_code == 200:
                            d_data = d_resp.json()
                            sections = d_data.get("jobAd", {}).get("sections", {})
                            desc_parts = []
                            for sec_key in ["jobDescription", "qualifications", "additionalInformation"]:
                                sec = sections.get(sec_key, {})
                                if sec.get("text"):
                                    desc_parts.append(f"<h2>{sec.get('title', sec_key)}</h2>")
                                    desc_parts.append(sec.get("text"))
                            desc_raw = "\n".join(desc_parts)
                    except:
                        desc_raw = title # fallback

                    if not is_entry_level(title, desc_raw):
                        continue

                    batch.append({
                        "external_id": str(job_id),
                        "title": title,
                        "company_name": name,
                        "external_apply_url": external_url,
                        "description_raw": desc_raw,
                        "skills_required": [],
                        "location": item.get("location", {}).get("city", "Remote"),
                    })

                if batch:
                    yield batch
            except Exception as e:
                logger.error("❌ SmartRecruiters %s failed: %s", name, e)
