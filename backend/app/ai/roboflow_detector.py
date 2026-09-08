"""
RoadSense Fleet - Multi-Workflow Roboflow Detector
Supports 3 hosted Roboflow Serverless Workflows:
  1. Road Damage (potholes, alligator cracking, edge cracking, lateral/longitudinal cracks)
  2. Traffic / Safety Signs (stop, no entry, roundabout, pedestrian crossing, no parking)
  3. Zebra Crossing (pedestrian zebra crossings)

API key is securely loaded from environment variable ROBOFLOW_API_KEY.
"""

import base64
from concurrent.futures import ThreadPoolExecutor
import logging
from typing import Dict, List, Optional

import cv2
import numpy as np
import requests

from app.ai import Detection, compute_severity
from app.config import settings

logger = logging.getLogger(__name__)

# Road damage classes mapping
ROAD_DAMAGE_CLASSES = "pothole, Alligator, Edge Cracking, Lateral-Crack, Longitudinal-Crack"
ROAD_DAMAGE_MAPPING = {
    "pothole": ("pothole", None),
    "alligator": ("alligator_crack", None),
    "alligator crack": ("alligator_crack", None),
    "alligator_crack": ("alligator_crack", None),
    "edge cracking": ("edge_crack", None),
    "edge crack": ("edge_crack", None),
    "edge_crack": ("edge_crack", None),
    "lateral-crack": ("lateral_crack", None),
    "lateral crack": ("lateral_crack", None),
    "lateral_crack": ("lateral_crack", None),
    "longitudinal-crack": ("longitudinal_crack", None),
    "longitudinal crack": ("longitudinal_crack", None),
    "longitudinal_crack": ("longitudinal_crack", None),
}

# Traffic signs classes mapping
TRAFFIC_SIGN_CLASSES = "stop, no entry, roundabout, pedestrian crossing, no parking"
TRAFFIC_SIGN_MAPPING = {
    "stop": ("traffic_sign", "stop"),
    "no entry": ("traffic_sign", "no_entry"),
    "no_entry": ("traffic_sign", "no_entry"),
    "roundabout": ("traffic_sign", "roundabout"),
    "pedestrian crossing": ("traffic_sign", "pedestrian_crossing"),
    "pedestrian_crossing": ("traffic_sign", "pedestrian_crossing"),
    "no parking": ("traffic_sign", "no_parking"),
    "no_parking": ("traffic_sign", "no_parking"),
}

# Zebra crossing classes mapping
ZEBRA_CROSSING_CLASSES = "zebra crossing, zebra crossing - v1 2025-01-24 3:08am"


