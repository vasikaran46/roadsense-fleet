"""
RoadSense Fleet - Configuration
Loads settings from .env file with sensible defaults.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Project root is the parent of the backend directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Database
    DATABASE_URL: str = "sqlite:///./roadsense.db"

    # AI Model Paths (relative to project root)
    POTHOLE_MODEL_PATH: str = "backend/models/pothole_yolov8.pt"
    ROAD_DAMAGE_MODEL_PATH: str = "backend/models/road_damage.pt"
    VEHICLE_MODEL_PATH: str = "backend/models/yolov8n.pt"

    # Detection Settings
    DETECTION_CONFIDENCE: float = 0.40
    EVENT_COOLDOWN_SECONDS: int = 5
    DUPLICATE_IOU_THRESHOLD: float = 0.3

    # Frame Processing
    FRAME_PROCESS_INTERVAL: int = 5  # Process every Nth frame
    JPEG_QUALITY: int = 70

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Map Defaults (Chennai)
    DEFAULT_LATITUDE: float = 13.0827
    DEFAULT_LONGITUDE: float = 80.2707
    MAP_ZOOM: int = 12

    # Snapshot storage
    SNAPSHOT_DIR: str = "backend/uploads/snapshots"

    def get_model_path(self, relative_path: str) -> Path:
        """Resolve a model path relative to the project root."""
        return BASE_DIR / relative_path

    def get_snapshot_dir(self) -> Path:
        """Get absolute snapshot directory path."""
        path = BASE_DIR / self.SNAPSHOT_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
