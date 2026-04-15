"""
Admin endpoints — Control Tower management.
"""

import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel

from app.dependencies import get_ai_service, get_db, get_embedding_service
from app.domain.models import MockInterviewAdminReview
from app.ports.ai_port import AIPort
from app.ports.database_port import DatabasePort
from app.ports.embedding_port import EmbeddingPort
from app.services.auth_service import get_current_user
from app.services.chat_service import ChatService
from app.services.enrichment_service import EnrichmentService
from app.services.mock_interview_service import MockInterviewService
from app.scheduler import trigger_ingestion # Manual trigger import

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


def _require_admin(current_user: dict[str, Any]) -> None:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint",
        )


@router.get("/sessions", status_code=status.HTTP_200_OK)
async def get_all_sessions(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """
    Get all active chat sessions for the Control Tower.
    """
    _require_admin(current_user)
    
    sessions = await db.get_all_chat_sessions()
    return sessions


@router.get("/sessions/{session_id}", status_code=status.HTTP_200_OK)
async def get_session_details(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """
    Get full details for a specific chat session (Admin only).
    """
    _require_admin(current_user)
    
    session = await db.get_chat_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    return session


@router.post("/sessions/{session_id}/intercept", status_code=status.HTTP_200_OK)
async def intercept_session(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """
    Admin intercepts a chat session.
    Injects a system notification into the chat log and pushes it
    live to the user via their active WebSocket connection.
    """
    _require_admin(current_user)

    session = await db.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Inject a system notification into the conversation log
    import json
    from datetime import datetime, timezone
    from app.services.chat_service import ChatService

    log = ChatService._parse_log(session.get("conversation_log"))
    notification = {
        "role": "system",
        "content": "🛡️ An expert has joined the conversation.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log.append(notification)
    await db.update_chat_session(session_id, {"conversation_log": log, "is_intercepted": True})

    # Push live via WebSocket if user is connected
    from app.routers.chat import manager
    try:
        await manager.send_message(
            session_id,
            json.dumps({"type": "system_notification", "content": notification["content"]}),
        )
    except Exception:
        pass  # User may not be connected right now — message is saved in log anyway

    return {"ok": True, "message": "Expert notification sent"}


class AdminMessageBody(BaseModel):
    content: str


@router.post("/sessions/{session_id}/message", status_code=status.HTTP_200_OK)
async def send_admin_message(
    session_id: str,
    body: AdminMessageBody,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """
    Admin sends a message directly into a seeker's chat session.
    The message is saved to the conversation log and pushed
    live to the seeker's active WebSocket connection.
    """
    _require_admin(current_user)

    session = await db.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    import json
    from datetime import datetime, timezone
    from app.services.chat_service import ChatService
    from app.routers.chat import manager

    log = ChatService._parse_log(session.get("conversation_log"))
    msg = {
        "role": "admin",
        "content": body.content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log.append(msg)
    await db.update_chat_session(session_id, {"conversation_log": log})

    # Push to the seeker's live WebSocket
    try:
        await manager.send_message(
            session_id,
            json.dumps({"type": "admin_message", "content": body.content}),
        )
    except Exception:
        pass

    return {"ok": True}


@router.post("/sessions/{session_id}/release", status_code=status.HTTP_200_OK)
async def release_session(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """
    Admin releases a chat session back to the AI coach.
    Sets is_intercepted = False and injects a resumption notification.
    """
    _require_admin(current_user)

    session = await db.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # 1. Update session state
    import json
    from datetime import datetime, timezone
    from app.services.chat_service import ChatService

    log = ChatService._parse_log(session.get("conversation_log"))
    notification = {
        "role": "system",
        "content": "Expert has left. AI assistant resuming.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log.append(notification)
    
    await db.update_chat_session(
        session_id, 
        {"conversation_log": log, "is_intercepted": False}
    )

    # 2. Push live via WebSocket
    from app.routers.chat import manager
    try:
        await manager.send_message(
            session_id,
            json.dumps({"type": "system_notification", "content": notification["content"]}),
        )
    except Exception:
        pass

    return {"ok": True, "message": "Session released to AI coach"}


@router.get("/mock-interviews", status_code=status.HTTP_200_OK)
async def list_mock_interview_reviews(
    status: str = "all",
    search: str = "",
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Admin review desk list for mock interviews."""
    _require_admin(current_user)
    if status not in {"pending_review", "reviewed", "all"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be one of: pending_review, reviewed, all",
        )
    svc = MockInterviewService(db=db)
    return await svc.list_admin_interviews(status_filter=status, search=search)


@router.get("/mock-interviews/{interview_id}", status_code=status.HTTP_200_OK)
async def get_mock_interview_review_detail(
    interview_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Full admin detail for a mock interview review."""
    _require_admin(current_user)
    svc = MockInterviewService(db=db)
    try:
        return await svc.get_interview_details(interview_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/mock-interviews/{interview_id}/review", status_code=status.HTTP_200_OK)
@router.post("/mock-interviews/{interview_id}/review", status_code=status.HTTP_200_OK)
async def review_mock_interview(
    interview_id: str,
    body: MockInterviewAdminReview,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """Save admin-authored feedback and mark the interview as reviewed."""
    _require_admin(current_user)
    svc = MockInterviewService(db=db)
    try:
        return await svc.submit_admin_review(interview_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))




@router.post("/ingest/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_manual_ingestion(
    background_tasks: BackgroundTasks,
    scraper_name: Optional[str] = None,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Manually trigger the job ingestion process.
    - scraper_name: 'deloitte', 'pwc', etc. or None for all.
    """
    role = current_user.get("role")
    if role not in ["admin", "provider"]:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to trigger ingestion",
        )

    # Run in background to avoid blocking the request
    background_tasks.add_task(trigger_ingestion, scraper_name)
    
    return {
        "message": f"Ingestion triggered for {scraper_name or 'ALL scrapers'}",
        "status": "processing_in_background"
    }


async def _reenrich_unenriched_jobs(db: DatabasePort, ai: AIPort, emb: EmbeddingPort):
    """Background task: find all jobs missing enrichment and re-run the pipeline in small batches."""
    import asyncio

    BATCH_SIZE = 3          # Process 3 jobs at a time
    BATCH_DELAY_SECS = 3    # Wait 3 seconds between batches

    enricher = EnrichmentService(db=db, ai=ai, embeddings=emb)

    # Query all jobs missing any enrichment data
    result = (
        db._client.table("jobs_jobs")
        .select("id, title, company_name, prep_guide_generated, resume_guide_generated, embedding, status")
        .execute()
    )
    all_jobs = result.data or []

    unenriched = [
        j for j in all_jobs
        if not j.get("prep_guide_generated")
        or not j.get("resume_guide_generated")
        or not j.get("embedding")
    ]

    logger.info("Re-enrichment: %d/%d jobs need enrichment", len(unenriched), len(all_jobs))

    success = 0
    failed = 0

    # Process in small batches to avoid overloading the server
    for batch_start in range(0, len(unenriched), BATCH_SIZE):
        batch = unenriched[batch_start:batch_start + BATCH_SIZE]
        batch_num = (batch_start // BATCH_SIZE) + 1
        total_batches = (len(unenriched) + BATCH_SIZE - 1) // BATCH_SIZE
        logger.info("Processing batch %d/%d (%d jobs)", batch_num, total_batches, len(batch))

        for job in batch:
            job_id = job["id"]
            try:
                await enricher.enrich_job(job_id)
                # Fix stuck 'processing' status
                if job.get("status") == "processing":
                    await db.update_job(job_id, {"status": "active"})
                success += 1
                logger.info("Re-enriched: %s (%s)", job.get("title"), job.get("company_name"))
            except Exception:
                failed += 1
                logger.exception("Re-enrichment failed for job %s", job_id)

        # Pause between batches to let the server breathe
        if batch_start + BATCH_SIZE < len(unenriched):
            logger.info("Batch %d done. Pausing %ds before next batch...", batch_num, BATCH_DELAY_SECS)
            await asyncio.sleep(BATCH_DELAY_SECS)

    logger.info("Re-enrichment complete: %d success, %d failed", success, failed)


@router.post("/reenrich", status_code=status.HTTP_202_ACCEPTED)
async def reenrich_jobs(
    background_tasks: BackgroundTasks,
    db: DatabasePort = Depends(get_db),
    ai: AIPort = Depends(get_ai_service),
    emb: EmbeddingPort = Depends(get_embedding_service),
):
    """
    Re-run AI enrichment for all jobs missing prep_guide, resume_guide, or embedding.
    Does NOT require auth — use for development/debugging only.
    """
    background_tasks.add_task(_reenrich_unenriched_jobs, db, ai, emb)
    return {"message": "Re-enrichment started in background. Check server logs for progress."}


@router.post("/scrape-all", status_code=status.HTTP_202_ACCEPTED)
async def scrape_all_sources(
    background_tasks: BackgroundTasks,
):
    """
    Trigger full scraping from all sources (no auth — dev only).
    """
    from app.scheduler import trigger_ingestion
    background_tasks.add_task(trigger_ingestion, "all")
    return {"message": "Scraping ALL sources triggered in background. Check server logs for progress."}

