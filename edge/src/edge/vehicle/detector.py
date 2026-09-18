"""
Vehicle Detector (Phase 5 - Step 11)
======================================
Detects vehicle classes using YOLO (MODE_A) or simulation (MODE_B).

Mandatory Vehicle Classes (Step 11):
------------------------------------
  - car
  - bus
  - truck
  - motorcycle
  - auto_rickshaw
  (Additional supported classes: bicycle, van)

Calculates:
  - Per-class counts
  - Total vehicle count

MODE_A – Real YOLOv8 inference with Indian road vehicle class mapping.
MODE_B – Temporally consistent deterministic simulation for ByteTrack tracking.
"""

from __future__ import annotations

import logging
import random
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
except ImportError:
    np = None

logger = logging.getLogger("vehicle.detector")

# Mandatory classes per Step 11 + urban Indian fleet vehicles
PRIMARY_VEHICLE_CLASSES = ["car", "bus", "truck", "motorcycle", "auto_rickshaw"]
VEHICLE_LABELS = ["car", "bus", "truck", "motorcycle", "auto_rickshaw", "bicycle", "van"]

# Map from YOLO COCO / Indian dataset class names -> canonical vehicle labels
COCO_TO_VEHICLE = {
    "car":           "car",
    "bus":           "bus",
    "truck":         "truck",
    "motorcycle":    "motorcycle",
    "motorbike":     "motorcycle",
    "two_wheeler":   "motorcycle",
    "auto_rickshaw": "auto_rickshaw",
    "autorickshaw":  "auto_rickshaw",
    "rickshaw":      "auto_rickshaw",
    "bicycle":       "bicycle",
    "van":           "van",
}


class VehicleDetectorMode(str, Enum):
    MODE_A = "MODE_A"
    MODE_B = "MODE_B"


def count_vehicles(detections: List[Tuple[str, float, List[float]]]) -> Dict[str, int]:
    """
    Step 11: Calculate total vehicle count and per-class breakdown.
    Ensures all 5 core vehicle types (car, bus, truck, motorcycle, auto_rickshaw)
    are always represented in the counts dict.
    """
    counts: Dict[str, int] = {
        "car": 0,
        "bus": 0,
        "truck": 0,
        "motorcycle": 0,
        "auto_rickshaw": 0,
        "total": 0,
    }
    for item in detections:
        label = item[0].lower()
        if label in counts:
            counts[label] += 1
        else:
            counts[label] = 1
        counts["total"] += 1
    return counts


# ── Simulation backend ────────────────────────────────────────────────────────

class _SimVehicle:
    __slots__ = ("vclass", "cx", "cy", "dx", "dy", "w", "h", "conf")

    def __init__(self, vclass: str, cx: float, cy: float, dx: float, dy: float, w: int, h: int, conf: Optional[float] = None):
        self.vclass = vclass
        self.cx = cx
        self.cy = cy
        self.dx = dx
        self.dy = dy
        self.w = w
        self.h = h
        self.conf = conf if conf is not None else round(random.uniform(0.70, 0.95), 2)

    def step(self):
        self.cx += self.dx
        self.cy += self.dy

    def bbox(self) -> List[float]:
        return [self.cx - self.w / 2.0, self.cy - self.h / 2.0,
                self.cx + self.w / 2.0, self.cy + self.h / 2.0]

    @property
    def alive(self) -> bool:
        fw, fh = 1280, 720
        return -self.w < self.cx < fw + self.w and -self.h < self.cy < fh + self.h


