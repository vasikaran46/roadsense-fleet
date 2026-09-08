"""
RoadSense Fleet - Stream Relay WebSocket
Relays live video to admin viewers and pushes detection events.
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.stream_manager import stream_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/watch/{device_id}")
async def watch_stream(websocket: WebSocket, device_id: str):
    """Admin watches a device's live stream."""
    await websocket.accept()
    logger.info(f"Admin viewer connected for device: {device_id}")

    stream_manager.subscribe_viewer(device_id, websocket)

    # Send device info if available
    if device_id in stream_manager.devices:
        state = stream_manager.devices[device_id]
        await websocket.send_text(json.dumps({
            "type": "device_info",
            "data": {
                "device_id": device_id,
                "name": state.get("name", ""),
                "frame_count": state.get("frame_count", 0),
            }
        }))

    try:
        while True:
            # Keep connection alive — listen for pings
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except (json.JSONDecodeError, KeyError):
                pass
    except WebSocketDisconnect:
        logger.info(f"Admin viewer disconnected from {device_id}")
    except Exception as e:
        logger.error(f"Watch error: {e}")
    finally:
        stream_manager.unsubscribe_viewer(device_id, websocket)


@router.websocket("/ws/events")
async def event_feed(websocket: WebSocket):
    """Admin subscribes to real-time detection events."""
    await websocket.accept()
    logger.info("Admin event subscriber connected")

    stream_manager.subscribe_events(websocket)

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except (json.JSONDecodeError, KeyError):
                pass
    except WebSocketDisconnect:
        logger.info("Admin event subscriber disconnected")
    except Exception as e:
        logger.error(f"Event feed error: {e}")
    finally:
        stream_manager.unsubscribe_events(websocket)
