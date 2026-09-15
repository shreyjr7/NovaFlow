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
    ):
        self.id = str(uuid.uuid4())
        self.gps = gps
        self.timestamp = timestamp or datetime.utcnow()
        self.detections = detections or []
        self.clip_path = clip_path
        self.extra = extra or {}

    def to_dict(self):
        return {
            "id": self.id,
            "gps": self.gps,
            "timestamp": self.timestamp.isoformat() + "Z",
            "detections": [
                {"label": d.label, "confidence": d.confidence, "bbox": d.bbox}
                for d in self.detections
            ],
            "clip_path": self.clip_path,
            "extra": self.extra,
        }
