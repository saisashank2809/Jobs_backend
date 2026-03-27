"""Enums shared across the domain layer."""

from enum import Enum


class UserRole(str, Enum):
    SEEKER = "seeker"
    PROVIDER = "provider"
    ADMIN = "admin"


class ChatStatus(str, Enum):
    ACTIVE_AI = "active_ai"
    # active_human is deprecated in favor of automated AI mentor + structured mock interviews
    CLOSED = "closed"


class MockInterviewStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PENDING_REVIEW = "pending_review"
    REVIEWED = "reviewed"


class DocumentStatus(str, Enum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"
