from abc import ABC, abstractmethod
from typing import Any

from app.ports.user_port import UserPort
from app.ports.job_port import JobPort
from app.ports.blog_port import BlogPort
from app.ports.chat_port import ChatPort
from app.ports.mock_interview_port import MockInterviewPort
from app.ports.feedback_port import FeedbackPort

class DatabasePort(UserPort, JobPort, BlogPort, ChatPort, MockInterviewPort, FeedbackPort, ABC):
    """
    Aggregate port for CRUD operations against the data store.
    Inherits from domain-specific ports to strictly follow ISP.
    """

    # ── Scraping Logs (Still here for now, could be extracted too) ──

    @abstractmethod
    async def insert_scraping_log(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a scraping run log entry."""
        ...

    @abstractmethod
    async def update_scraping_log(
        self, log_id: str, data: dict[str, Any]
    ) -> None:
        """Update a scraping log entry (e.g., mark finished)."""
        ...

    @abstractmethod
    async def get_learning_resources(self, skills: list[str]) -> list[dict[str, Any]]:
        """Fetch learning resources for a list of skills."""
        ...
