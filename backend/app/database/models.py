"""
RoadSense Fleet - Database Models
SQLAlchemy models for Device and Event.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text

from app.database.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), default="")
    status = Column(String(20), default="offline")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(100), nullable=False, index=True)
    detection_type = Column(String(50), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    severity = Column(String(20), default="low", index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    snapshot_path = Column(String(500), nullable=True)
    status = Column(String(20), default="new")
    metadata_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
