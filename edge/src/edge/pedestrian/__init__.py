"""
Pedestrian Safety & School Zone Intelligence Package
====================================================
Provides school zone databases, pedestrian trajectory tracking,
and vulnerable pedestrian risk detection around road boundaries.
"""

from .school_zone_db import (
    GpsPoint,
    SchoolZone,
    SchoolZoneDatabase,
    DEFAULT_SCHOOL_ZONES,
)
from .trajectory_tracker import (
    CrossingBehavior,
    PedestrianTrack,
    PedestrianTrajectoryTracker,
    TrajectoryState,
)
from .pedestrian_risk_detector import (
    PedestrianRiskDetector,
    PedestrianRiskEvent,
)

__all__ = [
    "GpsPoint",
    "SchoolZone",
    "SchoolZoneDatabase",
    "DEFAULT_SCHOOL_ZONES",
    "CrossingBehavior",
    "PedestrianTrack",
    "PedestrianTrajectoryTracker",
    "TrajectoryState",
    "PedestrianRiskDetector",
    "PedestrianRiskEvent",
]
