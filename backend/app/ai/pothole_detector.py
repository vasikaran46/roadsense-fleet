"""
RoadSense Fleet - Pothole Detector
Uses YOLOv8 model fine-tuned for pothole detection.
"""

import logging
from pathlib import Path
from typing import List

import numpy as np

from app.ai import Detection, compute_severity
from app.config import settings

logger = logging.getLogger(__name__)


class PotholeDetector:
    """YOLO-based pothole detector."""

    def __init__(self):
        self.model = None
        self.model_path = settings.get_model_path(settings.POTHOLE_MODEL_PATH)

    def _load_model(self):
        if self.model is not None:
            return True
        if not self.model_path.exists():
            logger.warning(f"Pothole model not found at {self.model_path}")
            return False
        try:
            from ultralytics import YOLO
            self.model = YOLO(str(self.model_path))
            logger.info(f"Pothole model loaded: {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load pothole model: {e}")
            return False

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
                    cls_name = result.names[int(box.cls[0])]
                    severity = compute_severity(confidence, "pothole")
                    detections.append(Detection(
                        class_name="pothole",
                        confidence=confidence,
                        bbox=(int(x1), int(y1), int(x2), int(y2)),
                        detector_source="pothole_yolov8",
                        severity=severity,
                    ))
            return detections
        except Exception as e:
            logger.error(f"Pothole detection error: {e}")
            return []
