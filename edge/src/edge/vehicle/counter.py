"""
Vehicle Tracking – Counting Lines, Regions & Traffic Density (Phase 5 - Step 13)
================================================================================
Provides virtual counting lines, ROI regions, and traffic density calculation:
  Density = Vehicles / road area (veh/m²)

Key Components:
---------------
- CountingLine: Tracks line crossings by confirmed tracks; prevents duplicate counting.
- CountingRegion: Measures vehicles present inside road polygon ROI.
- calculate_traffic_density: Standalone function computing Vehicles / road area.
- TrafficStats: Aggregates real-time rolling statistics (counts, speed, density).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

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

# Mapping from detected class names to canonical reporting groups
CLASS_GROUP: Dict[str, str] = {
    "car":            "car",
    "bus":            "bus",
    "truck":          "truck",
    "motorcycle":     "two_wheeler",
    "auto_rickshaw":  "auto_rickshaw",
    "bicycle":        "bicycle",
    "van":            "van",
}

# Density thresholds for normalized traffic score
DENSITY_THRESHOLDS = {
    "low":      (0.0, 0.35),
    "medium":   (0.35, 0.70),
    "high":     (0.70, 1.0),
}


# ── Step 13: Traffic Density Calculation ──────────────────────────────────────

def calculate_traffic_density(
    vehicle_count: int,
    road_area_sqm: float = 150.0,
    jam_density_per_sqm: float = 0.12,  # ~1 vehicle per ~8.3 sqm is bumper-to-bumper
) -> Dict[str, Any]:
    """
    Step 13: Calculate traffic density as Vehicles / road area.

    Parameters
    ----------
    vehicle_count       : number of vehicles in the road area
    road_area_sqm       : surface area of the road section in square meters
    jam_density_per_sqm : saturation capacity threshold for 100% density score

    Returns
    -------
    dict with vehicle_count, road_area_sqm, vehicles_per_sqm, density_score, density_level
    """
    area = max(1.0, float(road_area_sqm))
    count = max(0, int(vehicle_count))
    density_val = count / area

    # Normalized score 0.0 to 1.0 against road saturation threshold
    score = min(1.0, max(0.0, density_val / jam_density_per_sqm))

    if score < DENSITY_THRESHOLDS["low"][1]:
        level = "low"
    elif score < DENSITY_THRESHOLDS["medium"][1]:
        level = "medium"
    else:
        level = "high"

    return {
        "vehicle_count": count,
        "road_area_sqm": round(area, 1),
        "vehicles_per_sqm": round(density_val, 4),
        "density_score": round(score, 3),
        "density_level": level,
    }


def _cross_product(v: Tuple[float, float], w: Tuple[float, float]) -> float:
    """2D cross product of vectors v and w."""
    return float(v[0] * w[1] - v[1] * w[0])


def _point_side(line_p1: Tuple[float, float], line_p2: Tuple[float, float], point: Any) -> float:
    """Returns sign of which side of line (p1->p2) the point is on."""
    v = (line_p2[0] - line_p1[0], line_p2[1] - line_p1[1])
    w = (float(point[0]) - line_p1[0], float(point[1]) - line_p1[1])
    return _cross_product(v, w)


def _point_in_polygon(polygon: List[Tuple[float, float]], point: Tuple[float, float]) -> bool:
    """Ray-casting algorithm for point-in-polygon test."""
    x, y = point
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
    Uses persistent track IDs to ensure each vehicle is counted exactly once.
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
        "two_wheeler": 0, "auto_rickshaw": 0, "van": 0, "bicycle": 0, "total": 0,
    })

    @property
    def p1(self) -> Tuple[float, float]:
        return (float(self.x1), float(self.y1))

    @property
    def p2(self) -> Tuple[float, float]:
        return (float(self.x2), float(self.y2))

    def update(self, tracks: List[Any]) -> List[Dict[str, Any]]:
        """
        Check each confirmed track for line crossing.
        Returns list of crossing event dicts for newly counted vehicles.
        """
        events: List[Dict[str, Any]] = []
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

            # Sign change indicates crossing (including hitting or moving past line)
            crossed = (prev * side < 0) or (prev < 0 and side >= 0) or (prev > 0 and side <= 0)
            if crossed:
                if self.direction == "any" or \
                   (self.direction == "positive" and prev < 0) or \
                   (self.direction == "negative" and prev > 0):
                    self._counted_ids.add(tid)
                    group = CLASS_GROUP.get(track.label, track.label)
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
    Step 13: Polygonal ROI measuring vehicle occupancy and road area density.
    """
    name:          str
    polygon:       List[Tuple[float, float]]
    road_area_sqm: float = 150.0   # Default estimated road area in square meters

    # Snapshot updated each frame
    occupancy: Dict[str, int] = field(default_factory=lambda: {
        "car": 0, "bus": 0, "truck": 0, "two_wheeler": 0,
        "auto_rickshaw": 0, "van": 0, "bicycle": 0, "total": 0,
    })
    density_level:    str   = "low"
    density_score:    float = 0.0
    vehicles_per_sqm: float = 0.0

    def update(self, tracks: List[Any]) -> Dict[str, Any]:
        """Snapshot current occupancy for tracks inside the region."""
        for k in self.occupancy:
            self.occupancy[k] = 0

        for track in tracks:
            cx, cy = track.centroid[0], track.centroid[1]
            if _point_in_polygon(self.polygon, (float(cx), float(cy))):
                group = CLASS_GROUP.get(track.label, track.label)
                self.occupancy[group] = self.occupancy.get(group, 0) + 1
                self.occupancy["total"] += 1

        total = self.occupancy["total"]
        metrics = calculate_traffic_density(vehicle_count=total, road_area_sqm=self.road_area_sqm)
        self.density_score = metrics["density_score"]
        self.density_level = metrics["density_level"]
        self.vehicles_per_sqm = metrics["vehicles_per_sqm"]

        return {
            "region":           self.name,
            "occupancy":        dict(self.occupancy),
            "vehicle_count":    total,
            "road_area_sqm":    self.road_area_sqm,
            "vehicles_per_sqm": self.vehicles_per_sqm,
            "density_score":    self.density_score,
            "density_level":    self.density_level,
        }


