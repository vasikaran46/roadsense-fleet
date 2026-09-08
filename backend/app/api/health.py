"""RoadSense Fleet - Health API"""

from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "RoadSense Fleet",
        "version": "1.0.0",
        "city": "Chennai",
        "models": {
            "pothole": {
                "path": settings.POTHOLE_MODEL_PATH,
                "loaded": settings.get_model_path(settings.POTHOLE_MODEL_PATH).exists(),
            },
            "road_damage": {
                "path": settings.ROAD_DAMAGE_MODEL_PATH,
                "loaded": settings.get_model_path(settings.ROAD_DAMAGE_MODEL_PATH).exists(),
            },
            "vehicle": {
                "path": settings.VEHICLE_MODEL_PATH,
                "loaded": settings.get_model_path(settings.VEHICLE_MODEL_PATH).exists(),
            },
        },
        "config": {
            "frame_process_interval": settings.FRAME_PROCESS_INTERVAL,
            "detection_confidence": settings.DETECTION_CONFIDENCE,
            "event_cooldown_seconds": settings.EVENT_COOLDOWN_SECONDS,
            "jpeg_quality": settings.JPEG_QUALITY,
        },
    }
