"""
RoadSense Fleet - Configuration
Loads settings from .env file with sensible defaults.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings

# backend/ directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    DATABASE_URL: str = "sqlite:///./roadsense.db"

    POTHOLE_MODEL_PATH: str = "models/pothole_yolov8.pt"
    ROAD_DAMAGE_MODEL_PATH: str = "models/road_damage.pt"
    VEHICLE_MODEL_PATH: str = "models/yolov8n.pt"

    # Roboflow Multi-Workflow Serverless API
    ROBOFLOW_ENABLED: bool = True
    ROBOFLOW_API_URL: str = "https://serverless.roboflow.com"
    ROBOFLOW_API_KEY: str = ""
    ROBOFLOW_WORKSPACE: str = "vasikaran-a"
    ROBOFLOW_ROAD_DAMAGE_WORKFLOW: str = "general-segmentation-api"
    ROBOFLOW_TRAFFIC_SIGN_WORKFLOW: str = "general-segmentation-api-2"
    ROBOFLOW_ZEBRA_CROSSING_WORKFLOW: str = "general-segmentation-api-3"
    ROBOFLOW_INTERVAL_SECONDS: float = 2.0

    DETECTION_CONFIDENCE: float = 0.40
    EVENT_COOLDOWN_SECONDS: int = 5
    DUPLICATE_IOU_THRESHOLD: float = 0.3

    FRAME_PROCESS_INTERVAL: int = 5
    JPEG_QUALITY: int = 70

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DEFAULT_LATITUDE: float = 13.0827
    DEFAULT_LONGITUDE: float = 80.2707
    MAP_ZOOM: int = 12

    SNAPSHOT_DIR: str = "uploads/snapshots"

    # CORS
    CORS_ORIGINS: str = "*"

    def get_model_path(self, relative_path: str) -> Path:
        return BACKEND_DIR / relative_path

    def get_snapshot_dir(self) -> Path:
        path = BACKEND_DIR / self.SNAPSHOT_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    class Config:
        env_file = (str(PROJECT_ROOT / ".env"), str(BACKEND_DIR / ".env"), ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
