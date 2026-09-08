"""
RoadSense Fleet - Main Application
FastAPI entry point for the backend server.
Works both locally and on Render deployment.
"""

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

# Ensure the backend directory is in the Python path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.database.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("roadsense")

# Create FastAPI app
app = FastAPI(
    title="RoadSense Fleet",
    description="Intelligent road monitoring system for Chennai's public transport",
    version="1.0.0",
)

# CORS — configurable via CORS_ORIGINS env var (comma-separated or "*")
cors_origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount snapshot directory for serving evidence images
snapshot_dir = settings.get_snapshot_dir()
app.mount("/snapshots", StaticFiles(directory=str(snapshot_dir)), name="snapshots")

# Mount frontend static files
frontend_admin_dir = BACKEND_DIR.parent / "frontend-admin"
frontend_stream_dir = BACKEND_DIR.parent / "frontend-stream"

if frontend_admin_dir.exists():
    app.mount("/admin", StaticFiles(directory=str(frontend_admin_dir), html=True), name="admin")
if frontend_stream_dir.exists():
    app.mount("/stream", StaticFiles(directory=str(frontend_stream_dir), html=True), name="stream")

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root path to admin dashboard."""
    return RedirectResponse(url="/admin/")

# Include API routers
from app.api.health import router as health_router
from app.api.devices import router as devices_router
from app.api.events import router as events_router

app.include_router(health_router)
app.include_router(devices_router)
app.include_router(events_router)

# Include WebSocket routers
from app.ws.stream_ingest import router as stream_ingest_router
from app.ws.stream_relay import router as stream_relay_router

app.include_router(stream_ingest_router)
app.include_router(stream_relay_router)


@app.on_event("startup")
async def startup():
    """Initialize database and log startup info."""
    logger.info("=" * 60)
    logger.info("  RoadSense Fleet — Starting Up")
    logger.info("  City: Chennai, Tamil Nadu")
    logger.info("=" * 60)

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Log model status (lazy-load frame processor)
    logger.info("AI detectors will initialize on first frame...")
    logger.info(f"Config: process_interval={settings.FRAME_PROCESS_INTERVAL}, "
                f"confidence={settings.DETECTION_CONFIDENCE}, "
                f"cooldown={settings.EVENT_COOLDOWN_SECONDS}s")
    logger.info("Server ready! Endpoints:")
    logger.info("  Health:    GET  /health")
    logger.info("  Devices:   GET  /devices")
    logger.info("  Events:    GET  /events")
    logger.info("  Stats:     GET  /events/stats")
    logger.info("  Stream WS: WS   /ws/stream/{device_id}")
    logger.info("  Watch WS:  WS   /ws/watch/{device_id}")
    logger.info("  Events WS: WS   /ws/events")
    logger.info("  Admin UI:  GET  /admin/")
    logger.info("  Stream UI: GET  /stream/")
    logger.info("=" * 60)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=port,
        reload=True,
    )