class RoboflowDetector:
    """Orchestrates road damage, traffic sign, and zebra crossing inference via Roboflow Workflows."""

    def __init__(self):
        self.api_url = (settings.ROBOFLOW_API_URL or "https://serverless.roboflow.com").rstrip("/")
        self.api_key = settings.ROBOFLOW_API_KEY
        self.workspace = settings.ROBOFLOW_WORKSPACE or "vasikaran-a"
        self.road_damage_workflow = settings.ROBOFLOW_ROAD_DAMAGE_WORKFLOW or "general-segmentation-api"
        self.traffic_sign_workflow = settings.ROBOFLOW_TRAFFIC_SIGN_WORKFLOW or "general-segmentation-api-2"
        self.zebra_crossing_workflow = settings.ROBOFLOW_ZEBRA_CROSSING_WORKFLOW or "general-segmentation-api-3"
        self.enabled = settings.ROBOFLOW_ENABLED and bool(self.api_key)

        self.session = requests.Session()
        self._warned_missing_key = False

        if self.enabled:
            logger.info(
                f"Multi-Workflow Roboflow Detector initialized (workspace='{self.workspace}', "
                f"workflows: road_damage='{self.road_damage_workflow}', "
                f"traffic_signs='{self.traffic_sign_workflow}', "
                f"zebra_crossing='{self.zebra_crossing_workflow}')"
            )
        else:
            logger.warning(
                "Roboflow API key not configured or ROBOFLOW_ENABLED=false. Remote detection disabled."
            )

    def _prepare_image(self, frame: np.ndarray):
        """Scale and encode image to JPEG base64 payload under 200KB."""
        h_orig, w_orig = frame.shape[:2]
        target_w = min(640, w_orig)
        target_h = int(h_orig * (target_w / w_orig))

        if target_w != w_orig:
            resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
        else:
            resized = frame

        scale_x = w_orig / target_w
        scale_y = h_orig / target_h

        success, buffer = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not success:
            return None, 1.0, 1.0, w_orig, h_orig

        b64_str = base64.b64encode(buffer).decode("utf-8")
        return b64_str, scale_x, scale_y, w_orig, h_orig

    def _invoke_workflow(
        self,
        workflow_id: str,
        classes_str: str,
        b64_img: str,
        scale_x: float,
        scale_y: float,
        w_orig: int,
        h_orig: int,
        class_mapper,
        source_label: str,
    ) -> List[Detection]:
        """Send HTTP POST request to Roboflow workflow execution endpoint."""
        if not self.enabled or not self.api_key:
            if not self._warned_missing_key:
                logger.warning("Roboflow API key missing. Set ROBOFLOW_API_KEY environment variable.")
                self._warned_missing_key = True
            return []

        url = f"{self.api_url}/infer/workflows/{self.workspace}/{workflow_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "api_key": self.api_key,
            "inputs": {
                "image": {"type": "base64", "value": b64_img},
                "classes": classes_str,
            },
            "parameters": {
                "classes": classes_str,
            },
            "use_cache": True,
        }

        try:
            response = self.session.post(url, headers=headers, json=payload, timeout=12)
            if response.status_code != 200:
                logger.warning(
                    f"Roboflow [{workflow_id}] status {response.status_code}: {response.text[:180]}"
                )
                return []

            data = response.json()
            outputs = data.get("outputs", [])
            if not outputs:
                return []

            preds_block = outputs[0].get("predictions", {})
            predictions = preds_block.get("predictions", [])
            detections = []

            for p in predictions:
                conf = float(p.get("confidence", 0.0))
                if conf < settings.DETECTION_CONFIDENCE:
                    continue

                raw_cls = str(p.get("class") or p.get("class_name") or "").strip()
                cls_name, subtype = class_mapper(raw_cls)

                # Center coords in resized image
                x = float(p.get("x", 0.0))
                y = float(p.get("y", 0.0))
                w = float(p.get("width", 0.0))
                h = float(p.get("height", 0.0))

                # Rescale to original frame
                x_orig = x * scale_x
                y_orig = y * scale_y
                w_orig_box = w * scale_x
                h_orig_box = h * scale_y

                x1 = max(0, int(x_orig - w_orig_box / 2))
                y1 = max(0, int(y_orig - h_orig_box / 2))
                x2 = min(w_orig, int(x_orig + w_orig_box / 2))
                y2 = min(h_orig, int(y_orig + h_orig_box / 2))

                severity = compute_severity(conf, cls_name, subtype)

                detections.append(
                    Detection(
                        class_name=cls_name,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        detector_source=source_label,
                        severity=severity,
                        subtype=subtype,
                    )
                )

            return detections

        except Exception as e:
            logger.error(f"Roboflow [{workflow_id}] inference error: {e}")
            return []

    # ── 1. Road Damage Workflow ──────────────────────────────────────────────
    def detect_road_damage(self, frame: np.ndarray) -> List[Detection]:
        """Detect potholes and cracking via Workflow 1."""
        b64_img, scale_x, scale_y, w_orig, h_orig = self._prepare_image(frame)
        if not b64_img:
            return []

        def mapper(raw_cls: str):
            key = raw_cls.lower().strip()
            return ROAD_DAMAGE_MAPPING.get(key, (key.replace("-", "_").replace(" ", "_"), None))

        return self._invoke_workflow(
            workflow_id=self.road_damage_workflow,
            classes_str=ROAD_DAMAGE_CLASSES,
            b64_img=b64_img,
            scale_x=scale_x,
            scale_y=scale_y,
            w_orig=w_orig,
            h_orig=h_orig,
            class_mapper=mapper,
            source_label="roboflow_road_damage",
        )

    # ── 2. Traffic Sign Workflow ─────────────────────────────────────────────
    def detect_traffic_signs(self, frame: np.ndarray) -> List[Detection]:
        """Detect traffic & safety signs via Workflow 2."""
        b64_img, scale_x, scale_y, w_orig, h_orig = self._prepare_image(frame)
        if not b64_img:
            return []

        def mapper(raw_cls: str):
            key = raw_cls.lower().strip()
            return TRAFFIC_SIGN_MAPPING.get(key, ("traffic_sign", key.replace(" ", "_")))

        return self._invoke_workflow(
            workflow_id=self.traffic_sign_workflow,
            classes_str=TRAFFIC_SIGN_CLASSES,
            b64_img=b64_img,
            scale_x=scale_x,
            scale_y=scale_y,
            w_orig=w_orig,
            h_orig=h_orig,
            class_mapper=mapper,
            source_label="roboflow_traffic_signs",
        )

    # ── 3. Zebra Crossing Workflow ───────────────────────────────────────────
    def detect_zebra_crossing(self, frame: np.ndarray) -> List[Detection]:
        """Detect pedestrian zebra crossings via Workflow 3."""
        b64_img, scale_x, scale_y, w_orig, h_orig = self._prepare_image(frame)
        if not b64_img:
            return []

        def mapper(raw_cls: str):
            # Both "zebra crossing" and versioned tags normalize to zebra_crossing
            return ("zebra_crossing", "pedestrian_crossing")

        return self._invoke_workflow(
            workflow_id=self.zebra_crossing_workflow,
            classes_str=ZEBRA_CROSSING_CLASSES,
            b64_img=b64_img,
            scale_x=scale_x,
            scale_y=scale_y,
            w_orig=w_orig,
            h_orig=h_orig,
            class_mapper=mapper,
            source_label="roboflow_zebra_crossing",
        )

    # ── Orchestrator: Detect All ─────────────────────────────────────────────
    def detect_all(self, frame: np.ndarray) -> List[Detection]:
        """Runs road damage, traffic sign, and zebra crossing workflows concurrently."""
        if not self.enabled or frame is None:
            return []

        all_detections = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_road = executor.submit(self.detect_road_damage, frame)
            future_sign = executor.submit(self.detect_traffic_signs, frame)
            future_zebra = executor.submit(self.detect_zebra_crossing, frame)

            try:
                all_detections.extend(future_road.result())
            except Exception as e:
                logger.error(f"Road damage execution error: {e}")

            try:
                all_detections.extend(future_sign.result())
            except Exception as e:
                logger.error(f"Traffic sign execution error: {e}")

            try:
                all_detections.extend(future_zebra.result())
            except Exception as e:
                logger.error(f"Zebra crossing execution error: {e}")

        return all_detections
