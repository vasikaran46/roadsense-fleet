"""
RoadSense Fleet - Database Models
SQLAlchemy ORM models for Device and Event entities.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from backend.app.database.database import Base


class Device(Base):
    """Represents a streaming device (mobile phone on a bus)."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), default="Unknown Device")
    status = Column(String(20), default="offline")  # online / offline
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "name": self.name,
            "status": self.status,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Event(Base):
    """Represents a detected road/traffic event with evidence."""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(100), nullable=False, index=True)
    detection_type = Column(String(50), nullable=False, index=True)  # pothole, road_damage, vehicle, waterlogging
    confidence = Column(Float, nullable=False)
    severity = Column(String(20), default="low")  # high / medium / low
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    snapshot_path = Column(String(500), nullable=True)
    status = Column(String(20), default="new")  # new / reviewed / resolved
    description = Column(Text, nullable=True)
    bbox_x = Column(Integer, nullable=True)
    bbox_y = Column(Integer, nullable=True)
    bbox_w = Column(Integer, nullable=True)
    bbox_h = Column(Integer, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "detection_type": self.detection_type,
            "confidence": round(self.confidence, 3),
            "severity": self.severity,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "snapshot_path": self.snapshot_path,
            "status": self.status,
            "description": self.description,
        }
