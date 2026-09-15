"""
Road Defect AI – Defect Detector
==================================
Detects seven classes of road / infrastructure defects.

Classes
-------
  pothole              – surface deformation / hole
  damaged_road         – cracking, rutting, surface damage
  waterlogging         – standing water on road surface
  missing_road_divider – absent median / lane divider markings
  missing_zebra        – absent pedestrian crossing
  damaged_sign         – visible traffic sign but physically damaged
  missing_sign         – expected sign absent from view

Two operating modes
-------------------
  MODE_A – Real YOLOv8 inference (requires ``ultralytics`` + trained weights)
  MODE_B – Deterministic simulation with prepared detection sequences
            (ideal for hackathon demo without GPU)

Pipeline per frame
------------------
  1. Quality check (→ CAMERA_DEGRADED if unusable)
  2. YOLO / simulation inference  →  raw detections
  3. Temporal consistency filter  →  confirmed detections
  4. Confidence scoring           →  final event confidence
  5. Build & return RoadDefectEvent list
"""

from __future__ import annotations

import base64
import logging
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

from .quality_checker import check_quality, QualityStatus, QualityResult
from .temporal_tracker import TemporalConsistencyTracker

logger = logging.getLogger("road_defect.detector")


# ── Defect class definitions ──────────────────────────────────────────────────

ROAD_DEFECT_CLASSES: List[str] = [
    "pothole",
    "damaged_road",
    "waterlogging",
    "missing_road_divider",
    "missing_zebra",
    "damaged_sign",
    "missing_sign",
]

# Human-readable labels for the dashboard
DEFECT_LABELS: Dict[str, str] = {
    "pothole":              "Pothole",
    "damaged_road":         "Damaged Road",
    "waterlogging":         "Waterlogging",
    "missing_road_divider": "Missing Road Divider",
    "missing_zebra":        "Missing Zebra Crossing",
    "damaged_sign":         "Damaged Traffic Sign",
    "missing_sign":         "Missing Traffic Sign",
}

# Severity levels (used for event prioritisation in dashboard)
DEFECT_SEVERITY: Dict[str, str] = {
    "pothole":              "HIGH",
    "damaged_road":         "MEDIUM",
    "waterlogging":         "HIGH",
    "missing_road_divider": "MEDIUM",
    "missing_zebra":        "MEDIUM",
    "damaged_sign":         "HIGH",
    "missing_sign":         "HIGH",
}


class DetectorMode(str, Enum):
    MODE_A = "MODE_A"   # Real YOLO inference
    MODE_B = "MODE_B"   # Simulation / demo


# ── Confidence scorer ─────────────────────────────────────────────────────────

def compute_event_confidence(
    raw_confidence: float,
    quality: QualityResult,
    hit_ratio: float = 1.0,   # confirmed_frames / window_size
) -> float:
    """
    Weighted event confidence combining:
      - Raw model confidence (60%)
      - Frame quality penalty (20%) – blur/brightness reduce confidence
      - Temporal consistency bonus (20%)
    """
    quality_factor = min(quality.blur_score / 200.0, 1.0) * 0.5 + \
                     (1.0 - abs(quality.brightness - 128) / 128.0) * 0.5
    score = (raw_confidence * 0.6) + (quality_factor * 0.2) + (hit_ratio * 0.2)
    return round(min(max(score, 0.0), 1.0), 3)


# ── Simulation mode sequences ─────────────────────────────────────────────────

