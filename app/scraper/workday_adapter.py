"""Generalized Workday CXS JSON API adapter."""
import json
import logging
import os
from typing import Any, AsyncGenerator

import requests
from app.scraper.scraper_port import ScraperPort
from app.scraper.experience_filter import is_entry_level

logger = logging.getLogger(__name__)


class WorkdayAdapter(ScraperPort):
    """
    Fetches jobs from multiple Workday tenants using the Candidate Experience Service (CXS) API.
    Endpoint: https://{tenant}.{wd_number}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
    """

    COMPANY_NAME = "Workday"

    def __init__(self):
        super().__init__()
        config_path = os.path.join(os.getcwd(), "ats_config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.targets = config.get("workday", [])
            logger.info("Loaded %d Workday targets from ats_config.json", len(self.targets))
        except Exception as e:
            logger.error("Failed to load Workday targets: %s", e)
            self.targets = []

    async def fetch_jobs(self) -> AsyncGenerator[list[dict[str, Any]], None]:
        """Fetches and yields jobs in batches."""
        for target in self.targets:
            name = target.get("company_name", "Workday Partner")
            tenant = target.get("tenant")
            site = target.get("site", "External")
            wd_num = target.get("wd_number", "wd3")
            
            if not tenant:
                continue

            logger.info("🕸️ Fetching %s jobs from Workday CXS API (%s)...", name, tenant)
            
            base_domain = f"{tenant}.{wd_num}.myworkdayjobs.com"
            api_url = f"https://{base_domain}/wday/cxs/{tenant}/{site}/jobs"
            base_job_url = f"https://{base_domain}/en-US/{site}"

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            try:
                # Fetch up to 50 jobs per site
                payload = {
                    "appliedFacets": {},
                    "limit": 20,
                    "offset": 0,
                    "searchText": "",
                }

                all_extracted = []
                for page in range(3): # Fetch 3 pages max
                    payload["offset"] = page * 20
                    resp = requests.post(api_url, json=payload, headers=headers, timeout=20)
                    if resp.status_code != 200:
                        break

                    data = resp.json()
                    postings = data.get("jobPostings", [])
                    if not postings:
                        break

                    for job in postings:
                        title = job.get("title", "")
                        ext_path = job.get("externalPath", "")
                        
                        # Detail fetch for description
                        slug = ext_path.split("/")[-1] if ext_path else ""
                        if not slug:
                            continue
                        
                        detail_url = f"https://{base_domain}/wday/cxs/{tenant}/{site}/job/{slug}"
                        desc_raw = ""
                        try:
                            d_resp = requests.get(detail_url, headers=headers, timeout=10)
                            if d_resp.status_code == 200:
                                d_data = d_resp.json()
                                desc_raw = d_data.get("jobPostingInfo", {}).get("jobDescription", "")
                        except:
                            desc_raw = title

                        if not is_entry_level(title, desc_raw):
                            continue

                        all_extracted.append({
                            "external_id": slug,
                            "title": title,
                            "company_name": name,
                            "external_apply_url": f"{base_job_url}{ext_path}",
                            "description_raw": desc_raw,
                            "skills_required": [],
                            "location": job.get("locationsText", "India"),
                        })

                if all_extracted:
                    yield all_extracted
            except Exception as e:
                logger.error("❌ Workday %s failed: %s", name, e)
