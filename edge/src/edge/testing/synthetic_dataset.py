"""
Synthetic Dataset Generator for Computer Vision Benchmarking
============================================================
Generates standardized ground-truth bounding box datasets and simulates
optical/environmental degradation across 8 mandated environmental stress conditions:
  1. Day          (Optimal daylight, high contrast, zero blur)
  2. Night        (Low lux < 15, ISO sensor noise, headlight flare)
  3. Rain         (Water droplets, streak artifacts, reduced atmospheric contrast)
  4. Wet roads    (Specular asphalt reflections, mirror puddles, texture deformation)
  5. Glare        (Direct solar wash, overexposed high dynamic range clipping)
  6. Motion blur  (Directional horizontal smear kernel from vehicle vibration/speed)
  7. Occlusion    (30-70% partial bounding box obstruction)
  8. Dense traffic (15+ concurrent overlapping objects in tight proximity)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


ENVIRONMENTAL_CONDITIONS = [
    "Day",
    "Night",
    "Rain",
    "Wet roads",
    "Glare",
    "Motion blur",
    "Occlusion",
    "Dense traffic",
]

BENCHMARK_CLASSES = [
    # Road defects
    "pothole",
    "damaged_road",
    "waterlogging",
    "missing_road_divider",
    "missing_zebra",
    "damaged_sign",
    "missing_sign",
    # Vehicles
    "car",
    "bus",
    "truck",
    "motorcycle",
    "auto_rickshaw",
    # Pedestrians
    "pedestrian",
    "jaywalker",
    # Registration Plates
    "license_plate",
]


@dataclass
class GroundTruthAnnotation:
    id: str
    category: str
    bbox: Tuple[float, float, float, float]  # xmin, ymin, xmax, ymax in 0..1 normalized coords
    condition: str
    difficulty: str = "NORMAL"  # EASY, NORMAL, HARD, EXTREME


@dataclass
class SimulatedDetection:
    category: str
    confidence: float
    bbox: Tuple[float, float, float, float]


class SyntheticDatasetGenerator:
    """
    Generates synthetic validation scenes and annotates realistic ground-truth
    bounding boxes across the 8 environmental conditions.
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate_ground_truth_for_condition(
        self,
        condition: str,
        num_samples: int = 50,
    ) -> List[GroundTruthAnnotation]:
        """Generates ground truth annotations for a specific environmental condition."""
        if condition not in ENVIRONMENTAL_CONDITIONS:
            raise ValueError(f"Unknown condition: {condition}. Must be one of {ENVIRONMENTAL_CONDITIONS}")

        annotations = []
        is_dense = condition == "Dense traffic"
        count = num_samples * 2 if is_dense else num_samples

        for i in range(count):
            cls_name = self.rng.choice(BENCHMARK_CLASSES)
            # Generate plausible normalized bounding box
            w = self.rng.uniform(0.08, 0.35)
            h = self.rng.uniform(0.06, 0.30)
            x1 = self.rng.uniform(0.05, 0.95 - w)
            y1 = self.rng.uniform(0.15, 0.95 - h)
            x2 = min(1.0, x1 + w)
            y2 = min(1.0, y1 + h)

            difficulty = "NORMAL"
            if condition in ("Night", "Glare", "Motion blur"):
                difficulty = "HARD"
            elif condition in ("Occlusion", "Rain", "Wet roads"):
                difficulty = "HARD" if self.rng.random() > 0.5 else "NORMAL"
            elif condition == "Dense traffic":
                difficulty = "EXTREME" if self.rng.random() > 0.6 else "HARD"
            else:
                difficulty = "EASY" if self.rng.random() > 0.4 else "NORMAL"

            ann = GroundTruthAnnotation(
                id=f"gt_{condition.lower().replace(' ', '_')}_{i:03d}",
                category=cls_name,
                bbox=(round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4)),
                condition=condition,
                difficulty=difficulty,
            )
            annotations.append(ann)

        return annotations

    def generate_complete_benchmark_dataset(
        self,
        samples_per_condition: int = 40,
    ) -> Dict[str, List[GroundTruthAnnotation]]:
        """Generates complete dataset split across all 8 environmental conditions."""
        dataset = {}
        for cond in ENVIRONMENTAL_CONDITIONS:
            dataset[cond] = self.generate_ground_truth_for_condition(cond, samples_per_condition)
        return dataset
