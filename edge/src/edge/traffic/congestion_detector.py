"""
Traffic Bottleneck Detection Service
====================================
Evaluates real-time traffic sensor inputs:
  - Vehicle count
  - Vehicle density
  - Average speed
  - Road segment
  - Timestamp
  - GPS
  - Historical traffic baseline

Congestion Score Levels:
  LOW     (0.0 - 29.9)
  MEDIUM  (30.0 - 59.9)
  HIGH    (60.0 - 79.9)
  SEVERE  (80.0 - 100.0)

Bottleneck Condition:
  High vehicle density AND Low average speed AND Persistent for a time window.
  CRITICAL GUARD: Never classifies a single slow vehicle (or isolated tracks)
  as a bottleneck.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Deque, Dict, List, Optional
import uuid

from .historical_baseline import HistoricalTrafficBaseline, BaselineMetric
from .road_segment_manager import ROAD_SEGMENTS, RoadSegment, _SEGMENT_BY_ID

logger = logging.getLogger("traffic.congestion_detector")


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    SEVERE = "SEVERE"


@dataclass
class CongestionObservation:
    timestamp_epoch:         float
    vehicle_count:           int
    density:                 float
    average_speed:           float
    congestion_score:        float
    severity:                Severity
    is_bottleneck_candidate: bool


@dataclass
class CongestionEvent:
    event_id:         str
    road_segment:     str
    segment_name:     str
    density:          float
    average_speed:    float
    congestion_score: float
    severity:         str   # "LOW" | "MEDIUM" | "HIGH" | "SEVERE"
    timestamp:        str
    location:         Dict[str, float]  # {"lat": float, "lon": float}
    vehicle_count:    int   = 0
    duration_seconds: float = 0.0
    is_bottleneck:    bool  = False
    bus_id:           Optional[str] = None
    camera_id:        Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":         self.event_id,
            "event_type":       "congestion_event",
            "road_segment":     self.road_segment,
            "segment_name":     self.segment_name,
            "density":          round(self.density, 3),
            "average_speed":    round(self.average_speed, 1),
            "congestion_score": round(self.congestion_score, 1),
            "severity":         self.severity,
            "timestamp":        self.timestamp,
            "location":         self.location,
            "vehicle_count":    self.vehicle_count,
            "duration_seconds": round(self.duration_seconds, 1),
            "is_bottleneck":    self.is_bottleneck,
            "bus_id":           self.bus_id,
            "camera_id":        self.camera_id,
        }


class CongestionDetector:
    """
    Evaluates real-time traffic conditions and detects persistent bottlenecks.

    Parameters
    ----------
    baseline_provider          : HistoricalTrafficBaseline instance
    min_bottleneck_vehicles    : Minimum vehicle count required to trigger bottleneck
                                 (prevents single slow vehicle false positives, default 3)
    density_bottleneck_thresh  : Density threshold to flag bottleneck candidate (default 0.55)
    speed_drop_ratio_thresh    : Drop below baseline speed to flag bottleneck (default 0.45)
    absolute_low_speed_kmh     : Low speed threshold regardless of baseline (default 18.0 km/h)
    persistence_window_sec     : Sliding time window for persistence verification (default 20s)
    min_persistent_samples     : Minimum candidate samples within window (default 3)
    cooldown_sec               : Minimum seconds between re-firing alert for same segment (default 15s)
    """

    def __init__(
        self,
        baseline_provider:         Optional[HistoricalTrafficBaseline] = None,
        min_bottleneck_vehicles:   int   = 3,
        density_bottleneck_thresh: float = 0.55,
        speed_drop_ratio_thresh:   float = 0.45,
        absolute_low_speed_kmh:    float = 18.0,
        persistence_window_sec:    float = 20.0,
        min_persistent_samples:    int   = 3,
        cooldown_sec:              float = 15.0,
    ):
        self.baseline_provider = baseline_provider or HistoricalTrafficBaseline()
        self.min_bottleneck_vehicles = min_bottleneck_vehicles
        self.density_bottleneck_thresh = density_bottleneck_thresh
        self.speed_drop_ratio_thresh = speed_drop_ratio_thresh
        self.absolute_low_speed_kmh = absolute_low_speed_kmh
        self.persistence_window_sec = persistence_window_sec
        self.min_persistent_samples = min_persistent_samples
        self.cooldown_sec = cooldown_sec

        # Sliding window buffer per segment: segment_id -> deque of CongestionObservation
        self._history: Dict[str, Deque[CongestionObservation]] = collections.defaultdict(
            lambda: collections.deque()
        )
        # Last alert timestamp per segment
        self._last_alert_time: Dict[str, float] = {}

    def calculate_congestion_score(
        self,
        vehicle_count: int,
        density:       float,
        average_speed: float,
        baseline:      BaselineMetric,
    ) -> float:
        """
        Calculates normalized Congestion Score from 0.0 to 100.0.

        Formula:
          Speed Deficit Ratio: S_def = max(0, (V_baseline - V_avg) / V_baseline)
          Density Factor:      D_fac = min(1.0, max(0.0, density))
          Raw Score:           100 * (0.55 * S_def + 0.45 * D_fac)

        CRITICAL GUARD:
          If vehicle_count < min_bottleneck_vehicles, an isolated slow car or
          bus stopping at a bus stop must NEVER produce a high or severe score.
        """
        v_base = max(10.0, baseline.baseline_speed_kmh)
        speed_deficit = max(0.0, min(1.0, (v_base - average_speed) / v_base))
        density_factor = max(0.0, min(1.0, density))

        raw_score = 100.0 * (0.55 * speed_deficit + 0.45 * density_factor)

        # Single or dual vehicle suppression guard
        if vehicle_count < self.min_bottleneck_vehicles:
            # Dampen score significantly: isolated vehicle cannot dominate segment traffic state
            vehicle_factor = vehicle_count / max(1, self.min_bottleneck_vehicles)
            raw_score = min(raw_score * 0.4 * vehicle_factor, 28.0)

        return max(0.0, min(100.0, round(raw_score, 1)))

    @staticmethod
    def score_to_severity(score: float) -> Severity:
        """Map score 0-100 to Severity enum."""
        if score >= 80.0:
            return Severity.SEVERE
        elif score >= 60.0:
            return Severity.HIGH
        elif score >= 30.0:
            return Severity.MEDIUM
        return Severity.LOW

    def evaluate(
        self,
        vehicle_count: int,
        density:       float,
        average_speed: float,
        road_segment:  str | RoadSegment,
        timestamp:     Optional[str] = None,
        gps:           Optional[Dict[str, float]] = None,
        bus_id:        Optional[str] = None,
        camera_id:     Optional[str] = None,
    ) -> Optional[CongestionEvent]:
        """
        Evaluate traffic parameters for a road segment and generate a CongestionEvent
        if a persistent bottleneck is verified.
        """
        # Resolve road segment
        if isinstance(road_segment, str):
            seg = _SEGMENT_BY_ID.get(road_segment)
            seg_id = road_segment
            seg_name = seg.name if seg else f"Segment {road_segment}"
        else:
            seg = road_segment
            seg_id = seg.segment_id
            seg_name = seg.name

        # Timestamp and epoch
        now_dt = datetime.now(timezone.utc)
        if timestamp:
            try:
                now_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except Exception:
                pass
        now_epoch = now_dt.timestamp()
        ts_str = timestamp or now_dt.isoformat()

        # Historical baseline lookup
        baseline = self.baseline_provider.get_baseline(seg or seg_id, now_dt)

        # 1. Congestion score
        score = self.calculate_congestion_score(
            vehicle_count=vehicle_count,
            density=density,
            average_speed=average_speed,
            baseline=baseline,
        )
        severity = self.score_to_severity(score)

        # 2. Bottleneck candidate condition:
        # - Must have sufficient vehicles (GUARD: not a single slow vehicle!)
        # - High vehicle density
        # - Low average speed (relative to baseline or absolute)
        speed_deficit = max(0.0, (baseline.baseline_speed_kmh - average_speed) / max(1.0, baseline.baseline_speed_kmh))
        is_candidate = (
            vehicle_count >= self.min_bottleneck_vehicles
            and density >= self.density_bottleneck_thresh
            and (speed_deficit >= self.speed_drop_ratio_thresh or average_speed <= self.absolute_low_speed_kmh)
        )

        # 3. Maintain sliding persistence window
        history = self._history[seg_id]
        obs = CongestionObservation(
            timestamp_epoch=now_epoch,
            vehicle_count=vehicle_count,
            density=density,
            average_speed=average_speed,
            congestion_score=score,
            severity=severity,
            is_bottleneck_candidate=is_candidate,
        )
        history.append(obs)

        # Prune old observations outside persistence window
        cutoff = now_epoch - self.persistence_window_sec
        while history and history[0].timestamp_epoch < cutoff:
            history.popleft()

        # Count candidate observations within window
        candidate_samples = sum(1 for o in history if o.is_bottleneck_candidate)
        earliest_epoch = history[0].timestamp_epoch if history else now_epoch
        window_duration = max(0.0, now_epoch - earliest_epoch)

        # Check persistence condition
        is_persistent_bottleneck = (
            candidate_samples >= self.min_persistent_samples
            and (window_duration >= min(self.persistence_window_sec * 0.6, 12.0) or len(history) >= self.min_persistent_samples)
        )

        # Location fallback
        loc = gps or (
            {"lat": seg.midpoint.lat, "lon": seg.midpoint.lon}
            if seg and hasattr(seg, "midpoint")
            else {"lat": 28.6139, "lon": 77.2090}
        )

        # If persistent bottleneck condition is met:
        if is_persistent_bottleneck:
            # Upgrade severity if score was moderate but persistence proves jam
            effective_severity = severity
            if effective_severity in (Severity.LOW, Severity.MEDIUM):
                effective_severity = Severity.HIGH
                score = max(score, 65.0)

            last_alert = self._last_alert_time.get(seg_id, 0.0)
            if (now_epoch - last_alert) >= self.cooldown_sec:
                self._last_alert_time[seg_id] = now_epoch
                event = CongestionEvent(
                    event_id=str(uuid.uuid4()),
                    road_segment=seg_id,
                    segment_name=seg_name,
                    density=density,
                    average_speed=average_speed,
                    congestion_score=score,
                    severity=effective_severity.value,
                    timestamp=ts_str,
                    location=loc,
                    vehicle_count=vehicle_count,
                    duration_seconds=round(window_duration, 1),
                    is_bottleneck=True,
                    bus_id=bus_id,
                    camera_id=camera_id,
                )
                logger.warning(
                    f"BOTTLENECK DETECTED on {seg_name} ({seg_id}): "
                    f"Severity={effective_severity.value}, Score={score}, "
                    f"Speed={average_speed:.1f}km/h (Base={baseline.baseline_speed_kmh:.1f}), "
                    f"Density={density:.2f}, Vehicles={vehicle_count}, Duration={window_duration:.1f}s"
                )
                return event

        return None

    def get_current_status(
        self,
        segment_id: str,
        gps: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Get the current aggregated snapshot for a segment from recent observations.
        """
        seg = _SEGMENT_BY_ID.get(segment_id)
        seg_name = seg.name if seg else f"Segment {segment_id}"
        baseline = self.baseline_provider.get_baseline(segment_id)

        history = self._history.get(segment_id)
        if not history:
            return {
                "road_segment":     segment_id,
                "segment_name":     seg_name,
                "density":          0.1,
                "average_speed":    baseline.baseline_speed_kmh,
                "congestion_score": 10.0,
                "severity":         Severity.LOW.value,
                "is_bottleneck":    False,
                "vehicle_count":    0,
                "baseline_speed":   baseline.baseline_speed_kmh,
                "free_flow_speed":  baseline.free_flow_speed_kmh,
            }

        latest = history[-1]
        is_bottleneck = any(o.is_bottleneck_candidate for o in history)
        return {
            "road_segment":     segment_id,
            "segment_name":     seg_name,
            "density":          latest.density,
            "average_speed":    latest.average_speed,
            "congestion_score": latest.congestion_score,
            "severity":         latest.severity.value,
            "is_bottleneck":    is_bottleneck,
            "vehicle_count":    latest.vehicle_count,
            "baseline_speed":   baseline.baseline_speed_kmh,
            "free_flow_speed":  baseline.free_flow_speed_kmh,
        }

    def reset(self):
        self._history.clear()
        self._last_alert_time.clear()
