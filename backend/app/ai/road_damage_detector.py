"""
RoadSense Fleet - Road Damage / Crack Detector
Uses YOLOv8 model fine-tuned for road damage detection (RDD dataset).
"""

import logging
from pathlib import Path
from typing import List

import numpy as np

from app.ai import Detection, compute_severity
from app.config import settings

logger = logging.getLogger(__name__)

# Class name mapping for RDD-style models
RDD_CLASSES = {
    "D00": "longitudinal_crack",
    "D10": "transverse_crack",
    "D20": "alligator_crack",
    "D40": "pothole",
    "D43": "road_damage",
    "D44": "road_damage",
}


class RoadDamageDetector:
    """YOLO-based road damage and crack detector."""

    def __init__(self):
        self.model = None
        self.model_path = settings.get_model_path(settings.ROAD_DAMAGE_MODEL_PATH)

    def _load_model(self):
        if self.model is not None:
            return True
        if not self.model_path.exists():
            logger.warning(f"Road damage model not found at {self.model_path}")
            return False
        try:
            from ultralytics import YOLO
            self.model = YOLO(str(self.model_path))
            logger.info(f"Road damage model loaded: {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load road damage model: {e}")
            return False

    def _map_class(self, cls_name: str) -> str:
        return RDD_CLASSES.get(cls_name, cls_name.lower().replace(" ", "_"))

    def detect(self, frame: np.ndarray) -> List[Detection]:
        if not self._load_model():
            return []
        try:
            results = self.model(frame, conf=settings.DETECTION_CONFIDENCE, verbose=False)
            detections = []
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    confidence = float(box.conf[0])
                    raw_name = result.names[int(box.cls[0])]
                    mapped_name = self._map_class(raw_name)
                    severity = compute_severity(confidence, mapped_name)
                    detections.append(Detection(
                        class_name=mapped_name,
                        confidence=confidence,
                        bbox=(int(x1), int(y1), int(x2), int(y2)),
                        detector_source="road_damage_rdd",
                        severity=severity,
                    ))
            return detections
        except Exception as e:
            logger.error(f"Road damage detection error: {e}")
            return []
