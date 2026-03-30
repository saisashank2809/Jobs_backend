"""
User endpoints — thin HTTP layer, delegates all logic to services.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status  # type: ignore
from fastapi.responses import JSONResponse  # type: ignore

from app.dependencies import get_db, get_document_parser, get_embedding_service, get_storage, get_user_service  # type: ignore
from app.domain.models import ResumeDownloadResponse, ResumeUploadResponse, ResumeReuploadResponse, UserProfile  # type: ignore
from app.ports.database_port import DatabasePort  # type: ignore
from app.ports.document_port import DocumentPort  # type: ignore
from app.ports.embedding_port import EmbeddingPort  # type: ignore
from app.ports.storage_port import StoragePort  # type: ignore
from app.services.auth_service import get_current_user  # type: ignore
from app.services.user_service import UserService  # type: ignore

router = APIRouter(prefix="/users", tags=["Users"])

# Allowed resume file extensions
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


@router.get("/me", response_model=UserProfile)
async def get_my_profile(
    current_user: dict[str, Any] = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """Return the authenticated user's profile with full details from DB."""
    profile = await user_service.get_profile(current_user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return UserProfile(**profile)


@router.post(
    "/resume",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_resume(
    file: UploadFile,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
    doc_parser: DocumentPort = Depends(get_document_parser),
    emb: EmbeddingPort = Depends(get_embedding_service),
    storage: StoragePort = Depends(get_storage),
):
    """Upload a PDF or DOCX resume → store original → parse → embed → save."""

    _get_extension(file.filename)  # validate extension

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded",
        )

    svc = UserService(db=db, doc_parser=doc_parser, embeddings=emb, storage=storage)

    try:
        chars = await svc.process_resume(
            user_id=current_user["id"],
            file_bytes=file_bytes,
            file_name=file.filename,
            content_type=file.content_type or "application/octet-stream",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume processing failed: {exc}",
        )

    return ResumeUploadResponse(characters_extracted=chars)


@router.put(
    "/resume",
    response_model=ResumeReuploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Re-upload / replace an existing resume",
)
async def reupload_resume(
    file: UploadFile,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
    doc_parser: DocumentPort = Depends(get_document_parser),
    emb: EmbeddingPort = Depends(get_embedding_service),
    storage: StoragePort = Depends(get_storage),
):
    """
    Replace the authenticated user's existing resume with a new file.
    Runs the same full pipeline: upload → parse → embed → save.
    Returns `replaced: true` so callers know this was a replacement operation.
    """

    _get_extension(file.filename)  # validate extension

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded",
        )

    svc = UserService(db=db, doc_parser=doc_parser, embeddings=emb, storage=storage)

    try:
        chars = await svc.process_resume(
            user_id=current_user["id"],
            file_bytes=file_bytes,
            file_name=file.filename,
            content_type=file.content_type or "application/octet-stream",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume re-upload failed: {exc}",
        )

    return ResumeReuploadResponse(characters_extracted=chars, replaced=True)


@router.get("/me/resume")
async def download_resume(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
    doc_parser: DocumentPort = Depends(get_document_parser),
    emb: EmbeddingPort = Depends(get_embedding_service),
    storage: StoragePort = Depends(get_storage),
):
    """
    Get a fresh, short-lived signed download URL for the user's resume.
    Every request generates a new 15-minute URL — never cached.
    """

    svc = UserService(db=db, doc_parser=doc_parser, embeddings=emb, storage=storage)
    url = await svc.get_resume_download_url(current_user["id"])

    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found. Upload one via POST /users/resume first.",
        )

    return JSONResponse(
        content={
            "download_url": url,
            "expires_in_seconds": 900,
        },
        headers={"Cache-Control": "no-store"},
    )
