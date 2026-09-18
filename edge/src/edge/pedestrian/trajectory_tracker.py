"""
Pedestrian Trajectory Tracker & Crossing Behavior Analyzer (Phase 6 - Steps 16 & 17)
=====================================================================================
Tracks pedestrian foot points across multiple frames to detect crossing behaviors:
  - NORMAL         : Person walking parallel to road
  - POTENTIAL_RISK : Person moving toward road
  - HIGH_RISK      : Person enters roadway

Also estimates:
  - Approximate bounding box size (width, height, area, aspect ratio)
  - Approximate camera distance in meters (optical height perspective proxy)
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from enum import Enum
import math
import time
from typing import Any, Dict, List, Optional, Tuple


class CrossingBehavior(str, Enum):
    """
    Step 17 Crossing Behavior Classification:
      NORMAL         -> Person walking parallel to road
      POTENTIAL_RISK -> Person moving toward road
      HIGH_RISK      -> Person enters roadway
    """
    NORMAL         = "NORMAL"
    POTENTIAL_RISK = "POTENTIAL_RISK"
    HIGH_RISK      = "HIGH_RISK"


@dataclass
class TrajectoryState:
    speed_px_s:                float
    heading_deg:               float
    dx:                        float
    dy:                        float
    moving_toward_road:        bool
    crossing_behavior:         CrossingBehavior = CrossingBehavior.NORMAL
    distance_to_boundary_px:   float = 0.0
    delta_distance_to_boundary: float = 0.0
    in_roadway:                bool = False


@dataclass
class PedestrianTrack:
    track_id:      int
    bbox:          List[int]  # [x1, y1, x2, y2]
    history:       collections.deque = field(default_factory=lambda: collections.deque(maxlen=15))
    confidence:    float = 0.8
    last_seen:     float = 0.0
    hits:          int   = 1
    trajectory:    Optional[TrajectoryState] = None

    @property
    def foot_point(self) -> Tuple[float, float]:
        """Pavement contact point (bottom-center of bounding box)."""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, float(y2))

    @property
    def approx_size(self) -> Dict[str, float]:
        """
        Step 16: Approximate size metrics from bounding box geometry.
        """
        x1, y1, x2, y2 = self.bbox
        w = max(1.0, float(x2 - x1))
        h = max(1.0, float(y2 - y1))
        return {
            "width_px": round(w, 1),
            "height_px": round(h, 1),
            "aspect_ratio": round(w / h, 2),
            "area_px": round(w * h, 1),
        }

    @property
    def approx_distance_m(self) -> float:
        """
        Step 16: Approximate distance in meters based on optical perspective:
        D = (focal_length_px * nominal_height_m) / bbox_height_px
        Using standard bus camera calibration (1000px focal length @ 720p, 1.5m nominal height).
        """
        h_px = max(8.0, float(self.bbox[3] - self.bbox[1]))
        dist = (1000.0 * 1.5) / h_px
        return round(max(1.0, min(dist, 100.0)), 1)


class PedestrianTrajectoryTracker:
    """
    Step 17: Tracks individual pedestrians over multiple frames and evaluates
    their 2D movement trajectory and crossing behavior.
    """

    def __init__(
        self,
        max_match_dist_px:     float = 90.0,
        min_hits_for_velocity: int   = 3,
        max_idle_seconds:      float = 2.0,
        road_center_x:         float = 640.0,
        road_horizon_y:        float = 360.0,
        roadway_entry_margin:  float = 15.0,
    ):
        self.max_match_dist_px = max_match_dist_px
        self.min_hits_for_velocity = min_hits_for_velocity
        self.max_idle_seconds = max_idle_seconds
        self.road_center_x = road_center_x
        self.road_horizon_y = road_horizon_y
        self.roadway_entry_margin = roadway_entry_margin

        self._next_id = 1
        self._tracks: Dict[int, PedestrianTrack] = {}

    def update(
        self,
        detections: List[Tuple[float, List[int]]],  # [(confidence, [x1, y1, x2, y2]), ...]
        current_time: Optional[float] = None,
        road_boundary_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None,
    ) -> List[PedestrianTrack]:
        now = current_time if current_time is not None else time.time()

        new_items = []
        for conf, bbox in detections:
            x1, y1, x2, y2 = bbox
            foot = ((x1 + x2) / 2.0, float(y2))
            new_items.append({"conf": conf, "bbox": bbox, "foot": foot, "matched": False})

        matched_tracks = set()

        for track_id, track in list(self._tracks.items()):
            t_x, t_y = track.foot_point
            best_idx = -1
            best_dist = float("inf")

            for idx, item in enumerate(new_items):
                if item["matched"]:
                    continue
                d_x = item["foot"][0] - t_x
                d_y = item["foot"][1] - t_y
                dist = math.hypot(d_x, d_y)
                if dist < self.max_match_dist_px and dist < best_dist:
                    best_dist = dist
                    best_idx = idx

            if best_idx != -1:
                item = new_items[best_idx]
                item["matched"] = True
                matched_tracks.add(track_id)

                track.bbox = item["bbox"]
                track.confidence = item["conf"]
                track.last_seen = now
                track.hits += 1
                track.history.append((now, item["foot"][0], item["foot"][1]))

                track.trajectory = self._compute_trajectory(track, road_boundary_line)

        for item in new_items:
            if not item["matched"]:
                t = PedestrianTrack(
                    track_id=self._next_id,
                    bbox=item["bbox"],
                    confidence=item["conf"],
                    last_seen=now,
                    hits=1,
                )
                t.history.append((now, item["foot"][0], item["foot"][1]))
                self._tracks[self._next_id] = t
                self._next_id += 1

        for tid in list(self._tracks.keys()):
            if tid not in matched_tracks and (now - self._tracks[tid].last_seen) > self.max_idle_seconds:
                del self._tracks[tid]

        return list(self._tracks.values())

    def _compute_trajectory(
        self,
        track: PedestrianTrack,
        road_boundary_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None,
    ) -> Optional[TrajectoryState]:
        """
        Step 17: Multi-frame trajectory analysis to classify crossing behavior:
          - NORMAL         : Walking parallel to road
          - POTENTIAL_RISK : Moving toward road
          - HIGH_RISK      : Enters roadway
        """
        if len(track.history) < self.min_hits_for_velocity:
            return None

        t_old, x_old, y_old = track.history[0]
        t_new, x_new, y_new = track.history[-1]
        dt = t_new - t_old

        if dt < 0.04:
            return None

        dx = x_new - x_old
        dy = y_new - y_old
        dist = math.hypot(dx, dy)
        speed = dist / dt

        heading = (math.degrees(math.atan2(dy, dx)) + 360) % 360
        foot_x, foot_y = track.foot_point

        if road_boundary_line:
            (bx1, by1), (bx2, by2) = road_boundary_line
            d_old = _point_to_line_dist(x_old, y_old, bx1, by1, bx2, by2)
            d_new = _point_to_line_dist(x_new, y_new, bx1, by1, bx2, by2)
            dist_to_boundary = d_new
            delta_d = d_new - d_old

            # Determine road vs sidewalk side based on road_center_x
            curb_x = (bx1 + bx2) / 2.0
            # Interpolate boundary line x at foot_y
            if abs(by2 - by1) > 1e-3:
                line_x_at_foot = bx1 + (foot_y - by1) * (bx2 - bx1) / (by2 - by1)
            else:
                line_x_at_foot = curb_x

            if curb_x >= self.road_center_x:
                # Right boundary: road is to the left (x <= line_x)
                in_roadway = (foot_x <= line_x_at_foot + 5.0)
            else:
                # Left boundary: road is to the right (x >= line_x)
                in_roadway = (foot_x >= line_x_at_foot - 5.0)

            if in_roadway:
                behavior = CrossingBehavior.HIGH_RISK
                toward_road = True
            elif delta_d < -2.0:
                behavior = CrossingBehavior.POTENTIAL_RISK
                toward_road = True
            else:
                behavior = CrossingBehavior.NORMAL
                toward_road = False
        else:
            # Heuristic road geometry
            dist_to_center_old = abs(x_old - self.road_center_x)
            dist_to_center_new = abs(foot_x - self.road_center_x)
            delta_center = dist_to_center_new - dist_to_center_old
            dist_to_boundary = dist_to_center_new
            delta_d = delta_center

            in_roadway = (dist_to_center_new <= 140.0)
            if in_roadway:
                behavior = CrossingBehavior.HIGH_RISK
                toward_road = True
            elif delta_center < -5.0:
                behavior = CrossingBehavior.POTENTIAL_RISK
                toward_road = True
            else:
                behavior = CrossingBehavior.NORMAL
                toward_road = False

        return TrajectoryState(
            speed_px_s=round(speed, 1),
            heading_deg=round(heading, 1),
            dx=round(dx, 1),
            dy=round(dy, 1),
            moving_toward_road=toward_road,
            crossing_behavior=behavior,
            distance_to_boundary_px=round(dist_to_boundary, 1),
            delta_distance_to_boundary=round(delta_d, 1),
            in_roadway=in_roadway,
        )

    def reset(self):
        self._tracks.clear()
        self._next_id = 1


def _point_to_line_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)
