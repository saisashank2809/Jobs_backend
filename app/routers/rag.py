from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from starlette.concurrency import run_in_threadpool
from supabase import create_client, Client
from app.config import settings
from app.services.graph_client import GraphClient
from app.tasks.rag_tasks import process_rag_document

router = APIRouter(prefix="/rag", tags=["RAG Document Processing"])
graph_client = GraphClient()

# Initialize Supabase Admin Client to bypass RLS for background jobs
supabase_admin: Client = create_client(
    settings.supabase_url, 
    settings.supabase_service_role_key
)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

def check_file_extension(filename: str):
    ext = filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {ALLOWED_EXTENSIONS}"
        )

@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...)
):
    check_file_extension(file.filename)
    
    file_bytes = await file.read()
    
    # 1. Store initial metadata in DB (Status: 'uploading')
    def _insert():
        return supabase_admin.table("jobs_resumes").insert({
            "file_name": file.filename,
            "status": "uploading"
        }).execute()
        
    insert_res = await run_in_threadpool(_insert)
    doc_id = insert_res.data[0]["doc_id"]

    try:
        # 2. Upload to Microsoft OneDrive
        onedrive_meta = await graph_client.upload_file(
            file_name=f"{doc_id}_{file.filename}", 
            file_bytes=file_bytes
        )
        
        # 3. Update DB with OneDrive references (Status: 'uploaded')
        def _update():
            return supabase_admin.table("jobs_resumes").update({
                "file_id": onedrive_meta["file_id"],
                "url": onedrive_meta["url"],
                "status": "uploaded"
            }).eq("doc_id", doc_id).execute()
            
        update_res = await run_in_threadpool(_update)

        # 4. Dispatch Celery Task for asynchronous processing
        process_rag_document.delay(doc_id)

        return {
            "message": "Document successfully uploaded and queued for indexing.",
            "doc_id": doc_id,
            "file_url": onedrive_meta["url"],
            "status": "uploaded"
        }

    except Exception as e:
        # Wait, rollback isn't trivial in REST API without saga pattern, but we can set status to failed.
        await run_in_threadpool(
            lambda: supabase_admin.table("jobs_resumes").update({"status": "failed"}).eq("doc_id", doc_id).execute()
        )
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
