"""
RoadSense Fleet - Health Check API
"""

from fastapi import APIRouter
from backend.app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """System health check endpoint."""
    import os

    models_status = {}
    for name, path_attr in [
        ("pothole", settings.POTHOLE_MODEL_PATH),
        ("road_damage", settings.ROAD_DAMAGE_MODEL_PATH),
        ("vehicle", settings.VEHICLE_MODEL_PATH),
    ]:
        full_path = settings.get_model_path(path_attr)
        models_status[name] = {
            "path": str(path_attr),
            "loaded": full_path.exists(),
        }

    return {
        "status": "healthy",
        "service": "RoadSense Fleet",
        "version": "1.0.0",
        "city": "Chennai",
        "models": models_status,
        "config": {
            "frame_process_interval": settings.FRAME_PROCESS_INTERVAL,
            "detection_confidence": settings.DETECTION_CONFIDENCE,
            "event_cooldown_seconds": settings.EVENT_COOLDOWN_SECONDS,
            "jpeg_quality": settings.JPEG_QUALITY,
        },
    }