class _SimVehicleDetector:
    """
    Produces realistic, temporally consistent vehicle detections
    so ByteTracker can form stable CONFIRMED tracks across frames.
    """

    _FRAME_W = 1280
    _FRAME_H = 720

    def __init__(self, spawn_interval: int = 12):
        self._vehicles: List[_SimVehicle] = []
        self._frame = 0
        self._spawn_every = spawn_interval
        self._spawn_counter = 0

    def detect(self, frame: Any = None) -> List[Tuple[str, float, List[float]]]:
        self._frame += 1

        self._spawn_counter += 1
        if self._spawn_counter >= self._spawn_every:
            self._spawn_counter = 0
            self._spawn_vehicle()

        # Step existing vehicles and prune dead ones
        self._vehicles = [v for v in self._vehicles if v.alive]
        for v in self._vehicles:
            v.step()

        return [(v.vclass, v.conf, v.bbox()) for v in self._vehicles]

    def inject_vehicle(
        self,
        vclass: str,
        cx: float,
        cy: float,
        dx: float = 0.0,
        dy: float = 8.0,
        w: int = 80,
        h: int = 50,
        conf: float = 0.90,
    ) -> None:
        """Inject a deterministic vehicle for unit testing."""
        self._vehicles.append(_SimVehicle(vclass, cx, cy, dx, dy, w, h, conf=conf))

    def clear(self) -> None:
        self._vehicles.clear()
        self._spawn_counter = 0
        self._frame = 0

    def _spawn_vehicle(self):
        FW = self._FRAME_W
        # Indian road distribution including auto-rickshaws
        vclass = random.choices(
            ["car", "motorcycle", "auto_rickshaw", "bus", "truck", "bicycle", "van"],
            weights=[35, 25, 20, 8, 5, 4, 3],
        )[0]
        dims = {
            "car": (90, 50),
            "bus": (160, 80),
            "truck": (140, 70),
            "motorcycle": (40, 55),
            "auto_rickshaw": (60, 55),
            "bicycle": (30, 55),
            "van": (100, 60),
        }
        w, h = dims[vclass]
        cx = random.uniform(w, FW - w)
        cy = -h / 2.0
        speed = random.uniform(4.0, 14.0)
        dx = random.uniform(-1.5, 1.5)
        self._vehicles.append(_SimVehicle(vclass, cx, cy, dx, speed, w, h))


# ── YOLO backend ──────────────────────────────────────────────────────────────

class _YOLOVehicleDetector:
    def __init__(self, model_path: str = "yolov8n.pt"):
        try:
            from ultralytics import YOLO
            self._model = YOLO(model_path)
            logger.info(f"YOLO vehicle detector loaded: {model_path}")
        except Exception as e:
            logger.warning(f"YOLO load failed ({e}) – falling back to simulation.")
            self._model = None
        self._fallback = _SimVehicleDetector()

    def detect(self, frame: Any) -> List[Tuple[str, float, List[float]]]:
        if self._model is None or frame is None:
            return self._fallback.detect(frame)
        try:
            results = self._model(frame, verbose=False)
            detections = []
            for r in results:
                for box in r.boxes:
                    label = r.names[int(box.cls)]
                    mapped = COCO_TO_VEHICLE.get(label.lower())
                    if mapped is None:
                        continue
                    conf = float(box.conf)
                    x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                    detections.append((mapped, conf, [x1, y1, x2, y2]))
            return detections
        except Exception as e:
            logger.error(f"YOLO inference error ({e}) – using simulation fallback")
            return self._fallback.detect(frame)


# ── Public factory ────────────────────────────────────────────────────────────

class VehicleDetector:
    """
    Step 11 Vehicle Detector:
    Detects vehicles (at least: Car, Bus, Truck, Motorcycle, Auto-rickshaw)
    and calculates vehicle counts.
    """

    def __init__(
        self,
        mode: VehicleDetectorMode = VehicleDetectorMode.MODE_B,
        model_path: str = "yolov8n.pt",
    ):
        self._mode = mode
        if mode == VehicleDetectorMode.MODE_A:
            self._backend = _YOLOVehicleDetector(model_path)
        else:
            self._backend = _SimVehicleDetector()

    def detect(self, frame: Any = None) -> List[Tuple[str, float, List[float]]]:
        """Return [(label, confidence, [x1, y1, x2, y2]), ...]"""
        return self._backend.detect(frame)

    def detect_with_counts(
        self,
        frame: Any = None,
    ) -> Tuple[List[Tuple[str, float, List[float]]], Dict[str, int]]:
        """
        Step 11: Detects vehicles and returns both raw detections and the
        computed vehicle count dictionary.
        """
        detections = self.detect(frame)
        counts = count_vehicles(detections)
        return detections, counts

    @staticmethod
    def count_vehicles(detections: List[Tuple[str, float, List[float]]]) -> Dict[str, int]:
        """Convenience method to calculate vehicle counts from detections."""
        return count_vehicles(detections)

    def inject_simulated_vehicle(
        self,
        vclass: str,
        cx: float,
        cy: float,
        dx: float = 0.0,
        dy: float = 8.0,
        w: int = 80,
        h: int = 50,
        conf: float = 0.90,
    ) -> None:
        """Inject vehicle into simulation backend (for testing)."""
        if hasattr(self._backend, "inject_vehicle"):
            self._backend.inject_vehicle(vclass, cx, cy, dx, dy, w, h, conf=conf)
        elif hasattr(self._backend, "_fallback"):
            self._backend._fallback.inject_vehicle(vclass, cx, cy, dx, dy, w, h, conf=conf)

    def reset(self) -> None:
        if hasattr(self._backend, "clear"):
            self._backend.clear()
        elif hasattr(self._backend, "_fallback"):
            self._backend._fallback.clear()
