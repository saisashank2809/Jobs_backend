"""
Chat service — message routing for the Control Tower.
Handles AI auto-response vs admin takeover state machine.

Production hardening:
  - get_recent_history() for WebSocket state recovery on reconnect.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.domain.models import ChatMessage
from app.ports.ai_port import AIPort
from app.ports.database_port import DatabasePort

logger = logging.getLogger(__name__)


class ChatService:
    """Manages chat session state and routes messages."""

    def __init__(self, db: DatabasePort, ai: AIPort) -> None:
        self._db = db
        self._ai = ai

    async def get_recent_history(
        self, session_id: str, count: int = 10
    ) -> tuple[list[dict[str, Any]], str]:
        """
        Fetch the last `count` messages and current session status.
        Used for WebSocket state recovery after reconnect / server restart.

        Returns:
            (messages, session_status) — the N most recent log entries
            and the current status string (strictly 'active_ai' or 'closed').
        """
        session = await self._db.get_chat_session(session_id)
        if not session:
            return [], "closed"

        log = self._parse_log(session.get("conversation_log"))
        # Filter out hidden system context entries (not for display)
        visible_log = [m for m in log if not m.get("hidden")]
        # active_human is deprecated; default to active_ai
        status = session.get("status", "active_ai")
        if status == "active_human":
            status = "active_ai"
            
        return (visible_log[-count:] or []), status

    async def handle_message(
        self, session_id: str, user_message: str
    ) -> str | None:
        """
        Process an incoming user message and generate a PERSONALIZED AI reply.
        Human takeover mode is deprecated; all messages are handled by the AI mentor.
        """
        session = await self._db.get_chat_session(session_id)
        if not session:
            raise ValueError(f"Chat session {session_id} not found")

        # If an expert has intercepted, AI steps back
        if session.get("is_intercepted"):
            logger.info("Session %s is intercepted; skipping AI auto-reply.", session_id)
            
            # Still save the user message to the log for the expert to see
            log = self._parse_log(session.get("conversation_log"))
            log.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            await self._db.update_chat_session(session_id, {"conversation_log": log})
            return None

        # ── Extract text from JSON if submitted as an object ──
        if user_message.strip().startswith("{"):
            try:
                import json
                parsed = json.loads(user_message)
                user_message = parsed.get("message") or parsed.get("text") or parsed.get("content") or user_message
            except:
                pass

        # Append user message to log
        log = self._parse_log(session.get("conversation_log"))
        log.append(
            {
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # ── Build personalized context from user profile + job ──
        user_context = await self._build_user_context(
            session.get("user_id"), conversation_log=log
        )

        # Convert log to ChatMessage objects for the AI
        # (skip hidden system context entries)
        history = [
            ChatMessage(
                role=m["role"],
                content=m["content"],
                timestamp=m.get("timestamp", datetime.now(timezone.utc)),
            )
            for m in log
            if not m.get("hidden")
        ]

        ai_reply = await self._ai.chat(history, user_context=user_context)

        log.append(
            {
                "role": "assistant",
                "content": ai_reply,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        await self._db.update_chat_session(
            session_id, {"conversation_log": log}
        )
        return ai_reply or "I'm having a small glitch—please try again!"

    @staticmethod
    def _parse_log(raw: Any) -> list[dict[str, Any]]:
        """
        Parse conversation_log from the database.
        It may be a JSON string, a list, or None.
        """
        if raw is None:
            return []
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    async def _build_user_context(
        self, user_id: str | None, conversation_log: list[dict] | None = None
    ) -> str:
        """
        Build a rich context string from user profile + job info
        to inject into the AI system prompt for personalization.
        """
        if not user_id:
            return ""

        parts = []
        try:
            user = await self._db.get_user(user_id)
            if user:
                if user.get("full_name"):
                    parts.append(f"Candidate name: {user['full_name']}")
                if user.get("resume_text"):
                    # Truncate resume to avoid token overflow
                    resume_snippet = user["resume_text"][:2000]
                    parts.append(f"Candidate resume:\n{resume_snippet}")
                if user.get("skills"):
                    skills = user["skills"] if isinstance(user["skills"], list) else []
                    if skills:
                        parts.append(f"Candidate skills: {', '.join(skills)}")

            # ── Add Job Context from Conversation Log ──
            if conversation_log:
                for entry in conversation_log:
                    if entry.get("hidden") and entry.get("job_title"):
                        parts.append(f"Target Job: {entry['job_title']}")
                        if entry.get("job_description"):
                            # Already truncated in router, but just in case
                            parts.append(f"Job Description: {entry['job_description'][:1000]}")
                        if entry.get("skills_required"):
                            skills = entry["skills_required"]
                            if isinstance(skills, list):
                                parts.append(f"Required Skills: {', '.join(skills)}")
                        break
        except Exception as e:
            logger.warning("Failed to fetch user context for %s: %s", user_id, e)

        return "\n\n".join(parts)

    async def generate_greeting(self, session_id: str) -> str | None:
        """
        Generate a personalized greeting for a new chat session.
        Called on first WebSocket connect when no messages exist yet.
        """
        session = await self._db.get_chat_session(session_id)
        if not session:
            return None

        user_context = await self._build_user_context(session.get("user_id"))

        # Check if there's job context in the log
        log = self._parse_log(session.get("conversation_log"))
        job_title = None
        for entry in log:
            if entry.get("hidden") and entry.get("job_title"):
                job_title = entry["job_title"]
                break

        if job_title:
            greeting = (
                f"Hey! I'm your career coach. I see you're exploring the "
                f"**{job_title}** role. I can help you prepare for it — "
                f"ask me about interview tips, skills to develop, or anything else!"
            )
        else:
            greeting = (
                "Hey! I'm your career coach. Ask me anything about job prep, "
                "interview tips, resume advice, or career planning!"
            )

        # Save greeting to conversation log
        log.append({
            "role": "assistant",
            "content": greeting,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await self._db.update_chat_session(session_id, {"conversation_log": log})

        return greeting

