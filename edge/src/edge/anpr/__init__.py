"""
Vehicle Registration Recognition (ANPR) Package
================================================
"""

from .format_validator import (
    INDIAN_STATE_CODES,
    STANDARD_RTO_REGEX,
    BH_SERIES_REGEX,
    PlateFormatValidator,
    ValidationResult,
)
from .perspective import PerspectiveCorrector, order_points
from .pipeline import (
    AnprPipeline,
    AnprRecord,
    AnprState,
    PlateState,
    PlateNumberStr,
    PIPELINE_STAGES,
    HUMAN_VERIFICATION_NOTICE,
    compute_frame_sharpness,
)

__all__ = [
    "INDIAN_STATE_CODES",
    "STANDARD_RTO_REGEX",
    "BH_SERIES_REGEX",
    "PlateFormatValidator",
    "ValidationResult",
    "PerspectiveCorrector",
    "order_points",
    "AnprPipeline",
    "AnprRecord",
    "AnprState",
    "PlateState",
    "PlateNumberStr",
    "PIPELINE_STAGES",
    "HUMAN_VERIFICATION_NOTICE",
    "compute_frame_sharpness",
]
