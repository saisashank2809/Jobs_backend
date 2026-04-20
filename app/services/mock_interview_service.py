from typing import Any
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.domain.enums import MockInterviewStatus
from app.domain.models import MockInterviewAdminReview, MockInterviewSubmit
from app.ports.database_port import DatabasePort
from app.ports.ai_port import AIPort


class MockInterviewService:
    """
    Mock interview review workflow:
    1. Create interview record.
    2. Persist transcript and metadata at submission time.
    3. Queue for admin review.
    4. Return expert feedback only after review is complete.
    """

    def __init__(self, db: DatabasePort, ai: AIPort | None = None) -> None:
        self._db = db
        self._ai = ai

    async def start_interview(self, user_id: str, job_id: str | None) -> dict[str, Any]:
        """Initialize a new mock interview review record."""
        if job_id:
            job = await self._db.get_job(job_id)
            if not job:
                raise ValueError("Job not found")

        now = datetime.now(timezone.utc).isoformat()
        data = {
            "user_id": user_id,
            "job_id": job_id,
            "transcript": [],
            "ai_scorecard": {
                "interview_type": None,
                "duration_minutes": None,
                "user_transcript": [],
                "ai_transcript": [],
                "combined_transcript": [],
                "review_state": MockInterviewStatus.IN_PROGRESS.value,
                "submitted_at": None,
                "admin_review": None,
            },
            "status": MockInterviewStatus.IN_PROGRESS.value,
            "expert_feedback": None,
            "created_at": now,
            "updated_at": now,
        }
        return await self._db.create_mock_interview(data)

    async def submit_interview(
        self,
        interview_id: str,
        user_id: str,
        body: MockInterviewSubmit,
    ) -> dict[str, Any]:
        """Persist the finished transcript and queue the record for admin review."""
        interview = await self._get_owned_interview(interview_id, user_id)
        transcript = await self._build_combined_transcript(interview, body)
        user_transcript, ai_transcript = self._split_transcript(transcript, body)
        submitted_at = (body.submitted_at or datetime.now(timezone.utc)).isoformat()
        update_data = {
            "transcript": transcript,
            "ai_scorecard": {
                "interview_type": body.interview_type,
                "duration_minutes": body.duration_minutes,
                "user_transcript": user_transcript,
                "ai_transcript": ai_transcript,
                "combined_transcript": body.combined_transcript or transcript,
                "review_state": MockInterviewStatus.PENDING_REVIEW.value,
                "submitted_at": submitted_at,
                "admin_review": None,
            },
            "status": MockInterviewStatus.PENDING_REVIEW.value,
            "expert_feedback": None,
            "updated_at": submitted_at,
        }
        await self._db.update_mock_interview(interview_id, update_data)
        saved = await self._db.get_mock_interview(interview_id)
        if not saved:
            raise ValueError("Interview not found")
        return {
            "id": saved["id"],
            "status": saved["status"],
            "submitted_at": submitted_at,
            "message": "Mock interview submitted for admin review.",
        }

    async def request_review(self, interview_id: str, user_id: str) -> None:
        """Mark an interview as pending expert review."""
        interview = await self._get_owned_interview(interview_id, user_id)
        now = datetime.now(timezone.utc).isoformat()
        scorecard = self._coerce_scorecard(interview.get("ai_scorecard"))
        scorecard["review_state"] = MockInterviewStatus.PENDING_REVIEW.value
        await self._db.update_mock_interview(
            interview_id,
            {
                "status": MockInterviewStatus.PENDING_REVIEW.value,
                "ai_scorecard": scorecard,
                "updated_at": now,
            },
        )

    async def list_user_interviews(self, user_id: str) -> list[dict[str, Any]]:
        interviews = await self._db.list_user_mock_interviews(user_id)
        return [self._serialize_user_list_item(item) for item in interviews]

    async def get_interview_details(
        self,
        interview_id: str,
        current_user: dict[str, Any],
    ) -> dict[str, Any]:
        interview = await self._db.get_mock_interview(interview_id)
        if not interview:
            raise ValueError("Interview not found")

        if current_user.get("role") == "admin":
            return await self._serialize_admin_detail(interview)

        if str(interview.get("user_id")) != str(current_user["id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own mock interviews",
            )

        return await self._serialize_user_detail(interview)

    async def list_admin_interviews(
        self,
        status_filter: str = "all",
        search: str = "",
    ) -> list[dict[str, Any]]:
        interviews = await self._db.list_admin_mock_interviews(status_filter=status_filter)
        search_term = search.strip().lower()
        items = [self._serialize_admin_list_item(item) for item in interviews]
        if not search_term:
            return items

        return [
            item for item in items
            if search_term in (item.get("user_full_name") or "").lower()
            or search_term in (item.get("user_email") or "").lower()
            or search_term in (item.get("job_title") or "").lower()
            or search_term in (item.get("company_name") or "").lower()
        ]

    async def submit_admin_review(
        self,
        interview_id: str,
        review: MockInterviewAdminReview,
    ) -> dict[str, Any]:
        interview = await self._db.get_mock_interview(interview_id)
        if not interview:
            raise ValueError("Interview not found")

        current_scorecard = self._coerce_scorecard(interview.get("ai_scorecard"))
        reviewed_at = datetime.now(timezone.utc).isoformat()
        current_scorecard.update(
            {
                "review_state": MockInterviewStatus.REVIEWED.value,
                "admin_review": review.model_dump(),
            }
        )
        update_data = {
            "ai_scorecard": current_scorecard,
            "expert_feedback": review.feedback_markdown,
            "status": MockInterviewStatus.REVIEWED.value,
            "reviewed_at": reviewed_at,
            "updated_at": reviewed_at,
        }
        await self._db.update_mock_interview(interview_id, update_data)
        updated = await self._db.get_mock_interview(interview_id)
        if not updated:
            raise ValueError("Interview not found")
        return await self._serialize_admin_detail(updated)

    async def _get_owned_interview(self, interview_id: str, user_id: str) -> dict[str, Any]:
        interview = await self._db.get_mock_interview(interview_id)
        if not interview:
            raise ValueError("Interview not found")
        if str(interview.get("user_id")) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only modify your own mock interviews",
            )
        return interview

    async def _build_combined_transcript(
        self,
        interview: dict[str, Any],
        body: MockInterviewSubmit,
    ) -> list[dict[str, str]]:
        if body.transcript:
            return body.transcript

        if body.combined_transcript:
            return body.combined_transcript

        if body.user_transcript or body.ai_transcript:
            transcript: list[dict[str, str]] = []
            max_len = max(len(body.user_transcript), len(body.ai_transcript))
            for index in range(max_len):
                if index < len(body.ai_transcript):
                    transcript.append({"role": "assistant", "content": body.ai_transcript[index]})
                if index < len(body.user_transcript):
                    transcript.append({"role": "user", "content": body.user_transcript[index]})
            return transcript

        if not body.answers:
            raise ValueError("No transcript was provided for this interview")

        job_id = interview.get("job_id")
        prep_questions: list[Any] = []
        if job_id:
            job = await self._db.get_job(str(job_id))
            if job:
                prep_questions = job.get("prep_guide_generated", []) or []

        transcript = []
        for index, answer in enumerate(body.answers):
            question_text = "Question"
            if index < len(prep_questions):
                question = prep_questions[index]
                question_text = question.get("question") if isinstance(question, dict) else str(question)
            transcript.append({"role": "assistant", "content": question_text})
            transcript.append({"role": "user", "content": answer})
        return transcript

    def _split_transcript(
        self,
        transcript: list[dict[str, str]],
        body: MockInterviewSubmit,
    ) -> tuple[list[str], list[str]]:
        if body.user_transcript or body.ai_transcript:
            return body.user_transcript, body.ai_transcript

        user_transcript = [
            item.get("content", "")
            for item in transcript
            if item.get("role") in {"user", "candidate", "seeker"}
        ]
        ai_transcript = [
            item.get("content", "")
            for item in transcript
            if item.get("role") in {"assistant", "ai", "interviewer", "system"}
        ]
        return user_transcript, ai_transcript

    def _coerce_scorecard(self, scorecard: Any) -> dict[str, Any]:
        if isinstance(scorecard, dict):
            return {
                "interview_type": scorecard.get("interview_type"),
                "duration_minutes": scorecard.get("duration_minutes"),
                "user_transcript": scorecard.get("user_transcript") or [],
                "ai_transcript": scorecard.get("ai_transcript") or [],
                "combined_transcript": scorecard.get("combined_transcript") or [],
                "review_state": scorecard.get("review_state"),
                "submitted_at": scorecard.get("submitted_at"),
                "admin_review": scorecard.get("admin_review"),
            }

        return {
            "interview_type": None,
            "duration_minutes": None,
            "user_transcript": [],
            "ai_transcript": [],
            "combined_transcript": [],
            "review_state": None,
            "submitted_at": None,
            "admin_review": None,
        }

    def _serialize_user_list_item(self, interview: dict[str, Any]) -> dict[str, Any]:
        job = interview.get("jobs_jobs") or {}
        return {
            "id": interview.get("id"),
            "status": interview.get("status"),
            "created_at": interview.get("created_at"),
            "updated_at": interview.get("updated_at"),
            "reviewed_at": interview.get("reviewed_at"),
            "viewed_at": interview.get("viewed_at"),
            "job_title": job.get("title"),
            "company_name": job.get("company_name"),
            "expert_feedback": interview.get("expert_feedback") if interview.get("status") == MockInterviewStatus.REVIEWED.value else None,
        }

    async def _serialize_user_detail(self, interview: dict[str, Any]) -> dict[str, Any]:
        job = await self._db.get_job(str(interview["job_id"])) if interview.get("job_id") else None
        detail = {
            "id": interview.get("id"),
            "status": interview.get("status"),
            "created_at": interview.get("created_at"),
            "updated_at": interview.get("updated_at"),
            "reviewed_at": interview.get("reviewed_at"),
            "viewed_at": interview.get("viewed_at"),
            "transcript": interview.get("transcript") or [],
            "job_title": (job or {}).get("title"),
            "company_name": (job or {}).get("company_name"),
        }
        if interview.get("status") == MockInterviewStatus.REVIEWED.value:
            detail["expert_feedback"] = interview.get("expert_feedback")
            detail["admin_review"] = self._coerce_scorecard(interview.get("ai_scorecard")).get("admin_review")
        else:
            detail["expert_feedback"] = None
        return detail

    async def mark_interview_as_viewed(self, interview_id: str, user_id: str) -> None:
        """Update the viewed_at timestamp for a mock interview."""
        await self._get_owned_interview(interview_id, user_id)
        now = datetime.now(timezone.utc).isoformat()
        await self._db.update_mock_interview(
            interview_id,
            {
                "viewed_at": now,
                "updated_at": now,
            },
        )

    def _serialize_admin_list_item(self, interview: dict[str, Any]) -> dict[str, Any]:
        user = interview.get("users_jobs") or {}
        job = interview.get("jobs_jobs") or {}
        return {
            "interview_id": interview.get("id"),
            "user_full_name": user.get("full_name"),
            "user_email": user.get("email"),
            "status": interview.get("status"),
            "created_at": interview.get("created_at"),
            "job_title": job.get("title"),
            "company_name": job.get("company_name"),
        }

    async def _serialize_admin_detail(self, interview: dict[str, Any]) -> dict[str, Any]:
        user = await self._db.get_user(str(interview["user_id"]))
        job = await self._db.get_job(str(interview["job_id"])) if interview.get("job_id") else None
        scorecard = self._coerce_scorecard(interview.get("ai_scorecard"))
        return {
            "interview_id": interview.get("id"),
            "user_name": (user or {}).get("full_name"),
            "user_email": (user or {}).get("email"),
            "transcript": interview.get("transcript") or [],
            "user_transcript": scorecard.get("user_transcript") or [],
            "ai_transcript": scorecard.get("ai_transcript") or [],
            "expert_feedback": interview.get("expert_feedback"),
            "status": interview.get("status"),
            "admin_review": scorecard.get("admin_review"),
            "job_title": (job or {}).get("title"),
            "company_name": (job or {}).get("company_name"),
        }