_SIM_SEQUENCES: List[List[Tuple[str, float, List[int]]]] = [
    # Frame group 1 – pothole detected repeatedly (will confirm after 3 hits)
    [("pothole",  0.78, [120, 300, 220, 380])],
    [("pothole",  0.82, [118, 298, 222, 382])],
    [("pothole",  0.80, [121, 299, 221, 381]), ("waterlogging", 0.55, [50, 350, 250, 420])],
    [("pothole",  0.76, [119, 300, 220, 380])],
    [("waterlogging", 0.71, [45, 345, 255, 425])],
    [("damaged_road", 0.65, [0, 400, 640, 460])],
    [("damaged_road", 0.70, [0, 398, 640, 462])],
    [("damaged_road", 0.73, [0, 397, 640, 463])],
    [("missing_sign", 0.60, [500, 50, 580, 150])],
    [("missing_sign", 0.68, [498, 52, 582, 148])],
    [("missing_sign", 0.72, [501, 51, 581, 149])],
    [("missing_zebra", 0.58, [0, 480, 640, 520])],
    [("missing_zebra", 0.63, [0, 478, 640, 522])],
    [("missing_zebra", 0.67, [0, 479, 640, 521])],
    [("damaged_sign",  0.74, [510, 60, 570, 140])],
    [("damaged_sign",  0.79, [508, 58, 572, 142])],
    [("damaged_sign",  0.76, [509, 59, 571, 141])],
    [("missing_road_divider", 0.61, [300, 0, 340, 480])],
    [("missing_road_divider", 0.66, [299, 0, 341, 480])],
    [("missing_road_divider", 0.69, [301, 0, 339, 480])],
]


class _SimDetector:
    """Cycles through prepared detection sequences for demo mode."""

    def __init__(self):
        self._idx = 0

    def detect(self, _frame: np.ndarray) -> List[Tuple[str, float, List[float]]]:
        seq = _SIM_SEQUENCES[self._idx % len(_SIM_SEQUENCES)]
        self._idx += 1
        return [(cls, conf, [float(v) for v in bbox]) for cls, conf, bbox in seq]


