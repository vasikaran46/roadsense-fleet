"""
RoadSense Fleet - Frame Processor
Orchestrates AI inference on incoming video frames with throttling.
"""

import logging
import asyncio
from typing import List, Optional

import cv2
import numpy as np

from backend.app.ai import Detection
from backend.app.ai.pothole_detector import PotholeDetector
from backend.app.ai.road_damage_detector import RoadDamageDetector
from backend.app.ai.vehicle_detector import VehicleDetector
from backend.app.ai.waterlogging_heuristic import WaterloggingHeuristic
from backend.app.services.snapshot_service import save_snapshot
from backend.app.services.event_service import create_event
from backend.app.services.stream_manager import stream_manager
from backend.app.config import settings

logger = logging.getLogger(__name__)


class FrameProcessor:
    """Runs AI detectors on frames, creates snapshots and events."""

    def __init__(self):
        logger.info("Initializing AI detectors...")
        self.pothole_detector = PotholeDetector()
        self.road_damage_detector = RoadDamageDetector()
        self.vehicle_detector = VehicleDetector()
        self.waterlogging_heuristic = WaterloggingHeuristic()

        self._processing = False
        logger.info(
            f"Frame processor ready. Available detectors: "
            f"pothole={self.pothole_detector.is_available}, "
            f"road_damage={self.road_damage_detector.is_available}, "
            f"vehicle={self.vehicle_detector.is_available}, "
            f"waterlogging={self.waterlogging_heuristic.is_available}"
        )

    def get_status(self) -> dict:
        """Get detector availability status."""
        return {
            "pothole": self.pothole_detector.is_available,
            "road_damage": self.road_damage_detector.is_available,
            "vehicle": self.vehicle_detector.is_available,
            "waterlogging": self.waterlogging_heuristic.is_available,
        }

    async def process_frame(self, device_id: str, frame_bytes: bytes) -> List[dict]:
        """
        Decode and process a frame through all detectors.
        Creates snapshots and events for valid detections.
        Returns list of created event dicts.
        """
        if self._processing:
            return []  # Skip if already processing

        self._processing = True
        try:
            # Decode JPEG frame
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                logger.warning(f"Failed to decode frame from {device_id}")
                return []

            # Run all detectors concurrently via thread pool
            loop = asyncio.get_event_loop()
            all_detections = await loop.run_in_executor(
                None, self._run_detectors, frame
            )

            if not all_detections:
                return []

            # Get device GPS
            lat, lon = stream_manager.get_device_gps(device_id)

            # Process road-hazard detections (create events + snapshots)
            # Vehicle detections are counted but don't create individual events
            created_events = []
            road_hazards = [
                d for d in all_detections
                if d.detector_source != "vehicle_yolo"
            ]
            vehicle_detections = [
                d for d in all_detections
                if d.detector_source == "vehicle_yolo"
            ]

            # Create events for road hazards
            for detection in road_hazards:
                snapshot_file = await loop.run_in_executor(
                    None, save_snapshot, frame, [detection]
                )

                if snapshot_file:
                    event_data = create_event(
                        device_id=device_id,
                        detection=detection,
                        snapshot_filename=snapshot_file,
                        latitude=lat,
                        longitude=lon,
                    )

                    if event_data:
                        created_events.append(event_data)
                        # Push to admin viewers in real-time
                        await stream_manager.broadcast_event(event_data)
                        await stream_manager.broadcast_detection_to_viewers(
                            device_id, event_data
                        )

            # Create a single vehicle count event periodically (not per-vehicle)
            if vehicle_detections:
                vehicle_summary = self._summarize_vehicles(vehicle_detections)
                # Broadcast vehicle count to viewers but don't create DB events for each
                await stream_manager.broadcast_detection_to_viewers(
                    device_id,
                    {
                        "type": "vehicle_count",
                        "data": vehicle_summary,
                        "device_id": device_id,
                    },
                )

            return created_events

        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            return []
        finally:
            self._processing = False

    def _run_detectors(self, frame: np.ndarray) -> List[Detection]:
        """Run all detectors synchronously (called from thread pool)."""
        all_detections = []

        # Pothole detection
        try:
            all_detections.extend(self.pothole_detector.detect(frame))
        except Exception as e:
            logger.error(f"Pothole detector failed: {e}")

        # Road damage detection
        try:
            all_detections.extend(self.road_damage_detector.detect(frame))
        except Exception as e:
            logger.error(f"Road damage detector failed: {e}")

        # Vehicle detection
        try:
            all_detections.extend(self.vehicle_detector.detect(frame))
        except Exception as e:
            logger.error(f"Vehicle detector failed: {e}")

        # Waterlogging heuristic
        try:
            all_detections.extend(self.waterlogging_heuristic.detect(frame))
        except Exception as e:
            logger.error(f"Waterlogging heuristic failed: {e}")

        return all_detections

    def _summarize_vehicles(self, detections: List[Detection]) -> dict:
        """Summarize vehicle detections into counts by type."""
        counts = {}
        for d in detections:
            counts[d.class_name] = counts.get(d.class_name, 0) + 1
        return counts


# Singleton
frame_processor = FrameProcessor()
