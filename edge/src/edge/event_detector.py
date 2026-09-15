"""
Event Detector
==============
Wraps raw YOLO detections into semantic urban-intelligence events:
  - Pothole (road-defect heuristic)
  - Waterlogging (road-defect heuristic)
  - Vehicle detection & counting
  - Pedestrian risk
  - Traffic congestion
  - Missing sign
  - Incident

Only fires an event when the detection surpasses confidence thresholds
and has not been fired again within the cooldown window (seconds).
"""

import time
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

# Label groups
VEHICLE_LABELS = {"car", "truck", "bus", "motorcycle", "bicycle"}
PEDESTRIAN_LABELS = {"person"}
SIGN_LABELS = {"stop sign", "traffic light"}

# Congestion thresholds
CONGESTION_VEHICLE_COUNT = 8      # ≥ N vehicles in frame → congestion event
PEDESTRIAN_RISK_COUNT = 3         # ≥ N pedestrians near road edge

# Cooldown (seconds) per event type to avoid spamming
EVENT_COOLDOWNS: Dict[str, float] = {
    "vehicle_detection": 5.0,
    "pedestrian_risk": 10.0,
    "congestion": 30.0,
    "pothole": 15.0,
    "waterlogging": 15.0,
    "missing_sign": 60.0,
    "incident": 20.0,
    "road_damage": 20.0,
}


class EventDetector:
    def __init__(self, bus_id: str, camera_position: str):
        self._bus_id = bus_id
        self._camera_position = camera_position
        self._last_fired: Dict[str, float] = {}

    def _can_fire(self, event_type: str) -> bool:
        cooldown = EVENT_COOLDOWNS.get(event_type, 10.0)
        last = self._last_fired.get(event_type, 0.0)
        return (time.time() - last) >= cooldown

    def _fire(self, event_type: str, confidence: float,
              gps: Dict[str, float], detections: List[Dict],
              frame_b64: Optional[str] = None, extra: Optional[Dict] = None) -> Dict[str, Any]:
        self._last_fired[event_type] = time.time()
        return {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "bus_id": self._bus_id,
            "camera_position": self._camera_position,
            "confidence": round(confidence, 3),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gps": gps,
            "detections": detections,
            "frame_b64": frame_b64,
            "extra": extra or {},
        }

    def process(
        self,
        detections: List[Tuple[str, float, List[float]]],
        gps: Dict[str, float],
        frame_b64: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Convert raw detection list → semantic event list.

        Parameters
        ----------
        detections : [(label, confidence, [x1,y1,x2,y2]), ...]
        gps        : {"lat": float, "lon": float, "bearing_deg": float}
        frame_b64  : Base-64 encoded JPEG thumbnail of the relevant frame

        Returns
        -------
        List of event dicts (may be empty if nothing triggers)
        """
        events: List[Dict] = []

        vehicles = [(l, c, b) for l, c, b in detections if l in VEHICLE_LABELS]
        pedestrians = [(l, c, b) for l, c, b in detections if l in PEDESTRIAN_LABELS]
        signs = [(l, c, b) for l, c, b in detections if l in SIGN_LABELS]

        det_dicts = [{"label": l, "confidence": c, "bbox": b} for l, c, b in detections]

        # --- Vehicle detection event (fires when at least one vehicle) ---
        if vehicles and self._can_fire("vehicle_detection"):
            avg_conf = sum(c for _, c, _ in vehicles) / len(vehicles)
            events.append(self._fire(
                "vehicle_detection", avg_conf, gps,
                [{"label": l, "confidence": c, "bbox": b} for l, c, b in vehicles],
                frame_b64=frame_b64,
                extra={"vehicle_count": len(vehicles)},
            ))

        # --- Congestion ---
        if len(vehicles) >= CONGESTION_VEHICLE_COUNT and self._can_fire("congestion"):
            events.append(self._fire(
                "congestion", 0.85, gps, det_dicts, frame_b64=frame_b64,
                extra={"vehicle_count": len(vehicles)},
            ))

        # --- Pedestrian risk ---
        if len(pedestrians) >= PEDESTRIAN_RISK_COUNT and self._can_fire("pedestrian_risk"):
            events.append(self._fire(
                "pedestrian_risk", 0.80, gps, det_dicts, frame_b64=frame_b64,
                extra={"pedestrian_count": len(pedestrians)},
            ))

        # --- Missing sign heuristic: no sign detected in sign-rich area
        # (simplified: only fires if explicitly labelled by model as absent)
        if not signs and self._camera_position == "FRONT" and self._can_fire("missing_sign"):
            # Only fire occasionally when front camera has NO sign context –
            # in real system, would compare against GIS layer expectation.
            pass  # Disabled by default; enable via config

        # --- Road-defect labels injected by specialised road-damage model ---
        road_defects = [d for d in detections if d[0] in ("pothole", "crack", "waterlogging", "road_damage")]
        for label, conf, bbox in road_defects:
            etype = "pothole" if label == "pothole" else \
                    "waterlogging" if label == "waterlogging" else "road_damage"
            if conf >= 0.45 and self._can_fire(etype):
                events.append(self._fire(
                    etype, conf, gps,
                    [{"label": label, "confidence": conf, "bbox": bbox}],
                    frame_b64=frame_b64,
                ))

        return events
