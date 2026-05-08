from abc import ABC, abstractmethod
from typing import Any

from app.ports.user_port import UserPort
from app.ports.job_port import JobPort
from app.ports.blog_port import BlogPort
from app.ports.chat_port import ChatPort
from app.ports.mock_interview_port import MockInterviewPort
from app.ports.feedback_port import FeedbackPort
from app.ports.playbook_port import PlaybookPort

class DatabasePort(UserPort, JobPort, BlogPort, ChatPort, MockInterviewPort, FeedbackPort, PlaybookPort, ABC):
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

    # ── Interview Materials ──

    @abstractmethod
    async def create_interview_material(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a new interview material record."""
        ...

    @abstractmethod
    async def list_interview_materials(self, company_name: str | None = None, folder_id: str | None = None) -> list[dict[str, Any]]:
        """List interview materials, optionally filtered by company or folder."""
        ...

    @abstractmethod
    async def delete_interview_material(self, material_id: str) -> dict[str, Any] | None:
        """Delete an interview material by ID, returning the deleted record if it existed."""
        ...

    @abstractmethod
    async def get_interview_material(self, material_id: str) -> dict[str, Any] | None:
        """Get a single interview material by ID."""
        pass

    # ── Material Folders ──

    @abstractmethod
    async def get_material_folder(self, folder_id: str) -> dict[str, Any] | None:
        """Get a single material folder by ID."""
        pass

    @abstractmethod
    async def list_material_folders(self) -> list[dict[str, Any]]:
        """List all interview material folders."""
        pass

    @abstractmethod
    async def create_material_folder(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new interview material folder."""
        pass

    @abstractmethod
    async def delete_material_folder(self, folder_id: str) -> bool:
        """Delete an interview material folder."""
        pass

    @abstractmethod
    async def update_material_folder(self, folder_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """Update an interview material folder."""
        pass
