"""
Explainable Trajectory Signals & Compound Anomaly Condition
===========================================================
Evaluates vehicle trajectories for anomalous physical behavior without asserting
legal fault or criminal culpability.

Seven Explainable Signals:
  1. sudden_deceleration:      Delta v < -15 km/h or a < -4.5 m/s^2
  2. abrupt_heading_change:    |Delta theta| > 35 deg
  3. trajectory_discontinuity: Unexpected positional jump > 75 px
  4. vehicle_interaction:      Inter-vehicle distance < 2.5m or bbox overlap
  5. object_disappearance:     Track vanished within 1.5s of close interaction
  6. unusual_acceleration:     a > 4.0 m/s^2 or rapid speed increase post-event
  7. vehicle_leaving_scene:    Vehicle speeds away while interacting object is missing/stopped

Compound Condition:
  Solitary hard-braking is NOT an incident. An incident is only flagged when
  compound conditions (multiple corroborating physical signals) are met.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SignalResult:
    name: str
    triggered: bool
    value: float
    threshold: float
    unit: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "triggered": self.triggered,
            "value": round(self.value, 2),
            "threshold": round(self.threshold, 2),
            "unit": self.unit,
            "description": self.description,
        }


@dataclass
class VehicleTrackState:
    track_id: int
    class_name: str
    speed_kmh: float
    bbox: List[int]  # [x1, y1, x2, y2]
    heading_deg: float = 0.0
    prev_speed_kmh: Optional[float] = None
    prev_heading_deg: Optional[float] = None
    prev_bbox: Optional[List[int]] = None
    acceleration_m_s2: float = 0.0
    disappeared: bool = False
    disappeared_at_s: Optional[float] = None
    had_recent_interaction: bool = False
    interaction_track_id: Optional[int] = None

    @property
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def prev_center(self) -> Optional[Tuple[float, float]]:
        if not self.prev_bbox:
            return None
        x1, y1, x2, y2 = self.prev_bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _heading_diff(h1: float, h2: float) -> float:
    """Computes the shortest angular difference in degrees between two headings [0, 360)."""
    diff = (h2 - h1 + 180.0) % 360.0 - 180.0
    return abs(diff)


def _bbox_iou(boxA: List[int], boxB: List[int]) -> float:
    """Calculate Intersection over Union between two bounding boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_w = max(0, xB - xA)
    inter_h = max(0, yB - yA)
    inter_area = inter_w * inter_h
    if inter_area == 0:
        return 0.0

    areaA = max(1, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    areaB = max(1, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))
    union_area = float(areaA + areaB - inter_area)
    return inter_area / union_area if union_area > 0 else 0.0


def _pixel_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


