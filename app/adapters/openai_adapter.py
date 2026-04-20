"""
Concrete implementation of AIPort using OpenAI GPT-4o-mini + Instructor.
"""

import instructor  # type: ignore
from openai import AsyncOpenAI  # type: ignore

from app.domain.models import AIEnrichment, ChatMessage, MissingSkillsExtraction, SkillsExtraction, MockScorecard  # type: ignore
from app.ports.ai_port import AIPort  # type: ignore


class OpenAIAdapter(AIPort):
    """Talks to OpenAI's chat completions API for structured + freeform output."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._raw_client = AsyncOpenAI(api_key=api_key, timeout=30.0)
        self._instructor_client = instructor.from_openai(self._raw_client)
        self._model = model

    async def generate_enrichment(
        self,
        description: str,
        skills: list[str],
        title: str = "",
        company_name: str = "",
    ) -> AIEnrichment:
        """Use Instructor to force GPT output into the AIEnrichment schema."""

        skills_text = ", ".join(skills) if skills else "Not specified"
        role_header = f"{title} at {company_name}" if title and company_name else (title or "this role")

        result = await self._instructor_client.chat.completions.create(
            model=self._model,
            response_model=AIEnrichment,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert career coach. Given a specific job posting, "
                        "you MUST produce exactly 5 resume optimization bullet points, "
                        "exactly 5 technical interview questions, AND a list of the top 5-10 "
                        "technical skills required for the role based on the description. "
                        "ALSO produce exactly 6-8 short, plain-language sentences for a role overview. "
                        "These sentences must be easy for both freshers and experienced candidates to understand. "
                        "Keep them simple, practical, and free of corporate filler. "
                        "For each interview question, provide a specific 'answer_strategy' "
                        "that explains EXACTLY what the interviewer is looking for and "
                        "what key technical concepts or experiences the candidate should highlight. "
                        "ALSO, identify and extract the required 'qualification' and 'experience' levels. "
                        "ALSO, estimate the annual salary range for this role (prefer INR/LPA format like '₹4 LPA - ₹7 LPA') "
                        "based on the description or standard market rates for this title/company. "
                        "Be HIGHLY SPECIFIC to this exact role and company — "
                        "reference the company name, role title, and specific "
                        "technologies/skills mentioned in the description. "
                        "Do NOT give generic advice."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"## Role: {role_header}\n\n"
                        f"## Job Description\n{description}\n\n"
                        f"## Required Skills\n{skills_text}\n\n"
                        "Generate the resume guide, role overview, and prep questions now. "
                        "Make them specific to this exact role and company."
                    ),
                },
            ],
        )
        return result

    async def extract_missing_skills(self, resume_text: str, required_skills: list[str]) -> list[str]:
        """Identify missing skills using structured output."""
        
        if not required_skills:
            return []

        skills_text = ", ".join(required_skills)
        
        result = await self._instructor_client.chat.completions.create(
            model=self._model,
            response_model=MissingSkillsExtraction,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict technical recruiter. Compare the candidate's resume "
                        "against the required skills list. "
                        "Return ONLY the skills from the required list that are completely missing "
                        "or significantly weak in the resume. "
                        "Do not include soft skills. "
                        "Do not hallucinate skills not in the required list."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"## Required Skills\n{skills_text}\n\n"
                        f"## Candidate Resume\n{resume_text[:3000]}\n\n" # type: ignore # Truncate for cost/speed
                        "Extract the missing skills now."
                    ),
                },
            ],
            max_tokens=300,
        )
        return result.missing_skills

    async def extract_skills(self, text: str) -> list[str]:
        """Extract a list of technical/soft skills from the provided text."""
        
        result = await self._instructor_client.chat.completions.create(
            model=self._model,
            response_model=SkillsExtraction,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert technical recruiter. "
                        "Identify and extract all relevant technical skills, programming languages, "
                        "frameworks, tools, and key soft skills from the provided text. "
                        "Return them as a flat list of strings. "
                        "Be exhaustive but accurate."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"## Text for Analysis\n{text[:4000]}\n\n" # Truncate for efficiency
                        "Extract the skills now."
                    ),
                },
            ],
            max_tokens=500,
        )
        return result.skills

    async def chat(
        self, history: list[ChatMessage], user_context: str = ""
    ) -> str:
        """Standard chat completion for the Control Tower AI mode."""

        base_prompt = (
            "You are a personalized career coach on Ottobon (jobs.ottobon.cloud). "
            "You help candidates understand job requirements, identify skill gaps, "
            "optimize their resumes, and prepare for interviews. "
            "Be specific, actionable, and encouraging. "
            "Reference the candidate's actual skills and experience when available."
        )

        if user_context:
            system_content = f"{base_prompt}\n\n{user_context}"
        else:
            system_content = base_prompt

        messages = [{"role": "system", "content": system_content}]

        for msg in history:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})

        response = await self._raw_client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=512,
        )
        return response.choices[0].message.content or ""

    async def analyze_gap(self, resume_text: str, job_description: str) -> str:
        """
        Generate a concise explanation of the skill gap.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful career coach. You are analyzing the gap between a candidate's resume and a job description. "
                    "Identify the key missing skills or experiences that likely caused a lower match score. "
                    "Provide a brief, encouraging, but direct explanation (2-3 sentences max). "
                    "Do not list everything, just the most critical missing requirements. "
                    "Address the candidate directly as 'you'."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"## Job Description\n{job_description[:4000]}\n\n" # type: ignore
                    f"## Candidate Resume\n{resume_text[:4000]}\n\n" # type: ignore
                    "Explain the gap briefly."
                ),
            },
        ]

        response = await self._raw_client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=150,
        )
        return response.choices[0].message.content or "We identified some missing key requirements compared to the job description."

    async def tailor_resume(self, resume_text: str, job_description: str) -> str:
        """
        Rewrite resume to target the job description.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert ATS specialist and resume writer. "
                    "Your task is to REWRITE the candidate's resume to specifically target the provided job description. "
                    "1. Keep the candidate's truth - do not invent experiences they don't have. "
                    "2. Rephrase bullet points to use keywords from the JD (e.g., if JD says 'collaborated with cross-functional teams' and candidate says 'worked with others', update it). "
                    "3. Add a 'Targeted Professional Summary' at the top. "
                    "4. Output the result in clean Markdown format."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"## Target Job\n{job_description[:4000]}\n\n" # type: ignore
                    f"## Current Resume\n{resume_text[:4000]}\n\n" # type: ignore
                    "Rewrite my resume now."
                ),
            },
        ]

        response = await self._raw_client.chat.completions.create(
            model="gpt-4o",  # Use stronger model for writing
            messages=messages,
        )
        return response.choices[0].message.content or "Failed to tailor resume."

    async def generate_blog_post(self, prompt: str) -> dict:
        """
        Generate a structured blog post using OpenAI.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert technical writer for the Ottobon Jobs blog. "
                    "Generate a high-quality, engaging blog post based on the user's prompt. "
                    "Output valid JSON with the following keys: "
                    "'slug' (URL-friendly string), "
                    "'title' (Catchy title), "
                    "'summary' (2-3 sentence teaser), "
                    "'content' (Full article in Markdown format). "
                    "Ensure the content is professional and insightful."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        response = await self._raw_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"},
        )
        
        try:
            import json
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {
                "slug": "ai-generated-post",
                "title": "Error Generating Post",
                "summary": "An error occurred during generation.",
                "content": response.choices[0].message.content
            }

    async def evaluate_mock_interview(
        self, transcript: list[dict[str, str]], job_description: str
    ) -> MockScorecard:
        """
        Evaluate a complete mock interview transcript against job requirements.
        Returns a structured MockScorecard.
        """
        # Format transcript for the prompt
        formatted = "\n".join(
            f"**Q:** {item.get('question', '')}\n**A:** {item.get('answer', '')}\n"
            for item in transcript
        )

        result = await self._instructor_client.chat.completions.create(
            model=self._model,
            response_model=MockScorecard,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior technical interviewer evaluating a candidate's mock interview. "
                        "Assess their responses against the job description. "
                        "Score each dimension from 1-10: "
                        "technical_accuracy (correctness of technical answers), "
                        "clarity (how well they communicate their thoughts), "
                        "confidence (how composed and assertive they are). "
                        "Provide summary_notes with specific, constructive feedback "
                        "highlighting strengths and areas for improvement."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"## Job Description\n{job_description[:3000]}\n\n" # type: ignore
                        f"## Interview Transcript\n{formatted}\n\n"
                        "Evaluate this candidate now."
                    ),
                },
            ],
            max_tokens=500,
        )
        return result

