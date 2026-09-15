"""
Vehicle Detector
=================
Detects the 7 vehicle classes using YOLO (MODE_A) or simulation (MODE_B).

Vehicle classes
---------------
  car, bus, truck, motorcycle, auto_rickshaw, bicycle, van

MODE_A – Real YOLOv8 inference.
         The standard COCO-trained YOLOv8 model already detects: car, bus,
         truck, motorcycle, bicycle. auto_rickshaw and van require a custom
         model or can be approximated from COCO: motorcycle≈auto_rickshaw,
         truck≈van when small.

MODE_B – Deterministic simulation cycling through realistic traffic sequences.
         Produces stable detections that ByteTracker can form CONFIRMED tracks on.
"""

from __future__ import annotations

import logging
import random
from enum import Enum
from typing import List, Optional, Tuple

try:
    import numpy as np
except ImportError:
    np = None

logger = logging.getLogger("vehicle.detector")

VEHICLE_LABELS = ["car", "bus", "truck", "motorcycle", "auto_rickshaw", "bicycle", "van"]

# Map from YOLO COCO class names → canonical vehicle labels
COCO_TO_VEHICLE = {
    "car":        "car",
    "bus":        "bus",
    "truck":      "truck",
    "motorcycle": "motorcycle",
    "bicycle":    "bicycle",
    "van":        "van",         # not a COCO class; added by custom model
    "auto_rickshaw": "auto_rickshaw",
}


class VehicleDetectorMode(str, Enum):
    MODE_A = "MODE_A"
    MODE_B = "MODE_B"


# ── Simulation backend ────────────────────────────────────────────────────────

class _SimVehicleDetector:
    """
    Produces realistic, temporally consistent vehicle detections
    so ByteTracker can form stable CONFIRMED tracks across frames.

    Each simulated vehicle follows a linear trajectory across the frame
    so it consistently crosses counting lines.
    """

    _FRAME_W = 1280
    _FRAME_H = 720

    class _SimVehicle:
        def __init__(self, vclass: str, cx: float, cy: float, dx: float, dy: float, w: int, h: int):
            self.vclass = vclass
            self.cx, self.cy = cx, cy
            self.dx, self.dy = dx, dy
            self.w, self.h   = w, h
            self.conf        = round(random.uniform(0.65, 0.95), 2)

        def step(self):
            self.cx += self.dx
            self.cy += self.dy

        def bbox(self) -> List[float]:
            return [self.cx - self.w/2, self.cy - self.h/2,
                    self.cx + self.w/2, self.cy + self.h/2]

        @property
        def alive(self) -> bool:
            fw, fh = _SimVehicleDetector._FRAME_W, _SimVehicleDetector._FRAME_H
            return -self.w < self.cx < fw + self.w and -self.h < self.cy < fh + self.h

    def __init__(self, spawn_interval: int = 12):
        self._vehicles: List[self._SimVehicle] = []
        self._frame    = 0
        self._spawn_every = spawn_interval
        self._spawn_counter = 0

    def detect(self, frame: Optional[np.ndarray] = None) -> List[Tuple[str, float, List[float]]]:
        self._frame += 1

        # Spawn new vehicles at the top of frame, moving downward
        self._spawn_counter += 1
        if self._spawn_counter >= self._spawn_every:
            self._spawn_counter = 0
            self._spawn_vehicle()

        # Step all vehicles
        self._vehicles = [v for v in self._vehicles if v.alive]
        for v in self._vehicles:
            v.step()

        return [(v.vclass, v.conf, v.bbox()) for v in self._vehicles]

    def _spawn_vehicle(self):
        FW, FH = self._FRAME_W, self._FRAME_H
        # Weighted class distribution reflecting urban Indian traffic
        vclass = random.choices(
            ["car", "motorcycle", "auto_rickshaw", "bus", "truck", "bicycle", "van"],
            weights=       [35,     25,             20,     8,       5,         4,       3],
            k=1,
        )[0]

        dims = {
            "car":          (90,  50),
            "bus":          (160, 80),
            "truck":        (140, 70),
            "motorcycle":   (40,  55),
            "auto_rickshaw":(60,  55),
            "bicycle":      (30,  55),
            "van":          (100, 60),
        }
        w, h   = dims[vclass]
        # Spawn anywhere across the top, move downward at random speed
        cx     = random.uniform(w, FW - w)
        cy     = -h / 2
        speed  = random.uniform(4, 14)    # px per frame downward
        dx     = random.uniform(-1.5, 1.5)
        dy     = speed
        self._vehicles.append(self._SimVehicle(vclass, cx, cy, dx, dy, w, h))


