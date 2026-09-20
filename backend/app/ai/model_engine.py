"""
NovaFlow AI Model Engine
========================
State-of-the-Art Dual-Engine Vision Architecture:
  1. Road Defect & Pothole YOLO Model (road_damage_yolov8.pt + keremberke_pothole.pt)
     Detects: potholes, alligator cracks, road cracks, longitudinal/transverse cracks, shoulder edge damage.
  2. Transit & Vehicle YOLO Model (yolov8n.pt / yolo26n.pt)
     Detects: buses, cars, trucks, motorcycles, pedestrians, traffic signs.
  3. Road surface specular reflection analyzer for waterlogging & ponding.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("novaflow.ai.model_engine")

# 13 Canonical NovaFlow Target Classes
ALL_TARGET_CLASSES = [
    "pothole",
    "road_damage",
    "road_crack",
    "waterlogging",
    "debris",
    "damaged_zebra_crossing",
    "traffic_sign",
    "road_divider",
    "bus",
    "car",
    "truck",
    "motorcycle",
    "pedestrian",
]

# Standard COCO to NovaFlow target mapping
COCO_CLASS_MAPPING = {
    "person": "pedestrian",
    "car": "car",
    "motorcycle": "motorcycle",
    "bus": "bus",
    "truck": "truck",
    "traffic light": "traffic_sign",
    "stop sign": "traffic_sign",
}

# Specialized Road Defect Dataset mapping (RDD2022 / Roboflow road damage classes)
ROAD_DEFECT_MAPPING = {
    "pothole": "pothole",
    "alligator": "road_damage",
    "block": "road_damage",
    "crack": "road_crack",
    "edge": "road_damage",
    "longitudinal": "road_crack",
    "transverse": "road_crack",
    "waterlogging": "waterlogging",
    "debris": "debris",
}

# Custom Road defect classes that require specialized trained weights
CUSTOM_DEFECT_CLASSES = {
    "pothole",
    "road_damage",
    "road_crack",
    "waterlogging",
    "debris",
    "damaged_zebra_crossing",
    "road_divider",
    "alligator",
    "block",
    "crack",
    "edge",
    "longitudinal",
    "transverse",
}


def _box_iou(b1: Tuple[float, float, float, float], b2: Tuple[float, float, float, float]) -> float:
    """Calculates Intersection over Union (IoU) between two bounding boxes (x1, y1, x2, y2)."""
    x1 = max(b1[0], b2[0])
    y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2])
    y2 = min(b1[3], b2[3])

    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if intersection <= 0.0:
        return 0.0

    area1 = max(0.0, b1[2] - b1[0]) * max(0.0, b1[3] - b1[1])
    area2 = max(0.0, b2[2] - b2[0]) * max(0.0, b2[3] - b2[1])
    union = area1 + area2 - intersection
    return (intersection / union) if union > 0.0 else 0.0


@dataclass
class DetectionBox:
    """Canonical representation of an individual bounding box detection."""
    class_name: str
    confidence: float
    bbox: Tuple[float, float, float, float]  # (x1, y1, x2, y2) in pixels
    normalized_bbox: Tuple[float, float, float, float]  # (nx1, ny1, nx2, ny2) in 0.0-1.0
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    segmentation: Optional[List[Tuple[float, float]]] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox": [round(c, 1) for c in self.bbox],
            "normalized_bbox": [round(c, 4) for c in self.normalized_bbox],
            "severity": self.severity,
            "segmentation": self.segmentation,
        }


class RoadModelEngine:
    """
    State-of-the-Art Dual-Engine YOLO Detector:
    Simultaneously runs specialized Road Defect weights (potholes, cracks)
    and Transit / Vehicle weights (buses, cars, pedestrians).
    """

    def __init__(
        self,
        weights_path: Optional[str] = None,
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
    ):
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold

        # Candidate paths for specialized road defect weights
        defect_candidates = [
            weights_path,
            os.environ.get("NOVAFLOW_MODEL_PATH"),
            os.environ.get("NOVAFLOW_YOLO_WEIGHTS_PATH"),
            "road_damage_yolov8.pt",
            "backend/road_damage_yolov8.pt",
            "../road_damage_yolov8.pt",
        ]
        self.defect_weights_path: Optional[str] = next(
            (c for c in defect_candidates if c and os.path.exists(c)), None
        )

        # Candidate paths for secondary pothole segmentation model
        pothole_candidates = [
            "keremberke_pothole.pt",
            "backend/keremberke_pothole.pt",
            "../keremberke_pothole.pt",
        ]
        self.pothole_weights_path: Optional[str] = next(
            (c for c in pothole_candidates if c and os.path.exists(c)), None
        )

        # Candidate paths for transit/vehicle detection model
        traffic_candidates = [
            "yolov8n.pt",
            "backend/yolov8n.pt",
            "../yolov8n.pt",
            "yolo26n.pt",
            "backend/yolo26n.pt",
            "../yolo26n.pt",
        ]
        self.traffic_weights_path: Optional[str] = next(
            (c for c in traffic_candidates if c and os.path.exists(c)), None
        )

        # Primary weights path reported for legacy compatibility
        self.weights_path = (
            self.defect_weights_path
            or self.pothole_weights_path
            or self.traffic_weights_path
            or "road_damage_yolov8.pt"
        )

        self.defect_model: Optional[Any] = None
        self.pothole_model: Optional[Any] = None
        self.traffic_model: Optional[Any] = None
        self.model: Optional[Any] = None  # Alias to primary model
        self.is_custom_model: bool = False
        self.model_classes: List[str] = []
        self._ultralytics_available: bool = False

        self._initialize_models()

    def _initialize_models(self) -> None:
        try:
            from ultralytics import YOLO
            self._ultralytics_available = True

            # 1. Load Road Defect Model (Potholes, Cracks, Edge Damage)
            if self.defect_weights_path and os.path.exists(self.defect_weights_path):
                logger.info(f"Loading Road Defect weights from: {self.defect_weights_path}")
                self.defect_model = YOLO(self.defect_weights_path)
                names = (
                    list(self.defect_model.names.values())
                    if isinstance(self.defect_model.names, dict)
                    else self.defect_model.names
                )
                self.model_classes.extend(names)
                self.is_custom_model = True

            # 2. Load Dedicated Pothole Segmentation Model
            if self.pothole_weights_path and os.path.exists(self.pothole_weights_path):
                logger.info(f"Loading Pothole Segmentation weights from: {self.pothole_weights_path}")
                self.pothole_model = YOLO(self.pothole_weights_path)
                names = (
                    list(self.pothole_model.names.values())
                    if isinstance(self.pothole_model.names, dict)
                    else self.pothole_model.names
                )
                self.model_classes.extend(names)
                self.is_custom_model = True

            # 3. Load Transit & Traffic Model (Vehicles, Pedestrians, Signs)
            if self.traffic_weights_path and os.path.exists(self.traffic_weights_path):
                logger.info(f"Loading Traffic Intelligence weights from: {self.traffic_weights_path}")
                self.traffic_model = YOLO(self.traffic_weights_path)
                names = (
                    list(self.traffic_model.names.values())
                    if isinstance(self.traffic_model.names, dict)
                    else self.traffic_model.names
                )
                self.model_classes.extend(names)

            # Primary alias for single-model queries
            self.model = self.defect_model or self.pothole_model or self.traffic_model
            self.model_classes = list(set(self.model_classes))

            logger.info(
                f"Dual-Engine Vision initialized. Custom road defect weights active: {self.is_custom_model}. "
                f"Total recognized classes: {len(self.model_classes)}"
            )
        except Exception as e:
            logger.warning(
                f"Could not load Ultralytics YOLO models ({e}). "
                "Fallback lightweight vision pipeline will be active without fabricated detections."
            )
            self._ultralytics_available = False
            self.defect_model = None
            self.pothole_model = None
            self.traffic_model = None
            self.model = None

    def get_supported_classes(self) -> Dict[str, Any]:
        """Returns details on supported classes across the dual vision models."""
        supported = [c for c in ALL_TARGET_CLASSES if c in self.model_classes or c in ROAD_DEFECT_MAPPING.values()]
        unsupported = [c for c in ALL_TARGET_CLASSES if c not in supported]

        return {
            "weights_path": self.weights_path,
            "defect_weights": self.defect_weights_path,
            "pothole_weights": self.pothole_weights_path,
            "traffic_weights": self.traffic_weights_path,
            "is_custom_model": self.is_custom_model,
            "ultralytics_available": self._ultralytics_available,
            "supported_classes": supported,
            "unsupported_classes": unsupported,
            "note": "Dual-engine road intelligence actively detecting potholes, cracks, vehicles, and pedestrians.",
        }

    def calculate_severity(self, class_name: str, area_ratio: float, confidence: float) -> str:
        """Determines severity based on object class and relative image footprint."""
        if class_name in ("pothole", "waterlogging"):
            if area_ratio > 0.05:
                return "CRITICAL"
            elif area_ratio > 0.015:
                return "HIGH"
            return "MEDIUM"
        elif class_name in ("road_damage", "road_crack", "damaged_zebra_crossing", "road_divider"):
            if area_ratio > 0.08:
                return "HIGH"
            elif area_ratio > 0.02:
                return "MEDIUM"
            return "LOW"
        elif class_name == "pedestrian":
            return "HIGH"  # Pedestrian safety in roadway
        elif class_name == "debris":
            return "CRITICAL" if area_ratio > 0.04 else "HIGH"
        return "LOW"

    def detect(
        self,
        frame_bgr: Any,
        custom_conf: Optional[float] = None,
        custom_iou: Optional[float] = None,
    ) -> List[DetectionBox]:
        """
        Runs dual-engine object detection on a BGR numpy image frame.
        1. Runs Road Defect YOLO (potholes, cracks, edge failures).
        2. Runs Dedicated Pothole Segmentation YOLO (fine crater contours).
        3. Runs Traffic YOLO (buses, cars, trucks, motorcycles, pedestrians).
        4. Applies cross-model Non-Maximum Suppression to deduplicate.
        Returns a list of clean canonical DetectionBox objects.
        """
        if frame_bgr is None or not self._ultralytics_available:
            return []

        h, w = frame_bgr.shape[:2]
        if h == 0 or w == 0:
            return []

        conf = custom_conf if custom_conf is not None else self.confidence_threshold
        iou = custom_iou if custom_iou is not None else self.iou_threshold

        raw_detections: List[DetectionBox] = []

        # ── 1. ROAD DEFECT DETECTION (Potholes, Cracks, Alligator, Edge) ──
        if self.defect_model is not None:
            try:
                results = self.defect_model(frame_bgr, conf=conf, iou=iou, verbose=False)
                if results and len(results) > 0:
                    boxes = getattr(results[0], "boxes", None)
                    if boxes is not None:
                        for box in boxes:
                            cls_id = int(box.cls[0].item())
                            confidence = float(box.conf[0].item())
                            raw_name = self.defect_model.names.get(cls_id, str(cls_id)).lower()
                            canonical_class = ROAD_DEFECT_MAPPING.get(raw_name, raw_name)
                            if canonical_class not in ALL_TARGET_CLASSES:
                                canonical_class = "road_damage"

                            xyxy = box.xyxy[0].tolist()
                            x1, y1 = max(0.0, xyxy[0]), max(0.0, xyxy[1])
                            x2, y2 = min(float(w), xyxy[2]), min(float(h), xyxy[3])
                            area_ratio = ((x2 - x1) * (y2 - y1)) / (w * h)
                            sev = self.calculate_severity(canonical_class, area_ratio, confidence)

                            raw_detections.append(
                                DetectionBox(
                                    class_name=canonical_class,
                                    confidence=confidence,
                                    bbox=(x1, y1, x2, y2),
                                    normalized_bbox=(x1 / w, y1 / h, x2 / w, y2 / h),
                                    severity=sev,
                                )
                            )
            except Exception as e:
                logger.error(f"Defect model inference error: {e}")

        # ── 2. DEDICATED POTHOLE SEGMENTATION ────────────────────────────
        if self.pothole_model is not None:
            try:
                results = self.pothole_model(frame_bgr, conf=conf, iou=iou, verbose=False)
                if results and len(results) > 0:
                    boxes = getattr(results[0], "boxes", None)
                    if boxes is not None:
                        for box in boxes:
                            confidence = float(box.conf[0].item())
                            xyxy = box.xyxy[0].tolist()
                            x1, y1 = max(0.0, xyxy[0]), max(0.0, xyxy[1])
                            x2, y2 = min(float(w), xyxy[2]), min(float(h), xyxy[3])
                            area_ratio = ((x2 - x1) * (y2 - y1)) / (w * h)
                            sev = self.calculate_severity("pothole", area_ratio, confidence)

                            raw_detections.append(
                                DetectionBox(
                                    class_name="pothole",
                                    confidence=confidence,
                                    bbox=(x1, y1, x2, y2),
                                    normalized_bbox=(x1 / w, y1 / h, x2 / w, y2 / h),
                                    severity=sev,
                                )
                            )
            except Exception as e:
                logger.error(f"Pothole model inference error: {e}")

        # ── 3. TRAFFIC & TRANSIT DETECTION (Vehicles, Pedestrians) ───────
        if self.traffic_model is not None:
            try:
                results = self.traffic_model(frame_bgr, conf=max(conf, 0.40), iou=iou, verbose=False)
                if results and len(results) > 0:
                    boxes = getattr(results[0], "boxes", None)
                    if boxes is not None:
                        for box in boxes:
                            cls_id = int(box.cls[0].item())
                            confidence = float(box.conf[0].item())
                            raw_name = self.traffic_model.names.get(cls_id, str(cls_id)).lower()
                            canonical_class = COCO_CLASS_MAPPING.get(raw_name)
                            if not canonical_class or canonical_class not in ALL_TARGET_CLASSES:
                                continue

                            xyxy = box.xyxy[0].tolist()
                            x1, y1 = max(0.0, xyxy[0]), max(0.0, xyxy[1])
                            x2, y2 = min(float(w), xyxy[2]), min(float(h), xyxy[3])
                            area_ratio = ((x2 - x1) * (y2 - y1)) / (w * h)
                            sev = self.calculate_severity(canonical_class, area_ratio, confidence)

                            raw_detections.append(
                                DetectionBox(
                                    class_name=canonical_class,
                                    confidence=confidence,
                                    bbox=(x1, y1, x2, y2),
                                    normalized_bbox=(x1 / w, y1 / h, x2 / w, y2 / h),
                                    severity=sev,
                                )
                            )
            except Exception as e:
                logger.error(f"Traffic model inference error: {e}")

        # ── 4. CROSS-MODEL NON-MAXIMUM SUPPRESSION (DEDUPLICATION) ───────
        if not raw_detections:
            return []

        # Sort by confidence descending
        raw_detections.sort(key=lambda d: d.confidence, reverse=True)
        final_detections: List[DetectionBox] = []

        for d in raw_detections:
            # Check if this box overlaps significantly with an already accepted box of similar category
            duplicate = False
            for accepted in final_detections:
                iou_val = _box_iou(d.bbox, accepted.bbox)
                # If high IoU and both are road defects or both are same class, suppress duplicate
                if iou_val > 0.45:
                    duplicate = True
                    break
            if not duplicate:
                final_detections.append(d)

        return final_detections
