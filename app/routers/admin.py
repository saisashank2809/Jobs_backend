"""
Admin endpoints — Control Tower management.
"""

import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks  # type: ignore
from pydantic import BaseModel  # type: ignore

from app.dependencies import get_ai_service, get_db, get_embedding_service  # type: ignore
from app.ports.ai_port import AIPort  # type: ignore
from app.ports.database_port import DatabasePort  # type: ignore
from app.ports.embedding_port import EmbeddingPort  # type: ignore
from app.services.auth_service import get_current_user  # type: ignore
from app.services.chat_service import ChatService  # type: ignore
from app.services.enrichment_service import EnrichmentService  # type: ignore
from app.scheduler import trigger_ingestion  # type: ignore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/sessions", status_code=status.HTTP_200_OK)
async def get_all_sessions(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
):
    """
    Get all active chat sessions for the Control Tower.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view all sessions",
        )
    
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
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view session details",
        )
    
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
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can intercept sessions",
        )

    session = await db.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Inject a system notification into the conversation log
    import json
    from datetime import datetime, timezone
    from app.services.chat_service import ChatService  # type: ignore

    log = ChatService._parse_log(session.get("conversation_log"))
    notification = {
        "role": "system",
        "content": "🛡️ An expert has joined the conversation.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log.append(notification)
    await db.update_chat_session(session_id, {"conversation_log": log})

    # Push live via WebSocket if user is connected
    from app.routers.chat import manager  # type: ignore
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
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")

    session = await db.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    import json
    from datetime import datetime, timezone
    from app.services.chat_service import ChatService  # type: ignore
    from app.routers.chat import manager  # type: ignore

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
        batch = list(unenriched[batch_start:batch_start + BATCH_SIZE])  # type: ignore[index]
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
    from app.scheduler import trigger_ingestion  # type: ignore
    background_tasks.add_task(trigger_ingestion, "all")
    return {"message": "Scraping ALL sources triggered in background. Check server logs for progress."}

