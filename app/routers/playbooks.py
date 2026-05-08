from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_db
from app.domain.models import Playbook, PlaybookCreate, PlaybookUpdate
from app.ports.database_port import DatabasePort
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/playbooks", tags=["Playbooks"])


def _require_admin(current_user: dict[str, Any]) -> None:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action",
        )


@router.get("/", response_model=list[Playbook])
async def list_playbooks(
    hiring_zone: str | None = None,
    db: DatabasePort = Depends(get_db),
):
    """List all playbooks."""
    return await db.list_playbooks(hiring_zone=hiring_zone)


@router.get("/{playbook_id}", response_model=Playbook)
async def get_playbook(
    playbook_id: UUID,
    db: DatabasePort = Depends(get_db),
):
    """Get a playbook by ID."""
    pb = await db.get_playbook(str(playbook_id))
    if not pb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook not found",
        )
    return pb


@router.get("/slug/{slug}", response_model=Playbook)
async def get_playbook_by_slug(
    slug: str,
    db: DatabasePort = Depends(get_db),
):
    """Get a playbook by slug."""
    pb = await db.get_playbook_by_slug(slug)
    if not pb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook not found",
        )
    return pb


@router.post("/", response_model=Playbook, status_code=status.HTTP_201_CREATED)
async def create_playbook(
    body: PlaybookCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Create a new playbook (Admin only)."""
    _require_admin(current_user)
    
    # Check if slug exists
    existing = await db.get_playbook_by_slug(body.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Playbook with this slug already exists",
        )
        
    return await db.create_playbook(body.model_dump())


@router.patch("/{playbook_id}", response_model=Playbook)
async def update_playbook(
    playbook_id: UUID,
    body: PlaybookUpdate,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Update an existing playbook (Admin only)."""
    _require_admin(current_user)
    
    pb = await db.get_playbook(str(playbook_id))
    if not pb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook not found",
        )
        
    update_data = body.model_dump(exclude_unset=True)
    updated = await db.update_playbook(str(playbook_id), update_data)
    return updated


@router.delete("/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playbook(
    playbook_id: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Delete a playbook (Admin only)."""
    _require_admin(current_user)
    
    success = await db.delete_playbook(str(playbook_id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook not found",
        )
    return None
