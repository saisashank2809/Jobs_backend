"""
Abstract interface for file storage operations.
"""

from abc import ABC, abstractmethod


class StoragePort(ABC):
    """Port for uploading and retrieving files from cloud storage."""

    @abstractmethod
    async def upload_file(
        self, bucket: str, path: str, file_bytes: bytes, content_type: str
    ) -> str:
        """
        Upload a file and return its storage path.

        Args:
            bucket: Storage bucket name
            path: Destination path within the bucket
            file_bytes: Raw file content
            content_type: MIME type (e.g., 'application/pdf')

        Returns:
            The storage path of the uploaded file.
        """
        ...

    @abstractmethod
    async def get_signed_url(
        self, bucket: str, path: str, expires_in: int = 3600
    ) -> str:
        """
        Generate a short-lived signed URL for downloading a private file.

        Args:
            bucket: Storage bucket name
            path: File path within the bucket
            expires_in: URL validity in seconds (default: 1 hour)

        Returns:
            A signed download URL.
        """
        ...

    @abstractmethod
    async def delete_file(self, bucket: str, path: str) -> None:
        """
        Delete a file from storage.

        Args:
            bucket: Storage bucket name
            path: File path within the bucket
        """
        ...
