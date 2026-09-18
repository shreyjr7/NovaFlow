"""
Standardized AI Event Schema (Phase 3 - Step 5)
================================================
Defines the canonical event representation across Edge AI,
Backend Ingestion, Database, and Frontend GIS:

{
  "eventId": "EVT-00124",
  "type": "pothole",
  "confidence": 0.94,
  "latitude": 28.6139,
  "longitude": 77.2090,
  "timestamp": "2026-09-15T04:22:00Z",
  "busId": "BUS-102",
  "routeId": "R-12",
  "severity": "high",
  "status": "unverified"
}
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, model_validator


class StandardEvent(BaseModel):
    """
    Standardized AI Event format mandated by Phase 3, Step 5.
    Guarantees consistent communication across Frontend, Backend, and Edge.
    """
    eventId: str = Field(..., description="Unique event identifier (e.g. EVT-00124)")
    type: str = Field(..., description="Defect/incident class in lower/snake_case (e.g. pothole, waterlogging)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI detection confidence score (0.0 - 1.0)")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude coordinate")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    busId: str = Field(default="BUS-001", description="Source bus identifier (e.g. BUS-102)")
    routeId: str = Field(default="R-01", description="Bus transit route identifier (e.g. R-12)")
    severity: str = Field(default="medium", description="Severity grade (low, medium, high, severe)")
    status: str = Field(default="unverified", description="Lifecycle status (unverified, confirmed, under_repair, resolved, dismissed)")

    # Optional evidentiary attachments
    evidenceImageB64: Optional[str] = None
    evidenceClipUrl: Optional[str] = None
    address: Optional[str] = None
    roadSegment: Optional[str] = None
    district: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            event_id = data.get("eventId") or data.get("event_id") or data.get("id") or "EVT-00001"
            event_type = (data.get("type") or data.get("event_type") or data.get("label") or "unknown").lower()
            confidence = float(data.get("confidence", 1.0))

            lat = data.get("latitude")
            lon = data.get("longitude")
            if lat is None:
                lat = data.get("gps_lat")
            if lon is None:
                lon = data.get("gps_lon")
            if (lat is None or lon is None) and "gps" in data and isinstance(data["gps"], dict):
                lat = data["gps"].get("lat", data["gps"].get("latitude", 28.6139))
                lon = data["gps"].get("lon", data["gps"].get("longitude", 77.2090))
            if lat is None:
                lat = 28.6139
            if lon is None:
                lon = 77.2090

            ts = data.get("timestamp")
            if isinstance(ts, datetime):
                ts = ts.astimezone(timezone.utc).isoformat()
            elif not ts:
                ts = datetime.now(timezone.utc).isoformat()

            bus_id = data.get("busId") or data.get("bus_id") or "BUS-001"
            route_id = data.get("routeId") or data.get("route_id") or "R-01"
            severity = str(data.get("severity", "medium")).lower()

            raw_status = str(data.get("status", "unverified")).lower().replace(" ", "_")
            if raw_status in ("active", "ai_detected"):
                raw_status = "unverified"
            status = raw_status

            return {
                "eventId": str(event_id),
                "type": event_type,
                "confidence": round(confidence, 3),
                "latitude": float(lat),
                "longitude": float(lon),
                "timestamp": str(ts),
                "busId": str(bus_id),
                "routeId": str(route_id),
                "severity": severity,
                "status": status,
                "evidenceImageB64": data.get("evidenceImageB64") or data.get("evidence_image_b64"),
                "evidenceClipUrl": data.get("evidenceClipUrl") or data.get("evidence_clip_url"),
                "address": data.get("address"),
                "roadSegment": data.get("roadSegment") or data.get("road_segment"),
                "district": data.get("district"),
                "details": data.get("details") or {},
            }
        return data

    def to_standard_dict(self) -> Dict[str, Any]:
        """Returns precisely the 10-key dictionary structure specified in Step 5."""
        return {
            "eventId": self.eventId,
            "type": self.type,
            "confidence": self.confidence,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": self.timestamp,
            "busId": self.busId,
            "routeId": self.routeId,
            "severity": self.severity,
            "status": self.status,
        }

    @classmethod
    def from_any(cls, obj: Any) -> "StandardEvent":
        """Factory method to convert ORM models, dicts, or features into StandardEvent."""
        if isinstance(obj, StandardEvent):
            return obj
        if hasattr(obj, "to_geojson_feature"):
            feat = obj.to_geojson_feature()
            props = feat.get("properties", {})
            coords = feat.get("geometry", {}).get("coordinates", [77.2090, 28.6139])
            return cls(
                eventId=props.get("event_id", "EVT-00001"),
                type=props.get("event_type", "pothole").lower(),
                confidence=props.get("confidence", 1.0),
                latitude=coords[1],
                longitude=coords[0],
                timestamp=props.get("timestamp", datetime.now(timezone.utc).isoformat()),
                busId=props.get("bus_id", "BUS-001"),
                routeId=props.get("route_id", "R-01"),
                severity=props.get("severity", "medium").lower(),
                status=props.get("status", "unverified").lower(),
                evidenceImageB64=props.get("evidence_image_b64"),
                evidenceClipUrl=props.get("evidence_clip_url"),
                details=props.get("details", {}),
            )
        if isinstance(obj, dict):
            return cls.model_validate(obj)
        return cls(
            eventId=getattr(obj, "event_id", "EVT-00001"),
            type=getattr(obj, "event_type", "pothole").lower(),
            confidence=getattr(obj, "confidence", 1.0),
            latitude=getattr(obj, "gps_lat", 28.6139),
            longitude=getattr(obj, "gps_lon", 77.2090),
            timestamp=str(getattr(obj, "timestamp", datetime.now(timezone.utc).isoformat())),
            busId=getattr(obj, "bus_id", "BUS-001"),
            routeId=getattr(obj, "route_id", "R-01"),
            severity=str(getattr(obj, "severity", "medium")).lower(),
            status=str(getattr(obj, "status", "unverified")).lower(),
        )
