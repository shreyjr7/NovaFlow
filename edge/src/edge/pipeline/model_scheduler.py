"""
Edge AI Model Scheduler & Frame Sampler (Step 38)
=================================================
Optimizes simultaneous execution of the 4 AI modules:
  1. Road Defect (Potholes, Waterlogging, Road Damage)
  2. Vehicle Detection, Counting & Tracking (ByteTrack)
  3. Safety & Pedestrian Risk Detection
  4. ANPR (Automatic Number Plate Recognition)

Prevents edge device hardware overload via:
  - TensorRT acceleration configuration
  - FP16 and INT8 engine precision selection
  - Dynamic frame sampling (time-division multiplexing)
  - Priority-based preemptive scheduling (Safety > Vehicle > Road Defect > ANPR)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional
from ..hardware.device_profile import (
    HardwareProfile,
    JETSON_ORIN_NANO_PROFILE,
    QuantizationPrecision,
)

logger = logging.getLogger("edge.model_scheduler")


class ModelPriority:
    SAFETY_PEDESTRIAN = 1   # Highest priority (life safety)
    VEHICLE_TRAFFIC   = 2   # High priority (smooth trajectory tracking)
    ROAD_DEFECT       = 3   # Medium priority (static infrastructure)
    ANPR_RECOGNITION  = 4   # Batch / Event-driven priority


class EdgeModelScheduler:
    """
    Coordinates frame dispatch and model execution across the 4 edge AI pipelines.
    """

    def __init__(
        self,
        profile: HardwareProfile = JETSON_ORIN_NANO_PROFILE,
        precision: Optional[QuantizationPrecision] = None,
    ):
        self.profile = profile
        self.precision = precision or profile.default_precision
        self.frame_counter: int = 0
        self.sampling_rates = dict(profile.recommended_frame_sampling)
        self.last_execution_times: Dict[str, float] = {}

    def should_execute_module(self, module_name: str) -> bool:
        """
        Determines whether a specific AI module should run on current frame
        based on hardware frame-sampling ratios.
        """
        sample_rate = self.sampling_rates.get(module_name, 1)
        return (self.frame_counter % sample_rate) == 0

    def step_frame(self) -> int:
        """Advances hardware frame counter by 1."""
        self.frame_counter += 1
        return self.frame_counter

    def schedule_frame(
        self,
        frame_id: int,
        active_modules: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Returns list of AI modules scheduled to execute on this frame,
        ordered by safety and operational priority.
        """
        all_modules = active_modules or ["road_defect", "vehicle_traffic", "pedestrian_risk", "anpr"]
        scheduled = []

        for mod in all_modules:
            sample_rate = self.sampling_rates.get(mod, 1)
            if (frame_id % sample_rate) == 0:
                scheduled.append(mod)

        # Sort by strict priority
        priority_map = {
            "pedestrian_risk": ModelPriority.SAFETY_PEDESTRIAN,
            "vehicle_traffic": ModelPriority.VEHICLE_TRAFFIC,
            "road_defect": ModelPriority.ROAD_DEFECT,
            "anpr": ModelPriority.ANPR_RECOGNITION,
        }

        scheduled.sort(key=lambda m: priority_map.get(m, 99))
        return scheduled

    def get_runtime_status(self) -> Dict[str, Any]:
        return {
            "device": self.profile.name,
            "inference_engine": self.profile.inference_engine,
            "precision": self.precision.value,
            "frame_counter": self.frame_counter,
            "sampling_rates": self.sampling_rates,
            "supports_tensorrt": self.profile.supports_tensorrt,
            "max_power_watts": self.profile.max_power_watts,
        }
