"""
Road Defect AI – Image Quality Checker
========================================
Analyses a frame before inference and classifies its quality into one of:

  OK            – frame is usable for inference
  BLURRY        – Laplacian variance below threshold
  DARK          – mean brightness too low (night/tunnel without IR)
  OVEREXPOSED   – mean brightness too high (direct sunlight glare)
  OBSTRUCTED    – large uniform/monotone region in frame centre (camera blocked)
  DEGRADED      – multiple issues simultaneously

When quality is NOT OK, the pipeline should skip inference and optionally
emit a CAMERA_DEGRADED event (handled by the defect detector).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

logger = logging.getLogger("road_defect.quality")


class QualityStatus(str, Enum):
    OK          = "OK"
    BLURRY      = "BLURRY"
    DARK        = "DARK"
    OVEREXPOSED = "OVEREXPOSED"
    OBSTRUCTED  = "OBSTRUCTED"
    DEGRADED    = "DEGRADED"


@dataclass
class QualityResult:
    status:        QualityStatus
    blur_score:    float   # Laplacian variance (higher = sharper)
    brightness:    float   # mean pixel intensity 0-255
    obstruction:   float   # central uniformity score 0-1 (0 = obstructed)
    message:       str     = ""
    is_usable:     bool    = True


# ── Thresholds ────────────────────────────────────────────────────────────────

BLUR_THRESHOLD       = 60.0    # below this → BLURRY
DARK_THRESHOLD       = 20.0    # mean brightness below → DARK
OVEREXP_THRESHOLD    = 240.0   # mean brightness above → OVEREXPOSED
OBSTRUCT_THRESHOLD   = 0.15    # central-region std dev below → OBSTRUCTED


def check_quality(frame: np.ndarray) -> QualityResult:
    """
    Analyse the quality of a BGR frame and return a QualityResult.

    Parameters
    ----------
    frame : np.ndarray – BGR image from cv2.VideoCapture

    Returns
    -------
    QualityResult with status and metrics.
    """
    if cv2 is None or np is None:
        return QualityResult(
            status=QualityStatus.OK,
            blur_score=100.0,
            brightness=128.0,
            obstruction=0.5,
            message="Frame OK (fallback mode)",
            is_usable=True,
        )

    if frame is None or (hasattr(frame, "size") and frame.size == 0):
        return QualityResult(
            status=QualityStatus.DEGRADED,
            blur_score=0.0, brightness=0.0, obstruction=0.0,
            message="Empty frame", is_usable=False,
        )

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # ── Blur (Laplacian variance) ─────────────────────────────────────────────
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # ── Brightness ───────────────────────────────────────────────────────────
    brightness = float(gray.mean())

    # ── Central obstruction ───────────────────────────────────────────────────
    # Extract central 40% of frame; if it is nearly uniform, camera is blocked
    cy1, cy2 = int(h * 0.3), int(h * 0.7)
    cx1, cx2 = int(w * 0.3), int(w * 0.7)
    centre = gray[cy1:cy2, cx1:cx2]
    centre_std = float(centre.std()) / 255.0   # normalise to 0-1
    obstruction_score = centre_std              # low → obstructed

    # ── Classify ──────────────────────────────────────────────────────────────
    issues = []
    if blur_score < BLUR_THRESHOLD:
        issues.append("BLURRY")
    if brightness < DARK_THRESHOLD:
        issues.append("DARK")
    if brightness > OVEREXP_THRESHOLD:
        issues.append("OVEREXPOSED")
    if obstruction_score < OBSTRUCT_THRESHOLD:
        issues.append("OBSTRUCTED")

    if len(issues) == 0:
        status = QualityStatus.OK
        is_usable = True
        message = "Frame OK"
    elif len(issues) == 1:
        status = QualityStatus(issues[0])
        is_usable = False
        message = f"Frame degraded: {issues[0]}"
    else:
        status = QualityStatus.DEGRADED
        is_usable = False
        message = f"Frame degraded: {', '.join(issues)}"

    return QualityResult(
        status=status,
        blur_score=round(blur_score, 2),
        brightness=round(brightness, 2),
        obstruction=round(obstruction_score, 4),
        message=message,
        is_usable=is_usable,
    )
