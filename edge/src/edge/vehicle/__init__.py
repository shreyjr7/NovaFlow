"""Vehicle detection + tracking sub-package."""
from .detector       import VehicleDetector, VehicleDetectorMode, VEHICLE_LABELS
from .tracker        import ByteTracker, Track, TrackState
from .speed_estimator import SpeedEstimator, EstimationMode
from .counter        import CountingLine, CountingRegion, TrafficStats, CLASS_GROUP, default_counting_config
from .processor      import VehicleProcessor

__all__ = [
    "VehicleDetector", "VehicleDetectorMode", "VEHICLE_LABELS",
    "ByteTracker", "Track", "TrackState",
    "SpeedEstimator", "EstimationMode",
    "CountingLine", "CountingRegion", "TrafficStats", "CLASS_GROUP", "default_counting_config",
    "VehicleProcessor",
]