class TrajectorySignalEvaluator:
    """
    Evaluates the 7 explainable signals between primary track and nearby vehicles,
    then applies the compound condition guard.
    """

    DECELERATION_SPEED_DELTA_THRESH = -15.0   # km/h
    DECELERATION_ACCEL_THRESH       = -4.5    # m/s^2
    HEADING_CHANGE_THRESH_DEG       = 35.0    # deg
    DISCONTINUITY_PIXEL_THRESH      = 75.0    # px
    INTERACTION_PIXEL_THRESH        = 70.0    # px
    INTERACTION_IOU_THRESH          = 0.04    # overlap
    ACCELERATION_ACCEL_THRESH       = 4.0     # m/s^2
    LEAVING_SCENE_SPEED_THRESH      = 28.0    # km/h

    def evaluate_signals(
        self,
        primary_track: VehicleTrackState,
        nearby_tracks: List[VehicleTrackState],
        dt: float = 0.2,
    ) -> Dict[str, SignalResult]:
        """
        Calculates the 7 explainable signals for a primary vehicle track.
        """
        results: Dict[str, SignalResult] = {}

        # 1. Sudden Deceleration
        speed_delta = 0.0
        accel = primary_track.acceleration_m_s2
        if primary_track.prev_speed_kmh is not None:
            speed_delta = primary_track.speed_kmh - primary_track.prev_speed_kmh
            if dt > 0:
                accel = (speed_delta / 3.6) / dt

        is_sudden_decel = (
            speed_delta <= self.DECELERATION_SPEED_DELTA_THRESH
            or accel <= self.DECELERATION_ACCEL_THRESH
        )
        results["sudden_deceleration"] = SignalResult(
            name="sudden_deceleration",
            triggered=is_sudden_decel,
            value=accel,
            threshold=self.DECELERATION_ACCEL_THRESH,
            unit="m/s^2",
            description=f"Rapid deceleration (a={accel:.1f} m/s^2, delta_v={speed_delta:.1f} km/h)",
        )

        # 2. Abrupt Heading Change
        heading_change = 0.0
        if primary_track.prev_heading_deg is not None:
            heading_change = _heading_diff(primary_track.prev_heading_deg, primary_track.heading_deg)
        is_abrupt_turn = heading_change >= self.HEADING_CHANGE_THRESH_DEG
        results["abrupt_heading_change"] = SignalResult(
            name="abrupt_heading_change",
            triggered=is_abrupt_turn,
            value=heading_change,
            threshold=self.HEADING_CHANGE_THRESH_DEG,
            unit="deg",
            description=f"Abrupt yaw or heading deviation ({heading_change:.1f} deg)",
        )

        # 3. Sudden Trajectory Discontinuity
        disp_px = 0.0
        if primary_track.prev_center is not None:
            disp_px = _pixel_distance(primary_track.center, primary_track.prev_center)
        is_discontinuity = disp_px >= self.DISCONTINUITY_PIXEL_THRESH
        results["trajectory_discontinuity"] = SignalResult(
            name="trajectory_discontinuity",
            triggered=is_discontinuity,
            value=disp_px,
            threshold=self.DISCONTINUITY_PIXEL_THRESH,
            unit="px",
            description=f"Sharp positional displacement jump ({disp_px:.1f} px)",
        )

        # 4. Nearby Vehicle Interaction
        min_dist_px = 9999.0
        max_iou = 0.0

        for other in nearby_tracks:
            if other.track_id == primary_track.track_id:
                continue
            dist = _pixel_distance(primary_track.center, other.center)
            iou = _bbox_iou(primary_track.bbox, other.bbox)
            if dist < min_dist_px:
                min_dist_px = dist
            if iou > max_iou:
                max_iou = iou
            if dist <= self.INTERACTION_PIXEL_THRESH or iou >= self.INTERACTION_IOU_THRESH:
                primary_track.had_recent_interaction = True
                primary_track.interaction_track_id = other.track_id

        is_interaction = (
            min_dist_px <= self.INTERACTION_PIXEL_THRESH
            or max_iou >= self.INTERACTION_IOU_THRESH
            or primary_track.had_recent_interaction
        )
        results["nearby_vehicle_interaction"] = SignalResult(
            name="nearby_vehicle_interaction",
            triggered=is_interaction,
            value=min_dist_px,
            threshold=self.INTERACTION_PIXEL_THRESH,
            unit="px",
            description=f"Close proximity / overlap with adjacent vehicle (min_dist={min_dist_px:.1f} px, iou={max_iou:.2f})",
        )

        # 5. Object Disappearance After Interaction
        disappeared_nearby = any(
            (other.disappeared or (other.track_id == primary_track.interaction_track_id and other.disappeared))
            for other in nearby_tracks
        )
        is_disappearance = (
            (primary_track.disappeared and primary_track.had_recent_interaction)
            or (primary_track.had_recent_interaction and disappeared_nearby)
        )
        results["object_disappearance_after_interaction"] = SignalResult(
            name="object_disappearance_after_interaction",
            triggered=is_disappearance,
            value=1.0 if is_disappearance else 0.0,
            threshold=1.0,
            unit="binary",
            description="Vehicle track vanished from sensor view immediately following close proximity interaction",
        )

        # 6. Unusual Acceleration
        accel_val = primary_track.acceleration_m_s2
        if speed_delta > 0 and dt > 0:
            accel_val = (speed_delta / 3.6) / dt
        is_unusual_accel = accel_val >= self.ACCELERATION_ACCEL_THRESH
        results["unusual_acceleration"] = SignalResult(
            name="unusual_acceleration",
            triggered=is_unusual_accel,
            value=accel_val,
            threshold=self.ACCELERATION_ACCEL_THRESH,
            unit="m/s^2",
            description=f"High post-event acceleration spike (a={accel_val:.1f} m/s^2)",
        )

        # 7. Vehicle Leaving Scene After Anomaly
        is_leaving_scene = False
        if primary_track.had_recent_interaction and (is_disappearance or is_sudden_decel or is_abrupt_turn):
            if primary_track.speed_kmh >= self.LEAVING_SCENE_SPEED_THRESH or is_unusual_accel:
                is_leaving_scene = True

        results["vehicle_leaving_scene"] = SignalResult(
            name="vehicle_leaving_scene",
            triggered=is_leaving_scene,
            value=primary_track.speed_kmh,
            threshold=self.LEAVING_SCENE_SPEED_THRESH,
            unit="km/h",
            description=f"Vehicle rapidly departing scene post-interaction (speed={primary_track.speed_kmh:.1f} km/h)",
        )

        return results

    def evaluate_compound_condition(
        self,
        signals: Dict[str, SignalResult],
    ) -> Tuple[bool, str, float]:
        """
        Enforces compound condition rules:
          - A single hard-braking event alone MUST NOT trigger an incident.
          - Returns (is_incident, anomaly_category, compound_confidence).
        """
        triggered_names = {k for k, v in signals.items() if v.triggered}

        # Guard: Solitary hard-braking check
        if triggered_names == {"sudden_deceleration"}:
            return False, "HARD_BRAKING_NORMAL", 0.0

        # Step 18 Explainable Rule: Sudden decel + Abrupt heading change + Nearby anomaly
        if (
            "sudden_deceleration" in triggered_names
            and "abrupt_heading_change" in triggered_names
            and "nearby_vehicle_interaction" in triggered_names
        ):
            conf = 0.76 + (0.05 * len(triggered_names))
            return True, "POTENTIAL_INCIDENT", min(0.95, conf)

        # Hit-and-run signature:
        # Interaction + (Disappearance OR Discontinuity) + Leaving scene
        if "vehicle_leaving_scene" in triggered_names and (
            "object_disappearance_after_interaction" in triggered_names
            or "nearby_vehicle_interaction" in triggered_names
        ):
            conf = 0.70 + (0.08 * len(triggered_names))
            return True, "HIT_AND_RUN_SIGNATURE", min(0.96, conf)

        # Collision / Interaction Anomaly:
        # Interaction + (Sudden Deceleration OR Heading Change OR Discontinuity)
        if "nearby_vehicle_interaction" in triggered_names and (
            "sudden_deceleration" in triggered_names
            or "abrupt_heading_change" in triggered_names
            or "trajectory_discontinuity" in triggered_names
        ):
            conf = 0.65 + (0.07 * len(triggered_names))
            return True, "COLLISION_RISK", min(0.95, conf)

        # Severe Trajectory Discontinuity + Heading Deviation
        if "trajectory_discontinuity" in triggered_names and "abrupt_heading_change" in triggered_names:
            conf = 0.60 + (0.06 * len(triggered_names))
            return True, "TRAJECTORY_ANOMALY", min(0.90, conf)

        # Object Disappearance + Deceleration
        if "object_disappearance_after_interaction" in triggered_names and "sudden_deceleration" in triggered_names:
            conf = 0.72 + (0.05 * len(triggered_names))
            return True, "COLLISION_RISK", min(0.94, conf)

        # Default: Not enough corroborating signals
        return False, "NORMAL_DRIVING", 0.0


# ── Step 18: Explainable Trajectory Rule ──────────────────────────────────────

def check_explainable_incident_rule(
    sudden_deceleration: bool,
    abrupt_heading_change: bool,
    nearby_vehicle_anomaly: bool,
) -> bool:
    """
    Step 18: Explainable physical trajectory rule:
      Sudden deceleration + Abrupt heading change + Nearby vehicle trajectory anomaly
      -> Potential incident

    Replaces black-box 'accident classifiers' with transparent physical signals.
    """
    return sudden_deceleration and abrupt_heading_change and nearby_vehicle_anomaly
