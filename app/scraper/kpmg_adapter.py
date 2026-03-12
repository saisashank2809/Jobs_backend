import logging
import requests  # type: ignore
import time
from typing import Any
from app.scraper.scraper_port import ScraperPort  # type: ignore
from app.scraper.experience_filter import is_entry_level  # type: ignore

logger = logging.getLogger(__name__)


class KPMGAdapter(ScraperPort):
    """Scrapes jobs from KPMG via Oracle Cloud HCM REST API (no browser needed)."""

    COMPANY_NAME = "KPMG"
    # Oracle Cloud HCM REST API for KPMG external career site
    API_URL = (
        "https://ejvp.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
        "?onlyData=true"
        "&expand=requisitionList.secondaryLocations,flexFieldsFacet.values"
        "&finder=findReqs;siteNumber=CX_1,"
        "facetsList=LOCATIONS%3BWORK_LOCATIONS%3BWORKPLACE_TYPES%3BTITLES%3BCATEGORIES%3BORGANIZATIONS%3BPOSTING_DATES%3BFLEX_FIELDS,"
        "limit=25,"
        "sortBy=POSTING_DATES_DESC"
    )
    PORTAL_BASE = "https://ejvp.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job"

    COMMON_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://ejvp.fa.us2.oraclecloud.com",
        "Referer": "https://ejvp.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/requisitions",
    }

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        """Fetches jobs directly from Oracle Cloud HCM API — no Playwright needed."""
        logger.info(f"🕸️ Fetching {self.COMPANY_NAME} jobs from Oracle Cloud HCM API...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }

        all_jobs = []

        try:
            # Fetch multiple pages via offset, stop after 15 enriched jobs
            desired_count = 7

            for page_offset in range(0, 100, 25):
                if len(all_jobs) >= desired_count:
                    break

                url = self.API_URL + f",offset={page_offset}"
                resp = requests.get(url, headers=headers, timeout=15)

                if resp.status_code != 200:
                    logger.warning(f"⚠️ KPMG API returned {resp.status_code}")
                    break

                data = resp.json()
                items = data.get("items", [])

                if not items:
                    break

                # The Oracle API returns a wrapper; actual jobs are inside requisitionList
                for wrapper in items:
                    if len(all_jobs) >= desired_count:
                        break

                    req_list = wrapper.get("requisitionList", [])
                    if not req_list:
                        continue

                    for job in req_list:
                        if len(all_jobs) >= desired_count:
                            break

                        title = job.get("Title", "")
                        job_id = str(job.get("Id", ""))
                        location = job.get("PrimaryLocation", "India")
                        posted = job.get("PostedDate", "")
                        workplace_type = job.get("WorkplaceType", "")

                        if not title or not job_id:
                            continue

                        full_url = f"{self.PORTAL_BASE}/{job_id}"

                        # Check entry level
                        if not is_entry_level(title, ""):
                            continue

                        # --- Fetch Full Description ---
                        # Detail API: Oracle Cloud HCM uses recruitingCEJobRequisitionDetails with finder=ById
                        detail_url = f"https://ejvp.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?expand=all&finder=ById;Id={job_id},siteNumber=CX_1"
                        desc_raw = "Posted: Check official site." # Initialize desc_raw
                        # Retry logic
                        for attempt in range(3):
                            try:
                                # Fetch detail
                                d_resp = requests.get(detail_url, headers=self.COMMON_HEADERS, timeout=30)
                                if d_resp.status_code == 200:
                                    d_json = d_resp.json()
                                    items = d_json.get("items", [{}])
                                    job_info = items[0] if items else {}
                                    
                                    desc = job_info.get("ExternalDescriptionStr") or ""
                                    resp = job_info.get("ExternalResponsibilitiesStr") or ""
                                    qual = job_info.get("ExternalQualificationsStr") or ""
                                    
                                    # Combine parts with clear headers for enrichment
                                    desc_parts = []
                                    if desc: desc_parts.append(f"<h3>About the Role</h3>{desc}")
                                    if resp: desc_parts.append(f"<h3>Responsibilities</h3>{resp}")
                                    if qual: desc_parts.append(f"<h3>Requirements</h3>{qual}")
                                    
                                    desc_raw = "<br><br>".join(desc_parts) if desc_parts else str(job_info)

                                    # Clean up if it's just raw JSON to save tokens?
                                    # No, let the enrichment filter handle length.
                                    if len(desc_raw) > 200:
                                        break # Success
                            except Exception as e:
                                logger.warning(f"    Retry {attempt+1} failed for {title}: {e}")
                                time.sleep(2 * (attempt + 1))

                        # Fallback if still failing
                        if not desc_raw or len(desc_raw) < 50:
                             desc_raw = f"Posted: {posted}. Workplace: {workplace_type}."

                        all_jobs.append({
                            "external_id": job_id,
                            "title": title,
                            "company_name": self.COMPANY_NAME,
                            "external_apply_url": full_url,
                            "description_raw": desc_raw,
                            "skills_required": [],
                            "location": location,
                            "salary_range": None,
                        })

                has_more = data.get("hasMore", False)
                logger.info(f"  ↳ KPMG page offset {page_offset}: {len(all_jobs)} entry-level so far")
                if not has_more:
                    break

            logger.info(f"  ✅ KPMG: Total {len(all_jobs)} entry-level jobs with full details")
            return all_jobs

        except Exception as e:
            logger.error(f"❌ Failed to fetch KPMG jobs: {e}")
            return []
