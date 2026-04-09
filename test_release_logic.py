import asyncio
from unittest.mock import AsyncMock
from app.services.chat_service import ChatService

async def test_release_logic():
    db = AsyncMock()
    ai = AsyncMock()
    chat_svc = ChatService(db, ai)
    
    session_id = "test-session-id"
    
    # --- Test Case 1: Intercepted session ---
    db.get_chat_session.return_value = {
        "id": session_id,
        "is_intercepted": True,
        "conversation_log": []
    }
    
    print("Testing intercepted session (AI should be suppressed)...")
    reply = await chat_svc.handle_message(session_id, "Hello help me")
    assert reply is None, "AI should not reply when intercepted"
    print("AI suppressed correctly.")
    
    # --- Test Case 2: Released session ---
    db.get_chat_session.return_value = {
        "id": session_id,
        "is_intercepted": False,
        "conversation_log": []
    }
    ai.chat.return_value = "AI Response"
    # mock _build_user_context
    chat_svc._build_user_context = AsyncMock(return_value="User info")
    
    print("\nTesting released session (AI should resume)...")
    reply = await chat_svc.handle_message(session_id, "Hello again")
    assert reply == "AI Response", f"AI should reply when not intercepted. Got: {reply}"
    print("AI resumed correctly.")

if __name__ == "__main__":
    asyncio.run(test_release_logic())
