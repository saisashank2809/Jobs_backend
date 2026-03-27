"""
Pydantic models for requests, responses, and internal data transfer.
Pure data — no I/O, no side effects.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field  # type: ignore

from app.domain.enums import ChatStatus, UserRole, MockInterviewStatus  # type: ignore


# ── User ──────────────────────────────────────────────────────


class UserProfile(BaseModel):
    """Response model for GET /users/me."""

    id: UUID
    email: str
    role: UserRole
    full_name: str | None = None
    phone: str | None = None
    location: str | None = None
    resume_text: str | None = None
    resume_file_url: str | None = None
    resume_file_name: str | None = None
    created_at: datetime | None = None


class ResumeUploadResponse(BaseModel):
    """Response after successful resume upload."""

    message: str = "Resume processed successfully"
    characters_extracted: int


class ResumeDownloadResponse(BaseModel):
    """Response for GET /users/me/resume."""

    download_url: str


# ── Job ───────────────────────────────────────────────────────


class JobCreate(BaseModel):
    """Request body for POST /jobs."""

    title: str = Field(..., min_length=3, max_length=200)
    description_raw: str = Field(..., min_length=20)
    skills_required: list[str] = Field(default_factory=list)


class JobDetail(BaseModel):
    """Full 4-Pillar response for GET /jobs/{id}/details."""

    id: UUID
    title: str
    description_raw: str
    skills_required: list[str] | None = None
    resume_guide_generated: list[str] | None = None
    prep_guide_generated: list[InterviewQuestion | str | dict] | None = None
    status: str = "active"
    company_name: str | None = None
    external_apply_url: str | None = None
    external_id: str | None = None
    created_at: datetime | None = None


class JobFeedItem(BaseModel):
    """Lightweight item for the jobs feed."""

    id: UUID
    title: str
    skills_required: list[str] | None = None
    status: str = "active"
    company_name: str | None = None
    external_apply_url: str | None = None
    created_at: datetime | None = None


class JobCreateResponse(BaseModel):
    """Response after job creation."""

    id: UUID
    message: str = "Job created. AI enrichment is processing in the background."


# ── Matching ──────────────────────────────────────────────────


class MatchResult(BaseModel):
    """Response for POST /jobs/{id}/match."""

    job_id: UUID
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    gap_detected: bool
    gap_analysis: str | None = None
    missing_skills: list[str] = Field(default_factory=list)
    learning_recommendations: list[dict] = Field(default_factory=list)


class MissingSkillsExtraction(BaseModel):
    """Structured output for identifying missing skills."""

    missing_skills: list[str] = Field(
        ...,
        description="List of specific technical skills present in the requirements but absent or weak in the resume."
    )


# ── AI Enrichment ─────────────────────────────────────────────


class InterviewQuestion(BaseModel):
    """Structured interview question with a suggested answer strategy."""
    
    question: str = Field(..., description="The interview question")
    answer_strategy: str = Field(..., description="Specific advice on how to answer this question (e.g. key points to hit, STAR method application)")


class AIEnrichment(BaseModel):
    """Schema enforced by Instructor for structured AI output."""

    resume_guide: list[str] = Field(
        ...,
        min_length=5,
        max_length=5,
        description="5 actionable resume optimization bullet points",
    )
    prep_questions: list[InterviewQuestion] = Field(
        ...,
        min_length=5,
        max_length=5,
        description="5 technical interview preparation questions with strategies",
    )
    extracted_skills: list[str] = Field(
        default_factory=list,
        min_length=0,
        max_length=15,
        description="Top 5-10 technical skills extracted from the job description",
    )
    estimated_salary_range: str | None = Field(
        None,
        description="Estimated annual salary range (e.g. '₹4 LPA - ₹7 LPA') based on title and market data if not explicitly stated.",
    )
    qualification: str | None = Field(
        None,
        description="Educational qualification required (e.g. 'B.E/B.Tech', 'MBA', 'Any Graduate')",
    )
    experience: str | None = Field(
        None,
        description="Years of experience required or 'Freshers'",
    )


# ── Chat ──────────────────────────────────────────────────────


class ChatMessage(BaseModel):
    """Single message in a chat conversation."""

    role: str = Field(..., pattern=r"^(user|assistant|admin)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TakeoverRequest(BaseModel):
    """Request body for POST /admin/takeover."""

    session_id: UUID


class ChatSessionInfo(BaseModel):
    """Info about a chat session."""

    id: UUID
    user_id: UUID | None = None
    status: ChatStatus
    job_id: UUID | None = None
    job_title: str | None = None
    created_at: datetime | None = None


# ── Mock Interview ────────────────────────────────────────────


class MockScorecard(BaseModel):
    """Structured evaluation of a mock interview."""

    technical_accuracy: int = Field(..., ge=1, le=10)
    clarity: int = Field(..., ge=1, le=10)
    confidence: int = Field(..., ge=1, le=10)
    summary_notes: str


class MockInterview(BaseModel):
    """Full mock interview record."""

    id: UUID
    user_id: UUID
    job_id: UUID
    transcript: list[dict[str, str]] = Field(default_factory=list)
    ai_scorecard: MockScorecard | None = None
    expert_feedback: str | None = None
    status: MockInterviewStatus
    created_at: datetime | None = None


class MockInterviewStart(BaseModel):
    """Request to start a mock interview."""
    job_id: UUID


class MockInterviewSubmit(BaseModel):
    """Request to submit mock interview answers."""
    answers: list[str]


# ── Documents ─────────────────────────────────────────────────


class Document(BaseModel):
    """Internal model for a document in the RAG pipeline."""
    
    doc_id: UUID
    file_name: str
    file_id: str | None = None
    url: str | None = None
    status: DocumentStatus
    created_at: datetime | None = None
    

class DocumentUploadResponse(BaseModel):
    """Response returned when a document is uploaded for processing."""
    
    doc_id: UUID
    message: str = "Document uploaded successfully and is being processed."
    status: DocumentStatus
