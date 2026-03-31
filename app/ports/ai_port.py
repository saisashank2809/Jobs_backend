"""
Abstract interface for AI operations.
Concrete implementations (OpenAI, Ollama, etc.) must implement this port.
"""

from abc import ABC, abstractmethod

from app.domain.models import AIEnrichment, ChatMessage, MockScorecard


class AIPort(ABC):
    """Port for AI-powered text generation."""

    @abstractmethod
    async def generate_enrichment(
        self, description: str, skills: list[str], title: str = "", company_name: str = ""
    ) -> AIEnrichment:
        """
        Generate resume guide + interview prep questions
        from a job description and required skills.
        """
        ...

    @abstractmethod
    async def extract_skills(self, text: str) -> list[str]:
        """
        Extract a list of technical/soft skills from the provided text.
        """
        ...

    @abstractmethod
    async def extract_missing_skills(self, resume_text: str, required_skills: list[str]) -> list[str]:
        """
        Identify missing skills from resume against requirements.
        Returns a list of specific missing technical skills.
        """
        ...

    @abstractmethod
    async def chat(
        self, history: list[ChatMessage], user_context: str = ""
    ) -> str:
        """
        Given a conversation history, return the assistant's next reply.
        user_context: Optional rich context about the user (resume, profile)
                      injected into the system prompt for personalization.
        """
        ...

    @abstractmethod
    async def analyze_gap(self, resume_text: str, job_description: str) -> str:
        """
        Analyze the gap between a resume and a job description.
        Returns a brief, constructive explanation of what is missing.
        """
        ...

    @abstractmethod
    async def tailor_resume(self, resume_text: str, job_description: str) -> str:
        """
        Rewrite resume content to emphasize skills relevant to the job.
        Returns markdown formatted resume.
        """
        ...

    @abstractmethod
    async def generate_blog_post(self, prompt: str) -> dict:
        """
        Generates a blog post structure (title, slug, summary, content) from a prompt.
        Returns a dict.
        """
        ...

    @abstractmethod
    async def evaluate_mock_interview(
        self, transcript: list[dict[str, str]], job_description: str
    ) -> MockScorecard:
        """
        Evaluate a complete mock interview transcript against job requirements.
        Returns a structured MockScorecard.
        """
        ...
