"""
RoadSense Fleet - Waterlogging Heuristic
OpenCV-based image analysis for detecting possible waterlogging.
NOT a trained AI model — uses color/reflectivity heuristics.
"""

import logging
from typing import List

import cv2
import numpy as np

from backend.app.ai import Detection, compute_severity

logger = logging.getLogger(__name__)

# Configurable thresholds
DARK_THRESHOLD = 60       # Pixels darker than this (in value channel)
REFLECT_THRESHOLD = 200   # Pixels brighter than this (potential reflection)
MIN_DARK_RATIO = 0.15     # Min ratio of dark pixels in lower half
MIN_REFLECT_RATIO = 0.03  # Min ratio of reflective pixels
BLUE_HUE_LOW = 90
BLUE_HUE_HIGH = 130


class WaterloggingHeuristic:
    """
    OpenCV heuristic for detecting waterlogged road areas.
    Analyzes the lower portion of the frame for:
    - Large dark regions (standing water absorbs light)
    - Reflective surfaces (water reflects sky/surroundings)
    - Blue-ish color dominance (water appearance)

    IMPORTANT: This is a heuristic, NOT a trained AI model.
    Results should be labeled as 'Waterlogging — Heuristic' in the UI.
    """

    def __init__(self):
        self.dark_threshold = DARK_THRESHOLD
        self.reflect_threshold = REFLECT_THRESHOLD
        self.min_dark_ratio = MIN_DARK_RATIO
        self.min_reflect_ratio = MIN_REFLECT_RATIO
        logger.info("Waterlogging heuristic initialized (OpenCV-based)")

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Analyze frame for waterlogging indicators."""
        try:
            h, w = frame.shape[:2]

            # Focus on lower half of frame (road area)
            road_region = frame[h // 2:, :]
            rh, rw = road_region.shape[:2]

            # Convert to HSV
            hsv = cv2.cvtColor(road_region, cv2.COLOR_BGR2HSV)
            hue, sat, val = cv2.split(hsv)

            # Detect dark regions (standing water)
            dark_mask = val < self.dark_threshold
            dark_ratio = np.count_nonzero(dark_mask) / (rh * rw)

            # Detect reflective regions
            reflect_mask = val > self.reflect_threshold
            reflect_ratio = np.count_nonzero(reflect_mask) / (rh * rw)

            # Detect blue-ish regions (water color)
            blue_mask = (hue > BLUE_HUE_LOW) & (hue < BLUE_HUE_HIGH) & (sat > 30)
            blue_ratio = np.count_nonzero(blue_mask) / (rh * rw)

            # Combined water indicator
            combined_mask = dark_mask | (blue_mask & reflect_mask)
            combined_ratio = np.count_nonzero(combined_mask) / (rh * rw)

            # Score calculation
            score = 0.0
            if dark_ratio > self.min_dark_ratio:
                score += dark_ratio * 0.4
            if reflect_ratio > self.min_reflect_ratio:
                score += reflect_ratio * 0.3
            if blue_ratio > 0.02:
                score += blue_ratio * 0.3

            # Normalize to 0-1 confidence
            confidence = min(score * 2.0, 0.95)

            if confidence < 0.30:
                return []

            # Find bounding box of the detected region
            contours, _ = cv2.findContours(
                combined_mask.astype(np.uint8) * 255,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE,
            )

            if not contours:
                # Fallback: entire lower region
                bbox = (0, h // 2, w, h)
            else:
                # Largest contour
                largest = max(contours, key=cv2.contourArea)
                x, y, bw, bh = cv2.boundingRect(largest)
                # Offset y by half-height since we cropped
                bbox = (x, y + h // 2, x + bw, y + h // 2 + bh)

            return [
                Detection(
                    class_name="waterlogging",
                    confidence=confidence,
                    bbox=bbox,
                    detector_source="waterlogging_heuristic",
                    severity=compute_severity(confidence, "waterlogging"),
                )
            ]

        except Exception as e:
            logger.error(f"Waterlogging heuristic error: {e}")
            return []

    @property
    def is_available(self) -> bool:
        return True  # Always available — no model needed
