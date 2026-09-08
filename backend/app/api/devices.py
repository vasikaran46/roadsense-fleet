"""RoadSense Fleet - Devices API"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Device

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/devices")
async def list_devices(db: Session = Depends(get_db)):
    """List all registered devices with live status."""
    from app.services.stream_manager import stream_manager

    db_devices = db.query(Device).all()
    devices = []
    for d in db_devices:
        is_online = d.device_id in stream_manager.devices
        devices.append({
            "device_id": d.device_id,
            "name": d.name,
            "status": "online" if is_online else "offline",
            "latitude": d.latitude,
            "longitude": d.longitude,
            "last_seen": d.last_seen.isoformat() if d.last_seen else None,
        })

    # Also include any streaming devices not yet in DB
    for dev_id in stream_manager.devices:
        if not any(d["device_id"] == dev_id for d in devices):
            state = stream_manager.devices[dev_id]
            devices.append({
                "device_id": dev_id,
                "name": state.get("name", dev_id),
                "status": "online",
                "latitude": state.get("latitude"),
                "longitude": state.get("longitude"),
                "last_seen": None,
            })

    return {"devices": devices, "count": len(devices)}
