"""
Vehicle Detection + Tracking – Main Processor
===============================================
Orchestrates the full vehicle pipeline for one camera channel:

  Frame → VehicleDetector → ByteTracker → SpeedEstimator
        → CountingLines/Regions → TrafficStats → Event JSON

Emits two types of events:
  vehicle_snapshot  – periodic stats snapshot (counts, speed, density)
  vehicle_crossing  – fired each time a vehicle crosses a counting line
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import numpy as np
except ImportError:
    np = None

from .detector      import VehicleDetector, VehicleDetectorMode
from .tracker       import ByteTracker
from .speed_estimator import SpeedEstimator, EstimationMode
from .counter       import TrafficStats, CountingLine, CountingRegion, default_counting_config

logger = logging.getLogger("vehicle.processor")

# How often (in processed frames) to emit a snapshot event
SNAPSHOT_EVERY_N_FRAMES = 30


class VehicleProcessor:
    """
    Full vehicle detection, tracking, counting, and speed estimation pipeline
    for a single camera channel.

    Parameters
    ----------
    camera_id    : e.g. "FRONT"
    bus_id       : bus identifier
    route_id     : route identifier
    mode         : VehicleDetectorMode (MODE_A or MODE_B)
    fps          : video source FPS for speed estimation
    sample_rate  : pipeline frame sample rate
    frame_w/h    : frame dimensions
    pixels_per_meter : speed calibration
    counting_lines   : optional custom CountingLine list (uses default if None)
    counting_regions : optional custom CountingRegion list
    snapshot_every   : how many processed frames between snapshot events
    """

    def __init__(
        self,
        camera_id:        str,
        bus_id:           str,
        route_id:         str  = "ROUTE_1",
        mode:             VehicleDetectorMode = VehicleDetectorMode.MODE_B,
        fps:              float = 25.0,
        sample_rate:      int   = 5,
        frame_w:          int   = 1280,
        frame_h:          int   = 720,
        pixels_per_meter: float = 45.0,
        counting_lines:   Optional[List[CountingLine]]  = None,
        counting_regions: Optional[List[CountingRegion]] = None,
        snapshot_every:   int   = SNAPSHOT_EVERY_N_FRAMES,
    ):
        self._camera_id  = camera_id
        self._bus_id     = bus_id
        self._route_id   = route_id
        self._snapshot_every = snapshot_every
        self._frame_count = 0

        # Sub-components
        self._detector = VehicleDetector(mode=mode)
        self._tracker  = ByteTracker(frame_w=frame_w, frame_h=frame_h)
        self._speed_est = SpeedEstimator(
            fps=fps,
            sample_rate=sample_rate,
            pixels_per_meter=pixels_per_meter,
            mode=EstimationMode.PIXEL_SCALE,
        )

        lines, regions = (
            (counting_lines, counting_regions)
            if counting_lines is not None
            else default_counting_config(frame_w, frame_h)
        )
        self._stats = TrafficStats(lines=lines, regions=regions)

    def process_frame(
        self,
        frame:       Optional[np.ndarray],
        gps:         Dict[str, Any],
        timestamp:   Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run full vehicle pipeline on one (sampled) frame.

        Returns a list of event dicts emitted this frame.
        (empty list on most frames; events appear on line crossings and
        every SNAPSHOT_EVERY_N_FRAMES processed frames)
        """
        self._frame_count += 1
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        events: List[Dict[str, Any]] = []

        # ── Detection ─────────────────────────────────────────────────────────
        raw_detections = self._detector.detect(frame)

        # ── Tracking ──────────────────────────────────────────────────────────
        frame_w = frame.shape[1] if (frame is not None and hasattr(frame, "shape")) else 1280
        frame_h = frame.shape[0] if (frame is not None and hasattr(frame, "shape")) else 720
        confirmed_tracks = self._tracker.update(raw_detections, frame_w=frame_w, frame_h=frame_h)

        # ── Speed estimation ───────────────────────────────────────────────────
        speeds: Dict[int, float] = {}
        for track in confirmed_tracks:
            spd = self._speed_est.estimate(track)
            if spd is not None:
                speeds[track.track_id] = spd
        active_ids = [t.track_id for t in confirmed_tracks]
        self._speed_est.cleanup(active_ids)

        # ── Counting / density update ──────────────────────────────────────────
        crossing_events = self._stats.update(confirmed_tracks, speeds)

        # Build crossing event dicts
        for ce in crossing_events:
            events.append({
                "event_id":   str(uuid.uuid4()),
                "event_type": "vehicle_crossing",
                "camera_id":  self._camera_id,
                "bus_id":     self._bus_id,
                "route_id":   self._route_id,
                "timestamp":  ts,
                "gps":        gps,
                "track_id":   ce["track_id"],
                "label":      ce["label"],
                "group":      ce["group"],
                "line":       ce["line"],
                "direction":  ce["side"],
            })

        # ── Periodic snapshot ──────────────────────────────────────────────────
        if self._frame_count % self._snapshot_every == 0:
            snap = self._stats.snapshot()
            events.append({
                "event_id":           str(uuid.uuid4()),
                "event_type":         "vehicle_snapshot",
                "camera_id":          self._camera_id,
                "bus_id":             self._bus_id,
                "route_id":           self._route_id,
                "timestamp":          ts,
                "gps":                gps,
                "active_tracks":      len(confirmed_tracks),
                "counts":             snap["counts"],
                "avg_speed_kmh":      snap["avg_speed_kmh"],
                "density":            snap["density"],
                "lines":              snap["lines"],
            })

        return events

    def reset(self):
        self._tracker.reset()
        self._stats.reset_counts()
        self._frame_count = 0

    def current_snapshot(self) -> Dict[str, Any]:
        """Synchronous stats snapshot for the WebSocket stats feed."""
        snap = self._stats.snapshot()
        return {
            "camera_id":     self._camera_id,
            "active_tracks": self._tracker.confirmed_count,
            "counts":        snap["counts"],
            "avg_speed_kmh": snap["avg_speed_kmh"],
            "density":       snap["density"],
        }
