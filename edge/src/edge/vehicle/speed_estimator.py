"""
Vehicle Tracking – Speed Estimator (Phase 5 - Step 14)
======================================================
Estimates vehicle speed (km/h) from track centroid displacement across frames.

Two estimation strategies
--------------------------
PIXEL_SCALE   – pixels/frame × calibration_scale → km/h
HOMOGRAPHY    – 4-point ground-plane homography maps pixel coords to metric coords.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
except ImportError:
    np = None

logger = logging.getLogger("vehicle.speed_estimator")


class EstimationMode(str, Enum):
    PIXEL_SCALE = "PIXEL_SCALE"
    HOMOGRAPHY  = "HOMOGRAPHY"


@dataclass
class SpeedRecord:
    track_id:    int
    label:       str
    speed_kmh:   float
    smoothed_kmh: float


class SpeedEstimator:
    """
    Step 14: Estimates per-track vehicle speed from centroid trajectories.
    """

    def __init__(
        self,
        fps:              float = 25.0,
        sample_rate:      int   = 5,
        pixels_per_meter: float = 45.0,
        mode:             EstimationMode = EstimationMode.PIXEL_SCALE,
        homography_src:   Optional[List[List[float]]] = None,
        homography_dst:   Optional[List[List[float]]] = None,
        smooth_window:    int   = 10,
        min_track_len:    int   = 3,
    ):
        self._fps              = fps
        self._sample_rate      = sample_rate
        self._ppm              = pixels_per_meter
        self._mode             = mode
        self._smooth_window    = smooth_window
        self._min_track_len    = min_track_len
        self._ema: Dict[int, float] = {}   # track_id -> current EMA speed

        # Homography matrix (computed once if src/dst provided)
        self._H: Optional[Any] = None
        if mode == EstimationMode.HOMOGRAPHY and homography_src and homography_dst:
            try:
                import cv2
                if np is not None:
                    src = np.array(homography_src, dtype=np.float32)
                    dst = np.array(homography_dst, dtype=np.float32)
                    self._H, _ = cv2.findHomography(src, dst)
                    logger.info("Homography matrix computed successfully.")
            except Exception as e:
                logger.warning(f"Homography setup failed ({e}) – falling back to PIXEL_SCALE.")
                self._mode = EstimationMode.PIXEL_SCALE

    def estimate(self, track: Any) -> Optional[float]:
        """
        Estimate the current speed for a Track object.
        Returns smoothed speed in km/h, or None if track history is too short.
        """
        if len(track.centroids) < self._min_track_len:
            return None

        # Use the last two centroids
        c1 = track.centroids[-2]
        c2 = track.centroids[-1]

        if self._mode == EstimationMode.HOMOGRAPHY and self._H is not None:
            speed_kmh = self._speed_homography(c1, c2)
        else:
            speed_kmh = self._speed_pixel_scale(c1, c2)

        # Clamp to plausible urban speed range (0 to 140 km/h)
        speed_kmh = max(0.0, min(speed_kmh, 140.0))

        # Exponential moving average smoothing
        alpha = 2.0 / (self._smooth_window + 1)
        prev  = self._ema.get(track.track_id, speed_kmh)
        smoothed = alpha * speed_kmh + (1 - alpha) * prev
        self._ema[track.track_id] = smoothed

        return round(smoothed, 1)

    def cleanup(self, active_track_ids: List[int]):
        """Remove EMA records for tracks that are no longer active."""
        gone = [tid for tid in self._ema if tid not in active_track_ids]
        for tid in gone:
            del self._ema[tid]

    # ── Private helpers ────────────────────────────────────────────────────────

    def _speed_pixel_scale(self, c1: Any, c2: Any) -> float:
        """Pixel displacement -> speed using pixel-per-metre calibration."""
        dt_sec = self._sample_rate / self._fps
        if dt_sec <= 0:
            return 0.0
        dx = float(c2[0] - c1[0])
        dy = float(c2[1] - c1[1])
        dist_px = math.sqrt(dx * dx + dy * dy)
        dist_m = dist_px / max(1.0, self._ppm)
        speed_ms = dist_m / dt_sec
        return speed_ms * 3.6   # m/s -> km/h

    def _speed_homography(self, c1: Any, c2: Any) -> float:
        """Map centroids to ground plane via homography, then compute speed."""
        try:
            import cv2
            p = np.array([[[float(c1[0]), float(c1[1])]], [[float(c2[0]), float(c2[1])]]], dtype=np.float32)
            t = cv2.perspectiveTransform(p, self._H)
            w1, w2 = t[0][0], t[1][0]
            dx = float(w2[0] - w1[0])
            dy = float(w2[1] - w1[1])
            dist_m = math.sqrt(dx * dx + dy * dy)
            dt_sec = self._sample_rate / self._fps
            if dt_sec <= 0:
                return 0.0
            return (dist_m / dt_sec) * 3.6
        except Exception:
            return self._speed_pixel_scale(c1, c2)
