"""
Job service — CRUD for job listings.
Single Responsibility: only handles job data operations.
"""

from typing import Any

from app.ports.database_port import DatabasePort
from app.services.job_summary_service import enrich_job_summary


class JobService:
    """Handles job CRUD operations."""

    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def create_job(
        self, provider_id: str, title: str, description: str, skills: list[str]
    ) -> dict[str, Any]:
        """Insert a new job record and return the created row."""
        data = {
            "provider_id": provider_id,
            "title": title,
            "description_raw": description,
            "skills_required": skills,
        }
        return await self._db.create_job(data)

    async def list_by_provider(self, provider_id: str) -> list[dict[str, Any]]:
        """List all jobs created by a given provider."""
        jobs = await self._db.list_jobs_by_provider(provider_id)
        return [enrich_job_summary(job) for job in jobs]

    async def list_feed(self, skip: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Paginated list of active jobs for the job seeker feed."""
        jobs = await self._db.list_active_jobs(skip=skip, limit=limit)
        return [enrich_job_summary(job) for job in jobs]

    async def get_details(self, job_id: str) -> dict[str, Any] | None:
        """Get full 4-Pillar job details."""
        job = await self._db.get_job(job_id)
        return enrich_job_summary(job) if job else None

    async def delete_job(self, job_id: str, provider_id: str) -> bool:
        """Permanently delete a job, verifying ownership first."""
        job = await self._db.get_job(job_id)
        if not job or job.get("provider_id") != provider_id:
            return False
        
        await self._db.delete_job(job_id)
        return True
