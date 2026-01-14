"""Main FastAPI application entry point.

Copyright 2025 milbert.ai
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.config import settings
from app.db.session import engine, init_db
from app.services.task_queue import task_queue

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Cleanup task - defined before lifespan so it's available
async def cleanup_old_jobs():
    """Clean up old jobs and outputs."""
    from datetime import datetime, timedelta
    from sqlalchemy import delete, select

    from app.db.session import async_session
    from app.models.job import Job, JobOutput, JobStatus

    retention_days = 30
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    async with async_session() as db:
        # Get old job IDs
        old_jobs = await db.execute(
            select(Job.id).where(
                Job.status.in_([
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value
                ]),
                Job.created_at < cutoff_date
            )
        )
        job_ids = [j[0] for j in old_jobs.all()]

        if job_ids:
            # Delete outputs
            await db.execute(delete(JobOutput).where(JobOutput.job_id.in_(job_ids)))
            # Delete jobs
            await db.execute(delete(Job).where(Job.id.in_(job_ids)))
            await db.commit()
            logger.info(f"Cleaned up {len(job_ids)} old jobs")

    return {"deleted": len(job_ids) if job_ids else 0}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting kwebbie...")

    # Ensure data directories exist
    settings.data_path.mkdir(parents=True, exist_ok=True)
    settings.uploads_path.mkdir(parents=True, exist_ok=True)
    settings.reports_path.mkdir(parents=True, exist_ok=True)
    settings.outputs_path.mkdir(parents=True, exist_ok=True)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Start task queue
    await task_queue.start()
    logger.info("Task queue started")

    # Schedule cleanup task (daily) - function defined below
    task_queue.schedule(cleanup_old_jobs, interval_seconds=86400, task_name="cleanup")

    yield

    # Shutdown
    logger.info("Shutting down kwebbie...")
    await task_queue.stop()
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="kwebbie - Web interface for Kali Linux security tools. Copyright 2025 milbert.ai",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Serve static files (frontend build)
static_path = Path(__file__).parent.parent.parent / "static"
if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
    }


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/api/docs" if settings.debug else None,
    }


# Create Socket.IO app
try:
    from app.websocket.manager import sio
    socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
    application = socket_app
except ImportError:
    application = app