# ── Traffic Statistics Aggregator ─────────────────────────────────────────────

class TrafficStats:
    """
    Aggregates per-frame track data into rolling statistics:
      - total / per-class vehicle counts (via counting lines)
      - per-region density (vehicles / road area)
      - per-class and overall average speed
    """

    def __init__(self, lines: List[CountingLine], regions: List[CountingRegion]):
        self.lines   = lines
        self.regions = regions
        self._speed_history: Dict[str, List[float]] = {
            g: [] for g in ["car", "bus", "truck", "two_wheeler", "auto_rickshaw", "van", "all"]
        }
        self._max_speed_history = 120   # keep last N speed samples

    def update(
        self,
        tracks:  List[Any],
        speeds:  Dict[int, float],   # track_id -> speed km/h
    ) -> List[Dict[str, Any]]:
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
        for track in tracks:
            if track.track_id in speeds:
                spd = speeds[track.track_id]
                group = CLASS_GROUP.get(track.label, track.label)
                if group in self._speed_history:
                    self._speed_history[group].append(spd)
                self._speed_history["all"].append(spd)

        # Trim history
        for k in self._speed_history:
            if len(self._speed_history[k]) > self._max_speed_history:
                self._speed_history[k] = self._speed_history[k][-self._max_speed_history:]

        return all_crossing_events

    def snapshot(self) -> Dict[str, Any]:
        """Return current statistics as a serialisable dict."""
        def _avg(lst: List[float]) -> float:
            return round(sum(lst) / len(lst), 1) if lst else 0.0

        # Total counts from all lines combined
        total_counts: Dict[str, int] = {
            "car": 0, "bus": 0, "truck": 0,
            "two_wheeler": 0, "auto_rickshaw": 0, "van": 0, "total": 0,
        }
        for line in self.lines:
            for k in total_counts:
                total_counts[k] += line.counts.get(k, 0)

        # Density from regions
        region_snapshots = []
        for region in self.regions:
            region_snapshots.append({
                "name":             region.name,
                "total":            region.occupancy["total"],
                "road_area_sqm":    region.road_area_sqm,
                "vehicles_per_sqm": region.vehicles_per_sqm,
                "density_score":    region.density_score,
                "density_level":    region.density_level,
                "occupancy":        dict(region.occupancy),
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
            road_area_sqm=150.0,
        ),
    ]
    return lines, regions
