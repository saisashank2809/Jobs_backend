"""
Matching endpoint — cosine similarity between user and job embeddings.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_matching_service, get_db, get_ai_service
from app.domain.models import MatchResult
from app.ports.database_port import DatabasePort
from app.ports.ai_port import AIPort
from app.services.auth_service import get_current_user
from app.services.matching_service import MatchingService

router = APIRouter(prefix="/jobs", tags=["Matching"])


@router.api_route("/{job_id}/match", methods=["GET", "POST"], response_model=MatchResult)
async def match_user_to_job(
    job_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    svc: MatchingService = Depends(get_matching_service),
):
    """Calculate semantic fit between the user's resume and a job posting."""
    import asyncio
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Wrap in timeout to prevent hanging forever on slow AI/DB calls
        result = await asyncio.wait_for(
            svc.calculate_match(
                user_id=current_user["id"],
                job_id=job_id,
            ),
            timeout=45.0,
        )
    except asyncio.TimeoutError:
        logger.error(f"Match request timed out for job {job_id}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Match analysis timed out. The AI service may be overloaded — please try again.",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Match failed for job {job_id}: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Matching failed: {type(exc).__name__}: {exc}",
        )

    return result


@router.post("/{job_id}/tailor-resume", response_model=dict)
async def tailor_resume(
    job_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
    ai: AIPort = Depends(get_ai_service),
):
    """
    Rewrites the user's resume bullet points to better match the job description.
    """
    # 1. Get User Resume
    user = await db.get_user(current_user["id"])
    if not user or not user.get("resume_text"):
        raise HTTPException(status_code=400, detail="No resume found. Please upload one first.")

    # 2. Get Job Description
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    # 3. Call AI
    tailored_markdown = await ai.tailor_resume(
        resume_text=user["resume_text"],
        job_description=job["description_raw"]
    )

    return {"tailored_resume": tailored_markdown}
