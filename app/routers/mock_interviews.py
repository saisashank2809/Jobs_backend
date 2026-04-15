from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_db
from app.domain.models import MockInterviewStart, MockInterviewSubmit
from app.services.auth_service import get_current_user
from app.services.mock_interview_service import MockInterviewService
from app.ports.database_port import DatabasePort

router = APIRouter(prefix="/mock-interviews", tags=["Mock Interviews"])

@router.post("/start", response_model=dict)
async def start_mock_interview(
    body: MockInterviewStart,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Initiate a new mock interview session for a specific job."""
    svc = MockInterviewService(db=db)
    try:
        return await svc.start_interview(
            user_id=str(current_user["id"]), 
            job_id=str(body.job_id) if body.job_id else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{interview_id}/submit", response_model=dict)
async def submit_mock_interview(
    interview_id: str,
    body: MockInterviewSubmit,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Submit the completed interview and queue it for admin review."""
    svc = MockInterviewService(db=db)
    try:
        return await svc.submit_interview(
            interview_id=interview_id, 
            user_id=str(current_user["id"]),
            body=body,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{interview_id}/request-review", status_code=status.HTTP_204_NO_CONTENT)
async def request_expert_review(
    interview_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Ask for a human expert to review the transcript."""
    svc = MockInterviewService(db=db)
    await svc.request_review(interview_id, str(current_user["id"]))
    return None

@router.get("/my", response_model=list[dict])
async def get_my_mock_interviews(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """List all mock interviews for the current user."""
    svc = MockInterviewService(db=db)
    return await svc.list_user_interviews(str(current_user["id"]))

@router.get("/{interview_id}", response_model=dict)
async def get_mock_interview_details(
    interview_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Get interview details for the current seeker or admin."""
    svc = MockInterviewService(db=db)
    try:
        return await svc.get_interview_details(interview_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
