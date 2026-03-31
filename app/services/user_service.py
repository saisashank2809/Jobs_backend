"""
User service — profile retrieval and resume processing orchestration.
Depends on ports only (Dependency Inversion).
"""

import os
import re
import uuid
from typing import Any

from app.ports.database_port import DatabasePort
from app.ports.document_port import DocumentPort
from app.ports.embedding_port import EmbeddingPort
from app.ports.storage_port import StoragePort
from app.ports.ai_port import AIPort

RESUME_BUCKET = "resumes"


class UserService:
    """Orchestrates user-related business logic."""

    def __init__(
        self,
        db: DatabasePort,
        doc_parser: DocumentPort,
        embeddings: EmbeddingPort,
        storage: StoragePort,
        ai: AIPort | None = None,
    ) -> None:
        self._db = db
        self._doc = doc_parser
        self._emb = embeddings
        self._storage = storage
        self._ai = ai

    async def get_profile(self, user_id: str) -> dict[str, Any] | None:
        """Fetch user profile from the data store."""
        return await self._db.get_user(user_id)

    async def update_profile(self, user_id: str, data: dict[str, Any]) -> None:
        """
        Update user profile fields.
        Only fields provided in 'data' will be updated.
        """
        await self._db.upsert_user(user_id, data)

    async def process_resume(
        self,
        user_id: str,
        file_bytes: bytes,
        file_name: str,
        content_type: str,
    ) -> int:
        """
        Full resume pipeline:
        1. Upload original file to Supabase Storage
        2. Extract text from document (PDF or DOCX)
        3. Generate embedding vector
        4. Store file URL, text, and embedding in the user record

        Returns the number of characters extracted.
        """
        # Determine file extension
        ext = os.path.splitext(file_name)[1].lower().lstrip(".")

        # Sanitize filename — remove spaces, parens, special chars
        # "resume (1).pdf" → "resume_1.pdf"
        safe_name = re.sub(r"[^\w.\-]", "_", file_name)  # keep alphanum, dot, dash
        safe_name = re.sub(r"_+", "_", safe_name)        # collapse multiple _
        unique_prefix = uuid.uuid4().hex[:8]
        storage_path = f"{user_id}/{unique_prefix}_{safe_name}"

        # Step 1: Upload original file to storage
        await self._storage.upload_file(
            bucket=RESUME_BUCKET,
            path=storage_path,
            file_bytes=file_bytes,
            content_type=content_type,
        )

        # Step 2: Extract text from document
        text = await self._doc.extract_text(file_bytes, ext)
        extracted_len = len(text.strip())
        print(f"DEBUG: Extracted {extracted_len} characters from {file_name}")
        
        if extracted_len < 50:
            raise ValueError(
                f"Could not extract sufficient text from the uploaded .{ext} file (only {extracted_len} chars found). "
                "The document may be a scan or image-based. Please upload a text-based PDF or DOCX."
            )

        # Step 3: Generate embedding
        embedding = await self._emb.encode(text)

        # Step 4: Persist everything
        await self._db.upsert_user(
            user_id,
            {
                "resume_text": text,
                "resume_embedding": embedding,
                "resume_file_url": storage_path,
                "resume_file_name": file_name,
            },
        )

        return len(text)

    async def get_resume_download_url(self, user_id: str) -> str | None:
        """
        Generate a signed download URL for the user's original resume file.
        Returns None if no resume has been uploaded.
        """
        user = await self._db.get_user(user_id)
        if not user or not user.get("resume_file_url"):
            return None

        url = await self._storage.get_signed_url(
            bucket=RESUME_BUCKET,
            path=user["resume_file_url"],
            expires_in=900,  # 15-minute short-lived URL
        )
        return url

    async def extract_skills_from_resume(self, file_bytes: bytes, file_name: str) -> list[str]:
        """
        Extract text from file, then call AI to extract skills.
        Used for the signup questionnaire and profile page.
        """
        if self._ai is None:
            raise ValueError("AI service not initialized in UserService")

        ext = os.path.splitext(file_name)[1].lower().lstrip(".")
        text = await self._doc.extract_text(file_bytes, ext)
        
        if not text.strip():
            return []

        return await self._ai.extract_skills(text)
