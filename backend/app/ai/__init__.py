"""
NovaFlow AI Inference Package
==============================
Modular computer vision and object tracking engine for road intelligence.
"""

from .model_engine import RoadModelEngine, DetectionBox
from .tracker import DetectionTracker, TrackedObject
from .annotator import annotate_frame

__all__ = [
    "RoadModelEngine",
    "DetectionBox",
    "DetectionTracker",
    "TrackedObject",
    "annotate_frame",
]
