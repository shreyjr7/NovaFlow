import uuid
from datetime import datetime
from typing import List, Dict, Any

class Detection:
    def __init__(self, label: str, confidence: float, bbox: List[float]):
        self.label = label
        self.confidence = confidence
        self.bbox = bbox  # [x1, y1, x2, y2]

class Event:
    def __init__(
        self,
        gps: Dict[str, float],
        timestamp: datetime = None,
        detections: List[Detection] = None,
        clip_path: str = None,
        extra: Dict[str, Any] = None,
        event_type: str = "pothole",
        bus_id: str = "BUS-001",
        route_id: str = "R-01",
        severity: str = "medium",
        status: str = "unverified",
    ):
        self.id = f"EVT-{str(uuid.uuid4())[:8].upper()}"
        self.gps = gps
        self.timestamp = timestamp or datetime.utcnow()
        self.detections = detections or []
        self.clip_path = clip_path
        self.extra = extra or {}
        self.event_type = event_type
        self.bus_id = bus_id
        self.route_id = route_id
        self.severity = severity
        self.status = status

    def to_dict(self):
        return {
            "id": self.id,
            "eventId": self.id,
            "type": self.event_type,
            "confidence": round(self.detections[0].confidence, 3) if self.detections else 0.95,
            "latitude": self.gps.get("lat", 28.6139),
            "longitude": self.gps.get("lon", 77.2090),
            "timestamp": self.timestamp.isoformat() + "Z",
            "busId": self.bus_id,
            "routeId": self.route_id,
            "severity": self.severity,
            "status": self.status,
            "gps": self.gps,
            "detections": [
                {"label": d.label, "confidence": d.confidence, "bbox": d.bbox}
                for d in self.detections
            ],
            "clip_path": self.clip_path,
            "extra": self.extra,
        }

    def to_standard_dict(self):
        """Phase 3 Step 5 Canonical 10-Key Representation."""
        conf = round(self.detections[0].confidence, 3) if self.detections else 0.95
        return {
            "eventId": self.id,
            "type": self.event_type,
            "confidence": conf,
            "latitude": self.gps.get("lat", 28.6139),
            "longitude": self.gps.get("lon", 77.2090),
            "timestamp": self.timestamp.isoformat() + "Z",
            "busId": self.bus_id,
            "routeId": self.route_id,
            "severity": self.severity,
            "status": self.status,
        }


class StandardEvent:
    def __init__(
        self,
        eventId: str,
        type: str,
        confidence: float,
        latitude: float,
        longitude: float,
        timestamp: str,
        busId: str,
        routeId: str,
        severity: str = "medium",
        status: str = "unverified",
    ):
        self.eventId = eventId
        self.type = type
        self.confidence = round(confidence, 3)
        self.latitude = round(latitude, 6)
        self.longitude = round(longitude, 6)
        self.timestamp = timestamp
        self.busId = busId
        self.routeId = routeId
        self.severity = severity
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
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
