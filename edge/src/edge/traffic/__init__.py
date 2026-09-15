"""
Edge AI Traffic Intelligence Package
====================================
Provides road segment mapping, historical baselines, and bottleneck detection.
"""

from .road_segment_manager import (
    GpsPoint,
    RoadSegment,
    RoadSegmentManager,
    ROAD_SEGMENTS,
)
from .historical_baseline import (
    BaselineMetric,
    HistoricalTrafficBaseline,
)
from .congestion_detector import (
    CongestionDetector,
    CongestionEvent,
    CongestionObservation,
    Severity,
)

__all__ = [
    "GpsPoint",
    "RoadSegment",
    "RoadSegmentManager",
    "ROAD_SEGMENTS",
    "BaselineMetric",
    "HistoricalTrafficBaseline",
    "CongestionDetector",
    "CongestionEvent",
    "CongestionObservation",
    "Severity",
]
