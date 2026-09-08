"""
RoadSense Fleet - Vehicle Detector
Uses standard YOLOv8n (COCO) for traffic analytics.
Detects: car, bus, truck, motorcycle, person.
"""

import logging
from pathlib import Path
from typing import List

import numpy as np

from backend.app.ai import Detection, compute_severity
from backend.app.config import settings

logger = logging.getLogger(__name__)

# COCO class IDs we care about for traffic analytics
TRAFFIC_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


class VehicleDetector:
    """YOLO-based vehicle and traffic detector using COCO model."""

    def __init__(self):
        self.model = None
        self.model_path = settings.get_model_path(settings.VEHICLE_MODEL_PATH)
        self.confidence_threshold = settings.DETECTION_CONFIDENCE
        self._load_model()

    def _load_model(self):
        """Load the YOLOv8n COCO model."""
        try:
            if not self.model_path.exists():
                logger.info(
                    f"Vehicle model not found at {self.model_path}. "
                    "Attempting auto-download of yolov8n.pt..."
                )
                try:
                    from ultralytics import YOLO
                    self.model = YOLO("yolov8n.pt")
                    logger.info("Vehicle detector loaded (auto-downloaded yolov8n.pt)")
                    return
                except Exception as dl_err:
                    logger.error(f"Auto-download failed: {dl_err}")
                    return

            from ultralytics import YOLO
            self.model = YOLO(str(self.model_path))
            logger.info(f"Vehicle detector loaded from {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load vehicle model: {e}")
            self.model = None

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run vehicle/traffic detection on a frame."""
        if self.model is None:
            return []

        try:
            results = self.model(
                frame,
                conf=self.confidence_threshold,
                classes=list(TRAFFIC_CLASSES.keys()),
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

                    if cls_id not in TRAFFIC_CLASSES:
                        continue

                    cls_name = TRAFFIC_CLASSES[cls_id]

                    detection = Detection(
                        class_name=cls_name,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        detector_source="vehicle_yolo",
                        severity=compute_severity(conf, "vehicle"),
                    )
                    detections.append(detection)

            return detections

        except Exception as e:
            logger.error(f"Vehicle detection error: {e}")
            return []

    @property
    def is_available(self) -> bool:
        return self.model is not None
