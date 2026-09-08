"""
RoadSense Fleet - Events API
List, filter, and retrieve detection events.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.database.database import get_db
from backend.app.database.models import Event

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("")
async def list_events(
    device_id: Optional[str] = Query(None),
    detection_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List events with optional filters."""
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
        "events": [e.to_dict() for e in events],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats")
async def event_stats(db: Session = Depends(get_db)):
    """Get aggregated event statistics for dashboard."""
    from sqlalchemy import func

    total = db.query(Event).count()

    by_type = (
        db.query(Event.detection_type, func.count(Event.id))
        .group_by(Event.detection_type)
        .all()
    )
    type_counts = {t: c for t, c in by_type}

    by_severity = (
        db.query(Event.severity, func.count(Event.id))
        .group_by(Event.severity)
        .all()
    )
    severity_counts = {s: c for s, c in by_severity}

    by_device = (
        db.query(Event.device_id, func.count(Event.id))
        .group_by(Event.device_id)
        .all()
    )
    device_counts = {d: c for d, c in by_device}

    # Recent events (last 10)
    recent = (
        db.query(Event)
        .order_by(desc(Event.timestamp))
        .limit(10)
        .all()
    )

    return {
        "total_events": total,
        "by_type": type_counts,
        "by_severity": severity_counts,
        "by_device": device_counts,
        "recent_events": [e.to_dict() for e in recent],
    }


@router.get("/{event_id}")
async def get_event(event_id: int, db: Session = Depends(get_db)):
    """Get a single event by ID."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Event not found")
    return event.to_dict()
