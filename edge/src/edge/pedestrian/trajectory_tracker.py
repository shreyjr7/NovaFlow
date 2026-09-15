"""
Pedestrian Trajectory Tracker & Road Boundary Motion Analyzer
=============================================================
Tracks individual pedestrians over sampled camera frames, calculates
their 2D movement trajectory vectors, and determines whether their heading
indicates movement towards the vehicular roadway.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
import math
import time
from typing import Dict, List, Optional, Tuple


@dataclass
class TrajectoryState:
    speed_px_s:         float
    heading_deg:        float
    dx:                 float
    dy:                 float
    moving_toward_road: bool


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


class PedestrianTrajectoryTracker:
    """
    Lightweight centroid & foot-point tracker tailored for pedestrian trajectories.

    Parameters
    ----------
    max_match_dist_px : Max pixel distance between consecutive frames to link a track
    min_hits_for_velocity : Minimum frame observations needed to calculate trajectory
    max_idle_seconds : Maximum time to retain unmatched track before deleting
    """

    def __init__(
        self,
        max_match_dist_px:     float = 90.0,
        min_hits_for_velocity: int   = 3,
        max_idle_seconds:      float = 2.0,
        road_center_x:         float = 640.0,
        road_horizon_y:        float = 360.0,
    ):
        self.max_match_dist_px = max_match_dist_px
        self.min_hits_for_velocity = min_hits_for_velocity
        self.max_idle_seconds = max_idle_seconds
        self.road_center_x = road_center_x
        self.road_horizon_y = road_horizon_y

        self._next_id = 1
        self._tracks: Dict[int, PedestrianTrack] = {}

    def update(
        self,
        detections: List[Tuple[float, List[int]]],  # [(confidence, [x1, y1, x2, y2]), ...]
        current_time: Optional[float] = None,
        road_boundary_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None,
    ) -> List[PedestrianTrack]:
        """
        Associate detections with existing tracks and update trajectory vectors.
        """
        now = current_time if current_time is not None else time.time()

        # Extract foot points of new detections
        new_items = []
        for conf, bbox in detections:
            x1, y1, x2, y2 = bbox
            foot = ((x1 + x2) / 2.0, float(y2))
            new_items.append({"conf": conf, "bbox": bbox, "foot": foot, "matched": False})

        matched_tracks = set()

        # Greedy nearest-distance matching
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

                # Calculate trajectory
                track.trajectory = self._compute_trajectory(track, road_boundary_line)

        # Create new tracks for unmatched detections
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

        # Purge stale tracks
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
        Computes velocity and direction, and evaluates if the vector heads toward the road.
        """
        if len(track.history) < self.min_hits_for_velocity:
            return None

        # Compare oldest and newest in history window
        t_old, x_old, y_old = track.history[0]
        t_new, x_new, y_new = track.history[-1]
        dt = t_new - t_old

        if dt < 0.05:
            return None

        dx = x_new - x_old
        dy = y_new - y_old
        dist = math.hypot(dx, dy)
        speed = dist / dt

        # Heading angle in degrees [0, 360)
        heading = (math.degrees(math.atan2(dy, dx)) + 360) % 360

        # Evaluate if heading indicates movement towards the road:
        # In typical camera geometry:
        # If pedestrian is on left sidewalk (x < road_center_x), moving right (dx > 0) is toward road.
        # If pedestrian is on right sidewalk (x > road_center_x), moving left (dx < 0) is toward road.
        # Also stepping down into the foreground street (dy > 0) indicates entering the roadway.
        foot_x, foot_y = track.foot_point
        toward_road = False

        if road_boundary_line:
            # Distance from start of track window vs current foot position
            (bx1, by1), (bx2, by2) = road_boundary_line
            d_old = _point_to_line_dist(x_old, y_old, bx1, by1, bx2, by2)
            d_new = _point_to_line_dist(x_new, y_new, bx1, by1, bx2, by2)
            toward_road = (d_new < d_old - 2.0)
        else:
            # Heuristic road geometry:
            # Curbside left: movement to the right (dx > 5)
            # Curbside right: movement to the left (dx < -5)
            # Stepping into carriageway: dy > 5
            if foot_x < self.road_center_x and dx > 6.0:
                toward_road = True
            elif foot_x > self.road_center_x and dx < -6.0:
                toward_road = True
            elif dy > 10.0:  # Moving down towards the vehicle path
                toward_road = True

        return TrajectoryState(
            speed_px_s=round(speed, 1),
            heading_deg=round(heading, 1),
            dx=round(dx, 1),
            dy=round(dy, 1),
            moving_toward_road=toward_road,
        )

    def reset(self):
        self._tracks.clear()
        self._next_id = 1


def _point_to_line_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Distance from (px, py) to line segment (x1, y1) -> (x2, y2)."""
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)
