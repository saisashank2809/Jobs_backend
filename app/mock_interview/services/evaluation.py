"""
mock_interview/services/evaluation.py
Generates the final JSON grading report from the interview transcript.
API key is read from the shared app Settings — never hardcoded.
"""

import json
from openai import AsyncOpenAI
from app.config import settings  # type: ignore


async def evaluate_transcript(transcript: str, role_name: str = "Software Engineer") -> dict:
    """
    Evaluate the completed interview transcript and return a structured JSON report.
    """
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    system_prompt = f"""
**Role:** You are an Objective Interview Assessor.
**Objective:** Analyze the provided transcript of a technical interview for a {role_name} position and generate a structured evaluation.
**Evaluation Criteria:**
1. **Technical Accuracy:** Did the candidate's answers align with industry best practices and factual correctness?
2. **Communication:** Were the answers clear, concise, and logically structured?
3. **Problem Solving:** How well did the candidate handle follow-up questions or complex scenarios?

**Instructions:** Output your evaluation STRICTLY in the following JSON format. No markdown or conversational text outside the JSON block.
{{
  "overall_score": [Number between 1-100],
  "strengths": ["[List 2-3 specific strengths demonstrated]"],
  "areas_for_improvement": ["[List 2-3 specific areas lacking depth or clarity]"],
  "detailed_feedback": "[A comprehensive paragraph summarizing performance]",
  "recommended_topics_to_review": ["[List 1-3 concepts or technologies to study]"]
}}
"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"**Interview Transcript:**\n{transcript}\n\nPlease generate the JSON evaluation.",
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    result_text = response.choices[0].message.content or "{}"
    try:
        return json.loads(result_text)
    except Exception:
        return {"error": "Failed to parse evaluation JSON."}
