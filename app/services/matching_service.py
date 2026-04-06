"""
Matching service — cosine similarity between user and job embeddings.
"""

import json
import math
import logging
from typing import Any

from app.domain.models import MatchResult
from app.job_matching.service import JobMatchingService
from app.ports.database_port import DatabasePort
from app.ports.ai_port import AIPort

logger = logging.getLogger(__name__)


class MatchingService:
    """Calculates semantic fit between a user's resume and a job posting."""

    GAP_THRESHOLD = 0.7

    def __init__(self, db: DatabasePort, ai: AIPort) -> None:
        self._db = db
        self._ai = ai

    async def calculate_match(self, user_id: str, job_id: str) -> MatchResult:
        """
        Fetch both embeddings, compute cosine similarity,
        and flag a gap if the score is below the threshold.
        """
        user = await self._db.get_user(user_id)
        job = await self._db.get_job(job_id)

        if not user or not user.get("resume_embedding"):
            raise ValueError("User has no resume embedding. Upload a resume first.")

        if not job or not job.get("embedding"):
            raise ValueError(
                "Job has no embedding yet. AI enrichment may still be processing."
            )

        user_vec = self._parse_vector(user["resume_embedding"])
        job_vec = self._parse_vector(job["embedding"])

        raw_score = self._cosine_similarity(user_vec, job_vec)
        
        # Artificial piecewise multiplier to boost embedding scores closer to 100%
        # because ~0.60 cosine similarity represents a highly tailored text match.
        if raw_score >= 0.58:
            # Map raw [0.58, 0.85] explicitly to visual [0.70, 0.98]
            boosted = 0.70 + ((raw_score - 0.58) / 0.27) * 0.28
            score = min(boosted, 0.99)
        else:
            # Keep weak resumes proportionally low
            score = raw_score * 1.15
        
        score = min(score, 0.99)
        gap_detected = score < self.GAP_THRESHOLD
        
        import asyncio
        
        # 1 & 2. Generate analysis and extract skills in parallel
        required = job.get("skills_required", [])
        
        tasks = [
            self._ai.analyze_gap(
                resume_text=user.get("resume_text", ""),
                job_description=job.get("description_raw", "")
            )
        ]
        
        if required:
            tasks.append(
                self._ai.extract_missing_skills(
                    resume_text=user.get("resume_text", ""),
                    required_skills=required
                )
            )
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        gap_analysis = None
        missing_skills = []
        learning_recommendations = []

        if isinstance(results[0], str):
            gap_analysis = results[0]
        else:
            logger.error(f"Gap analysis failed: {results[0]}")
            gap_analysis = "Dynamic analysis stream interrupted."
            
        if len(results) > 1:
            if isinstance(results[1], list):
                missing_skills = results[1]
            else:
                logger.error(f"Skills extraction failed: {results[1]}")
        
        # 3. Fetch learning resources for those skills
        if missing_skills:
            learning_recommendations = await self._db.get_learning_resources(missing_skills)

        # Calculate deterministic scores to match Job Feed
        job_matcher = JobMatchingService()
        raw_skills = user.get("skills") or []
        raw_interests = user.get("interests") or []
        raw_aspirations = user.get("aspirations") or []
        
        user_skills = job_matcher.normalize_list(raw_skills)
        user_interests = job_matcher.normalize_list(raw_interests)
        user_aspirations = job_matcher.normalize_list(raw_aspirations)

        job_required = job_matcher.normalize_list(job.get("skills_required") or [])
        job_tags = job_matcher.normalize_list(job.get("tags") or [])

        skill_score = job_matcher.calculate_skill_score(user_skills, job_required)
        interest_score = job_matcher.calculate_interest_score(user_interests, job_tags, job.get("title", ""))
        aspiration_score = job_matcher.calculate_aspiration_score(user_aspirations, job_tags, job.get("title", ""))

        final_match_score = (skill_score * 0.50) + (interest_score * 0.25) + (aspiration_score * 0.25)

        return MatchResult(
            job_id=job_id,
            similarity_score=round(score, 4),
            match_score=round(final_match_score * 100),
            skills_score=round(skill_score * 100),
            interests_score=round(interest_score * 100),
            aspirations_score=round(aspiration_score * 100),
            gap_detected=gap_detected,
            gap_analysis=gap_analysis,
            missing_skills=missing_skills,
            learning_recommendations=learning_recommendations
        )

    @staticmethod
    def _parse_vector(vec: Any) -> list[float]:
        """Supabase may return pgvector embeddings as strings — parse them."""
        if isinstance(vec, str):
            return json.loads(vec)
        return vec

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
