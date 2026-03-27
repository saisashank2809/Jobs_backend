"""
Celery background worker application setup.
"""
from celery import Celery

from app.config import settings

celery_app = Celery(
    "rag_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Ensure background tasks for RAG are registered
    imports=("app.worker.tasks",)
)
