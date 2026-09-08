"""
RoadSense Fleet - AI Module
Shared data structures for all detectors.
"""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    detector_source: str
    severity: str = "low"
    subtype: Optional[str] = None

    def to_dict(self):
        d = {
            "class_name": self.class_name,
            "confidence": round(self.confidence, 3),
            "bbox": list(self.bbox),
            "detector_source": self.detector_source,
            "severity": self.severity,
        }
        if self.subtype:
            d["subtype"] = self.subtype
        return d


def compute_severity(confidence: float, detection_type: str, subtype: Optional[str] = None) -> str:
    road_hazards = (
        "pothole",
        "road_damage",
        "crack",
        "alligator_crack",
        "edge_crack",
        "lateral_crack",
        "longitudinal_crack",
        "transverse_crack",
        "waterlogging",
    )

    if detection_type in road_hazards:
        if confidence >= 0.75:
            return "high"
        elif confidence >= 0.50:
            return "medium"
        else:
            return "low"

    if detection_type == "traffic_sign":
        # Critical safety signs get higher severity
        critical_signs = ("stop", "no entry", "no_entry", "no parking", "no_parking")
        sign_sub = (subtype or "").lower()
        if any(c in sign_sub for c in critical_signs):
            return "high" if confidence >= 0.70 else "medium"
        return "medium" if confidence >= 0.70 else "low"

    if detection_type == "zebra_crossing":
        return "medium" if confidence >= 0.75 else "low"

    # Default (vehicles, pedestrians, etc.)
    if confidence >= 0.85:
        return "high"
    elif confidence >= 0.60:
        return "medium"
    else:
        return "low"
