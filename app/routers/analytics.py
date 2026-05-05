from fastapi import APIRouter, Depends, HTTPException
from typing import Any

from app.dependencies import get_analytics_service
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import get_current_user

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    responses={404: {"description": "Not found"}},
)

@router.get("/market")
async def get_market_intelligence(
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get aggregated market intelligence stats.
    Restricted to authenticated users (could be restricted to providers only later).
    """
    # Optional: Check if user is provider
    # if current_user.get("role") != "provider":
    #     raise HTTPException(status_code=403, detail="Only providers can view market intelligence.")
    
    return await service.get_market_stats()
