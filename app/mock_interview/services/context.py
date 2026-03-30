"""
mock_interview/services/context.py
Context retrieval for mock interview sessions.
Loads behavioral questions from local data file.
Path is resolved relative to this file — no hardcoding.
"""

import json
import os
import random

# Resolve path to the data directory relative to this file
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


async def get_behavioral_questions() -> str | None:
    """Load and shuffle the generic behavioral questions list."""
    questions_path = os.path.join(_DATA_DIR, "behavioral_questions.json")
    try:
        if not os.path.exists(questions_path):
            return "No behavioral questions found."
        with open(questions_path, "r", encoding="utf-8") as f:
            questions = json.load(f)
            random.shuffle(questions)
            formatted = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
            return f"Required Interview Questions (In Random Order):\n{formatted}"
    except Exception as exc:
        print(f"Failed to load behavioral questions: {exc}")
        return None


async def get_context(text: str) -> str | None:
    """
    Stub for RAG context retrieval.
    Returns None for now — can be wired to pgvector / Pinecone later.
    """
    return None
