"""
RoadSense Fleet - Pothole Detector
Uses YOLOv8 model fine-tuned for pothole detection.
"""

import logging
from pathlib import Path
from typing import List, Optional

import numpy as np

from backend.app.ai import Detection, compute_severity
from backend.app.config import settings

logger = logging.getLogger(__name__)


class PotholeDetector:
    """YOLO-based pothole detector."""

    def __init__(self):
        self.model = None
        self.model_path = settings.get_model_path(settings.POTHOLE_MODEL_PATH)
        self.confidence_threshold = settings.DETECTION_CONFIDENCE
        self._load_model()

    def _load_model(self):
        """Load the YOLO pothole model."""
        try:
            if not self.model_path.exists():
                logger.warning(
                    f"Pothole model not found at {self.model_path}. "
                    "Pothole detection will be disabled. "
                    "Download a pothole YOLOv8 model and place it there."
                )
                return

            from ultralytics import YOLO
            self.model = YOLO(str(self.model_path))
            logger.info(f"Pothole detector loaded from {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load pothole model: {e}")
            self.model = None

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run pothole detection on a frame."""
        if self.model is None:
            return []

        try:
            results = self.model(
                frame,
                conf=self.confidence_threshold,
                verbose=False,
            )

            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue

                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    cls_name = result.names.get(cls_id, "pothole")

                    detection = Detection(
                        class_name="pothole",
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        detector_source="pothole_yolo",
                        severity=compute_severity(conf, "pothole"),
                    )
                    detections.append(detection)

            return detections

        except Exception as e:
            logger.error(f"Pothole detection error: {e}")
            return []

    @property
    def is_available(self) -> bool:
        return self.model is not None
