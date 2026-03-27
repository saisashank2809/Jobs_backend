"""
Celery background tasks for document processing and RAG pipeline.
"""
import logging
import asyncio

from sqlalchemy.orm import Session

from app.worker.celery_app import celery_app
from app.database import SessionLocal
from app.domain.db_models import DocumentModel
from app.domain.enums import DocumentStatus
from app.adapters.msgraph_adapter import MSGraphAdapter

logger = logging.getLogger(__name__)

@celery_app.task(name="process_document_rag", bind=True, max_retries=3)
def process_document_rag(self, doc_id: str):
    """
    Background Task to process a document for RAG.
    Takes `doc_id`, updates DB status to 'indexing', runs the RAG pipeline placeholder, 
    and updates DB status to 'ready' when complete.
    """
    logger.info(f"Starting background RAG processing for doc_id: {doc_id}")
    db: Session = SessionLocal()
    
    document = None
    try:
        # 1. Start processing - update DB status to 'indexing'
        document = db.query(DocumentModel).filter(DocumentModel.doc_id == doc_id).first()
        if not document:
            logger.error(f"Document {doc_id} not found in PostgreSQL database.")
            return

        document.status = DocumentStatus.INDEXING.value
        db.commit()
        
        # 2. RAG Pipeline Placeholder
        # The user requested to leave placeholders for the actual RAG pipeline:
        logger.info(f"[{doc_id}] Download file via MS Graph GET /users/{{USER_ID}}/drive/items/{document.file_id}/content")
        logger.info(f"[{doc_id}] Extracting text from downloaded content...")
        logger.info(f"[{doc_id}] Chunking extracted text...")
        logger.info(f"[{doc_id}] Creating embeddings for text chunks...")
        logger.info(f"[{doc_id}] Inserting chunks and embeddings into vector database...")
        
        # 3. Processing complete - update DB status to 'ready'
        document.status = DocumentStatus.READY.value
        db.commit()
        
        logger.info(f"Successfully processed document {doc_id} for RAG.")
    except Exception as e:
        logger.error(f"Failed to process document {doc_id}: {str(e)}")
        if document:
            # Mark the document as failed if an error occurred during indexing
            document.status = DocumentStatus.FAILED.value
            db.commit()
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()
