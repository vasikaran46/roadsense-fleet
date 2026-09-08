"""
RoadSense Fleet - AI Module
Shared data structures for all detectors.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class Detection:
    """A single detection result from any detector."""
    class_name: str          # e.g. "pothole", "crack", "car"
    confidence: float        # 0.0 to 1.0
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    detector_source: str     # e.g. "pothole_yolo", "vehicle_yolo", "waterlogging_heuristic"
    severity: str = "low"    # high / medium / low

    def to_dict(self):
        return {
            "class_name": self.class_name,
            "confidence": round(self.confidence, 3),
            "bbox": list(self.bbox),
            "detector_source": self.detector_source,
            "severity": self.severity,
        }


def compute_severity(confidence: float, detection_type: str) -> str:
    """Determine severity based on confidence and detection type."""
    # Road hazards (potholes, damage) are weighted higher
    if detection_type in ("pothole", "road_damage", "crack", "waterlogging"):
        if confidence >= 0.75:
            return "high"
        elif confidence >= 0.50:
            return "medium"
        else:
            return "low"
    else:
        # Vehicles and other detections
        if confidence >= 0.85:
            return "high"
        elif confidence >= 0.60:
            return "medium"
        else:
            return "low"
