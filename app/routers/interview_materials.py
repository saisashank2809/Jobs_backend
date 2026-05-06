import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from app.config import settings
from app.dependencies import get_db, get_storage
from app.domain.models import InterviewMaterialResponse
from app.ports.database_port import DatabasePort
from app.ports.storage_port import StoragePort
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/interview-materials", tags=["Interview Materials"])

_ALLOWED_EXTENSIONS = {".pdf", ".docx"}

def _get_extension(filename: str | None) -> str:
    """Extract and validate the file extension."""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )
    import os
    ext = os.path.splitext(filename)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {', '.join(_ALLOWED_EXTENSIONS)} files are accepted",
        )
    return ext


@router.post("", response_model=InterviewMaterialResponse)
async def upload_interview_material(
    file: UploadFile = File(...),
    company_name: str = Form(...),
    title: str = Form(...),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    """
    Admin-only endpoint to upload an interview material (PDF/Word).
    We assume the frontend only shows the upload form to admins,
    but here we also ensure `current_user['role'] == 'admin'` to be safe.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can upload interview materials",
        )

    ext = _get_extension(file.filename)
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded",
        )

    # Generate a unique path in the public bucket
    file_id = str(uuid.uuid4())
    bucket_name = "public" # Or 'interview-materials'
    # Use public bucket so the frontend can just render the URL directly
    storage_path = f"interview-materials/{company_name.lower().replace(' ', '-')}/{file_id}{ext}"

    try:
        # We can use the existing storage adapter
        await storage.upload_file(
            bucket=bucket_name,
            path=storage_path,
            file_bytes=file_bytes,
            content_type=file.content_type or "application/octet-stream",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to storage: {str(e)}"
        )

    # Reconstruct public URL (Assuming standard supabase URL format)
    supabase_url = settings.supabase_url.rstrip("/")
    # Format: https://[project].supabase.co/storage/v1/object/public/[bucket]/[path]
    public_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{storage_path}"

    data = {
        "company_name": company_name,
        "title": title,
        "file_url": public_url,
        "file_path": storage_path
    }

    try:
        inserted = await db.create_interview_material(data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save record to database: {str(e)}"
        )

    return InterviewMaterialResponse(**inserted)


@router.get("", response_model=list[InterviewMaterialResponse])
async def list_interview_materials(
    company_name: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """
    List all interview materials, optionally filtered by company.
    Requires authentication (any role).
    """
    materials = await db.list_interview_materials(company_name=company_name)
    return [InterviewMaterialResponse(**m) for m in materials]

@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview_material(
    material_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    """
    Admin-only endpoint to delete an interview material.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete interview materials",
        )

    # First delete from db to get the record
    deleted_record = await db.delete_interview_material(material_id)
    if not deleted_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found",
        )

    # Then delete from storage
    try:
        await storage.delete_file(bucket="public", path=deleted_record["file_path"])
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to delete file from storage: {e}")
        # We don't fail the request since the DB record is already deleted

