"""
RoadSense Fleet - Event Service
Creates detection events in the database with de-duplication.
"""

import logging
import time
from datetime import datetime
from typing import Optional

from app.database.database import SessionLocal
from app.database.models import Event, Device
from app.ai import Detection
from app.config import settings

logger = logging.getLogger(__name__)

# In-memory cooldown cache: (device_id, detection_type) -> last_event_time
_cooldown_cache = {}


def create_event(
    device_id: str,
    detection: Detection,
    snapshot_path: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Optional[dict]:
    """Create an event record. Returns event dict or None if de-duplicated."""

    # De-duplication: skip if same type + subtype from same device within cooldown
    cache_key = (device_id, detection.class_name, detection.subtype)
    now = time.time()
    last_time = _cooldown_cache.get(cache_key, 0)
    if now - last_time < settings.EVENT_COOLDOWN_SECONDS:
        return None

    _cooldown_cache[cache_key] = now

    try:
        import json
        db = SessionLocal()

        # Upsert device
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            device = Device(device_id=device_id, name=device_id, status="online")
            db.add(device)
        device.status = "online"
        device.latitude = latitude
        device.longitude = longitude
        device.last_seen = datetime.utcnow()

        meta = {
            "source": detection.detector_source,
            "subtype": detection.subtype,
            "bbox": list(detection.bbox),
        }

        # Create event
        event = Event(
            device_id=device_id,
            detection_type=detection.class_name,
            confidence=detection.confidence,
            severity=detection.severity,
            latitude=latitude,
            longitude=longitude,
            snapshot_path=snapshot_path,
            status="new",
            metadata_json=json.dumps(meta),
            timestamp=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        event_dict = {
            "id": event.id,
            "device_id": event.device_id,
            "detection_type": event.detection_type,
            "subtype": detection.subtype,
            "confidence": event.confidence,
            "severity": event.severity,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "snapshot_path": event.snapshot_path,
            "status": event.status,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

        db.close()
        disp_name = f"{detection.class_name}:{detection.subtype}" if detection.subtype else detection.class_name
        logger.info(f"Event created: #{event.id} {disp_name} from {device_id}")
        return event_dict

    except Exception as e:
        logger.error(f"Event creation error: {e}")
        return None
