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
    "HUMAN_VERIFICATION_NOTICE",
    "compute_frame_sharpness",
]
