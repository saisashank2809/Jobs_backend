"""
Job endpoints — creation, listing, and detail retrieval.
All logic delegated to JobService and EnrichmentService.
"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status  # type: ignore

from app.dependencies import get_ai_service, get_db, get_embedding_service  # type: ignore
from app.domain.models import JobCreate, JobCreateResponse, JobDetail, JobFeedItem  # type: ignore
from app.ports.ai_port import AIPort  # type: ignore
from app.ports.database_port import DatabasePort  # type: ignore
from app.ports.embedding_port import EmbeddingPort  # type: ignore
from app.services.auth_service import get_current_user  # type: ignore
from app.services.enrichment_service import EnrichmentService  # type: ignore
from app.services.job_service import JobService  # type: ignore

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_job(
    body: JobCreate,
    background_tasks: BackgroundTasks,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
    ai: AIPort = Depends(get_ai_service),
    emb: EmbeddingPort = Depends(get_embedding_service),
):
    """
    Create a new job posting.
    AI enrichment (resume guide + prep questions) runs in the background.
    """
    job_svc = JobService(db=db)
    job = await job_svc.create_job(
        provider_id=current_user["id"],
        title=body.title,
        description=body.description_raw,
        skills=body.skills_required,
    )

    # Kick off enrichment as a background task
    enrichment_svc = EnrichmentService(db=db, ai=ai, embeddings=emb)
    background_tasks.add_task(enrichment_svc.enrich_job, job["id"])

    return JobCreateResponse(id=job["id"])


@router.get("/provider", response_model=list[JobDetail])
async def list_provider_jobs(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """List all jobs created by the authenticated provider."""
    job_svc = JobService(db=db)
    jobs = await job_svc.list_by_provider(current_user["id"])
    return [JobDetail(**j) for j in jobs]


@router.get("/feed", response_model=list[JobFeedItem])
async def get_job_feed(
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: DatabasePort = Depends(get_db),
):
    """Paginated feed of active job listings (public)."""
    job_svc = JobService(db=db)
    jobs = await job_svc.list_feed(skip=skip, limit=limit)
    return [JobFeedItem(**j) for j in jobs]


@router.get("/{job_id}/details", response_model=JobDetail)
async def get_job_details(
    job_id: str,
    db: DatabasePort = Depends(get_db),
):
    """Get full 4-Pillar details for a job posting."""
    job_svc = JobService(db=db)
    job = await job_svc.get_details(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return JobDetail(**job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Permanently delete a job listing (Provider only, ownership verified)."""
    job_svc = JobService(db=db)
    success = await job_svc.delete_job(job_id, current_user["id"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="NOT_AUTHORIZED_OR_NOT_FOUND",
        )
    
    return None
