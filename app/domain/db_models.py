"""
SQLAlchemy database models for the document processing pipeline.
"""
from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class DocumentModel(Base):
    __tablename__ = "jobs_resumes"

    doc_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String, nullable=False)
    file_id = Column(String, nullable=True)    # Received from Microsoft Graph API
    url = Column(String, nullable=True)        # Received from Microsoft Graph API
    status = Column(String, nullable=False, default="uploading")
    created_at = Column(DateTime, default=datetime.utcnow)
