"""
RoadSense Fleet - Snapshot Service
Annotates frames with detection bounding boxes and saves evidence images.
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from backend.app.ai import Detection
from backend.app.config import settings

logger = logging.getLogger(__name__)

# Color map for detection types
COLORS = {
    "pothole": (0, 0, 255),        # Red
    "road_damage": (0, 165, 255),   # Orange
    "crack": (0, 165, 255),         # Orange
    "longitudinal_crack": (0, 165, 255),
    "transverse_crack": (0, 165, 255),
    "alligator_crack": (0, 140, 255),
    "waterlogging": (255, 200, 0),  # Cyan-ish
    "car": (0, 255, 0),            # Green
    "bus": (0, 255, 128),          # Green variant
    "truck": (0, 200, 0),          # Dark green
    "motorcycle": (128, 255, 0),   # Lime
    "person": (255, 0, 255),       # Magenta
    "bicycle": (200, 200, 0),      # Teal
}

DEFAULT_COLOR = (255, 255, 255)


def annotate_frame(frame: np.ndarray, detections: list) -> np.ndarray:
    """Draw bounding boxes and labels on a frame."""
    annotated = frame.copy()

    for det in detections:
        x1, y1, x2, y2 = det.bbox
        color = COLORS.get(det.class_name, DEFAULT_COLOR)
        label = f"{det.class_name} {det.confidence:.0%}"

        if det.detector_source == "waterlogging_heuristic":
            label += " [Heuristic]"

        # Draw bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        # Draw label background
        (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(annotated, (x1, y1 - th - 10), (x1 + tw + 4, y1), color, -1)
        cv2.putText(
            annotated, label, (x1 + 2, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2,
        )

    return annotated


def save_snapshot(frame: np.ndarray, detections: list, event_id: int = None) -> str:
    """Annotate frame and save as JPEG. Returns the filename."""
    try:
        annotated = annotate_frame(frame, detections)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        uid = uuid.uuid4().hex[:8]
        eid = event_id or "0"
        filename = f"event_{eid}_{timestamp}_{uid}.jpg"

        snapshot_dir = settings.get_snapshot_dir()
        filepath = snapshot_dir / filename

        cv2.imwrite(
            str(filepath),
            annotated,
            [cv2.IMWRITE_JPEG_QUALITY, settings.JPEG_QUALITY],
        )

        logger.info(f"Snapshot saved: {filename}")
        return filename

    except Exception as e:
        logger.error(f"Failed to save snapshot: {e}")
        return None
