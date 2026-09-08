"""
RoadSense Fleet - Frame Processor
Orchestrates AI detection pipeline on received frames:
  - Local YOLOv8 for continuous real-time vehicle detection at full stream frame rate.
  - Multi-workflow Roboflow (Road Damage, Traffic Signs, Zebra Crossing) executing
    in decoupled background tasks with configurable sampling interval and zero stream freezing.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import time
from typing import Dict, List, Optional

import cv2
import numpy as np

from app.ai import Detection
from app.ai.pothole_detector import PotholeDetector
from app.ai.road_damage_detector import RoadDamageDetector
from app.ai.roboflow_detector import RoboflowDetector
from app.ai.vehicle_detector import VehicleDetector
from app.services.snapshot_service import save_snapshot
from app.services.event_service import create_event
from app.services.stream_manager import stream_manager
from app.config import settings

logger = logging.getLogger(__name__)

# Road hazard and urban safety classes that trigger event creation
HAZARD_CLASSES = {
    "pothole",
    "road_damage",
    "crack",
    "longitudinal_crack",
    "transverse_crack",
    "alligator_crack",
    "edge_crack",
    "lateral_crack",
    "traffic_sign",
    "zebra_crossing",
}


class FrameProcessor:
    """Runs AI detection on incoming frames with decoupled remote workflow execution."""

    def __init__(self):
        self.pothole_detector = PotholeDetector()
        self.road_damage_detector = RoadDamageDetector()
        self.vehicle_detector = VehicleDetector()
        self.roboflow_detector = RoboflowDetector()
        self.last_roboflow_time: Dict[str, float] = {}
        self._roboflow_busy: Dict[str, bool] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        logger.info(
            "Frame processor initialized (vehicle=local_yolo, road_damage/signs/zebra=roboflow_multi_workflow)"
        )

    def _run_local_detectors(self, frame: np.ndarray) -> List[Detection]:
        """Run local fast detectors synchronously in thread pool."""
        all_detections = []
        try:
            all_detections.extend(self.vehicle_detector.detect(frame))
        except Exception as e:
            logger.error(f"Vehicle detector error: {e}")

        # Fallback local detectors only when Roboflow is offline or disabled
        if not self.roboflow_detector.enabled:
            try:
                all_detections.extend(self.pothole_detector.detect(frame))
            except Exception as e:
                logger.error(f"Pothole detector fallback error: {e}")

            try:
                all_detections.extend(self.road_damage_detector.detect(frame))
            except Exception as e:
                logger.error(f"Road damage detector fallback error: {e}")

        return all_detections

    async def _run_roboflow_background(
        self,
        frame: np.ndarray,
        device_id: str,
        latitude: Optional[float],
        longitude: Optional[float],
    ):
        """Asynchronously execute multi-workflow Roboflow inference in the background."""
        try:
            loop = asyncio.get_event_loop()
            roboflow_dets = await loop.run_in_executor(
                self.executor, self.roboflow_detector.detect_all, frame
            )

            if not roboflow_dets:
                return

            significant = [
                d for d in roboflow_dets
                if d.class_name in HAZARD_CLASSES or d.confidence >= 0.50
            ]

            if significant:
                snapshot_path = save_snapshot(frame, significant, device_id)
                for det in significant:
                    if det.class_name in HAZARD_CLASSES:
                        event_data = create_event(
                            device_id=device_id,
                            detection=det,
                            snapshot_path=snapshot_path,
                            latitude=latitude,
                            longitude=longitude,
                        )
                        if event_data:
                            await stream_manager.broadcast_event(event_data)

        except Exception as e:
            logger.error(f"Background Roboflow inference error for {device_id}: {e}")
        finally:
            self._roboflow_busy[device_id] = False

    async def process_frame(
        self,
        frame_bytes: bytes,
        device_id: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> List[Detection]:
        """Process a frame through the AI pipeline. Completely non-blocking for live streams."""
        try:
            # Decode JPEG
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return []

            # 1. Run local YOLO vehicle detection immediately (non-blocking for video stream)
            loop = asyncio.get_event_loop()
            detections = await loop.run_in_executor(
                self.executor, self._run_local_detectors, frame
            )

            # 2. Check Roboflow sampling throttle and dispatch non-blocking background inference
            if self.roboflow_detector.enabled:
                now = time.time()
                last_time = self.last_roboflow_time.get(device_id, 0.0)
                is_busy = self._roboflow_busy.get(device_id, False)

                if not is_busy and (now - last_time >= settings.ROBOFLOW_INTERVAL_SECONDS):
                    self._roboflow_busy[device_id] = True
                    self.last_roboflow_time[device_id] = now
                    # Launch background task on latest frame without delaying stream
                    asyncio.create_task(
                        self._run_roboflow_background(
                            frame.copy(), device_id, latitude, longitude
                        )
                    )

            # 3. Handle any significant local detections (e.g. vehicles or offline fallback)
            significant = [
                d for d in detections
                if d.class_name in HAZARD_CLASSES or d.confidence >= 0.60
            ]

            if significant:
                snapshot_path = save_snapshot(frame, significant, device_id)
                for det in significant:
                    if det.class_name in HAZARD_CLASSES:
                        event_data = create_event(
                            device_id=device_id,
                            detection=det,
                            snapshot_path=snapshot_path,
                            latitude=latitude,
                            longitude=longitude,
                        )
                        if event_data:
                            await stream_manager.broadcast_event(event_data)

            return detections

        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            return []


# Singleton
frame_processor = FrameProcessor()
