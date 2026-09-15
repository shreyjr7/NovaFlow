"""
Ingested Event Database Model & PostGIS / GeoJSON Representation
================================================================
Stores canonical ingested events with spatial coordinates,
idempotency keys, and full evidentiary references.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class IngestedEvent(SQLModel, table=True):
    """
    Canonical persisted event entity.
    Compatible with SQLite and PostgreSQL/PostGIS.
    """
    __tablename__ = "ingested_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    idempotency_key: str = Field(unique=True, index=True, max_length=128)
    event_id: str = Field(index=True, max_length=128)
    event_type: str = Field(index=True, max_length=64)
    bus_id: str = Field(default="BUS_001", index=True, max_length=64)
    camera_id: str = Field(default="FRONT", max_length=32)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    gps_lat: float = Field(index=True)
    gps_lon: float = Field(index=True)
    bearing_deg: Optional[float] = None
    road_segment: Optional[str] = Field(default="UNKNOWN_SEGMENT", index=True, max_length=128)
    address: Optional[str] = Field(default="", max_length=255)
    district: Optional[str] = Field(default="Central", index=True, max_length=64)
    confidence: float = Field(default=1.0)
    evidence_reference: Optional[str] = Field(default="", max_length=255)
    evidence_image_b64: Optional[str] = None
    evidence_clip_url: Optional[str] = None
    severity: str = Field(default="MEDIUM", index=True, max_length=32)
    status: str = Field(default="ACTIVE", index=True, max_length=32)  # ACTIVE, CONFIRMED, DISMISSED, ESCALATED, RESOLVED
    metadata_json: str = Field(default="{}")
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_metadata(self) -> Dict[str, Any]:
        try:
            return json.loads(self.metadata_json)
        except Exception:
            return {}

    def to_geojson_feature(self) -> Dict[str, Any]:
        """Converts spatial entity into standard RFC 7946 GeoJSON Feature."""
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.gps_lon, self.gps_lat],  # GeoJSON is [lon, lat]
            },
            "properties": {
                "id": str(self.id),
                "event_id": self.event_id,
                "event_type": self.event_type,
                "idempotency_key": self.idempotency_key,
                "bus_id": self.bus_id,
                "camera_id": self.camera_id,
                "timestamp": self.timestamp.isoformat() if self.timestamp else "",
                "gps": {
                    "lat": self.gps_lat,
                    "lon": self.gps_lon,
                    "bearing_deg": self.bearing_deg,
                    "road_segment": self.road_segment,
                    "address": self.address,
                },
                "district": self.district,
                "confidence": self.confidence,
                "evidence_reference": self.evidence_reference,
                "evidence_image_b64": self.evidence_image_b64,
                "evidence_clip_url": self.evidence_clip_url,
                "severity": self.severity,
                "status": self.status,
                "details": self.get_metadata(),
            },
        }
