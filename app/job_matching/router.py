"""
Job Matching Router - Deterministic matching API for freshers.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db_session
from app.job_matching.service import JobMatchingService
from app.job_matching.schemas import JobMatchRequest, JobMatch

router = APIRouter(tags=["Job Matching (Deterministic)"])

from typing import Any
from app.dependencies import get_db
from app.ports.database_port import DatabasePort
from app.services.auth_service import get_current_user

def get_job_match_service():
    """Dependency to get the job matching service."""
    return JobMatchingService()

@router.post("/jobs/match", response_model=list[JobMatch])
async def match_jobs(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
    svc: JobMatchingService = Depends(get_job_match_service),
):
    """
    Get job matches for a user based on skills and interests.
    Deterministic scoring (60/30/10) for freshers with 0-1y experience.
    """
    try:
        results = await svc.get_matches(user_id=current_user["id"], db=db)
        return results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal matching error: {str(e)}")
