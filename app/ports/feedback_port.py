from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

class FeedbackPort(ABC):
    @abstractmethod
    async def create_feedback(self, user_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
        """Submit a new feedback entry."""
        ...

    @abstractmethod
    async def get_user_feedback(self, user_id: UUID) -> list[dict[str, Any]]:
        """Retrieve feedback history for a specific user."""
        ...

    @abstractmethod
    async def get_all_feedback(
        self, 
        limit: int = 100, 
        offset: int = 0,
        type: str | None = None,
        rating: int | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve all feedback for admins with optional filtering."""
        ...
