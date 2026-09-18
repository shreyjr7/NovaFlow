"""
Tests for Phase 15 (Hardware / Edge AI Optimization)
====================================================
Verifies:
  - Step 37: Edge device profiles (Jetson Orin Nano/NX and Raspberry Pi 5 + Coral TPU)
  - Step 38: Model scheduler, frame sampling, TensorRT/INT8 optimization
"""

import pytest
from edge.hardware.device_profile import (
    JETSON_ORIN_NANO_PROFILE,
    JETSON_ORIN_NX_PROFILE,
    RASPBERRY_PI_5_CORAL_PROFILE,
    QuantizationPrecision,
)
from edge.pipeline.model_scheduler import EdgeModelScheduler, ModelPriority


def test_step37_edge_hardware_profiles():
    # Jetson Orin Nano
    assert JETSON_ORIN_NANO_PROFILE.supports_tensorrt is True
    assert QuantizationPrecision.FP16 in JETSON_ORIN_NANO_PROFILE.supported_precisions
    assert JETSON_ORIN_NANO_PROFILE.concurrent_models_supported == 4

    # Raspberry Pi 5 + Coral
    assert RASPBERRY_PI_5_CORAL_PROFILE.supports_coral_tpu is True
    assert RASPBERRY_PI_5_CORAL_PROFILE.default_precision == QuantizationPrecision.INT8
    assert RASPBERRY_PI_5_CORAL_PROFILE.max_power_watts <= 15.0


def test_step38_model_scheduler_frame_sampling():
    scheduler = EdgeModelScheduler(profile=JETSON_ORIN_NANO_PROFILE)

    # Frame 0: all modules scheduled by priority
    frame0_mods = scheduler.schedule_frame(frame_id=0)
    assert frame0_mods[0] == "pedestrian_risk"  # highest priority
    assert "vehicle_traffic" in frame0_mods

    # Frame 1: road_defect skipped (sampled every 2 frames)
    frame1_mods = scheduler.schedule_frame(frame_id=1)
    assert "road_defect" not in frame1_mods
    assert "vehicle_traffic" in frame1_mods  # vehicle traffic runs every frame
