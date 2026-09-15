"""
Pedestrian Safety & Vulnerable Pedestrian Risk Detector
======================================================
Detects pedestrians from camera feeds, models their trajectory vectors,
checks proximity to the vehicular road boundary, verifies geospatial school-zone
containment and active bell schedules, and assesses crowd density.

ETHICAL AI NOTICE:
  In strict accordance with computer vision and transportation safety standards,
  this module DOES NOT claim to classify child age from a moving bus camera.
  Instead, vulnerable road user risk is identified using a validated proxy:
    Person Detected + Near Road Boundary + Trajectory Toward Road +
    School Zone Geofence + Active School Bell Hours.
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
from .trajectory_tracker import PedestrianTrack, PedestrianTrajectoryTracker, TrajectoryState

logger = logging.getLogger("pedestrian.risk_detector")


@dataclass
class PedestrianRiskEvent:
    event_id:         str
    event_type:       str   # Always "PEDESTRIAN_RISK"
    location:         Dict[str, float]  # {"lat": float, "lon": float}
    timestamp:        str
    bus_id:           str
    camera_id:        str
    confidence:       float
    trajectory:       Dict[str, Any]
    school_zone:      Dict[str, Any]
    road_boundary:    Dict[str, Any]
    zone_density:     Dict[str, Any]
    frame_b64:        Optional[str] = None
    crowded_area:     bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":         self.event_id,
            "event_type":       self.event_type,
            "location":         self.location,
            "timestamp":        self.timestamp,
            "bus_id":           self.bus_id,
            "camera_id":        self.camera_id,
            "confidence":       round(self.confidence, 3),
            "trajectory":       self.trajectory,
            "school_zone":      self.school_zone,
            "road_boundary":    self.road_boundary,
            "zone_density":     self.zone_density,
            "crowded_area":     self.crowded_area,
            "frame_b64":        self.frame_b64,
            "methodology_note": (
                "Proxy detection: Person + road boundary proximity + trajectory towards road "
                "+ school zone + active hours. No unscientific child age estimation is used."
            ),
        }


class PedestrianRiskDetector:
    """
    Evaluates pedestrian safety conditions around school zones.

    Parameters
    ----------
    school_db : SchoolZoneDatabase instance
    road_boundary_thresh_px : Maximum pixel distance from pavement contact to road boundary
    crowded_threshold : Count of detected persons to flag zone-level crowdedness
    cooldown_sec : Minimum cooldown between consecutive alerts per school zone
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

    def process_frame(
        self,
        frame: Optional[np.ndarray],
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

        lat = gps.get("lat", 28.5910)
        lon = gps.get("lon", 77.1650)

        # 1. Filter pedestrian detections ("person")
        person_detections = [
            (conf, bbox) for label, conf, bbox in detections
            if label.lower() in ("person", "pedestrian") and conf >= 0.40
        ]
        person_count = len(person_detections)
        zone_density = self.compute_crowd_density(person_count)

        # 2. Update trajectory tracking
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

        # 4. Calibrated road boundary line (default: right curb line for front bus camera)
        h, w = (frame.shape[:2] if frame is not None else (720, 1280))
        boundary = road_boundary_line or ((w * 0.65, h * 0.50), (w * 0.90, h * 0.95))

        # 5. Evaluate each tracked person against the risk conditions
        for track in active_tracks:
            foot_x, foot_y = track.foot_point
            traj = track.trajectory

            # Condition A: Track must have confirmed trajectory
            if not traj:
                continue

            # Condition B: Trajectory must indicate movement toward the road
            if not traj.moving_toward_road:
                continue

            # Condition C: Distance to road boundary line
            (bx1, by1), (bx2, by2) = boundary
            dist_to_boundary = _point_to_line_dist(foot_x, foot_y, bx1, by1, bx2, by2)
            near_boundary = dist_to_boundary <= self.road_boundary_thresh_px

            if not near_boundary:
                continue

            # All 5 Conditions met:
            # 1. Person detected
            # 2. Person near road boundary
            # 3. Trajectory indicates movement toward road
            # 4. Location within school-zone geofence
            # 5. Time falls within configured school hours

            # Check cooldown to prevent duplicate alert spamming
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
                trajectory={
                    "speed_px_s":         traj.speed_px_s,
                    "heading_deg":        traj.heading_deg,
                    "moving_toward_road": True,
                    "vector":             [traj.dx, traj.dy],
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
                f"Track {track.track_id} moving towards road (dx={traj.dx}, dy={traj.dy}), "
                f"DistToBoundary={dist_to_boundary:.1f}px, ZoneCrowd={zone_density['level']}"
            )
            events.append(event)

        return (events, zone_density)


def _point_to_line_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Distance from point to line segment."""
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
    """
    Renders an annotated evidence frame showing bounding box,
    trajectory vector arrow, and road boundary line.
    Returns base64-encoded JPEG.
    """
    if cv2 is None or frame is None or not hasattr(frame, "copy"):
        return "data:image/jpeg;base64,/9j/4AAQSkZJRg=="

    annotated = frame.copy()
    x1, y1, x2, y2 = track.bbox

    # Draw bounding box (Crimson / Red for alert)
    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 230), 2)

    # Draw road boundary line (Yellow dashed line)
    (bx1, by1), (bx2, by2) = boundary
    cv2.line(annotated, (int(bx1), int(by1)), (int(bx2), int(by2)), (0, 215, 255), 2)

    # Draw trajectory arrow
    if track.trajectory:
        fx, fy = track.foot_point
        end_x = int(fx + track.trajectory.dx * 1.5)
        end_y = int(fy + track.trajectory.dy * 1.5)
        cv2.arrowedLine(annotated, (int(fx), int(fy)), (end_x, end_y), (0, 0, 255), 3, tipLength=0.3)

    # Add label badge
    cv2.putText(
        annotated,
        "PEDESTRIAN RISK: MOVING TOWARD ROAD",
        (max(10, x1), max(25, y1 - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 0, 255),
        2,
    )

    # Encode as JPEG
    _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 60])
    return base64.b64encode(buf).decode("utf-8")
