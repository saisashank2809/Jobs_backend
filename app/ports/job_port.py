from abc import ABC, abstractmethod
from typing import Any, List

class JobPort(ABC):
    @abstractmethod
    async def create_job(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a new job and return the created row."""
        ...

    @abstractmethod
    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Fetch a single job by ID."""
        ...

    @abstractmethod
    async def update_job(self, job_id: str, data: dict[str, Any]) -> None:
        """Partially update a job record."""
        ...

    @abstractmethod
    async def list_jobs_by_provider(self, provider_id: str) -> list[dict[str, Any]]:
        """List all jobs owned by a given provider."""
        ...

    @abstractmethod
    async def archive_jobs_not_in(self, company_name: str, active_external_ids: list[str]) -> int:
        """Mark ALL jobs for a company as archived if their external ID is not in active_external_ids."""
        ...

    @abstractmethod
    async def find_job_by_external_id(self, company_name: str, external_id: str) -> dict[str, Any] | None:
        """Find a job by its external source identifier."""
        ...

    @abstractmethod
    async def find_job_by_description_hash(self, description_hash: str) -> dict[str, Any] | None:
        """Find an already-enriched job with a matching description hash."""
        ...

    @abstractmethod
    async def list_active_jobs(self, skip: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Paginated list of active jobs."""
        ...

    @abstractmethod
    async def get_all_jobs_for_analytics(self) -> list[dict[str, Any]]:
        """Fetch all active jobs with fields relevant for analytics (title, salary, skills)."""
        ...

    @abstractmethod
    async def delete_job(self, job_id: str) -> None:
        """Permanently remove a job record."""
        ...
