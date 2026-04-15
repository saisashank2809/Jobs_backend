"""
mock_interview/router.py
FastAPI router exposing all mock interview HTTP + WebSocket endpoints.
Mounted at /mock prefix on the main jobs.backend app.

Endpoints (relative to mount prefix /mock):
  POST /upload_resume          – upload resume for the session
  POST /update_job_context     – set company name + job description
  POST /set_mode               – set interview mode (technical | hr)
  POST /analyze_resume         – AI-powered resume analysis
  GET  /evaluate               – fetch post-interview evaluations
  WS   /ws                     – real-time voice interview WebSocket
"""

import json
import logging

from fastapi import APIRouter, UploadFile, File, WebSocket, WebSocketDisconnect, Depends, Query
from pydantic import BaseModel
from app.dependencies import get_db
from app.services.auth_service import get_current_user, _verify_token_locally

from app.mock_interview.orchestrator import orchestrate
from app.mock_interview.services.session import (
    get_full_transcript_text,
    manage_session,
    append_to_session,
    active_sessions,
    set_resume_text,
    get_resume_text,
    set_job_context,
    get_job_context,
    set_interview_mode,
    get_interview_mode,
)
from app.mock_interview.services.context import get_context
from app.mock_interview.services.llm import generate_response
from app.mock_interview.services.tts import text_to_speech_stream
from app.mock_interview.services.resume import extract_text_from_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mock", tags=["Mock Interview"])


# ── Pydantic request models ────────────────────────────────────

class JobContextRequest(BaseModel):
    company_name: str = ""
    job_description: str = ""
    session_id: str = "default_session"


class ModeRequest(BaseModel):
    mode: str
    session_id: str = "default_session"


# ── HTTP Endpoints ─────────────────────────────────────────────

@router.post("/upload_resume")
async def upload_resume(
    file: UploadFile = File(...),
    session_id: str = "default_session",
):
    """Upload and parse a resume file; store extracted text in the session."""
    try:
        contents = await file.read()
        text = extract_text_from_file(contents, file.filename or "resume.pdf")
        if not text:
            return {"error": "Failed to extract text from the uploaded file."}
        await set_resume_text(session_id, text)
        return {"message": "Resume uploaded successfully.", "preview": text[:200] + "..."}
    except Exception as exc:
        logger.error(f"Resume upload error: {exc}")
        return {"error": str(exc)}


@router.post("/update_job_context")
async def update_job_context(request: JobContextRequest):
    """Set company name and job description for the session."""
    try:
        await set_job_context(request.session_id, request.company_name, request.job_description)
        return {"message": "Job context updated successfully."}
    except Exception as exc:
        logger.error(f"Job context update error: {exc}")
        return {"error": str(exc)}


@router.post("/set_mode")
async def set_mode(request: ModeRequest):
    """Set the interview mode (technical | hr)."""
    try:
        await set_interview_mode(request.session_id, request.mode)
        return {"message": f"Interview mode set to {request.mode}."}
    except Exception as exc:
        logger.error(f"Set mode error: {exc}")
        return {"error": str(exc)}


