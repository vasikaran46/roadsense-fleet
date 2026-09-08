"""
RoadSense Fleet - Vehicle Detector
Uses YOLOv8n (COCO) for vehicle/traffic detection.
"""

import logging
from pathlib import Path
from typing import List

import numpy as np

from app.ai import Detection, compute_severity
from app.config import settings

logger = logging.getLogger(__name__)

VEHICLE_CLASSES = {"car", "bus", "truck", "motorcycle", "bicycle", "person"}


class VehicleDetector:
    """YOLO-based vehicle and traffic detector using COCO model."""

    def __init__(self):
        self.model = None
        self.model_path = settings.get_model_path(settings.VEHICLE_MODEL_PATH)

    def _load_model(self):
        if self.model is not None:
            return True
        try:
            from ultralytics import YOLO
            self.model = YOLO(str(self.model_path))
            logger.info(f"Vehicle model loaded: {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load vehicle model: {e}")
            return False

    def detect(self, frame: np.ndarray) -> List[Detection]:
        if not self._load_model():
            return []
        try:
            results = self.model(frame, conf=settings.DETECTION_CONFIDENCE, verbose=False)
            detections = []
            for result in results:
                for box in result.boxes:
                    cls_name = result.names[int(box.cls[0])]
                    if cls_name not in VEHICLE_CLASSES:
                        continue
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    confidence = float(box.conf[0])
                    severity = compute_severity(confidence, cls_name)
                    detections.append(Detection(
                        class_name=cls_name,
                        confidence=confidence,
                        bbox=(int(x1), int(y1), int(x2), int(y2)),
                        detector_source="yolov8n_coco",
                        severity=severity,
                    ))
            return detections
        except Exception as e:
            logger.error(f"Vehicle detection error: {e}")
            return []
