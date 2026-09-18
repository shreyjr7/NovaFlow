"""
Hardware Profile Specifications (Step 37 & Step 38)
===================================================
Defines edge AI execution profiles for bus on-board compute:
  1. NVIDIA Jetson Orin Nano / NX:
     - TensorRT execution provider
     - FP16 and INT8 engine support
     - Concurrent inference of all 4 AI modules
     - Power envelope: 15W - 25W

  2. Raspberry Pi 5 + Google Coral Edge TPU:
     - Edge TPU runtime / TFLite INT8 quantized models
     - Time-division multiplexed scheduling
     - Frame-sampled inference across the 4 modules
     - Power envelope: 5W - 12W
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EdgeDeviceType(str, Enum):
    JETSON_ORIN_NANO = "JETSON_ORIN_NANO"
    JETSON_ORIN_NX = "JETSON_ORIN_NX"
    RASPBERRY_PI_5_CORAL = "RASPBERRY_PI_5_CORAL"
    GENERIC_EDGE_CPU = "GENERIC_EDGE_CPU"


class QuantizationPrecision(str, Enum):
    FP32 = "FP32"
    FP16 = "FP16"
    INT8 = "INT8"


@dataclass
class HardwareProfile:
    device_type: EdgeDeviceType
    name: str
    inference_engine: str  # TensorRT, EdgeTPU_TFLite, ONNXRuntime
    supported_precisions: List[QuantizationPrecision]
    default_precision: QuantizationPrecision
    concurrent_models_supported: int
    recommended_frame_sampling: Dict[str, int]  # module_name -> sample_rate (every N frames)
    max_power_watts: float
    target_fps_per_camera: float
    supports_tensorrt: bool
    supports_coral_tpu: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_type": self.device_type.value,
            "name": self.name,
            "inference_engine": self.inference_engine,
            "supported_precisions": [p.value for p in self.supported_precisions],
            "default_precision": self.default_precision.value,
            "concurrent_models_supported": self.concurrent_models_supported,
            "recommended_frame_sampling": self.recommended_frame_sampling,
            "max_power_watts": self.max_power_watts,
            "target_fps_per_camera": self.target_fps_per_camera,
            "supports_tensorrt": self.supports_tensorrt,
            "supports_coral_tpu": self.supports_coral_tpu,
        }


# High-performance standard configuration
JETSON_ORIN_NANO_PROFILE = HardwareProfile(
    device_type=EdgeDeviceType.JETSON_ORIN_NANO,
    name="NVIDIA Jetson Orin Nano (8GB)",
    inference_engine="TensorRT",
    supported_precisions=[QuantizationPrecision.FP16, QuantizationPrecision.INT8, QuantizationPrecision.FP32],
    default_precision=QuantizationPrecision.FP16,
    concurrent_models_supported=4,
    recommended_frame_sampling={
        "road_defect": 2,      # 15 fps at 30 fps input
        "vehicle_traffic": 1,  # 30 fps (every frame for smooth ByteTrack)
        "pedestrian_risk": 2,  # 15 fps
        "anpr": 5,             # 6 fps (or event-driven on vehicle crop)
    },
    max_power_watts=15.0,
    target_fps_per_camera=30.0,
    supports_tensorrt=True,
    supports_coral_tpu=False,
)

JETSON_ORIN_NX_PROFILE = HardwareProfile(
    device_type=EdgeDeviceType.JETSON_ORIN_NX,
    name="NVIDIA Jetson Orin NX (16GB)",
    inference_engine="TensorRT",
    supported_precisions=[QuantizationPrecision.FP16, QuantizationPrecision.INT8, QuantizationPrecision.FP32],
    default_precision=QuantizationPrecision.FP16,
    concurrent_models_supported=4,
    recommended_frame_sampling={
        "road_defect": 1,
        "vehicle_traffic": 1,
        "pedestrian_risk": 1,
        "anpr": 3,
    },
    max_power_watts=25.0,
    target_fps_per_camera=30.0,
    supports_tensorrt=True,
    supports_coral_tpu=False,
)

# Cost-effective deployment configuration
RASPBERRY_PI_5_CORAL_PROFILE = HardwareProfile(
    device_type=EdgeDeviceType.RASPBERRY_PI_5_CORAL,
    name="Raspberry Pi 5 + Google Coral Edge TPU",
    inference_engine="EdgeTPU_TFLite",
    supported_precisions=[QuantizationPrecision.INT8],
    default_precision=QuantizationPrecision.INT8,
    concurrent_models_supported=2,
    recommended_frame_sampling={
        "road_defect": 3,      # 10 fps
        "vehicle_traffic": 2,  # 15 fps
        "pedestrian_risk": 2,  # 15 fps
        "anpr": 6,             # 5 fps
    },
    max_power_watts=12.0,
    target_fps_per_camera=20.0,
    supports_tensorrt=False,
    supports_coral_tpu=True,
)


def get_profile_by_device_type(device_type: EdgeDeviceType) -> HardwareProfile:
    if device_type == EdgeDeviceType.JETSON_ORIN_NANO:
        return JETSON_ORIN_NANO_PROFILE
    elif device_type == EdgeDeviceType.JETSON_ORIN_NX:
        return JETSON_ORIN_NX_PROFILE
    elif device_type == EdgeDeviceType.RASPBERRY_PI_5_CORAL:
        return RASPBERRY_PI_5_CORAL_PROFILE
    return JETSON_ORIN_NANO_PROFILE
