from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.ports.database_port import DatabasePort
from app.dependencies import get_db
from app.services.auth_service import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/material-folders", tags=["Material Folders"])

class FolderCreate(BaseModel):
    name: str

class FolderResponse(BaseModel):
    id: str
    name: str
    created_at: Any

@router.get("", response_model=list[FolderResponse])
async def list_folders(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db)
):
    return await db.list_material_folders()

@router.post("", response_model=FolderResponse)
async def create_folder(
    folder: FolderCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db)
):
    # Only admins can create folders
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create folders")
    
    try:
        return await db.create_material_folder({"name": folder.name})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db)
):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete folders")
    
    success = await db.delete_material_folder(folder_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

@router.patch("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    folder: FolderCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db)
):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can update folders")
    
    updated = await db.update_material_folder(folder_id, {"name": folder.name})
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return updated
