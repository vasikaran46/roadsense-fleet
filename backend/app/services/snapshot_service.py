"""
RoadSense Fleet - Snapshot Service
Annotates frames with bounding boxes and saves JPEG evidence.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

import cv2
import numpy as np

from app.ai import Detection
from app.config import settings

logger = logging.getLogger(__name__)

# Color map for bounding boxes (BGR format)
BBOX_COLORS = {
    "pothole": (0, 0, 255),        # Red
    "road_damage": (0, 165, 255),   # Orange
    "crack": (0, 165, 255),
    "longitudinal_crack": (0, 140, 255),
    "transverse_crack": (0, 120, 255),
    "lateral_crack": (0, 120, 255),
    "alligator_crack": (0, 100, 200),
    "edge_crack": (0, 140, 255),
    "traffic_sign": (255, 128, 0),  # Sky Blue
    "zebra_crossing": (200, 50, 160), # Purple
    "waterlogging": (255, 200, 0),  # Cyan
    "car": (0, 255, 0),             # Green
    "bus": (0, 220, 0),
    "truck": (0, 200, 0),
    "motorcycle": (0, 180, 0),
    "person": (255, 0, 255),        # Magenta
}


def save_snapshot(frame: np.ndarray, detections: List[Detection], device_id: str) -> str:
    """Annotate frame and save as JPEG. Returns the filename."""
    try:
        annotated = frame.copy()

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = BBOX_COLORS.get(det.class_name, (255, 255, 255))
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            display_name = det.subtype if det.subtype else det.class_name
            label = f"{display_name} {det.confidence:.0%}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            (tw, th), _ = cv2.getTextSize(label, font, font_scale, thickness)
            cv2.rectangle(annotated, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 2, y1 - 4), font, font_scale, (255, 255, 255), thickness)

        # Add timestamp overlay
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(annotated, f"{device_id} | {ts}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # Save
        filename = f"{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.jpg"
        filepath = settings.get_snapshot_dir() / filename
        cv2.imwrite(str(filepath), annotated, [cv2.IMWRITE_JPEG_QUALITY, settings.JPEG_QUALITY])
        logger.info(f"Snapshot saved: {filename}")
        return filename

    except Exception as e:
        logger.error(f"Snapshot save error: {e}")
        return ""
