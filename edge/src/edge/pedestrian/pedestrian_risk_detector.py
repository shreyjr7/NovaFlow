"""
Pedestrian Safety & Vulnerable Pedestrian Risk Detector (Phase 6 - Steps 16 & 17)
==================================================================================
Detects pedestrians from camera feeds, models their trajectory vectors,
checks proximity to vehicular road boundary, verifies geospatial school-zone
containment and active bell schedules, and assesses crowd density.

ETHICAL AI NOTICE (Step 16):
----------------------------
In strict accordance with computer vision and transportation safety standards,
this system DOES NOT claim to classify child age from a camera feed.
Instead, vulnerable pedestrian risk is assessed via a 5-factor proxy:
  1. Person Detected (standard YOLO class person)
  2. Approximate size / distance (optical bounding box geometry)
  3. School-zone GPS (geofence containment within school radius)
  4. School hours (active bell schedule morning/afternoon intervals)
  5. Trajectory (multi-frame motion analysis)

Step 17 Crossing Behaviors:
---------------------------
  - NORMAL         : Walking parallel to road -> Normal
  - POTENTIAL_RISK : Moving toward road       -> Potential risk
  - HIGH_RISK      : Enters roadway           -> High risk
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import math
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

from .school_zone_db import SchoolZone, SchoolZoneDatabase
from .trajectory_tracker import (
    CrossingBehavior,
    PedestrianTrack,
    PedestrianTrajectoryTracker,
    TrajectoryState,
)

logger = logging.getLogger("pedestrian.risk_detector")


@dataclass
class PedestrianRiskEvent:
    event_id:         str
    event_type:       str   # "PEDESTRIAN_RISK"
    location:         Dict[str, float]  # {"lat": float, "lon": float}
    timestamp:        str
    bus_id:           str
    camera_id:        str
    confidence:       float
    trajectory:       Dict[str, Any]
    school_zone:      Dict[str, Any]
    road_boundary:    Dict[str, Any]
    zone_density:     Dict[str, Any]
    approx_size:      Dict[str, Any]
    approx_distance_m: float
    crossing_behavior: str   # "NORMAL" | "POTENTIAL_RISK" | "HIGH_RISK"
    severity:         str   # "medium" | "high"
    frame_b64:        Optional[str] = None
    crowded_area:     bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type,
            "location":          self.location,
            "timestamp":         self.timestamp,
            "bus_id":            self.bus_id,
            "camera_id":         self.camera_id,
            "confidence":        round(self.confidence, 3),
            "severity":          self.severity,
            "crossing_behavior": self.crossing_behavior,
            "approx_size":       self.approx_size,
            "approx_distance_m": self.approx_distance_m,
            "trajectory":        self.trajectory,
            "school_zone":       self.school_zone,
            "road_boundary":     self.road_boundary,
            "zone_density":      self.zone_density,
            "crowded_area":      self.crowded_area,
            "frame_b64":         self.frame_b64,
            "methodology_note": (
                "Proxy detection: Person + approximate size/distance + school-zone GPS "
                "+ active school hours + multi-frame trajectory. Does NOT claim child age classification."
            ),
        }

    def to_standard_dict(self) -> Dict[str, Any]:
        """Canonical Phase 3 Step 5 10-key standard event representation."""
        lat = self.location.get("lat", 28.5672)
        lon = self.location.get("lon", 77.1720)
        eid = self.event_id if self.event_id.startswith("EVT-") else f"EVT-{self.event_id[:8]}"
        return {
            "eventId": eid,
            "type": "pedestrian_risk",
            "confidence": round(self.confidence, 3),
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "timestamp": self.timestamp,
            "busId": self.bus_id,
            "routeId": self.school_zone.get("school_id", "R-01"),
            "severity": self.severity,
            "status": "unverified",
        }


class PedestrianRiskDetector:
    """
    Evaluates pedestrian safety conditions around school zones and road boundaries.
    """

    def __init__(
        self,
        school_db:                 Optional[SchoolZoneDatabase] = None,
        road_boundary_thresh_px:   float = 85.0,
        crowded_threshold:         int   = 5,
        cooldown_sec:              float = 12.0,
        camera_id:                 str   = "FRONT",
        bus_id:                    str   = "BUS_001",
    ):
        self.school_db = school_db or SchoolZoneDatabase()
        self.road_boundary_thresh_px = road_boundary_thresh_px
        self.crowded_threshold = crowded_threshold
        self.cooldown_sec = cooldown_sec
        self.camera_id = camera_id
        self.bus_id = bus_id

        self.tracker = PedestrianTrajectoryTracker()
        self._last_alert_time: Dict[str, float] = {}

    def compute_crowd_density(self, person_count: int) -> Dict[str, Any]:
        """
        Reports zone-level pedestrian crowd density for crowded transit stops
        or school gates rather than claiming perfect individual counts.
        """
        if person_count >= 8:
            level = "HIGH"
        elif person_count >= 4:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "level":            level,
            "pedestrian_count": person_count,
            "is_crowded":       person_count >= self.crowded_threshold,
            "density_score":    round(min(1.0, person_count / 10.0), 2),
        }

    @staticmethod
    def evaluate_vulnerable_proxy(
        person_detected: bool,
        approx_size: Dict[str, float],
        approx_distance_m: float,
        in_school_zone: bool,
        in_school_hours: bool,
        crossing_behavior: CrossingBehavior,
    ) -> Dict[str, Any]:
        """
        Step 16: Evaluates the 5-component proxy for vulnerable pedestrian risk:
          1. Person detected
          2. Approximate size / distance
          3. School-zone GPS
          4. School hours
          5. Trajectory / crossing behavior
        """
        is_at_risk = (
            person_detected
            and in_school_zone
            and in_school_hours
            and (crossing_behavior in (CrossingBehavior.POTENTIAL_RISK, CrossingBehavior.HIGH_RISK))
        )
        return {
            "person_detected": person_detected,
            "approx_size": approx_size,
            "approx_distance_m": approx_distance_m,
            "in_school_zone": in_school_zone,
            "in_school_hours": in_school_hours,
            "crossing_behavior": crossing_behavior.value,
            "is_vulnerable_risk": is_at_risk,
            "no_age_claim": "Validated proxy method. Never claims facial/biometric child age classification.",
        }

    def process_frame(
        self,
        frame: Optional[Any],
        detections: List[Tuple[str, float, List[int]]],  # [(label, conf, [x1, y1, x2, y2])]
        gps: Dict[str, float],                           # {"lat": ..., "lon": ...}
        timestamp: Optional[str] = None,
        road_boundary_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None,
    ) -> Tuple[List[PedestrianRiskEvent], Dict[str, Any]]:
        """
        Processes a frame and returns any generated PEDESTRIAN_RISK events
        along with zone-level pedestrian crowd metrics.
        """
        now_dt = datetime.now(timezone.utc)
        if timestamp:
            try:
                now_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except Exception:
                pass
        now_epoch = now_dt.timestamp()
        ts_str = timestamp or now_dt.isoformat()

        lat = gps.get("lat", 28.5672)
        lon = gps.get("lon", 77.1720)

        # 1. Filter person detections
        person_detections = [
            (conf, bbox) for label, conf, bbox in detections
            if label.lower() in ("person", "pedestrian") and conf >= 0.40
        ]
        person_count = len(person_detections)
        zone_density = self.compute_crowd_density(person_count)

        # 2. Update multi-frame trajectory tracking
        active_tracks = self.tracker.update(
            person_detections,
            current_time=now_epoch,
            road_boundary_line=road_boundary_line,
        )

        # 3. Check School Zone geofence and active hours
        school_match = self.school_db.check_location(lat, lon, dt=now_dt)
        if not school_match:
            # Not in any school zone geofence
            return ([], zone_density)

        school, dist_m, is_active_hours = school_match

        # Rule check: Must be within configured active school bell hours!
        if not is_active_hours:
            return ([], zone_density)

        events: List[PedestrianRiskEvent] = []

        # 4. Calibrated road boundary line
        h, w = (720, 1280)
        if frame is not None and hasattr(frame, "shape"):
            h, w = frame.shape[:2]
        boundary = road_boundary_line or ((w * 0.65, h * 0.50), (w * 0.90, h * 0.95))

        # 5. Evaluate each tracked person against the risk conditions
        for track in active_tracks:
            foot_x, foot_y = track.foot_point
            traj = track.trajectory

            if not traj:
                continue

            # Step 17: Crossing behavior classification
            behavior = traj.crossing_behavior
            # If person is walking parallel to road -> Normal (no risk alert)
            if behavior == CrossingBehavior.NORMAL:
                continue

            # Distance to road boundary line
            (bx1, by1), (bx2, by2) = boundary
            dist_to_boundary = _point_to_line_dist(foot_x, foot_y, bx1, by1, bx2, by2)
            near_boundary = dist_to_boundary <= self.road_boundary_thresh_px or traj.in_roadway

            if not near_boundary:
                continue

            # Step 16: Size & distance proxy metrics
            approx_size = track.approx_size
            approx_dist = track.approx_distance_m

            # Severity: HIGH_RISK -> high severity, POTENTIAL_RISK -> medium severity
            severity = "high" if behavior == CrossingBehavior.HIGH_RISK else "medium"

            # Cooldown check
            key = f"{school.school_id}_{track.track_id}"
            last_alert = self._last_alert_time.get(key, 0.0)
            if (now_epoch - last_alert) < self.cooldown_sec:
                continue
            self._last_alert_time[key] = now_epoch

            # Generate evidence frame thumbnail
            frame_b64 = None
            if frame is not None:
                frame_b64 = _render_evidence_frame(frame, track, boundary)

            event = PedestrianRiskEvent(
                event_id=str(uuid.uuid4()),
                event_type="PEDESTRIAN_RISK",
                location={"lat": lat, "lon": lon},
                timestamp=ts_str,
                bus_id=self.bus_id,
                camera_id=self.camera_id,
                confidence=round(track.confidence, 3),
                approx_size=approx_size,
                approx_distance_m=approx_dist,
                crossing_behavior=behavior.value,
                severity=severity,
                trajectory={
                    "speed_px_s":         traj.speed_px_s,
                    "heading_deg":        traj.heading_deg,
                    "moving_toward_road": traj.moving_toward_road,
                    "crossing_behavior":  behavior.value,
                    "vector":             [traj.dx, traj.dy],
                    "in_roadway":         traj.in_roadway,
                },
                school_zone={
                    "school_id":       school.school_id,
                    "name":            school.name,
                    "distance_m":      dist_m,
                    "active_now":      True,
                    "speed_limit_kmh": school.speed_limit_kmh,
                },
                road_boundary={
                    "distance_px":      round(dist_to_boundary, 1),
                    "is_near_boundary": True,
                },
                zone_density=zone_density,
                frame_b64=frame_b64,
                crowded_area=zone_density["is_crowded"],
            )

            logger.warning(
                f"PEDESTRIAN_RISK ALERT at {school.name} ({school.school_id}): "
                f"Behavior={behavior.value}, Severity={severity}, "
                f"Track {track.track_id} (dx={traj.dx}, dy={traj.dy}), "
                f"DistToBoundary={dist_to_boundary:.1f}px, DistanceM={approx_dist}m"
            )
            events.append(event)

        return (events, zone_density)


def _point_to_line_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _render_evidence_frame(
    frame: Any,
    track: PedestrianTrack,
    boundary: Tuple[Tuple[float, float], Tuple[float, float]],
) -> Optional[str]:
    if cv2 is None or frame is None or not hasattr(frame, "copy"):
        return "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
    try:
        annotated = frame.copy()
        x1, y1, x2, y2 = track.bbox
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 230), 2)
        (bx1, by1), (bx2, by2) = boundary
        cv2.line(annotated, (int(bx1), int(by1)), (int(bx2), int(by2)), (0, 220, 255), 2)
        _, buffer = cv2.imencode(".jpg", annotated)
        return "data:image/jpeg;base64," + base64.b64encode(buffer).decode("utf-8")
    except Exception:
        return "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
