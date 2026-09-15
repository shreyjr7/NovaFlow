"""
NovaFlow AI — Edge & Autonomous Mobile Sensing Modules
======================================================
This module exposes the edge vision, tracking, defect detection,
ANPR, and incident detection pipelines.
"""

import sys
import os

# Add edge source path
_EDGE_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "edge", "src"))
if _EDGE_SRC not in sys.path:
    sys.path.insert(0, _EDGE_SRC)

try:
    from edge.road_defect import RoadDefectDetector
    from edge.vehicle import VehicleProcessor, ByteTracker
    from edge.traffic import CongestionDetector, RoadSegmentManager
    from edge.pedestrian import PedestrianRiskDetector
    from edge.incident import IncidentAnomalyDetector
    from edge.anpr import AnprPipeline
    from edge.pipeline.manager import CameraPipeline, SimulatorManager
except ImportError as e:
    pass