@router.post("/analyze_resume")
async def analyze_resume(
    session_id: str = "default_session",
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """AI-powered resume summary. Fallback to user profile if session is empty."""
    try:
        resume_text = await get_resume_text(session_id)
        if not resume_text and current_user:
            # Fallback to profile
            resume_text = current_user.get("resume_text", "")
            if resume_text:
                await set_resume_text(session_id, resume_text)

        if not resume_text:
            return {"error": "No resume found in session or profile. Please upload a resume first."}

        analysis_prompt = (
            "Analyze the following resume text and provide a very concise summary (max 3-4 sentences). "
            "Highlight the candidate's top 3 technical skills and their most significant project or experience. "
            "Format: clean summary followed by 'Top Skills: skill1, skill2, skill3'.\n\n"
            f"Resume Text:\n{resume_text}"
        )

        full_response = ""
        async for chunk in generate_response(analysis_prompt):
            full_response += chunk
        return {"analysis": full_response}
    except Exception as exc:
        logger.error(f"Analyze resume error: {exc}")
        return {"error": str(exc)}


@router.get("/evaluate")
async def get_evaluation(session_id: str = "default_session"):
    """Immediate AI evaluation is disabled in favor of admin review."""
    transcript = await get_full_transcript_text(session_id)
    if not transcript:
        return {"error": "No interview transcript found for this session."}
    return {
        "status": "pending_review",
        "message": "Immediate AI evaluation is disabled. Submit the interview for admin review.",
    }


# ── WebSocket Endpoint ─────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str = "default_session",
    token: str | None = Query(None)
):
    """
    Real-time AI voice interview WebSocket.
    Now supports an optional 'token' query param for automatic resume retrieval.
    """
    await websocket.accept()

    # Logged-in user fallback
    user_resume = ""
    if token:
        try:
            user_id = _verify_token_locally(token)
            db = get_db()  # get_db is a function that returns the adapter
            user = await db.get_user(user_id)
            if user:
                user_resume = user.get("resume_text", "")
        except Exception as e:
            logger.warning(f"WebSocket auth failed: {e}")

    # Require a resume before starting
    resume_text = await get_resume_text(session_id)
    if not resume_text and user_resume:
        resume_text = user_resume
        await set_resume_text(session_id, resume_text)

    if not resume_text:
        await websocket.send_text(json.dumps({
            "type": "response",
            "text": "System: No resume found. Please upload your resume before starting the interview.",
        }))
        await websocket.close()
        return

    try:
        # Init / clear session messages (keep resume + job context)
        if session_id not in active_sessions:
            await manage_session(session_id)
        else:
            active_sessions[session_id]["messages"] = []

        # Build dynamic greeting
        job_context = await get_job_context(session_id)
        company_name = job_context.get("company_name", "")
        job_desc = job_context.get("job_description", "")
        interview_mode = await get_interview_mode(session_id)

        greeting_prefix = "Begin the interview by stating your role as a "
        if interview_mode == "technical":
            greeting_prefix += "Technical Interviewer "
        else:
            greeting_prefix += "HR Recruiter "
        greeting_prefix += "and welcoming the candidate. "

        if company_name:
            greeting_prefix += f"Mention you are interviewing them for a position at {company_name}. "
        if interview_mode:
            greeting_prefix += f"Mention this will be a {interview_mode.upper()} interview. "

        greeting_prefix += (
            "Mention you have their resume and are ready to dive into their background."
            if resume_text
            else "Ask if they are ready to begin."
        )

        # Stream greeting text + TTS
        full_greeting = ""
        sentence_buffer = ""

        await websocket.send_text(json.dumps({"type": "response_start"}))

        context = await get_context("Greeting")
        async for chunk in generate_response(greeting_prefix, context=context):
            full_greeting += chunk
            sentence_buffer += chunk
            await websocket.send_text(json.dumps({"type": "response_chunk", "text": chunk}))

            if any(p in chunk for p in [".", "!", "?"]):
                to_speak = sentence_buffer.strip()
                if to_speak:
                    async for audio_chunk in text_to_speech_stream(to_speak):
                        await websocket.send_bytes(audio_chunk)
                sentence_buffer = ""

        if sentence_buffer.strip():
            async for audio_chunk in text_to_speech_stream(sentence_buffer.strip()):
                await websocket.send_bytes(audio_chunk)

        await append_to_session(session_id, "assistant", full_greeting)
        await websocket.send_text(json.dumps({"type": "response_done", "text": full_greeting}))

        # Main message loop
        while True:
            audio_data = await websocket.receive_bytes()
            await orchestrate(websocket, audio_data, session_id)

    except WebSocketDisconnect:
        logger.info(f"Mock interview WebSocket disconnected: session={session_id}")
    except Exception as exc:
        logger.error(f"Mock interview WebSocket error: {exc}")
        try:
            await websocket.send_text(json.dumps({"type": "response", "text": f"Server Error: {exc}"}))
        except Exception:
            pass
