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
    Evaluate the completed interview transcript and return a comprehensive Markdown report.
    """
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    system_prompt = f"""
**Role:** You are the Lead Career Analyst & Match Strategist.
**Objective:** Analyze the provided mock interview transcript for a {role_name} position.
**Output Format:** You must generate a comprehensive "Job Match Analysis" report STRICTLY in Markdown format.

**Required Sections:**
1. **Executive Summary:** A brief "Hire/No Hire" verdict with a 1-sentence justification.
2. **The Match Matrix (Table):**
   | Criteria | Candidate Performance | Company Alignment | Reason for Match/Mismatch |
   | :--- | :--- | :--- | :--- |
   | Technical Depth | [Score 1-10] | [Role Req] | [Detailed explanation] |
   | Culture Fit | [Observations] | [Company Values] | [Detailed explanation] |
   | Communication | [Observations] | [Standard] | [Detailed explanation] |
3. **Inside Insights :** Identify which of the candidate's answers would have passed or failed based on real-world Glassdoor review trends for top-tier firms. (e.g., "Reviewers mention this company hates 'I' statements; you used 'We' effectively").
4. **Strategic Improvement Plan:** Three actionable steps to increase the "Match" probability.

**Instructions:** Return the result as a JSON object with a single key "report_markdown" containing the full markdown text.
"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"**Interview Transcript:**\n{transcript}\n\nPlease generate the 'Job Match Analysis' Markdown report.",
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    result_text = response.choices[0].message.content or "{}"
    try:
        return json.loads(result_text)
    except Exception:
        return {"error": "Failed to parse evaluation JSON.", "report_markdown": "Error generating report."}

