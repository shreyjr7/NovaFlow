"""
Incident & Hit-and-Run Anomaly Detection Engine Package
"""

from .signals import (
    SignalResult,
    VehicleTrackState,
    TrajectorySignalEvaluator,
)
from .rolling_buffer import RollingFrameBuffer
from .anpr import NumberPlateRecognizer, AnprResult
from .anomaly_detector import IncidentAnomalyDetector, LEGAL_DISCLAIMER

__all__ = [
    "SignalResult",
    "VehicleTrackState",
    "TrajectorySignalEvaluator",
    "RollingFrameBuffer",
    "NumberPlateRecognizer",
    "AnprResult",
    "IncidentAnomalyDetector",
    "LEGAL_DISCLAIMER",
]
