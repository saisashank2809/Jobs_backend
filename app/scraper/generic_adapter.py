"""
Generic GCC Adapter — scrapes jobs from career pages in valid_gcc_links.json.

Uses Playwright directly (not crawl4ai) for reliable, dependency-light scraping.
Follows the same pattern as DeloitteAdapter:
  1. Visit each career page
  2. Extract job-like links
  3. Visit detail pages
  4. Filter for 2023/2024/2025 mentions
"""

import json
import logging
import os
import re
import hashlib
import asyncio
from typing import Any, AsyncGenerator, Union
from urllib.parse import urlparse

from bs4 import BeautifulSoup  # type: ignore
from playwright.async_api import async_playwright  # type: ignore

from app.scraper.scraper_port import ScraperPort  # type: ignore
from app.scraper.experience_filter import is_entry_level  # type: ignore

logger = logging.getLogger(__name__)


class GenericAdapter(ScraperPort):
    """
    Scrapes jobs from generic career pages listed in valid_gcc_links.json.
    Uses Playwright directly for headless browsing.
    """

    COMPANY_NAME = "Generic GCC"
    CAREER_PAGE_URL = "Multiple URLs via valid_gcc_links.json"

    # Max jobs to extract per career site (keeps run time manageable)
    MAX_JOBS_PER_SITE = 5
    # Page load timeout in ms
    PAGE_TIMEOUT = 30000

    def __init__(self):
        super().__init__()
        json_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "valid_gcc_links.json"
        )
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                self.target_urls = json.load(f)
            logger.info("Loaded %d URLs from valid_gcc_links.json", len(self.target_urls))
        except Exception as e:
            logger.error("Failed to load valid_gcc_links.json: %s", e)
            self.target_urls = []

    # Common job search subpaths to try appending to the base career URL
    _SEARCH_SUBPATHS = [
        "/search", "/jobs", "/en/jobs", "/job-search", "/search-jobs",
        "/positions", "/openings", "/listings", "/search?q=",
        "/global/en/jobs", "/us/en/jobs", "/in/en/jobs",
    ]

    async def fetch_jobs(self) -> AsyncGenerator[list[dict[str, Any]], None]:
        """Fetches jobs from all target URLs using Playwright with limited concurrency, yielding results as they finish."""
        logger.info(
            "🕸️ Scraping %s across %d sites...",
            self.COMPANY_NAME, len(self.target_urls),
        )

        semaphore = asyncio.Semaphore(10)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

            async def _process_site_with_sem(url: str) -> list[dict[str, Any]]:
                async with semaphore:
                    return await self._process_site(context, url)

            tasks = [asyncio.create_task(_process_site_with_sem(url)) for url in self.target_urls]
            
            for future in asyncio.as_completed(tasks):
                site_jobs: list[dict[str, Any]] = await future
                if site_jobs:
                    yield site_jobs

            await browser.close()

        logger.info("✅ Generic GCC: Finished scraping %d sites", len(self.target_urls))

    async def _process_site(self, context, target_url: str) -> list[dict[str, Any]]:
        """Scrapes a single career site."""
        site_jobs = []
        company_name = self._extract_company_name(target_url)
        logger.info("🕸️ [%s] Scraping: %s", company_name, target_url)

        try:
            # Strategy 1: Try the landing page itself first
            candidate_links = await self._scrape_page_for_jobs(context, target_url)

            # Strategy 2: If landing page had no real job links, try common subpaths
            if len(candidate_links) < 2:
                parsed = urlparse(target_url)
                base = f"{parsed.scheme}://{parsed.netloc}"
                for subpath in self._SEARCH_SUBPATHS:
                    try_url = base + subpath
                    more_links = await self._scrape_page_for_jobs(context, try_url)
                    candidate_links.extend(more_links)
                    if len(candidate_links) >= 5:
                        break

            # Deduplicate links
            seen = set()
            unique_links = []
            for link in candidate_links:
                if link["external_apply_url"] not in seen:
                    seen.add(link["external_apply_url"])
                    unique_links.append(link)
            candidate_links = unique_links

            logger.info("  ↳ [%s] Found %d candidate job links", company_name, len(candidate_links))

            count = 0
            for job in candidate_links:
                if count >= self.MAX_JOBS_PER_SITE:
                    break

                # Entry-level filter on title
                if job["title"] and len(job["title"]) > 3 and not is_entry_level(job["title"], ""):
                    continue

                # Fetch detail page
                job_url = job["external_apply_url"]
                try:
                    detail_page = await context.new_page()
                    await detail_page.goto(job_url, timeout=self.PAGE_TIMEOUT, wait_until="domcontentloaded")
                    await detail_page.wait_for_timeout(2000)

                    detail_html = await detail_page.content()
                    await detail_page.close()

                    d_soup = BeautifulSoup(detail_html, "html.parser")
                    raw_text = d_soup.body.get_text(separator="\n", strip=True) if d_soup.body else ""

                    # Content check
                    if not self._is_job_detail_page(d_soup):
                        continue

                    # YEAR FILTER
                    if not re.search(r"202[345]", raw_text) and not re.search(r"202[345]", job["title"]):
                        continue

                    desc_tag = (
                        d_soup.select_one(".job-description")
                        or d_soup.select_one(".job-details")
                        or d_soup.select_one("[itemprop='description']")
                        or d_soup.select_one("article")
                        or d_soup.select_one("main")
                    )

                    if desc_tag:
                        for junk in desc_tag(["script", "style", "iframe", "noscript", "nav", "footer"]):
                            junk.decompose()
                        description_raw = str(desc_tag)
                    else:
                        description_raw = "RAW_DUMP: " + raw_text[:3000]

                    site_jobs.append({
                        "external_id": job["external_id"],
                        "title": job["title"] or f"Job at {company_name}",
                        "company_name": company_name,
                        "external_apply_url": job["external_apply_url"],
                        "description_raw": description_raw,
                        "skills_required": [],
                        "location": "India",
                        "salary_range": None,
                    })
                    count += 1
                except Exception as e:
                    logger.warning("    [%s] Failed detail fetch for %s: %s", company_name, job_url, e)

        except Exception as e:
            logger.error("❌ [%s] Failed to scrape site: %s", company_name, e)
            
        return site_jobs


    async def _scrape_page_for_jobs(self, context, url: str) -> list[dict[str, Any]]:
        """Visit a page, extract job links from HTML and JSON-LD structured data."""
        results = []
        try:
            page = await context.new_page()
            await page.goto(url, timeout=self.PAGE_TIMEOUT, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            html = await page.content()
            await page.close()

            soup = BeautifulSoup(html, "html.parser")

            # Method A: Extract from JSON-LD structured data (schema.org JobPosting)
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get("@type") == "JobPosting":
                            title = item.get("title", "")
                            job_url = item.get("url", "")
                            if title and job_url:
                                results.append({
                                    "external_id": str(hashlib.md5(job_url.encode()).hexdigest())[:12] if isinstance(hashlib.md5(job_url.encode()).hexdigest(), str) else "",  # type: ignore
                                    "title": title,
                                    "external_apply_url": job_url,
                                    "location": "India",
                                })
                except (json.JSONDecodeError, TypeError):
                    pass

            # Method B: Extract from <a> links that look like job postings
            results.extend(self._parse_job_links(soup, url))

        except Exception as e:
            logger.debug("  Could not scrape %s: %s", url, e)

        return results

    # ── Helpers ────────────────────────────────────────────────

    # Words in link text that indicate a navigation/info page, NOT a job posting
    _SKIP_TEXTS = {
        "privacy", "faq", "frequently asked", "our stories", "about", "contact",
        "terms", "cookie", "help", "sign in", "sign up", "login", "register",
        "blog", "news", "careers home", "home", "apply now", "search", "back",
        "learn more", "read more", "see all", "view all", "returnship",
    }

    # URL path segments that strongly indicate an actual job detail page
    _JOB_URL_PATTERNS = re.compile(
        r"/(job|jobs|position|positions|opening|openings|vacancy|vacancies|requisition|req|role|roles)"
        r"/[^/]+",  # Must have at least one more path segment after (the actual job)
        re.IGNORECASE,
    )

    @staticmethod
    def _extract_company_name(url: str) -> str:
        """Derive a clean company name from the URL."""
        netloc = urlparse(url).netloc
        name = netloc.replace("www.", "").replace("careers.", "").replace("jobs.", "")
        name = name.split(".")[0].replace("-", " ").title()
        return name

    def _parse_job_links(self, soup: BeautifulSoup, base_url: str) -> list[dict[str, Any]]:
        """Extract links that look like individual job postings."""
        results = []
        seen_urls: set[str] = set()
        parsed_base = urlparse(base_url)

        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            text = a.get_text(strip=True)

            # Build full URL first
            if href.startswith("http"):
                full_url = href
            elif href.startswith("/"):
                full_url = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
            else:
                continue

            # Must match a job-specific URL pattern (e.g. /job/12345, /positions/analyst)
            if not self._JOB_URL_PATTERNS.search(full_url):
                continue

            # Skip known non-job link text
            text_lower = text.lower().strip()
            if any(skip in text_lower for skip in self._SKIP_TEXTS):
                continue

            # Title must be substantial (at least 5 chars to be a real job title)
            if len(text) < 5:
                continue

            # Deduplicate
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            external_id = str(hashlib.md5(full_url.encode()).hexdigest())[:12]  # type: ignore

            results.append({
                "external_id": external_id,
                "title": text,
                "external_apply_url": full_url,
                "location": "India",
            })

        return results

    @staticmethod
    def _is_job_detail_page(soup: BeautifulSoup) -> bool:
        """
        Heuristic check: does this page look like an actual job posting?
        Looks for common job-related keywords in the main content.
        """
        text = ""
        main = soup.select_one("main") or soup.select_one("article") or soup.body
        if main:
            text = main.get_text(separator=" ", strip=True).lower()

        job_keywords = ["responsibilities", "qualifications", "requirements", "apply", "experience", "skills", "salary", "benefits", "role", "position"]
        matches = sum(1 for kw in job_keywords if kw in text)
        # At least 3 job-related keywords should be present
        return matches >= 3

