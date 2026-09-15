"""
Historical Traffic Baseline Provider
====================================
Maintains historical speed, volume, and density baselines for road segments
indexed by road segment ID, day-of-week, and hour-of-day.

In a live smart-city deployment, these baselines are periodically updated
from aggregate edge sensor telemetry and loop detector feeds.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

from .road_segment_manager import ROAD_SEGMENTS, RoadSegment, _SEGMENT_BY_ID


@dataclass
class BaselineMetric:
    segment_id:          str
    free_flow_speed_kmh: float
    baseline_speed_kmh:  float
    baseline_density:    float
    baseline_volume_vph: int
    capacity_per_km:     int
    hour_of_day:         int
    is_peak_hour:        bool


class HistoricalTrafficBaseline:
    """
    Supplies time-dependent baseline traffic conditions for road segments.

    Parameters
    ----------
    custom_profiles : optional dictionary overriding hourly speed multipliers
                      keyed by segment_id -> list of 24 hourly speed factors (0.0 - 1.0)
    """

    # Typical urban diurnal speed factor (fraction of free-flow speed) by hour (0 to 23)
    # Reflects morning rush (8-10 AM) and evening rush (17-20 PM)
    DEFAULT_HOURLY_SPEED_FACTOR = [
        0.95, 0.98, 0.98, 0.95, 0.90, 0.85, 0.75, 0.65,  # 00:00 - 07:00
        0.55, 0.50, 0.60, 0.70, 0.75, 0.72, 0.70, 0.65,  # 08:00 - 15:00
        0.58, 0.48, 0.45, 0.52, 0.68, 0.78, 0.88, 0.92   # 16:00 - 23:00
    ]

    DEFAULT_HOURLY_DENSITY_FACTOR = [
        0.10, 0.05, 0.05, 0.08, 0.15, 0.25, 0.45, 0.65,  # 00:00 - 07:00
        0.80, 0.85, 0.70, 0.55, 0.50, 0.52, 0.55, 0.65,  # 08:00 - 15:00
        0.75, 0.90, 0.95, 0.85, 0.65, 0.45, 0.30, 0.18   # 16:00 - 23:00
    ]

    def __init__(self, custom_profiles: Optional[Dict[str, list]] = None):
        self._profiles = custom_profiles or {}

    def get_baseline(
        self,
        segment: str | RoadSegment,
        dt: Optional[datetime] = None,
    ) -> BaselineMetric:
        """
        Return the historical baseline traffic metric for a given segment and time.
        """
        if isinstance(segment, str):
            seg = _SEGMENT_BY_ID.get(segment)
            if seg is None:
                # Fallback default segment
                seg = RoadSegment(
                    segment_id=segment,
                    name=f"Segment {segment}",
                    road_type="arterial",
                    city="Unknown",
                    polyline=[],
                    capacity_per_km=80,
                    free_flow_speed_kmh=50.0,
                )
        else:
            seg = segment

        now = dt or datetime.now(timezone.utc)
        hour = now.hour

        # Check if custom profile exists, else use standard diurnal pattern
        speed_factors = self._profiles.get(seg.segment_id, self.DEFAULT_HOURLY_SPEED_FACTOR)
        speed_factor = speed_factors[hour % 24]
        density_factor = self.DEFAULT_HOURLY_DENSITY_FACTOR[hour % 24]

        # Weekend adjustment (Saturday=5, Sunday=6)
        if now.weekday() >= 5:
            speed_factor = min(1.0, speed_factor * 1.15)
            density_factor = max(0.05, density_factor * 0.75)

        is_peak = hour in (8, 9, 10, 17, 18, 19, 20)
        baseline_speed = round(seg.free_flow_speed_kmh * speed_factor, 1)
        baseline_density = round(density_factor, 2)
        baseline_volume = int(seg.capacity_per_km * density_factor * (baseline_speed / max(1.0, seg.free_flow_speed_kmh)))

        return BaselineMetric(
            segment_id=seg.segment_id,
            free_flow_speed_kmh=seg.free_flow_speed_kmh,
            baseline_speed_kmh=baseline_speed,
            baseline_density=baseline_density,
            baseline_volume_vph=baseline_volume,
            capacity_per_km=seg.capacity_per_km,
            hour_of_day=hour,
            is_peak_hour=is_peak,
        )
