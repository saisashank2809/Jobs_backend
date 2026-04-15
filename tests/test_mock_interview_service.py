from copy import deepcopy

import pytest

from app.services.mock_interview_service import MockInterviewService
from app.domain.models import MockInterviewAdminReview, MockInterviewSubmit


class DummyDB:
    def __init__(self) -> None:
        self.interviews = {
            "int-1": {
                "id": "int-1",
                "user_id": "user-1",
                "job_id": "job-1",
                "status": "in_progress",
                "transcript": [],
                "ai_scorecard": {},
                "expert_feedback": None,
                "created_at": "2026-04-15T00:00:00+00:00",
                "updated_at": "2026-04-15T00:00:00+00:00",
                "reviewed_at": None,
            }
        }
        self.jobs = {
            "job-1": {
                "id": "job-1",
                "title": "Backend Engineer",
                "company_name": "Acme",
                "prep_guide_generated": [
                    {"question": "Tell me about yourself"},
                    {"question": "Describe a backend project"},
                ],
            }
        }
        self.users = {
            "user-1": {"id": "user-1", "full_name": "Jane Doe", "email": "jane@example.com"},
        }

    async def get_job(self, job_id: str):
        return self.jobs.get(job_id)

    async def create_mock_interview(self, data):
        self.interviews["created"] = data
        return data

    async def get_mock_interview(self, interview_id: str):
        item = self.interviews.get(interview_id)
        return deepcopy(item) if item else None

    async def update_mock_interview(self, interview_id: str, data):
        self.interviews[interview_id].update(deepcopy(data))

    async def list_user_mock_interviews(self, user_id: str):
        return [deepcopy(item) for item in self.interviews.values() if item.get("user_id") == user_id]

    async def list_admin_mock_interviews(self, status_filter: str = "all"):
        items = [deepcopy(item) for item in self.interviews.values()]
        if status_filter == "all":
            return items
        return [item for item in items if item.get("status") == status_filter]

    async def get_user(self, user_id: str):
        return self.users.get(user_id)


class FailAI:
    async def evaluate_mock_interview(self, *args, **kwargs):
        raise AssertionError("AI scoring should not be called during seeker submission")


@pytest.mark.asyncio
async def test_submit_interview_queues_pending_review_without_ai():
    db = DummyDB()
    service = MockInterviewService(db=db, ai=FailAI())

    payload = MockInterviewSubmit(
        transcript=[
            {"role": "assistant", "content": "Tell me about yourself"},
            {"role": "user", "content": "I build APIs in Python."},
        ],
        interview_type="technical",
        duration_minutes=18,
    )

    result = await service.submit_interview("int-1", "user-1", payload)

    assert result["status"] == "pending_review"
    stored = db.interviews["int-1"]
    assert stored["status"] == "pending_review"
    assert stored["transcript"][1]["content"] == "I build APIs in Python."
    assert stored["ai_scorecard"]["user_transcript"] == ["I build APIs in Python."]
    assert stored["ai_scorecard"]["ai_transcript"] == ["Tell me about yourself"]
    assert stored["expert_feedback"] is None


@pytest.mark.asyncio
async def test_admin_review_marks_interview_reviewed():
    db = DummyDB()
    db.interviews["int-1"]["status"] = "pending_review"
    db.interviews["int-1"]["ai_scorecard"] = {
        "interview_type": "technical",
        "duration_minutes": 18,
        "user_transcript": ["Answer 1"],
        "ai_transcript": ["Question 1"],
        "combined_transcript": [
            {"role": "assistant", "content": "Question 1"},
            {"role": "user", "content": "Answer 1"},
        ],
        "review_state": "pending_review",
        "submitted_at": "2026-04-15T00:20:00+00:00",
        "admin_review": None,
    }

    service = MockInterviewService(db=db)
    review = MockInterviewAdminReview(
        overall_summary="Strong fundamentals with room to improve depth.",
        strengths=["Python basics", "Clear communication"],
        improvements=["Go deeper on architecture"],
        topics_to_work_on=["System design"],
        next_steps="Practice explaining tradeoffs in API design.",
        reviewer_name="Admin Reviewer",
        reviewer_id=None,
        feedback_markdown="## Feedback\nKeep practicing system design.",
    )

    result = await service.submit_admin_review("int-1", review)

    assert result["status"] == "reviewed"
    stored = db.interviews["int-1"]
    assert stored["status"] == "reviewed"
    assert stored["expert_feedback"] == "## Feedback\nKeep practicing system design."
    assert stored["ai_scorecard"]["admin_review"]["reviewer_name"] == "Admin Reviewer"
