"""
mock_interview/orchestrator.py
Pipeline controller that connects all services in order:
  audio bytes → STT → context → LLM → TTS → WebSocket
"""

import json
from fastapi import WebSocket

from app.mock_interview.services.stt import speech_to_text
from app.mock_interview.services.context import get_behavioral_questions
from app.mock_interview.services.llm import generate_response
from app.mock_interview.services.tts import text_to_speech_stream
from app.mock_interview.services.session import (
    manage_session,
    append_to_session,
    get_session_history,
    get_resume_text,
    get_job_context,
    get_interview_mode,
    set_interview_mode,
    increment_question_count,
    get_question_count,
)


async def orchestrate(websocket: WebSocket, audio_data: bytes, session_id: str) -> None:
    """
    Executes the complete real-time AI voice pipeline for one user turn.
    1. Transcribe audio  →  2. Build context  →  3. Generate LLM response  →  4. TTS  →  5. Send to client
    """
    try:
        # 1. Session housekeeping
        await manage_session(session_id)

        # 2. STT — audio bytes → text
        text = await speech_to_text(audio_data)
        if not text or not text.strip():
            return

        await websocket.send_text(json.dumps({"type": "transcript", "text": text}))
        await append_to_session(session_id, "user", text)

        # Handle explicit /analyze command
        if "/analyze" in text.lower():
            analysis_msg = "Understood. The interview has concluded. I am now synthesizing your 'Job Match Analysis' report. Please wait a moment."
            await websocket.send_text(json.dumps({"type": "response_start"}))
            await websocket.send_text(json.dumps({"type": "response_chunk", "text": analysis_msg}))
            async for audio_chunk in text_to_speech_stream(analysis_msg):
                await websocket.send_bytes(audio_chunk)
            await websocket.send_text(json.dumps({"type": "response_done", "text": analysis_msg}))
            await append_to_session(session_id, "assistant", analysis_msg)
            # Signal the frontend to stop and evaluate
            await websocket.send_text(json.dumps({"type": "session_end_trigger"}))
            return

        # 3. Build context
        current_mode = await get_interview_mode(session_id)
        q_count = await get_question_count(session_id)
        
        # Auto-detect mode...
        if not current_mode:
            lower = text.lower()
            if any(w in lower for w in ["hr", "human resources", "behavioral", "behaviour"]):
                current_mode = "hr"
                await set_interview_mode(session_id, "hr")
            elif any(w in lower for w in ["technical", "tech", "coding", "programming", "system design"]):
                current_mode = "technical"
                await set_interview_mode(session_id, "technical")

        job_context = await get_job_context(session_id)
        company_name = job_context.get("company_name", "")
        job_desc = job_context.get("job_description", "")

        context_parts: list[str] = []
        if q_count >= 7:
             context_parts.append("[SYSTEM_NOTE]: This is the final question. After this answer, conclude the interview and suggest the candidate types /analyze for the final report.")
        elif q_count >= 5:
             context_parts.append(f"[SYSTEM_NOTE]: You have asked {q_count} questions. You should aim to conclude the interview soon (within 7 questions total).")

        if current_mode == "hr":
            bq = await get_behavioral_questions()
            if bq:
                context_parts.append(f"BEHAVIORAL_QUESTIONS:\n{bq}")

        resume_text = await get_resume_text(session_id)
        if resume_text:
            context_parts.append(f"CANDIDATE_RESUME_DATA:\n{resume_text}")
        if company_name:
            context_parts.append(f"[TARGET_COMPANY]: {company_name}")
        if job_desc:
            context_parts.append(f"[JOB_DESCRIPTION]: {job_desc}")
        if current_mode:
            context_parts.append(f"[INTERVIEW_MODE_SELECTED]: {current_mode}")

        context = "\n".join(context_parts) or None

        history = await get_session_history(session_id)

        # 4. Generate LLM response
        full_response = ""
        sentence_buffer = ""

        await websocket.send_text(json.dumps({"type": "response_start"}))

        async for chunk in generate_response(text, history, context):
            full_response += chunk
            sentence_buffer += chunk
            await websocket.send_text(json.dumps({"type": "response_chunk", "text": chunk}))

            # Flush to TTS on sentence boundary
            if any(p in chunk for p in [".", "!", "?"]):
                to_speak = sentence_buffer.strip()
                if to_speak:
                    async for audio_chunk in text_to_speech_stream(to_speak):
                        await websocket.send_bytes(audio_chunk)
                sentence_buffer = ""

        # Speak any remaining buffer
        if sentence_buffer.strip():
            async for audio_chunk in text_to_speech_stream(sentence_buffer.strip()):
                await websocket.send_bytes(audio_chunk)

        # 5. Finalise
        await websocket.send_text(json.dumps({"type": "response_done", "text": full_response}))
        await append_to_session(session_id, "assistant", full_response)
        await increment_question_count(session_id)

    except Exception as exc:
        error_msg = f"Pipeline Error: {exc}"
        print(error_msg)
        try:
            await websocket.send_text(json.dumps({"type": "response", "text": error_msg}))
        except Exception:
            pass
