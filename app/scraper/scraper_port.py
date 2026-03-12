"""
Abstract interface for external job scrapers.
Each company adapter implements this port.
"""

from abc import ABC, abstractmethod
from typing import Any, Union, AsyncGenerator


class ScraperPort(ABC):
    """Port for fetching jobs from external career pages."""

    @abstractmethod
    async def fetch_jobs(self) -> Union[list[dict[str, Any]], AsyncGenerator[list[dict[str, Any]], None]]:
        """
        Scrape or fetch jobs from an external career page.

        Returns:
            A list of dicts, each with keys:
            - external_id: str — unique ID from the source
            - title: str — job title
            - description_raw: str — full job description
            - skills_required: list[str] — extracted skill tags
            - company_name: str — e.g., "Deloitte"
            - external_apply_url: str — link to apply on the company site
        """
        ...
