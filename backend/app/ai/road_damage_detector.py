"""
RoadSense Fleet - Road Damage / Crack Detector
Uses YOLOv8 model fine-tuned for road damage detection (RDD dataset).
"""

import logging
from pathlib import Path
from typing import List

import numpy as np

from backend.app.ai import Detection, compute_severity
from backend.app.config import settings

logger = logging.getLogger(__name__)


class RoadDamageDetector:
    """YOLO-based road damage and crack detector."""

    def __init__(self):
        self.model = None
        self.model_path = settings.get_model_path(settings.ROAD_DAMAGE_MODEL_PATH)
        self.confidence_threshold = settings.DETECTION_CONFIDENCE
        self._load_model()

    def _load_model(self):
        """Load the YOLO road damage model."""
        try:
            if not self.model_path.exists():
                logger.warning(
                    f"Road damage model not found at {self.model_path}. "
                    "Road damage detection will be disabled."
                )
                return

            from ultralytics import YOLO
            self.model = YOLO(str(self.model_path))
            logger.info(f"Road damage detector loaded from {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load road damage model: {e}")
            self.model = None

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run road damage detection on a frame."""
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
                    cls_name = result.names.get(cls_id, "road_damage")

                    # Normalize class names from RDD dataset
                    normalized_name = self._normalize_class(cls_name)

                    detection = Detection(
                        class_name=normalized_name,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        detector_source="road_damage_yolo",
                        severity=compute_severity(conf, "road_damage"),
                    )
                    detections.append(detection)

            return detections

        except Exception as e:
            logger.error(f"Road damage detection error: {e}")
            return []

    def _normalize_class(self, raw_name: str) -> str:
        """Map RDD dataset class names to our standard names."""
        name_lower = raw_name.lower()
        # Common RDD2022 class mappings
        mapping = {
            "d00": "longitudinal_crack",
            "d10": "transverse_crack",
            "d20": "alligator_crack",
            "d40": "pothole",
            "d43": "cross_walk_blur",
            "d44": "white_line_blur",
        }
        if name_lower in mapping:
            return mapping[name_lower]
        if "crack" in name_lower:
            return "crack"
        if "pothole" in name_lower:
            return "pothole"
        return "road_damage"

    @property
    def is_available(self) -> bool:
        return self.model is not None
