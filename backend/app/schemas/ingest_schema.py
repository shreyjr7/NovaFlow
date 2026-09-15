"""
Event Ingestion Schemas & Normalization Helpers
================================================
Defines strict Pydantic schemas for lightweight event ingestion,
idempotency key computation, and canonical envelope packaging.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


def compute_idempotency_key(
    event_id: str,
    timestamp: str,
    lat: float,
    lon: float,
    event_type: str,
) -> str:
    """
    Computes a deterministic SHA-256 idempotency key if not explicitly provided.
    Guarantees that identical payloads produced at the edge map to the same key.
    """
    raw = f"{event_id}_{timestamp}_{lat:.5f}_{lon:.5f}_{event_type}".encode("utf-8")
    return f"idemp_{hashlib.sha256(raw).hexdigest()[:24]}"


class GpsCoordinates(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in WGS84")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude in WGS84")
    bearing_deg: Optional[float] = Field(None, ge=0.0, le=360.0)
    speed_kmh: Optional[float] = Field(None, ge=0.0)
    road_segment: Optional[str] = None
    address: Optional[str] = None


class EventIngestIn(BaseModel):
    """
    Lightweight ingestion payload accepted from bus edge devices.
    Contains strictly the fields necessary for validation & queuing.
    """
    event_id: str = Field(..., min_length=1, max_length=128)
    event_type: str = Field(..., min_length=1, max_length=64)
    bus_id: str = Field(default="UNKNOWN_BUS", max_length=64)
    camera_id: str = Field(default="FRONT", max_length=32)
    timestamp: Union[datetime, str] = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    gps: GpsCoordinates
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_reference: Optional[str] = None
    evidence_ref: Optional[str] = None  # alias
    evidence_image_b64: Optional[str] = None
    evidence_clip_url: Optional[str] = None
    idempotency_key: Optional[str] = None
    severity: Optional[str] = "MEDIUM"
    district: Optional[str] = "Central"
    road_segment: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def resolve_gps_or_location(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Fallback location -> gps
            if "gps" not in data and "location" in data:
                data["gps"] = data["location"]
            # Copy top-level road_segment into gps if needed
            if "gps" in data and isinstance(data["gps"], dict):
                if "road_segment" in data and not data["gps"].get("road_segment"):
                    data["gps"]["road_segment"] = data["road_segment"]
        return data

    @field_validator("timestamp", mode="before")
    @classmethod
    def normalize_timestamp(cls, v: Any) -> str:
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            return v.astimezone(timezone.utc).isoformat()
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).isoformat()
            except Exception:
                return datetime.now(timezone.utc).isoformat()
        return datetime.now(timezone.utc).isoformat()

    def get_canonical_idempotency_key(self) -> str:
        """Returns provided idempotency_key or computes deterministic key."""
        if self.idempotency_key and self.idempotency_key.strip():
            return self.idempotency_key.strip()
        ts_str = self.timestamp if isinstance(self.timestamp, str) else self.timestamp.isoformat()
        return compute_idempotency_key(
            self.event_id,
            ts_str,
            self.gps.lat,
            self.gps.lon,
            self.event_type,
        )

    def to_envelope(self) -> Dict[str, Any]:
        """Converts into canonical queue envelope ready for stream serialization."""
        idemp_key = self.get_canonical_idempotency_key()
        ev_ref = self.evidence_reference or self.evidence_ref or ""
        ts_str = self.timestamp if isinstance(self.timestamp, str) else self.timestamp.isoformat()
        return {
            "idempotency_key": idemp_key,
            "event_id": self.event_id,
            "event_type": self.event_type.upper(),
            "bus_id": self.bus_id,
            "camera_id": self.camera_id,
            "timestamp": ts_str,
            "gps": {
                "lat": round(self.gps.lat, 6),
                "lon": round(self.gps.lon, 6),
                "bearing_deg": self.gps.bearing_deg,
                "road_segment": self.gps.road_segment or "UNKNOWN_SEGMENT",
                "address": self.gps.address or "",
            },
            "confidence": round(float(self.confidence), 4),
            "evidence_reference": ev_ref,
            "evidence_image_b64": self.evidence_image_b64,
            "evidence_clip_url": self.evidence_clip_url,
            "severity": (self.severity or "MEDIUM").upper(),
            "details": self.details,
            "queued_at": datetime.now(timezone.utc).isoformat(),
        }


class EventIngestResponse(BaseModel):
    status: str  # QUEUED, DUPLICATE_IGNORED, ACCEPTED
    event_id: str
    idempotency_key: str
    stream_message_id: Optional[str] = None
    queued_at: str
    duplicate: bool = False
    message: Optional[str] = None


class IngestionStatsResponse(BaseModel):
    total_received: int
    total_queued: int
    total_processed: int
    total_duplicates_prevented: int
    queue_depth: int
    queue_backend: str
    active_stream: str
    consumer_group: str
