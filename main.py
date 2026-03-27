"""
jobs.ottobon.cloud — FastAPI Application Entry Point

Registers all routers, applies middleware, and serves the API.
"""

import logging
import contextlib
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.routers import admin, auth, chat, ingestion, jobs, matching, users, blog, analytics, rag

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)
logger = logging.getLogger(__name__)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 jobs.ottobon.cloud is starting up")
    from app.scheduler import start_scheduler, shutdown_scheduler
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()
    logger.info("🛑 jobs.ottobon.cloud is shutting down")


# ── App factory ───────────────────────────────────────────────
app = FastAPI(
    title="jobs.ottobon.cloud",
    description=(
        "Outcome-Driven Recruitment Ecosystem — "
        "connecting providers directly with seekers via AI-powered matching."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ── Global Exception Handler ─────────────────────────────────
# Ensures ALL unhandled errors return proper JSON with CORS headers
# (prevents the browser from seeing a raw connection error)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: "
        f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}"},
    )


# ── Routers ───────────────────────────────────────────────────
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(matching.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(ingestion.router)
app.include_router(blog.router)
app.include_router(analytics.router)
app.include_router(rag.router)



# ── Health Check ──────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "jobs.ottobon.cloud"}