"""
RoadSense Fleet - Stream Manager
In-memory state for active device streams and admin viewers.
"""

import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class StreamManager:
    """Manages connected device streams and admin viewer subscriptions."""

    def __init__(self):
        # device_id -> { websocket, name, latitude, longitude, frame_count, latest_frame }
        self.devices: Dict[str, dict] = {}
        # device_id -> set of admin WebSocket connections
        self.admin_viewers: Dict[str, Set[WebSocket]] = {}
        # Admin event subscribers (receive all detection events)
        self.event_subscribers: Set[WebSocket] = set()

    def register_device(self, device_id: str, websocket: WebSocket, name: str = ""):
        self.devices[device_id] = {
            "websocket": websocket,
            "name": name,
            "latitude": None,
            "longitude": None,
            "frame_count": 0,
            "latest_frame": None,
        }
        logger.info(f"Device registered: {device_id}")

    def unregister_device(self, device_id: str):
        self.devices.pop(device_id, None)
        logger.info(f"Device unregistered: {device_id}")

    def update_device_gps(self, device_id: str, lat: float, lon: float):
        if device_id in self.devices:
            self.devices[device_id]["latitude"] = lat
            self.devices[device_id]["longitude"] = lon

    def update_device_frame(self, device_id: str, frame_bytes: bytes):
        if device_id in self.devices:
            self.devices[device_id]["latest_frame"] = frame_bytes
            self.devices[device_id]["frame_count"] += 1

    def subscribe_viewer(self, device_id: str, websocket: WebSocket):
        if device_id not in self.admin_viewers:
            self.admin_viewers[device_id] = set()
        self.admin_viewers[device_id].add(websocket)
        logger.info(f"Admin viewer subscribed to {device_id}")

    def unsubscribe_viewer(self, device_id: str, websocket: WebSocket):
        if device_id in self.admin_viewers:
            self.admin_viewers[device_id].discard(websocket)

    async def relay_frame(self, device_id: str, frame_bytes: bytes):
        """Relay a video frame to all admin viewers watching this device."""
        viewers = self.admin_viewers.get(device_id, set()).copy()
        dead = set()
        for ws in viewers:
            try:
                await ws.send_bytes(frame_bytes)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.admin_viewers.get(device_id, set()).discard(ws)

    async def broadcast_event(self, event_data: dict):
        """Push a detection event to all admin event subscribers."""
        dead = set()
        import json
        message = json.dumps({"type": "new_event", "data": event_data})
        for ws in self.event_subscribers.copy():
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.event_subscribers.discard(ws)

    def subscribe_events(self, websocket: WebSocket):
        self.event_subscribers.add(websocket)

    def unsubscribe_events(self, websocket: WebSocket):
        self.event_subscribers.discard(websocket)


# Singleton
stream_manager = StreamManager()
