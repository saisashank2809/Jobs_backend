import logging
from typing import Any
from bs4 import BeautifulSoup  # type: ignore
from crawl4ai import AsyncWebCrawler  # type: ignore
from app.scraper.base_scraper import BaseScraper  # type: ignore
from app.scraper.experience_filter import is_entry_level  # type: ignore

logger = logging.getLogger(__name__)

class DeloitteAdapter(BaseScraper):
    """Scrapes jobs from Deloitte's career page."""

    COMPANY_NAME = "Deloitte"
    CAREER_PAGE_URL: str = (
        "https://apply.deloitte.com/en_US/careers/SearchJobs"
        "/?listFilterMode=1&jobRecordsPerPage=100&sort=relevancy"
    )

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        """Fetches jobs + details using crawl4ai."""
        logger.info(f"🕸️ Scraping {self.COMPANY_NAME} from {self.CAREER_PAGE_URL}...")
        
        try:
            async with AsyncWebCrawler(verbose=True) as crawler:
                # 1. Fetch Search Page
                result = await crawler.arun(url=self.CAREER_PAGE_URL)
                if not result.html:
                    return []

                soup = BeautifulSoup(result.html, "html.parser")
                raw_jobs = self.parse_jobs(soup)
                logger.info(f"  ↳ Found {len(raw_jobs)} raw jobs (fetching details for top 15)")

                valid_jobs = []
                count = 0
                
                for job in raw_jobs:
                    if count >= 7:
                        break

                    # Check entry level logic (borrowed from base scraper)
                    # We do it early to save detail fetch time
                    # But parse_jobs returns dict with 'experience_text' empty
                    # So we check title.
                    if not is_entry_level(job["title"], ""):
                        continue

                    # 2. Fetch Detail Page
                    job_url = job["external_apply_url"]
                    try:
                        # logger.info(f"    Fetching details: {job['title'][:30]}")
                        detail_res = await crawler.arun(url=job_url)
                        
                        if detail_res.html:
                            d_soup = BeautifulSoup(detail_res.html, "html.parser")
                            # Deloitte Careers (Avature) - Multiple possible structures
                            # 1. Main detailed article content
                            # The structure often has multiple 'view--rich-text' items containing parts of the description
                            rich_text_items = d_soup.select("div.article__view__item.view--rich-text span.field-value")
                            
                            if rich_text_items:
                                # Join all rich text parts (Summary, Responsibilities, Qualifications usually separated)
                                html_parts = [str(item) for item in rich_text_items]
                                job["description_raw"] = "<br/><hr/><br/>".join(html_parts)
                            else:
                                # Fallback old selectors
                                desc_tag = (d_soup.select_one(".job-description") 
                                            or d_soup.select_one(".article__content")
                                            or d_soup.select_one(".cats-job-description")
                                            or d_soup.select_one("article.article--details"))

                                if desc_tag:
                                    job["description_raw"] = str(desc_tag)
                                else:
                                    logger.warning(f"   ⚠️ Desc selectors failed for {job['title']}")
                                    # Last resort: text dump of main section
                                    main_section = d_soup.select_one("section.section")
                                    if main_section:
                                         job["description_raw"] = "RAW_SECTION: " + str(main_section)
                                    else:
                                        job["description_raw"] = "Posted: Check official site."
                        else:
                            job["description_raw"] = "Posted: Check official site."

                    except Exception as e:
                        logger.warning(f"    Failed detail fetch for {job['title']}: {e}")
                        job["description_raw"] = "Posted: Check official site."

                    # Standardize keys
                    # parse_jobs returned partial structure, we assume BaseScraper normalization needed?
                    # No, BaseScraper logic was: fetch -> parse -> filter -> normalize.
                    # Here we do it all.
                    
                    normalized = {
                        "external_id": job["external_id"],
                        "title": job["title"],
                        "company_name": self.COMPANY_NAME,
                        "external_apply_url": job["external_apply_url"],
                        "description_raw": job["description_raw"],
                        "skills_required": [],
                        "location": job["location"],
                        "salary_range": None,
                    }
                    
                    valid_jobs.append(normalized)
                    count += 1

                logger.info(f"  ✅ Deloitte: Total {len(valid_jobs)} enriched-ready jobs")
                return valid_jobs

        except Exception as e:
            logger.error(f"❌ Failed to scrape {self.COMPANY_NAME}: {e}")
            return []
            
        return []

    def parse_jobs(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        results = []
        cards = soup.select("article.article--result")
        
        for card in cards:
            try:
                title_tag = card.select_one("h3.article__header__text__title a.link")
                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                relative_url = title_tag.get("href")
                if not relative_url:
                    continue
                
                full_url = relative_url if relative_url.startswith("http") else f"https://apply.deloitte.com{relative_url}"

                # Extract ID
                parts = full_url.split("/")
                external_id = parts[-1].split("?")[0]
                if not external_id or len(external_id) < 3:
                     external_id = parts[-2].split("?")[0] if len(parts) > 1 else "unknown"

                location = "India"
                subtitle = card.select_one(".article__header__text__subtitle")
                if subtitle:
                    spans = subtitle.select("span")
                    if spans and len(spans) > 0:
                        location = spans[-1].get_text(strip=True)

                results.append({
                    "external_id": external_id,
                    "title": title,
                    "external_apply_url": full_url,
                    "location": location,
                    # description_raw will be filled later
                })
            except Exception as e:
                pass
                
        return results
