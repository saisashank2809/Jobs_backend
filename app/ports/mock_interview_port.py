from abc import ABC, abstractmethod
from typing import Any

class MockInterviewPort(ABC):
    """Port for mock interview persistence."""

    @abstractmethod
    async def create_mock_interview(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a new mock interview record."""
        ...

    @abstractmethod
    async def get_mock_interview(self, interview_id: str) -> dict[str, Any] | None:
        """Fetch a single mock interview by ID."""
        ...

    @abstractmethod
    async def update_mock_interview(self, interview_id: str, data: dict[str, Any]) -> None:
        """Update a mock interview record (e.g., transcript, scorecard, status)."""
        ...

    @abstractmethod
    async def list_user_mock_interviews(self, user_id: str) -> list[dict[str, Any]]:
        """List all mock interviews for a specific seeker."""
        ...

    @abstractmethod
    async def list_admin_mock_interviews(self, status_filter: str = "all") -> list[dict[str, Any]]:
        """Fetch mock interviews for the admin dashboard."""
        ...
