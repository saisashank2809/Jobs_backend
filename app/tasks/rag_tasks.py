import time
from celery import Celery
from supabase import create_client, Client

from app.config import settings

# Initialize Supabase Admin Client
supabase_admin: Client = create_client(
    settings.supabase_url, 
    settings.supabase_service_role_key
)

# Initialize Celery app
celery_app = Celery(
    "rag_tasks", 
    broker=settings.celery_broker_url, 
    backend=settings.celery_broker_url  # Using broker as backend for simplicity
)

@celery_app.task(name="process_rag_document")
def process_rag_document(doc_id: str):
    """Background task to process document for RAG."""
    try:
        # Fetch document status sanity check
        res = supabase_admin.table("jobs_resumes").select("doc_id").eq("doc_id", doc_id).execute()
        if not res.data:
            return f"Doc {doc_id} not found."

        # Status Update: Indexing
        supabase_admin.table("jobs_resumes").update({"status": "indexing"}).eq("doc_id", doc_id).execute()

        # ------------------------------------------------------------------
        # [MOCK RAG PIPELINE]
        # In reality, you would:
        # 1. Download the file via GET /users/{id}/drive/items/{file_id}/content
        # 2. Extract text (PyPDF, docx, etc.)
        # 3. Chunk the text (LangChain/LlamaIndex)
        # 4. Generate Embeddings (OpenAI, HuggingFace)
        # 5. Insert vectors into your Vector DB (pgvector, Pinecone, Qdrant)
        # ------------------------------------------------------------------
        time.sleep(5)  # Simulating processing delay
        
        # Status Update: Ready
        supabase_admin.table("jobs_resumes").update({"status": "ready"}).eq("doc_id", doc_id).execute()

        return f"Successfully processed document {doc_id}"

    except Exception as e:
        # Set status to failed on unhandled exception
        supabase_admin.table("jobs_resumes").update({"status": "failed"}).eq("doc_id", doc_id).execute()
        raise e
