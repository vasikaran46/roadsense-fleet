"""
RoadSense Fleet - Stream Ingestion WebSocket
Receives video frames from mobile devices.
"""

import logging
import json
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.services.stream_manager import stream_manager
from backend.app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/stream/{device_id}")
async def stream_ingest(websocket: WebSocket, device_id: str):
    """
    WebSocket endpoint for device video streaming.

    The device sends:
    - Binary messages: JPEG frame data
    - Text messages: JSON with GPS/metadata updates
      {"type": "gps", "latitude": 13.08, "longitude": 80.27}
      {"type": "info", "name": "Route 21G Mobile"}
    """
    # Validate device ID
    if not device_id or len(device_id) > 100:
        await websocket.close(code=4001, reason="Invalid device ID")
        return

    await websocket.accept()
    logger.info(f"Stream connection opened: {device_id}")

    # Register device
    await stream_manager.register_device(device_id, websocket)

    frame_count = 0
    process_interval = settings.FRAME_PROCESS_INTERVAL

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            # Handle text messages (GPS/metadata)
            if "text" in message:
                try:
                    data = json.loads(message["text"])
                    msg_type = data.get("type", "")

                    if msg_type == "gps":
                        lat = data.get("latitude")
                        lon = data.get("longitude")
                        if lat is not None and lon is not None:
                            await stream_manager.update_device_gps(
                                device_id, float(lat), float(lon)
                            )

                    elif msg_type == "info":
                        name = data.get("name", device_id)
                        if device_id in stream_manager.devices:
                            stream_manager.devices[device_id]["name"] = name

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from {device_id}")
                continue

            # Handle binary messages (video frames)
            if "bytes" in message:
                frame_bytes = message["bytes"]

                # Validate frame size (max 5MB)
                if len(frame_bytes) > 5 * 1024 * 1024:
                    logger.warning(f"Frame too large from {device_id}: {len(frame_bytes)} bytes")
                    continue

                frame_count += 1

                # Update latest frame and relay to viewers
                await stream_manager.update_device_frame(device_id, frame_bytes)

                # Process every Nth frame for AI detection
                if frame_count % process_interval == 0:
                    # Run detection in background to not block stream
                    asyncio.create_task(
                        _process_frame_safe(device_id, frame_bytes)
                    )

    except WebSocketDisconnect:
        logger.info(f"Stream disconnected: {device_id}")
    except Exception as e:
        logger.error(f"Stream error for {device_id}: {e}")
    finally:
        await stream_manager.unregister_device(device_id)
        logger.info(f"Stream cleanup complete: {device_id}")


async def _process_frame_safe(device_id: str, frame_bytes: bytes):
    """Process a frame for AI detection without crashing the stream."""
    try:
        from backend.app.services.frame_processor import frame_processor
        await frame_processor.process_frame(device_id, frame_bytes)
    except Exception as e:
        logger.error(f"Background frame processing error for {device_id}: {e}")
