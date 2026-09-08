"""RoadSense Fleet - Events API"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database.database import get_db
from app.database.models import Event
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/events")
async def list_events(
    device_id: Optional[str] = None,
    detection_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Event)
    if device_id:
        query = query.filter(Event.device_id == device_id)
    if detection_type:
        query = query.filter(Event.detection_type == detection_type)
    if severity:
        query = query.filter(Event.severity == severity)
    if status:
        query = query.filter(Event.status == status)

    total = query.count()
    events = query.order_by(desc(Event.timestamp)).offset(offset).limit(limit).all()

    return {
        "events": [_event_to_dict(e) for e in events],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/events/stats")
async def event_stats(db: Session = Depends(get_db)):
    total = db.query(Event).count()

    by_type = {}
    type_counts = db.query(Event.detection_type, func.count()).group_by(Event.detection_type).all()
    for dt, count in type_counts:
        by_type[dt] = count

    by_severity = {}
    sev_counts = db.query(Event.severity, func.count()).group_by(Event.severity).all()
    for sev, count in sev_counts:
        by_severity[sev] = count

    by_device = {}
    dev_counts = db.query(Event.device_id, func.count()).group_by(Event.device_id).all()
    for dev, count in dev_counts:
        by_device[dev] = count

    recent = db.query(Event).order_by(desc(Event.timestamp)).limit(20).all()

    return {
        "total_events": total,
        "by_type": by_type,
        "by_severity": by_severity,
        "by_device": by_device,
        "recent_events": [_event_to_dict(e) for e in recent],
    }


@router.get("/events/{event_id}")
async def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return _event_to_dict(event)


@router.delete("/events/{event_id}")
async def delete_event(event_id: int, db: Session = Depends(get_db)):
    """Delete a single event by ID and remove its snapshot image."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.snapshot_path:
        try:
            snapshot_file = settings.get_snapshot_dir() / event.snapshot_path
            if snapshot_file.exists():
                snapshot_file.unlink()
        except Exception as ex:
            logger.warning(f"Could not remove snapshot file {event.snapshot_path}: {ex}")

    db.delete(event)
    db.commit()
    logger.info(f"Event #{event_id} deleted")
    return {"status": "deleted", "id": event_id}


@router.delete("/events")
async def clear_all_events(db: Session = Depends(get_db)):
    """Clear all events from the database."""
    events = db.query(Event).all()
    count = len(events)
    for ev in events:
        if ev.snapshot_path:
            try:
                snapshot_file = settings.get_snapshot_dir() / ev.snapshot_path
                if snapshot_file.exists():
                    snapshot_file.unlink()
            except Exception:
                pass
        db.delete(ev)
    db.commit()
    logger.info(f"Cleared {count} events")
    return {"status": "cleared", "deleted_count": count}


def _event_to_dict(e: Event) -> dict:
    return {
        "id": e.id,
        "device_id": e.device_id,
        "detection_type": e.detection_type,
        "confidence": e.confidence,
        "severity": e.severity,
        "latitude": e.latitude,
        "longitude": e.longitude,
        "snapshot_path": e.snapshot_path,
        "status": e.status,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
    }
