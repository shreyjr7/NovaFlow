# backend/models/event_model.py
from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Dict, Any

class Detection(SQLModel, table=False):
    label: str
    confidence: float
    bbox: str  # store as JSON string for simplicity

class Event(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    gps_lat: float = Field(index=True)
    gps_lng: float = Field(index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    detections: str = Field(sa_column_kwargs={ type_: JSON})
    clip_path: str | None = None
    extra: str | None = Field(sa_column_kwargs={type_: JSON})
