"""
mock_interview/services/session.py
Session management for interview interactions.
Stores messages and metadata (resume context, job context, mode) per session.
No external dependencies — pure in-memory store.
"""

from typing import List, Dict

# In-memory session datastore (session_id -> dict)
active_sessions: Dict[str, Dict] = {}


async def manage_session(session_id: str) -> None:
    """Initialize a user session if it doesn't exist."""
    if session_id not in active_sessions:
        active_sessions[session_id] = {
            "messages": [],
            "resume_text": "",
            "company_name": "",
            "job_description": "",
            "interview_mode": "",  # 'technical' | 'hr' | ''
            "question_count": 0,
        }


async def increment_question_count(session_id: str) -> None:
    if session_id not in active_sessions:
        await manage_session(session_id)
    active_sessions[session_id]["question_count"] += 1


async def get_question_count(session_id: str) -> int:
    session = active_sessions.get(session_id)
    return session.get("question_count", 0) if session else 0



async def set_resume_text(session_id: str, text: str) -> None:
    if session_id not in active_sessions:
        await manage_session(session_id)
    active_sessions[session_id]["resume_text"] = text


async def get_resume_text(session_id: str) -> str:
    session = active_sessions.get(session_id)
    return session.get("resume_text", "") if session else ""


async def set_job_context(session_id: str, company_name: str, job_description: str) -> None:
    if session_id not in active_sessions:
        await manage_session(session_id)
    active_sessions[session_id]["company_name"] = company_name
    active_sessions[session_id]["job_description"] = job_description


async def get_job_context(session_id: str) -> Dict[str, str]:
    session = active_sessions.get(session_id)
    if session:
        return {
            "company_name": session.get("company_name", ""),
            "job_description": session.get("job_description", ""),
        }
    return {"company_name": "", "job_description": ""}


async def set_interview_mode(session_id: str, mode: str) -> None:
    if session_id not in active_sessions:
        await manage_session(session_id)
    active_sessions[session_id]["interview_mode"] = mode


async def get_interview_mode(session_id: str) -> str:
    session = active_sessions.get(session_id)
    return session.get("interview_mode", "") if session else ""


async def append_to_session(session_id: str, role: str, content: str) -> None:
    if session_id not in active_sessions:
        await manage_session(session_id)
    active_sessions[session_id]["messages"].append({"role": role, "content": content})


async def get_session_history(session_id: str) -> List[Dict[str, str]]:
    session = active_sessions.get(session_id)
    return session.get("messages", []) if session else []


async def get_full_transcript_text(session_id: str) -> str:
    history = await get_session_history(session_id)
    lines = []
    for msg in history:
        label = "Candidate" if msg["role"] == "user" else "Interviewer"
        lines.append(f"{label}: {msg['content']}")
    return "\n\n".join(lines)
