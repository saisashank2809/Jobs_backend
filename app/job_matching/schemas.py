from uuid import UUID
from pydantic import BaseModel, Field

class JobMatchRequest(BaseModel):
    user_id: UUID

class JobMatch(BaseModel):
    id: UUID
    title: str
    company_name: str | None = None
    location: str | None = None
    created_at: str | None = None
    skills_required: list[str] | None = None
    salary_range: str | None = None
    match_score: int
    skills_score: int | None = None
    interests_score: int | None = None
    aspirations_score: int | None = None
    match_label: str
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)

class JobMatchResponse(BaseModel):
    count: int
    matches: list[JobMatch]
