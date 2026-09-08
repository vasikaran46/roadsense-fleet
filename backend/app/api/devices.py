"""
RoadSense Fleet - Devices API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.database import get_db
from backend.app.database.models import Device

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("")
async def list_devices(db: Session = Depends(get_db)):
    """List all known devices with their status."""
    # Merge DB records with live stream manager state
    from backend.app.services.stream_manager import stream_manager

    db_devices = db.query(Device).all()
    db_device_map = {d.device_id: d.to_dict() for d in db_devices}

    # Add live connection info
    live_devices = stream_manager.get_all_devices()
    for dev_id, live_info in live_devices.items():
        if dev_id in db_device_map:
            db_device_map[dev_id]["status"] = "online"
            db_device_map[dev_id]["latitude"] = live_info.get("latitude")
            db_device_map[dev_id]["longitude"] = live_info.get("longitude")
            db_device_map[dev_id]["last_seen"] = live_info.get("last_seen")
        else:
            db_device_map[dev_id] = {
                "device_id": dev_id,
                "name": live_info.get("name", dev_id),
                "status": "online",
                "latitude": live_info.get("latitude"),
                "longitude": live_info.get("longitude"),
                "last_seen": live_info.get("last_seen"),
            }

    return {"devices": list(db_device_map.values()), "count": len(db_device_map)}
