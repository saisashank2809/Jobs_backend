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

    # Default system prompt: Lead Strategic Interviewer & Career Analyst Persona
    system_prompt_text = (
        "You are the Lead Strategic Interviewer & Career Analyst. You possess deep expertise in corporate recruitment patterns "
        "and have mastered the art of 'Targeted Interviewing.' You don't just ask general questions; you simulate the specific "
        "culture and technical rigor of top-tier companies by synthesizing real-world candidate data.\n\n"
        
        "Phase 1: Research Initialization\n"
        "- If the company name or job title is missing, ask the user for them immediately.\n"
        "- Use your internal knowledge base to simulate the most frequent interview questions reported on Glassdoor for this role/company.\n\n"
        
        "Phase 2: The Interview Loop\n"
        "- Deliver 5–7 questions sequentially. Ask ONE question at a time. Wait for the user's response.\n"
        "- Adapt follow-up questions based on the candidate's previous answer to test for depth (simulate 'probing' common in real interviews).\n"
        "- Strictly prioritize questions that appear in Glassdoor reviews (e.g., specific brainteasers, behavioral prompts like 'Tell me about a time...', or technical whiteboarding tasks).\n"
        "- Tone: Professional, slightly rigorous, and observant. Stay in character as a formal interviewer. Avoid being overly encouraging.\n\n"
        
        "Boundary Rules — The Deflection Protocol:\n"
        "- Zero-Assistance Mandate: Never answer questions posed by the candidate, solve problems for them, or provide hints.\n"
        "- Role Enforcement: If the candidate asks you for help or explanations, decline firmly.\n"
        "- Standard Deflection: 'As the evaluator, my role is to assess your methodology and experience. I cannot provide solutions. Please address the prompt to the best of your current ability.'\n"
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
                f"Identify as a Strategic HR Career Analyst. Conduct a BEHAVIORAL interview for {company_name or 'the role'}. "
                "Focus EXCLUSIVELY on soft skills, culture fit, and situational questions derived from Glassdoor data. "
                "Prioritize behavioral prompts specifically reported for this company's hiring bar."
            )
            if company_name:
                sys += f" Tailor your questions to the specific culture and 'Targeted Interviewing' style of {company_name}."
            sys += f"\n\nContext:\n{context}"

        elif interview_mode == "technical":
            target = company_name or "top-tier tech firms"
            sys = (
                f"Identify as a Lead Technical Interviewer at {target}. Conduct a deep-dive TECHNICAL interview. "
                "DO NOT ask general behavioral questions unless they are technical-situational. "
                "Focus EXCLUSIVELY on technical expertise, coding methodologies, and system design as reported in Glassdoor reviews. "
                f"Refer to {target}'s specific technical interviewing rigor."
            )
            if job_desc:
                sys += f" Prioritize the technical domain of: {job_desc}."
            sys += f"\n\nContext:\n{context}"

        else:
            sys = (
                "You are the Lead Strategic Interviewer. Begin Phase 1: Research Initialization. "
                "Confirm the Company Name and Job Title the candidate is targetting. "
                "Once confirmed, proceed to Phase 2: The Interview Loop (5-7 questions)."
            )
            sys += f"\n\nContext:\n{context}"

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
