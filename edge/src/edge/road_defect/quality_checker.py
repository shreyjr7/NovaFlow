"""
Road Defect AI – Image Quality Checker & Difficult-Condition Analyzer (Phase 4 - Step 10)
========================================================================================
Analyses frames for difficult real-world transit camera conditions:
  - ☀️ DAY         – standard daylight operation
  - 🌙 NIGHT       – low-lux / headlight corridor (reduced baseline confidence)
  - ☔ RAIN        – water droplets & streak distortion (requires higher temporal confirmation)
  - 💧 WET_ROAD    – specular road surface reflections
  - 💡 GLARE       – direct solar or oncoming high-beam saturation
  - 📷 DIRTY_LENS  – dust, mud splash, or obstruction on protective camera glass
  - 🚍 MOTION_BLUR – high bus velocity / road vibration causing shutter drag
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

logger = logging.getLogger("road_defect.quality")


class RoadCondition(str, Enum):
    DAY = "DAY"
    NIGHT = "NIGHT"
    RAIN = "RAIN"
    WET_ROAD = "WET_ROAD"
    GLARE = "GLARE"
    DIRTY_LENS = "DIRTY_LENS"
    MOTION_BLUR = "MOTION_BLUR"
    NORMAL = "NORMAL"


class QualityStatus(str, Enum):
    OK          = "OK"
    BLURRY      = "BLURRY"
    DARK        = "DARK"
    OVEREXPOSED = "OVEREXPOSED"
    OBSTRUCTED  = "OBSTRUCTED"
    DEGRADED    = "DEGRADED"


@dataclass
class QualityResult:
    status:            QualityStatus
    blur_score:        float   # Laplacian variance (higher = sharper, <45 = blurry)
    brightness:        float   # mean pixel intensity (0-255)
    obstruction:       float   # central uniformity score (0=obstructed, 1=clear)
    primary_condition: RoadCondition = RoadCondition.NORMAL
    active_conditions: List[RoadCondition] = None
    confidence_penalty: float = 0.0  # discount to raw AI confidence based on environmental noise
    recommended_min_hits: int = 2     # adaptive temporal frames needed (2 or 3)
    message:           str = ""
    is_usable:         bool = True

    def __post_init__(self):
        if self.active_conditions is None:
            self.active_conditions = [self.primary_condition]


# Threshold constants
BLUR_THRESHOLD       = 50.0    # below this -> BLURRY / MOTION_BLUR
DARK_THRESHOLD       = 35.0    # mean brightness below -> NIGHT / DARK
OVEREXP_THRESHOLD    = 220.0   # mean brightness above -> GLARE / OVEREXPOSED
OBSTRUCT_THRESHOLD   = 0.18    # central std dev below -> DIRTY_LENS / OBSTRUCTED


def check_quality(
    frame: Optional[Any] = None,
    speed_kmh: float = 0.0,
    is_raining_sensor: bool = False,
    brightness_override: Optional[float] = None,
    blur_score_override: Optional[float] = None,
    obstruction_override: Optional[float] = None,
    is_wet_road_override: Optional[bool] = None,
) -> QualityResult:
    """
    Analyses optical frame quality and identifies real-world difficult conditions.
    Supports real OpenCV frames as well as hardware telemetry overrides.
    """
    if brightness_override is not None:
        brightness = float(brightness_override)
    elif cv2 is not None and np is not None and frame is not None and hasattr(frame, "mean"):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        brightness = float(gray.mean())
    else:
        brightness = 128.0

    if blur_score_override is not None:
        blur_score = float(blur_score_override)
    elif cv2 is not None and np is not None and frame is not None and hasattr(frame, "mean"):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    else:
        blur_score = 120.0

    if obstruction_override is not None:
        obstruction = float(obstruction_override)
    elif cv2 is not None and np is not None and frame is not None and hasattr(frame, "shape"):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        h, w = gray.shape
        qy, qx = max(1, h // 4), max(1, w // 4)
        center_patch = gray[h // 2 - qy : h // 2 + qy, w // 2 - qx : w // 2 + qx]
        obstruction = float(center_patch.std()) / 128.0
    else:
        obstruction = 0.60

    active_conditions: List[RoadCondition] = []
    penalty = 0.0
    recommended_hits = 2

    # Analyze Night vs Day
    if brightness < DARK_THRESHOLD:
        active_conditions.append(RoadCondition.NIGHT)
        penalty += 0.15
        recommended_hits = 3
    elif brightness > OVEREXP_THRESHOLD:
        active_conditions.append(RoadCondition.GLARE)
        penalty += 0.15
        recommended_hits = 3
    else:
        active_conditions.append(RoadCondition.DAY)

    # Analyze Motion Blur
    if blur_score < BLUR_THRESHOLD:
        if speed_kmh > 15.0:
            active_conditions.append(RoadCondition.MOTION_BLUR)
            penalty += 0.12
            recommended_hits = 3
        else:
            active_conditions.append(RoadCondition.MOTION_BLUR)
            penalty += 0.08

    # Analyze Dirty Lens / Lens Smudge
    if obstruction < OBSTRUCT_THRESHOLD:
        active_conditions.append(RoadCondition.DIRTY_LENS)
        penalty += 0.20
        recommended_hits = 3

    # Analyze Wet Road & Rain
    if is_raining_sensor:
        active_conditions.append(RoadCondition.RAIN)
        penalty += 0.15
        recommended_hits = 3
    elif is_wet_road_override:
        active_conditions.append(RoadCondition.WET_ROAD)
        penalty += 0.10
        recommended_hits = 3
    elif cv2 is not None and np is not None and frame is not None and hasattr(frame, "shape"):
        # Check specular highlight in lower road half (high variance with saturated spots)
        lower_road = gray[int(h * 0.6) : h, :]
        high_specular_ratio = float((lower_road > 240).sum()) / float(lower_road.size)
        if high_specular_ratio > 0.04 and RoadCondition.GLARE not in active_conditions:
            active_conditions.append(RoadCondition.WET_ROAD)
            penalty += 0.10
            recommended_hits = 3

    # Primary condition selection
    primary = active_conditions[0]
    if RoadCondition.RAIN in active_conditions:
        primary = RoadCondition.RAIN
    elif RoadCondition.GLARE in active_conditions:
        primary = RoadCondition.GLARE
    elif RoadCondition.NIGHT in active_conditions:
        primary = RoadCondition.NIGHT
    elif RoadCondition.DIRTY_LENS in active_conditions:
        primary = RoadCondition.DIRTY_LENS
    elif RoadCondition.MOTION_BLUR in active_conditions:
        primary = RoadCondition.MOTION_BLUR
    elif RoadCondition.WET_ROAD in active_conditions:
        primary = RoadCondition.WET_ROAD
    elif RoadCondition.DAY in active_conditions:
        primary = RoadCondition.DAY

    # Status classification
    is_usable = True
    status = QualityStatus.OK

    if RoadCondition.DIRTY_LENS in active_conditions and obstruction < 0.08:
        status = QualityStatus.OBSTRUCTED
        is_usable = False
    elif RoadCondition.NIGHT in active_conditions and brightness < 10.0:
        status = QualityStatus.DARK
        is_usable = False
    elif RoadCondition.GLARE in active_conditions and brightness > 250.0:
        status = QualityStatus.OVEREXPOSED
        is_usable = False
    elif RoadCondition.MOTION_BLUR in active_conditions and blur_score < 15.0:
        status = QualityStatus.BLURRY
        is_usable = False
    elif len(active_conditions) >= 3:
        status = QualityStatus.DEGRADED

    return QualityResult(
        status=status,
        blur_score=round(blur_score, 1),
        brightness=round(brightness, 1),
        obstruction=round(obstruction, 3),
        primary_condition=primary,
        active_conditions=active_conditions,
        confidence_penalty=round(min(penalty, 0.40), 2),
        recommended_min_hits=recommended_hits,
        message=f"Environment: {primary.value} (Penalty: -{int(penalty*100)}%)",
        is_usable=is_usable,
    )

class ImageQualityChecker:
    def check_quality(self, *args, **kwargs):
        return check_quality(*args, **kwargs)
