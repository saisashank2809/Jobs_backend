from abc import ABC, abstractmethod
from typing import Any

class PlaybookPort(ABC):
    """Port for Playbook CRUD operations."""

    @abstractmethod
    async def create_playbook(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new playbook."""
        pass

    @abstractmethod
    async def get_playbook(self, playbook_id: str) -> dict[str, Any] | None:
        """Get a playbook by ID."""
        pass

    @abstractmethod
    async def get_playbook_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Get a playbook by slug."""
        pass

    @abstractmethod
    async def list_playbooks(self, hiring_zone: str | None = None) -> list[dict[str, Any]]:
        """List all playbooks, optionally filtered by hiring zone."""
        pass

    @abstractmethod
    async def update_playbook(self, playbook_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """Update a playbook."""
        pass

    @abstractmethod
    async def delete_playbook(self, playbook_id: str) -> bool:
        """Delete a playbook."""
        pass
