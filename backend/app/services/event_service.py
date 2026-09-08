"""
RoadSense Fleet - Event Service
Creates, stores, and manages detection events with de-duplication.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy.orm import Session

from backend.app.database.database import SessionLocal
from backend.app.database.models import Event, Device
from backend.app.ai import Detection
from backend.app.config import settings

logger = logging.getLogger(__name__)

# In-memory cooldown tracker: (device_id, detection_type) -> last_event_time
_cooldown_cache: dict = {}


def _is_duplicate(device_id: str, detection: Detection) -> bool:
    """Check if this detection is a duplicate based on cooldown."""
    key = (device_id, detection.class_name)
    now = datetime.now(timezone.utc)

    if key in _cooldown_cache:
        last_time = _cooldown_cache[key]
        elapsed = (now - last_time).total_seconds()
        if elapsed < settings.EVENT_COOLDOWN_SECONDS:
            return True

    return False


def _update_cooldown(device_id: str, detection: Detection):
    """Update the cooldown tracker after creating an event."""
    key = (device_id, detection.class_name)
    _cooldown_cache[key] = datetime.now(timezone.utc)


def _ensure_device_exists(db: Session, device_id: str, name: str = None):
    """Create device record if it doesn't exist."""
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        device = Device(
            device_id=device_id,
            name=name or device_id,
            status="online",
        )
        db.add(device)
        db.commit()
    else:
        device.status = "online"
        device.last_seen = datetime.now(timezone.utc)
        db.commit()
    return device


def create_event(
    device_id: str,
    detection: Detection,
    snapshot_filename: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Optional[dict]:
    """
    Create a detection event in the database.
    Returns event dict if created, None if duplicate.
    """
    # Check duplicate
    if _is_duplicate(device_id, detection):
        logger.debug(f"Duplicate detection skipped: {detection.class_name} on {device_id}")
        return None

    try:
        db = SessionLocal()

        # Ensure device exists in DB
        _ensure_device_exists(db, device_id)

        # Create event record
        event = Event(
            device_id=device_id,
            detection_type=detection.class_name,
            confidence=detection.confidence,
            severity=detection.severity,
            latitude=latitude,
            longitude=longitude,
            timestamp=datetime.now(timezone.utc),
            snapshot_path=snapshot_filename,
            status="new",
            description=f"{detection.class_name} detected by {detection.detector_source}",
            bbox_x=detection.bbox[0],
            bbox_y=detection.bbox[1],
            bbox_w=detection.bbox[2] - detection.bbox[0],
            bbox_h=detection.bbox[3] - detection.bbox[1],
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        # Update cooldown
        _update_cooldown(device_id, detection)

        event_data = event.to_dict()
        logger.info(
            f"Event created: #{event.id} {detection.class_name} "
            f"({detection.confidence:.0%}) on {device_id}"
        )

        db.close()
        return event_data

    except Exception as e:
        logger.error(f"Failed to create event: {e}")
        return None
