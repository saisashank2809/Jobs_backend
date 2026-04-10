"""
Job Matching Service - Deterministic matching based on Skills, Interests, and Experience.
Targets freshers and candidates with 0-1 years of experience.
"""

import logging
from typing import Any
from uuid import UUID

from app.ports.database_port import DatabasePort

logger = logging.getLogger(__name__)

class JobMatchingService:
    """
    Deterministic scoring engine for matching users to jobs.
    Weights: 
    - Skill Match: 0.50
    - Interest Match: 0.25
    - Aspiration Match: 0.25
    """

    def normalize_list(self, items: list[str] | str | None) -> list[str]:
        """Lowercase, trim, and unique-ify a list of strings."""
        if not items:
            return []
        
        if isinstance(items, str):
            items = [items]
            
        processed = set()
        for item in items:
            if not item:
                continue
            sub_items = item.split(",")
            for si in sub_items:
                clean = si.strip().lower()
                if clean:
                    processed.add(clean)
        return sorted(list(processed))

    def calculate_skill_score(self, user_skills: list[str], job_required: list[str]) -> float:
        if not job_required:
            return 0.0
        user_skills_set = set(user_skills)
        job_required_set = set(job_required)
        matched = user_skills_set.intersection(job_required_set)
        return len(matched) / len(job_required_set)

    def calculate_interest_score(self, user_interests: list[str], job_tags: list[str], job_title: str) -> float:
        if not user_interests:
            return 0.0
        user_interests_set = set(user_interests)
        job_tags_set = set(job_tags)
        
        if user_interests_set.intersection(job_tags_set):
            return 0.3
            
        clean_title = job_title.lower()
        for interest in user_interests_set:
            if interest in clean_title:
                return 0.25
        return 0.0

    def calculate_aspiration_score(self, user_aspirations: list[str], job_tags: list[str], job_title: str) -> float:
        if not user_aspirations:
            return 0.0
        user_aspirations_set = set(user_aspirations)
        job_tags_set = set(job_tags)
        
        if user_aspirations_set.intersection(job_tags_set):
            return 0.25
            
        clean_title = job_title.lower()
        for aspiration in user_aspirations_set:
            if aspiration in clean_title:
                return 0.25
        return 0.0

    def calculate_experience_score(self, user_is_junior: bool, job_experience: str | None) -> float:
        if not job_experience or not user_is_junior:
            return 0.0
        exp_lower = job_experience.lower()
        junior_keywords = ["fresher", "junior", "intern", "entry level", "0-1", "0-2", "0 years", "graduate"]
        for kw in junior_keywords:
            if kw in exp_lower:
                return 0.1
        return 0.0
    
    def calculate_work_preference_score(self, user_preference: str | None, job_title: str, job_description: str, job_location: str | None) -> float:
        """
        Calculates match score for work preference:
        - If user prefers Remote: Score 1.0 if 'remote' in title, desc, or location.
        - If user prefers Onsite: Score 1.0 if NOT 'remote' in title/desc (simplistic but better than nothing).
        - If user prefers Hybrid/Both: Score 1.0 (neutral).
        """
        # Default to Hybrid / Both if not set
        pref = (user_preference or "Hybrid / Both").lower()
        
        if "hybrid" in pref or "both" in pref:
            return 1.0 # Neutral match for hybrid/both
            
        title_lower = job_title.lower()
        desc_lower = job_description.lower()
        loc_lower = (job_location or "").lower()
        
        is_job_remote = any("remote" in text for text in [title_lower, desc_lower, loc_lower])
        
        if "remote" in pref:
            return 1.0 if is_job_remote else 0.0
        
        if "onsite" in pref:
            return 0.0 if is_job_remote else 1.0
            
        return 1.0

    def get_match_label(self, total_score: float) -> str:
        perc = total_score * 100
        if perc >= 75:
            return "Good match, can apply"
        elif perc >= 50:
            return "Upskill and apply"
        elif perc >= 25:
            return "Need to upskill"
        else:
            return "Not a fit"

    async def get_matches(self, user_id: UUID, db: DatabasePort, limit: int = 20) -> list[dict[str, Any]]:
        userStr = str(user_id)
        user_res = await db.get_user(userStr)
        
        if not user_res:
            raise ValueError(f"User {user_id} not found.")

        raw_skills = user_res.get("skills") or []
        raw_interests = user_res.get("interests") or []
        raw_aspirations = user_res.get("aspirations") or []
        
        user_skills = self.normalize_list(raw_skills)
        user_interests = self.normalize_list(raw_interests)
        user_aspirations = self.normalize_list(raw_aspirations)
        user_work_pref = user_res.get("work_preference")

        jobs_res = await db.list_active_jobs(skip=0, limit=200)

        matches = []
        for job in jobs_res:
            job_required = self.normalize_list(job.get("skills_required") or [])
            job_tags = self.normalize_list(job.get("tags") or [])
            
            # Calculate baseline scores
            
            skill_score = self.calculate_skill_score(user_skills, job_required)
            interest_score = self.calculate_interest_score(user_interests, job_tags, job.get("title", ""))
            aspiration_score = self.calculate_aspiration_score(user_aspirations, job_tags, job.get("title", ""))
            work_pref_score = self.calculate_work_preference_score(
                user_work_pref, 
                job.get("title", ""), 
                job.get("description_raw", ""), 
                job.get("location")
            )
            
            # Recalculate Weights:
            # Skill: 0.40, Interest: 0.20, Aspiration: 0.20, Work Pref: 0.20
            final_score = (skill_score * 0.40) + (interest_score * 0.20) + (aspiration_score * 0.20) + (work_pref_score * 0.20)
            
            label = self.get_match_label(final_score)
            if skill_score < 0.2 and (interest_score > 0 or aspiration_score > 0):
                label = "Based on your interests (skills missing)"

            matched_skills = [s for s in user_skills if s in job_required]
            missing_skills = [s for s in job_required if s not in user_skills]

            matches.append({
                "id": job.get("id"),
                "title": job.get("title", ""),
                "company_name": job.get("company_name", ""),
                "location": job.get("location"),
                "created_at": job.get("created_at"),
                "skills_required": job.get("skills_required"),
                "salary_range": job.get("salary_range"),
                "match_score": round(final_score * 100),
                "skills_score": round(skill_score * 100),
                "interests_score": round(interest_score * 100),
                "aspirations_score": round(aspiration_score * 100),
                "work_preference_score": round(work_pref_score * 100),
                "match_label": label,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills
            })

        matches.sort(key=lambda x: x["match_score"], reverse=True)
        
        return matches[:limit]
