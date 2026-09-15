"""
Vehicle Tracking – Counting Lines & Region Counter
====================================================
Provides configurable virtual counting lines and counting regions
that use track IDs to prevent double-counting.

Counting line
-------------
A directed line segment (x1,y1)→(x2,y2) placed across the lane.
A vehicle is counted when its centroid crosses the line and:
  • It has not been counted by this line before (track_id guard).
  • Its track is CONFIRMED (min-hits passed).

Crossing direction is detected via sign change of the cross product
of the line vector and the centroid displacement vector.

Counting region (ROI)
---------------------
A polygon ROI. Vehicles *present inside* the region at a given frame
are counted per class for density estimation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

try:
    import numpy as np
except ImportError:
    np = None

logger = logging.getLogger("vehicle.counter")


# ── Vehicle class groups ──────────────────────────────────────────────────────

VEHICLE_CLASSES = {
    "car", "bus", "truck", "motorcycle",
    "auto_rickshaw", "bicycle", "van",
}

# Mapping from YOLO class names to canonical groups
CLASS_GROUP: Dict[str, str] = {
    "car":            "car",
    "bus":            "bus",
    "truck":          "truck",
    "motorcycle":     "two_wheeler",
    "auto_rickshaw":  "two_wheeler",
    "bicycle":        "two_wheeler",
    "van":            "van",
}

# Density thresholds (vehicles per counting-region area in norm. units)
DENSITY_THRESHOLDS = {
    "low":      (0.0, 0.3),
    "medium":   (0.3, 0.6),
    "high":     (0.6, 1.0),
}


def _cross_product(v: np.ndarray, w: np.ndarray) -> float:
    """2D cross product of vectors v and w."""
    return float(v[0]*w[1] - v[1]*w[0])


def _point_side(line_p1: np.ndarray, line_p2: np.ndarray, point: np.ndarray) -> float:
    """Returns sign of which side of line (p1→p2) the point is on."""
    v = line_p2 - line_p1
    w = point   - line_p1
    return _cross_product(v, w)


def _point_in_polygon(polygon: List[Tuple[float, float]], point: Tuple[float, float]) -> bool:
    """Ray-casting algorithm for point-in-polygon test."""
    x, y = point
    n = len(polygon)
    inside = False
    px, py = polygon[-1]
    for qx, qy in polygon:
        if ((py > y) != (qy > y)) and (x < (qx - px) * (y - py) / (qy - py + 1e-9) + px):
            inside = not inside
        px, py = qx, qy
    return inside


# ── Counting Line ─────────────────────────────────────────────────────────────

@dataclass
class CountingLine:
    """
    A virtual counting line across the frame.

    Parameters
    ----------
    name    : human-readable label (e.g. "Line A", "Inbound")
    x1, y1  : start point (pixels)
    x2, y2  : end point (pixels)
    direction: "any" | "in" | "out" – only count crossings in the given direction
    """
    name:      str
    x1:        float
    y1:        float
    x2:        float
    y2:        float
    direction: str = "any"     # "any" | "positive" | "negative"

    _counted_ids: Set[int] = field(default_factory=set, repr=False)
    _prev_sides:  Dict[int, float] = field(default_factory=dict, repr=False)

    # Per-class counts
    counts: Dict[str, int] = field(default_factory=lambda: {
        "car": 0, "bus": 0, "truck": 0,
        "two_wheeler": 0, "van": 0, "total": 0,
    })

    @property
    def p1(self) -> np.ndarray:
        return np.array([self.x1, self.y1])

    @property
    def p2(self) -> np.ndarray:
        return np.array([self.x2, self.y2])

    def update(self, tracks: List) -> List[Dict]:
        """
        Check each confirmed track for line crossing.
        Returns list of crossing event dicts for newly counted vehicles.
        """
        events = []
        for track in tracks:
            tid  = track.track_id
            cent = track.centroid
            side = _point_side(self.p1, self.p2, cent)

            if tid in self._counted_ids:
                continue

            prev = self._prev_sides.get(tid)
            self._prev_sides[tid] = side

            if prev is None:
                continue

            # Sign change → crossing
            if prev * side < 0:
                if self.direction == "any" or \
                   (self.direction == "positive" and prev < 0) or \
                   (self.direction == "negative" and prev > 0):
                    self._counted_ids.add(tid)
                    group = CLASS_GROUP.get(track.label, "car")
                    self.counts[group] = self.counts.get(group, 0) + 1
                    self.counts["total"] += 1
                    events.append({
                        "line":     self.name,
                        "track_id": tid,
                        "label":    track.label,
                        "group":    group,
                        "side":     "positive" if prev < 0 else "negative",
                    })
                    logger.debug(f"CountingLine[{self.name}] crossed by track {tid} ({track.label})")

        return events

    def reset_counts(self):
        for k in self.counts:
            self.counts[k] = 0
        self._counted_ids.clear()
        self._prev_sides.clear()


# ── Counting Region ───────────────────────────────────────────────────────────

@dataclass
class CountingRegion:
    """
    A polygonal region of interest for density / occupancy measurement.

    Parameters
    ----------
    name    : label (e.g. "Intersection", "Bus Stop")
    polygon : list of (x, y) pixel vertices (clockwise or CCW)
    """
    name:    str
    polygon: List[Tuple[float, float]]

    # Snapshot updated each frame
    occupancy:        Dict[str, int] = field(default_factory=lambda: {
        "car": 0, "bus": 0, "truck": 0, "two_wheeler": 0, "van": 0, "total": 0,
    })
    density_level:    str = "low"
    density_score:    float = 0.0
    _max_capacity:    int   = 20   # assumed max vehicles that fit in region

    def update(self, tracks: List) -> Dict:
        """Snapshot current occupancy for tracks inside the region."""
        for k in self.occupancy:
            self.occupancy[k] = 0

        for track in tracks:
            cx, cy = track.centroid
            if _point_in_polygon(self.polygon, (float(cx), float(cy))):
                group = CLASS_GROUP.get(track.label, "car")
                self.occupancy[group] = self.occupancy.get(group, 0) + 1
                self.occupancy["total"] += 1

        total = self.occupancy["total"]
        self.density_score = min(total / self._max_capacity, 1.0)
        if self.density_score < DENSITY_THRESHOLDS["medium"][0]:
            self.density_level = "low"
        elif self.density_score < DENSITY_THRESHOLDS["high"][0]:
            self.density_level = "medium"
        else:
            self.density_level = "high"

        return {
            "region":       self.name,
            "occupancy":    dict(self.occupancy),
            "density_score": round(self.density_score, 3),
            "density_level": self.density_level,
        }


# ── Traffic Statistics Aggregator ─────────────────────────────────────────────

class TrafficStats:
    """
    Aggregates per-frame track data into rolling statistics:
      - total / per-class vehicle counts (via counting lines)
      - per-region density
      - per-class average speed

    Call `update()` every processed frame, then `snapshot()` to get the
    current stats dict suitable for emitting as an event.
    """

    def __init__(self, lines: List[CountingLine], regions: List[CountingRegion]):
        self.lines   = lines
        self.regions = regions
        self._speed_history: Dict[str, List[float]] = {
            g: [] for g in ["car", "bus", "truck", "two_wheeler", "van", "all"]
        }
        self._max_speed_history = 120   # keep last N speed samples

    def update(
        self,
        tracks:  List,
        speeds:  Dict[int, float],   # track_id → speed km/h
    ) -> List[Dict]:
        """Update stats and return crossing events from counting lines."""
        # Lines
        all_crossing_events = []
        for line in self.lines:
            events = line.update(tracks)
            all_crossing_events.extend(events)

        # Regions
        for region in self.regions:
            region.update(tracks)

        # Speed aggregation
        active_ids = {t.track_id for t in tracks}
        for track in tracks:
            if track.track_id in speeds:
                spd = speeds[track.track_id]
                group = CLASS_GROUP.get(track.label, "car")
                self._speed_history[group].append(spd)
                self._speed_history["all"].append(spd)

        # Trim history
        for k in self._speed_history:
            if len(self._speed_history[k]) > self._max_speed_history:
                self._speed_history[k] = self._speed_history[k][-self._max_speed_history:]

        return all_crossing_events

    def snapshot(self) -> Dict:
        """Return current statistics as a serialisable dict."""
        def _avg(lst):
            return round(sum(lst)/len(lst), 1) if lst else 0.0

        # Total counts from all lines combined
        total_counts: Dict[str, int] = {
            "car": 0, "bus": 0, "truck": 0,
            "two_wheeler": 0, "van": 0, "total": 0,
        }
        for line in self.lines:
            for k in total_counts:
                total_counts[k] += line.counts.get(k, 0)

        # Density from regions
        region_snapshots = []
        for region in self.regions:
            region_snapshots.append({
                "name":          region.name,
                "total":         region.occupancy["total"],
                "density_score": region.density_score,
                "density_level": region.density_level,
                "occupancy":     dict(region.occupancy),
            })

        # Average speed per class
        avg_speeds = {k: _avg(v) for k, v in self._speed_history.items()}

        return {
            "counts":         total_counts,
            "density":        region_snapshots,
            "avg_speed_kmh":  avg_speeds,
            "lines":          [{"name": l.name, "counts": dict(l.counts)} for l in self.lines],
        }

    def reset_counts(self):
        for line in self.lines:
            line.reset_counts()
        for k in self._speed_history:
            self._speed_history[k].clear()


# ── Default counting configuration ────────────────────────────────────────────

def default_counting_config(frame_w: int = 1280, frame_h: int = 720) -> Tuple[List[CountingLine], List[CountingRegion]]:
    """
    Returns a default set of counting lines and regions for a front-facing camera.
    Positioned roughly:
      - Line A: 60% down the frame (primary counting line)
      - Line B: 40% down the frame (secondary / confirmation line)
      - Region: central lane zone for density
    """
    lines = [
        CountingLine(
            name="Line_A",
            x1=0,                  y1=frame_h * 0.60,
            x2=frame_w,            y2=frame_h * 0.60,
            direction="any",
        ),
        CountingLine(
            name="Line_B",
            x1=0,                  y1=frame_h * 0.40,
            x2=frame_w,            y2=frame_h * 0.40,
            direction="any",
        ),
    ]
    margin = frame_w * 0.1
    regions = [
        CountingRegion(
            name="Main_Lane",
            polygon=[
                (margin,            frame_h * 0.3),
                (frame_w - margin,  frame_h * 0.3),
                (frame_w - margin,  frame_h * 0.8),
                (margin,            frame_h * 0.8),
            ],
        ),
    ]
    return lines, regions