# Patch the invalid class attribute
import dataclasses

class _SimVehicleDetector:
    _FRAME_W = 1280
    _FRAME_H = 720

    class _SimVehicle:
        __slots__ = ("vclass", "cx", "cy", "dx", "dy", "w", "h", "conf")

        def __init__(self, vclass, cx, cy, dx, dy, w, h):
            self.vclass = vclass
            self.cx, self.cy = cx, cy
            self.dx, self.dy = dx, dy
            self.w, self.h   = w, h
            self.conf = round(random.uniform(0.65, 0.95), 2)

        def step(self):
            self.cx += self.dx
            self.cy += self.dy

        def bbox(self):
            return [self.cx - self.w/2, self.cy - self.h/2,
                    self.cx + self.w/2, self.cy + self.h/2]

        @property
        def alive(self):
            fw, fh = 1280, 720
            return -self.w < self.cx < fw + self.w and -self.h < self.cy < fh + self.h

    def __init__(self, spawn_interval: int = 12):
        self._vehicles: list = []
        self._spawn_every  = spawn_interval
        self._spawn_counter = 0

    def detect(self, frame=None) -> List[Tuple[str, float, List[float]]]:
        self._spawn_counter += 1
        if self._spawn_counter >= self._spawn_every:
            self._spawn_counter = 0
            self._spawn_vehicle()

        self._vehicles = [v for v in self._vehicles if v.alive]
        for v in self._vehicles:
            v.step()

        return [(v.vclass, v.conf, v.bbox()) for v in self._vehicles]

    def _spawn_vehicle(self):
        FW, FH = self._FRAME_W, self._FRAME_H
        vclass = random.choices(
            ["car", "motorcycle", "auto_rickshaw", "bus", "truck", "bicycle", "van"],
            weights=[35, 25, 20, 8, 5, 4, 3],
        )[0]
        dims = {
            "car": (90, 50), "bus": (160, 80), "truck": (140, 70),
            "motorcycle": (40, 55), "auto_rickshaw": (60, 55),
            "bicycle": (30, 55), "van": (100, 60),
        }
        w, h  = dims[vclass]
        cx    = random.uniform(w, FW - w)
        cy    = -h / 2
        speed = random.uniform(4, 14)
        dx    = random.uniform(-1.5, 1.5)
        self._vehicles.append(self._SimVehicle(vclass, cx, cy, dx, speed, w, h))


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

    def detect(self, frame) -> List[Tuple[str, float, List[float]]]:
        if self._model is None:
            return self._fallback.detect(frame)
        results = self._model(frame, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                label = r.names[int(box.cls)]
                mapped = COCO_TO_VEHICLE.get(label)
                if mapped is None:
                    continue
                conf = float(box.conf)
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                detections.append((mapped, conf, [x1, y1, x2, y2]))
        return detections


# ── Public factory ────────────────────────────────────────────────────────────

class VehicleDetector:
    """
    Thin factory wrapper exposing a unified `.detect(frame)` interface
    regardless of operating mode.
    """

    def __init__(self, mode: VehicleDetectorMode = VehicleDetectorMode.MODE_B,
                 model_path: str = "yolov8n.pt"):
        self._mode = mode
        if mode == VehicleDetectorMode.MODE_A:
            self._backend = _YOLOVehicleDetector(model_path)
        else:
            self._backend = _SimVehicleDetector()

    def detect(self, frame=None) -> List[Tuple[str, float, List[float]]]:
        """Return [(label, confidence, [x1,y1,x2,y2]), ...]"""
        return self._backend.detect(frame)