class _YOLODefectDetector:
    """
    Real YOLOv8 inference.
    Expects a model trained on ROAD_DEFECT_CLASSES.
    Falls back to _SimDetector if model weights file not found.
    """

    def __init__(self, model_path: str = "road_defect_yolov8.pt"):
        try:
            from ultralytics import YOLO
            self._model = YOLO(model_path)
            logger.info(f"Loaded YOLOv8 road defect model from {model_path}")
        except Exception as e:
            logger.warning(f"Could not load YOLO model ({e}) – falling back to simulation.")
            self._model = None
        self._fallback = _SimDetector()

    def detect(self, frame: np.ndarray) -> List[Tuple[str, float, List[float]]]:
        if self._model is None:
            return self._fallback.detect(frame)
        results = self._model(frame, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                label = r.names[int(box.cls)]
                if label not in ROAD_DEFECT_CLASSES:
                    continue
                conf = float(box.conf)
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                detections.append((label, conf, [x1, y1, x2, y2]))
        return detections


# ── Event data class ──────────────────────────────────────────────────────────

def build_defect_event(
    *,
    event_class:   str,
    confidence:    float,
    bounding_box:  List[float],
    camera_id:     str,
    bus_id:        str,
    gps:           Dict[str, float],
    frame_b64:     Optional[str],
    quality:       QualityResult,
    severity:      str,
) -> Dict[str, Any]:
    return {
        "event_id":     str(uuid.uuid4()),
        "event_type":   "road_defect",
        "class":        event_class,
        "label":        DEFECT_LABELS.get(event_class, event_class),
        "confidence":   confidence,
        "severity":     severity,
        "bounding_box": [round(v, 1) for v in bounding_box],
        "camera_id":    camera_id,
        "bus_id":       bus_id,
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "gps":          gps,
        "frame_b64":    frame_b64,
        "quality": {
            "status":     quality.status.value,
            "blur_score": quality.blur_score,
            "brightness": quality.brightness,
        },
    }


def build_camera_degraded_event(
    *,
    camera_id: str,
    bus_id:    str,
    gps:       Dict[str, float],
    quality:   QualityResult,
) -> Dict[str, Any]:
    return {
        "event_id":   str(uuid.uuid4()),
        "event_type": "CAMERA_DEGRADED",
        "camera_id":  camera_id,
        "bus_id":     bus_id,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "gps":        gps,
        "quality": {
            "status":     quality.status.value,
            "blur_score": quality.blur_score,
            "brightness": quality.brightness,
            "obstruction": quality.obstruction,
            "message":    quality.message,
        },
    }


# ── Main detector class ───────────────────────────────────────────────────────

class RoadDefectDetector:
    """
    Full road-defect detection pipeline for one camera channel.

    Parameters
    ----------
    camera_id  : e.g. "FRONT"
    bus_id     : bus identifier string
    mode       : DetectorMode.MODE_A (real YOLO) or MODE_B (simulation)
    model_path : path to custom YOLOv8 .pt weights (MODE_A only)
    temporal_window   : number of sampled frames to consider for confirmation
    temporal_min_hits : minimum hits within window to confirm a detection
    temporal_cooldown : seconds before re-confirming same class on same camera
    degraded_cooldown : seconds between repeated CAMERA_DEGRADED events
    """

    def __init__(
        self,
        camera_id:         str,
        bus_id:            str,
        mode:              DetectorMode = DetectorMode.MODE_B,
        model_path:        str = "road_defect_yolov8.pt",
        temporal_window:   int = 5,
        temporal_min_hits: int = 3,
        temporal_cooldown: float = 20.0,
        degraded_cooldown: float = 30.0,
    ):
        self._camera_id = camera_id
        self._bus_id = bus_id
        self._mode = mode

        if mode == DetectorMode.MODE_A:
            self._backend = _YOLODefectDetector(model_path)
        else:
            self._backend = _SimDetector()

        self._tracker = TemporalConsistencyTracker(
            window_size=temporal_window,
            min_hits=temporal_min_hits,
            cooldown_secs=temporal_cooldown,
        )
        self._degraded_cooldown = degraded_cooldown
        self._last_degraded = 0.0

    def process_frame(
        self,
        frame: np.ndarray,
        gps:   Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """
        Run the full pipeline on one frame.

        Returns
        -------
        List of event dicts – road defect confirmations + optional CAMERA_DEGRADED.
        """
        events: List[Dict[str, Any]] = []

        # ── 1. Quality check ──────────────────────────────────────────────────
        quality = check_quality(frame)

        if not quality.is_usable:
            # Emit CAMERA_DEGRADED event if not in cooldown
            if time.time() - self._last_degraded >= self._degraded_cooldown:
                self._last_degraded = time.time()
                events.append(build_camera_degraded_event(
                    camera_id=self._camera_id,
                    bus_id=self._bus_id,
                    gps=gps,
                    quality=quality,
                ))
                logger.warning(
                    f"[{self._camera_id}] Camera degraded – {quality.message}"
                )
            return events

        # ── 2. Inference ──────────────────────────────────────────────────────
        raw_detections = self._backend.detect(frame)

        # ── 3. Temporal consistency ───────────────────────────────────────────
        confirmed = self._tracker.update(
            camera_id=self._camera_id,
            raw_detections=raw_detections,
            all_classes=ROAD_DEFECT_CLASSES,
        )

        # ── 4. Build events for each confirmed defect ─────────────────────────
        for cls, agg_conf, bbox in confirmed:
            event_conf = compute_event_confidence(
                raw_confidence=agg_conf,
                quality=quality,
                hit_ratio=1.0,  # tracker already ensured min_hits
            )
            # Encode the relevant frame region as JPEG thumbnail
            frame_b64 = _crop_and_encode(frame, bbox)
            events.append(build_defect_event(
                event_class=cls,
                confidence=event_conf,
                bounding_box=bbox,
                camera_id=self._camera_id,
                bus_id=self._bus_id,
                gps=gps,
                frame_b64=frame_b64,
                quality=quality,
                severity=DEFECT_SEVERITY.get(cls, "MEDIUM"),
            ))
            logger.info(
                f"[{self._camera_id}] Confirmed: {cls} conf={event_conf:.3f} "
                f"gps=({gps['lat']:.5f},{gps['lon']:.5f})"
            )

        return events


# ── Utility ───────────────────────────────────────────────────────────────────

def _crop_and_encode(frame: np.ndarray, bbox: List[float], padding: int = 10) -> Optional[str]:
    """
    Crop the bounding-box region (with padding) from the frame and
    return it as a base-64 JPEG string.
    """
    try:
        h, w = frame.shape[:2]
        x1 = max(0, int(bbox[0]) - padding)
        y1 = max(0, int(bbox[1]) - padding)
        x2 = min(w, int(bbox[2]) + padding)
        y2 = min(h, int(bbox[3]) + padding)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None
        _, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 75])
        return base64.b64encode(buf.tobytes()).decode()
    except Exception:
        return None
