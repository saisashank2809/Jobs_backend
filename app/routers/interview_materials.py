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


@router.post("", response_model=list[InterviewMaterialResponse])
async def upload_interview_materials(
    files: list[UploadFile] = File(...),
    company_name: str | None = Form(None),
    title: str | None = Form(None),
    folder_id: str | None = Form(None),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    """
    Admin-only endpoint to upload multiple interview materials (PDF/Word).
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can upload interview materials",
        )

    # Pre-calculate common data
    final_company_name = company_name
    if not final_company_name or not final_company_name.strip():
        if folder_id:
            folder = await db.get_material_folder(folder_id)
            final_company_name = folder["name"] if folder else "General"
        else:
            final_company_name = "General"

    supabase_url = settings.supabase_url.rstrip("/")
    bucket_name = "public"
    
    results = []

    for file in files:
        ext = _get_extension(file.filename)
        file_bytes = await file.read()
        if not file_bytes:
            continue # Skip empty files

        # Generate a unique path for each file
        file_id = str(uuid.uuid4())
        storage_path = f"interview-materials/{final_company_name.lower().replace(' ', '-')}/{file_id}{ext}"

        try:
            await storage.upload_file(
                bucket=bucket_name,
                path=storage_path,
                file_bytes=file_bytes,
                content_type=file.content_type or "application/octet-stream",
            )
        except Exception as e:
            # For bulk uploads, we might want to continue or fail. Let's fail for now to be safe.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file {file.filename} to storage: {str(e)}"
            )

        public_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{storage_path}"
        
        # If multiple files are uploaded, we usually use their filenames as titles 
        # unless a specific title was provided (which would then apply to all, which is rare but possible)
        file_title = title if title and title.strip() else file.filename

        data = {
            "company_name": final_company_name,
            "title": file_title,
            "file_url": public_url,
            "file_path": storage_path,
            "folder_id": folder_id if folder_id else None
        }

        try:
            inserted = await db.create_interview_material(data)
            results.append(InterviewMaterialResponse(**inserted))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save record for {file.filename} to database: {str(e)}"
            )

    return results


@router.get("", response_model=list[InterviewMaterialResponse])
async def list_interview_materials(
    company_name: str | None = None,
    folder_id: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """
    List all interview materials, optionally filtered by company or folder.
    """
    # We need to update list_interview_materials in DB port to support folder_id
    materials = await db.list_interview_materials(company_name=company_name, folder_id=folder_id)
    return [InterviewMaterialResponse(**m) for m in materials]

@router.get("/{material_id}", response_model=InterviewMaterialResponse)
async def get_interview_material(
    material_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """
    Get a specific interview material by ID.
    """
    material = await db.get_interview_material(material_id)
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found",
        )
    return InterviewMaterialResponse(**material)

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

