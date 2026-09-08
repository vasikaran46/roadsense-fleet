"""
RoadSense Fleet - Stream Relay WebSocket
Relays a device's video stream to admin viewers.
Also provides a global event notification WebSocket.
"""

import logging
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.services.stream_manager import stream_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/watch/{device_id}")
async def stream_watch(websocket: WebSocket, device_id: str):
    """
    Admin connects here to watch a specific device's live stream.
    Receives:
    - Binary messages: JPEG frames relayed from the device
    - Text messages: JSON detection notifications
    """
    await websocket.accept()
    logger.info(f"Admin viewer connected for device: {device_id}")

    # Subscribe to this device's stream
    await stream_manager.subscribe_viewer(device_id, websocket)

    # Send initial device info
    device_info = stream_manager.get_device_info(device_id)
    if device_info:
        await websocket.send_text(json.dumps({
            "type": "device_info",
            "data": device_info,
        }))
    else:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Device {device_id} is not currently streaming",
        }))

    try:
        # Keep connection alive and listen for admin commands
        while True:
            data = await websocket.receive_text()
            # Admin could send commands like "ping"
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        logger.info(f"Admin viewer disconnected for {device_id}")
    except Exception as e:
        logger.error(f"Admin viewer error for {device_id}: {e}")
    finally:
        await stream_manager.unsubscribe_viewer(device_id, websocket)


@router.websocket("/ws/events")
async def event_stream(websocket: WebSocket):
    """
    Admin dashboard connects here to receive real-time event notifications.
    All new detection events are pushed through this WebSocket.
    """
    await websocket.accept()
    logger.info("Admin event stream connected")

    await stream_manager.subscribe_events(websocket)

    try:
        while True:
            # Keep alive — listen for pings
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        logger.info("Admin event stream disconnected")
    except Exception as e:
        logger.error(f"Admin event stream error: {e}")
    finally:
        await stream_manager.unsubscribe_events(websocket)
