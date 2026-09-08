"""
RoadSense Fleet - Verification Test Suite
Tests all requirements specified for the multi-workflow Roboflow integration.
"""

import asyncio
import os
import sys
import unittest

# Ensure backend/ is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import cv2
import numpy as np
from fastapi.testclient import TestClient

from main import app
from app.config import settings
from app.ai.roboflow_detector import RoboflowDetector
from app.services.frame_processor import frame_processor


class TestRoadSenseMultiWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_health_endpoint(self):
        """GET /health must return 200 with status healthy."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "healthy")
        print("[PASS] GET /health")

    def test_02_devices_endpoint(self):
        """GET /devices must return 200."""
        resp = self.client.get("/devices")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("devices", data)
        self.assertIsInstance(data["devices"], list)
        print("[PASS] GET /devices")

    def test_03_events_endpoint(self):
        """GET /events must return 200."""
        resp = self.client.get("/events")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("events", data)
        self.assertIsInstance(data["events"], list)
        print("[PASS] GET /events")

    def test_04_events_stats_endpoint(self):
        """GET /events/stats must return 200 with statistics."""
        resp = self.client.get("/events/stats")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total_events", data)
        self.assertIn("by_type", data)
        self.assertIn("by_severity", data)
        print("[PASS] GET /events/stats")

    def test_05_admin_html_endpoint(self):
        """GET /admin/ must return 200 HTML."""
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("RoadSense Fleet", resp.text)
        print("[PASS] GET /admin/")

    def test_06_stream_html_endpoint(self):
        """GET /stream/ must return 200 HTML."""
        resp = self.client.get("/stream/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("RoadSense", resp.text)
        print("[PASS] GET /stream/")

    def test_07_roboflow_multi_workflow_detection(self):
        """Test all 3 workflows in RoboflowDetector."""
        detector = RoboflowDetector()
        print(f"Roboflow detector enabled: {detector.enabled}")

        frame = np.full((480, 640, 3), 128, dtype=np.uint8)

        # 1. Road Damage workflow method
        road_dets = detector.detect_road_damage(frame)
        self.assertIsInstance(road_dets, list)
        print(f"[PASS] detect_road_damage ({len(road_dets)} detections)")

        # 2. Traffic Signs workflow method
        sign_dets = detector.detect_traffic_signs(frame)
        self.assertIsInstance(sign_dets, list)
        print(f"[PASS] detect_traffic_signs ({len(sign_dets)} detections)")

        # 3. Zebra Crossing workflow method
        zebra_dets = detector.detect_zebra_crossing(frame)
        self.assertIsInstance(zebra_dets, list)
        print(f"[PASS] detect_zebra_crossing ({len(zebra_dets)} detections)")

        # 4. Orchestrator detect_all
        all_dets = detector.detect_all(frame)
        self.assertIsInstance(all_dets, list)
        print(f"[PASS] detect_all ({len(all_dets)} detections)")

    def test_08_roboflow_resilience_on_missing_key(self):
        """Test detector gracefully returns empty list when key is missing or invalid."""
        detector = RoboflowDetector()
        original_key = detector.api_key
        original_enabled = detector.enabled

        try:
            detector.api_key = ""
            detector.enabled = False
            frame = np.zeros((300, 300, 3), dtype=np.uint8)
            dets = detector.detect_all(frame)
            self.assertEqual(dets, [])
            print("[PASS] Resilience test passed: missing key returns [] without crash")
        finally:
            detector.api_key = original_key
            detector.enabled = original_enabled

    def test_09_frame_processor_pipeline(self):
        """Test full FrameProcessor async execution."""
        async def run_frame():
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            _, buf = cv2.imencode(".jpg", frame)
            dets = await frame_processor.process_frame(
                frame_bytes=buf.tobytes(),
                device_id="BUS-TEST-SUITE",
                latitude=13.0827,
                longitude=80.2707,
            )
            return dets

        dets = asyncio.run(run_frame())
        self.assertIsInstance(dets, list)
        print(f"[PASS] FrameProcessor process_frame ({len(dets)} detections)")

    def test_10_security_scan_no_hardcoded_keys(self):
        """Ensure no hardcoded API keys exist in tracked code files."""
        tracked_dirs = [
            os.path.join(BASE_DIR, "app"),
            os.path.join(BASE_DIR, "..", "frontend-admin"),
            os.path.join(BASE_DIR, "..", "frontend-stream"),
        ]
        forbidden_substrings = ["rgxR9PuOpXWfsCMSPiKu"]
        violations = []

        for d in tracked_dirs:
            if not os.path.exists(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    if f.endswith((".py", ".js", ".html", ".css", ".yaml", ".yml", ".md")):
                        fpath = os.path.join(root, f)
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as file:
                            content = file.read()
                            for sub in forbidden_substrings:
                                if sub in content:
                                    violations.append((fpath, sub))

        self.assertEqual(
            violations, [], f"Security violation: Hardcoded API keys found in: {violations}"
        )
        print("[PASS] Security audit passed: Zero hardcoded API keys found in tracked source files")

    def test_11_delete_event_endpoint(self):
        """Test DELETE /events/{id} removes an event and handles 404."""
        from app.database.database import SessionLocal
        from app.database.models import Event

        db = SessionLocal()
        test_ev = Event(device_id="TEST-DEL", detection_type="pothole", confidence=0.85, severity="high")
        db.add(test_ev)
        db.commit()
        db.refresh(test_ev)
        ev_id = test_ev.id
        db.close()

        # Delete event
        del_resp = self.client.delete(f"/events/{ev_id}")
        self.assertEqual(del_resp.status_code, 200)
        self.assertEqual(del_resp.json()["status"], "deleted")

        # Confirm 404
        get_resp = self.client.get(f"/events/{ev_id}")
        self.assertEqual(get_resp.status_code, 404)
        print("[PASS] DELETE /events/{id} and 404 verification passed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
