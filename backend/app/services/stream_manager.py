"""
RoadSense Fleet - Stream Manager
In-memory state manager for connected devices and admin viewers.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class StreamManager:
    """Manages connected streaming devices and admin viewers in memory."""

    def __init__(self):
        # device_id -> device state dict
        self.devices: Dict[str, Dict[str, Any]] = {}
        # device_id -> list of admin WebSocket connections watching this device
        self.admin_viewers: Dict[str, List[WebSocket]] = {}
        # Global admin event subscribers (for real-time event push)
        self.event_subscribers: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def register_device(self, device_id: str, websocket: WebSocket, name: str = None):
        """Register a streaming device connection."""
        async with self._lock:
            self.devices[device_id] = {
                "websocket": websocket,
                "name": name or device_id,
                "status": "online",
                "latitude": None,
                "longitude": None,
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "frame_count": 0,
                "latest_frame": None,
            }
        logger.info(f"Device registered: {device_id}")

    async def unregister_device(self, device_id: str):
        """Remove a streaming device on disconnect."""
        async with self._lock:
            if device_id in self.devices:
                del self.devices[device_id]
            # Cleanup admin viewers for this device
            if device_id in self.admin_viewers:
                for ws in self.admin_viewers[device_id]:
                    try:
                        await ws.close()
                    except Exception:
                        pass
                del self.admin_viewers[device_id]
        logger.info(f"Device unregistered: {device_id}")

    async def update_device_gps(self, device_id: str, lat: float, lon: float):
        """Update device GPS coordinates."""
        if device_id in self.devices:
            self.devices[device_id]["latitude"] = lat
            self.devices[device_id]["longitude"] = lon
            self.devices[device_id]["last_seen"] = datetime.now(timezone.utc).isoformat()

    async def update_device_frame(self, device_id: str, frame_bytes: bytes):
        """Store latest frame and relay to admin viewers."""
        if device_id not in self.devices:
            return

        self.devices[device_id]["latest_frame"] = frame_bytes
        self.devices[device_id]["frame_count"] += 1
        self.devices[device_id]["last_seen"] = datetime.now(timezone.utc).isoformat()

        # Relay to admin viewers watching this device
        await self._relay_frame_to_viewers(device_id, frame_bytes)

    async def _relay_frame_to_viewers(self, device_id: str, frame_bytes: bytes):
        """Send frame to all admin clients watching this device."""
        if device_id not in self.admin_viewers:
            return

        disconnected = []
        for ws in self.admin_viewers[device_id]:
            try:
                await ws.send_bytes(frame_bytes)
            except Exception:
                disconnected.append(ws)

        # Cleanup disconnected viewers
        for ws in disconnected:
            self.admin_viewers[device_id].remove(ws)

    async def subscribe_viewer(self, device_id: str, websocket: WebSocket):
        """Admin subscribes to watch a device's stream."""
        async with self._lock:
            if device_id not in self.admin_viewers:
                self.admin_viewers[device_id] = []
            self.admin_viewers[device_id].append(websocket)
        logger.info(f"Admin viewer subscribed to {device_id}")

    async def unsubscribe_viewer(self, device_id: str, websocket: WebSocket):
        """Remove admin viewer subscription."""
        async with self._lock:
            if device_id in self.admin_viewers:
                if websocket in self.admin_viewers[device_id]:
                    self.admin_viewers[device_id].remove(websocket)
        logger.info(f"Admin viewer unsubscribed from {device_id}")

    async def subscribe_events(self, websocket: WebSocket):
        """Admin subscribes to real-time event notifications."""
        async with self._lock:
            self.event_subscribers.append(websocket)
        logger.info("Admin event subscriber connected")

    async def unsubscribe_events(self, websocket: WebSocket):
        """Remove admin event subscriber."""
        async with self._lock:
            if websocket in self.event_subscribers:
                self.event_subscribers.remove(websocket)

    async def broadcast_event(self, event_data: dict):
        """Push a new detection event to all admin event subscribers."""
        disconnected = []
        import json
        message = json.dumps({"type": "new_event", "data": event_data})

        for ws in self.event_subscribers:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.event_subscribers.remove(ws)

    async def broadcast_detection_to_viewers(self, device_id: str, detection_data: dict):
        """Push detection notification to admin viewers of a specific device."""
        if device_id not in self.admin_viewers:
            return

        import json
        message = json.dumps({"type": "detection", "data": detection_data})

        disconnected = []
        for ws in self.admin_viewers[device_id]:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.admin_viewers[device_id].remove(ws)

    def get_device_info(self, device_id: str) -> Optional[Dict]:
        """Get device info (excluding websocket and frame bytes)."""
        if device_id not in self.devices:
            return None
        dev = self.devices[device_id]
        return {
            "device_id": device_id,
            "name": dev["name"],
            "status": dev["status"],
            "latitude": dev["latitude"],
            "longitude": dev["longitude"],
            "last_seen": dev["last_seen"],
            "frame_count": dev["frame_count"],
        }

    def get_all_devices(self) -> Dict[str, Dict]:
        """Get info for all connected devices."""
        return {
            did: {
                "name": d["name"],
                "status": d["status"],
                "latitude": d["latitude"],
                "longitude": d["longitude"],
                "last_seen": d["last_seen"],
                "frame_count": d["frame_count"],
            }
            for did, d in self.devices.items()
        }

    def get_device_gps(self, device_id: str) -> tuple:
        """Get latest GPS for a device."""
        if device_id in self.devices:
            dev = self.devices[device_id]
            return dev.get("latitude"), dev.get("longitude")
        return None, None

    def is_device_online(self, device_id: str) -> bool:
        return device_id in self.devices


# Singleton instance
stream_manager = StreamManager()
