"""
RoadSense Fleet - Stream Ingestion WebSocket
Receives video frames and GPS data from mobile devices.
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.stream_manager import stream_manager
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/stream/{device_id}")
async def stream_ingest(websocket: WebSocket, device_id: str):
    """Receive video stream from a device."""
    await websocket.accept()
    logger.info(f"Stream connection from device: {device_id}")

    # Get device name from query params
    device_name = websocket.query_params.get("name", device_id)

    # Register device
    stream_manager.register_device(device_id, websocket, device_name)

    # Register/update device in DB
    try:
        from app.database.database import SessionLocal
        from app.database.models import Device
        db = SessionLocal()
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            device = Device(device_id=device_id, name=device_name, status="online")
            db.add(device)
        else:
            device.status = "online"
            device.name = device_name
            device.last_seen = datetime.utcnow()
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"DB device registration error: {e}")

    frame_count = 0
    latitude = None
    longitude = None

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"]:
                # Binary frame (JPEG)
                frame_bytes = message["bytes"]
                frame_count += 1
                stream_manager.update_device_frame(device_id, frame_bytes)

                # Relay to admin viewers
                await stream_manager.relay_frame(device_id, frame_bytes)

                # Process every Nth frame with AI
                if frame_count % settings.FRAME_PROCESS_INTERVAL == 0:
                    try:
                        from app.services.frame_processor import frame_processor
                        await frame_processor.process_frame(
                            frame_bytes, device_id, latitude, longitude
                        )
                    except Exception as e:
                        logger.error(f"AI processing error: {e}")

            elif "text" in message and message["text"]:
                # JSON message (GPS update, metadata)
                try:
                    data = json.loads(message["text"])
                    msg_type = data.get("type", "")

                    if msg_type == "gps":
                        latitude = data.get("latitude")
                        longitude = data.get("longitude")
                        if latitude and longitude:
                            stream_manager.update_device_gps(device_id, latitude, longitude)

                    elif msg_type == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))

                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        logger.info(f"Device disconnected: {device_id}")
    except Exception as e:
        logger.error(f"Stream error for {device_id}: {e}")
    finally:
        stream_manager.unregister_device(device_id)
        # Mark device offline
        try:
            from app.database.database import SessionLocal
            from app.database.models import Device
            db = SessionLocal()
            device = db.query(Device).filter(Device.device_id == device_id).first()
            if device:
                device.status = "offline"
                device.last_seen = datetime.utcnow()
                db.commit()
            db.close()
        except Exception:
            pass
        logger.info(f"Stream cleanup complete for {device_id}")
