"""
mock_interview/services/llm.py
Large Language Model service using OpenAI GPT-4o.
API key is read from the shared app Settings — never hardcoded.
"""

from typing import AsyncGenerator
from openai import AsyncOpenAI
from app.config import settings  # type: ignore


async def generate_response(
    text: str,
    history: list | None = None,
    context: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Generate an AI interviewer response as an async generator of text chunks.
    Supports technical and HR interview modes based on the context string.
    """
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # Default system prompt
    system_prompt_text = (
        "You are an AI Technical & Behavioral Interviewer conducting an interview. "
        "Ask one behavioral or technical question at a time. Wait for the user's response before asking follow-up questions. "
        "Keep your responses concise and conversational.\n\n"
        "Boundary Rules — The Deflection Protocol:\n"
        "- Zero-Assistance Mandate: Never answer questions posed by the candidate, solve problems for them, or provide hints.\n"
        "- Role Enforcement: If the candidate asks you for help or explanations, decline firmly.\n"
        "- Standard Deflection: 'As the evaluator, my role is to assess your methodology and experience. "
        "I cannot provide solutions. Please address the prompt to the best of your current ability.'\n"
        "- Redirection: After deflecting, immediately restate the original question."
    )

    messages: list[dict] = [{"role": "system", "content": system_prompt_text}]

    if context:
        # Parse context tags
        def _get_tag(tag: str) -> str | None:
            for line in context.split("\n"):
                if line.startswith(f"[{tag}]"):
                    parts = line.split(": ", 1)
                    return parts[1] if len(parts) > 1 else None
            return None

        company_name = _get_tag("TARGET_COMPANY")
        job_desc = _get_tag("JOB_DESCRIPTION")
        interview_mode = _get_tag("INTERVIEW_MODE_SELECTED")

        if interview_mode == "hr":
            sys = (
                "You are an HR Recruiter. Conduct a BEHAVIORAL interview. "
                "Focus EXCLUSIVELY on soft skills, culture fit, and situational questions. "
                "Use the provided BEHAVIORAL_QUESTIONS. Randomize the order — never follow the list sequentially. "
            )
            if company_name:
                sys += f"Tailor your questions to the culture of {company_name}. "
            sys += f"\n\nContext:\n{context}"

        elif interview_mode == "technical":
            target = company_name or "Google"
            sys = (
                f"You are a Senior Technical Interviewer at {target}. Conduct a deep-dive TECHNICAL interview. "
                "DO NOT ask general behavioral questions. "
                "Focus EXCLUSIVELY on technical expertise, coding methodologies, and system design. "
                f"Always randomize your questions. Refer to {target}'s interviewing standards. "
            )
            if job_desc:
                sys += f"Prioritize requirements for: {job_desc}. "
            sys += f"\n\nContext:\n{context}"

        else:
            sys = (
                "Identify if the candidate wants a Technical Interview or an HR/Behavioral session. "
                f"Welcome them and confirm you are ready to begin.\n\n{context}"
            )

        messages.append({"role": "system", "content": sys})

    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": text})

    stream = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=256,
        temperature=0.7,
        stream=True,
    )

    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content
