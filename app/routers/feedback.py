from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.dependencies import get_db
from app.domain.models import FeedbackCreate, FeedbackResponse
from app.ports.database_port import DatabasePort
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/feedback", tags=["Feedback"])

@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    body: FeedbackCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Submit new feedback for the platform or a mock interview."""
    # Use service role or RLS logic? 
    # The adapter uses the client which follows RLS if it's the anon client, 
    # but here we're using the DB port which might be using service role.
    # However, create_feedback in adapter just inserts.
    
    # Ensure user_id is set to the current user
    feedback_data = body.dict()
    feedback = await db.create_feedback(current_user["id"], feedback_data)
    
    # Format response (users_jobs relation might not be returned in insert)
    return FeedbackResponse(**feedback)

@router.get("/me", response_model=list[FeedbackResponse])
async def get_my_feedback(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Retrieve feedback history for the current user."""
    feedbacks = await db.get_user_feedback(current_user["id"])
    return [FeedbackResponse(**f) for f in feedbacks]

@router.get("/admin", response_model=list[FeedbackResponse])
async def get_all_feedback_admin(
    type: str | None = Query(None),
    rating: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Admin endpoint to view and filter all feedback."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ADMIN_ONLY",
        )
    
    feedbacks = await db.get_all_feedback(
        limit=limit,
        offset=skip,
        type=type,
        rating=rating
    )
    
    # Flatten user info if needed or map to FeedbackResponse
    formatted = []
    for f in feedbacks:
        user_info = f.pop("users_jobs", {})
        f["user_full_name"] = user_info.get("full_name")
        f["user_email"] = user_info.get("email")
        formatted.append(FeedbackResponse(**f))
        
    return formatted
