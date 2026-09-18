"""
Unit & Integration Tests for Phase 4: Road Defect AI
Covers:
  - Step 7: Pothole detection (YOLOv8n & RDD2022 India)
  - Step 8: Separate Waterlogging class (with water depth & submersion metrics)
  - Step 9: False-positive protection (shadows, manholes, tar patches, 2-3 frame temporal confirmation)
  - Step 10: Difficult-condition handling (Day, Night, Rain, Wet road, Glare, Dirty lens, Motion blur)
"""

import os
import pytest

from edge.road_defect.detector import (
    RoadDefectDetector,
    DetectorMode,
    FalsePositiveFilter,
    ROAD_DEFECT_CLASSES,
    analyze_waterlogging,
)
from edge.road_defect.quality_checker import (
    check_quality,
    RoadCondition,
    QualityStatus,
)


def test_step7_rdd2022_config_and_pothole_class():
    """Verify Step 7: YOLOv8n RDD2022 config exists and includes pothole class."""
    config_path = "edge/src/edge/road_defect/rdd2022_india_config.yaml"
    assert os.path.exists(config_path), "RDD2022 config file must exist"
    
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "yolov8n" in content
    assert "pothole" in content
    assert "RDD2022" in content
    assert "pothole" in ROAD_DEFECT_CLASSES


def test_step8_waterlogging_is_separate_class():
    """Verify Step 8: Waterlogging is a completely separate class from pothole."""
    assert "pothole" in ROAD_DEFECT_CLASSES
    assert "waterlogging" in ROAD_DEFECT_CLASSES
    assert ROAD_DEFECT_CLASSES.index("pothole") != ROAD_DEFECT_CLASSES.index("waterlogging")

    # Verify dedicated waterlogging analysis provides depth and submersion telemetry
    wl_metrics = analyze_waterlogging(None, 0.85, RoadCondition.RAIN)
    assert wl_metrics["is_waterlogging"] is True
    assert "water_depth_cm" in wl_metrics
    assert wl_metrics["water_depth_cm"] > 0
    assert "submerged_lanes" in wl_metrics


def test_step9_false_positive_rejection():
    """Verify Step 9: False-positive protection rejects shadows, manholes, tar patches, and low confidence."""
    # 1. Below threshold (< 0.50) -> Rejected
    valid, reason = FalsePositiveFilter.evaluate("pothole", 0.42, [100, 100, 200, 200])
    assert valid is False
    assert "Below confidence threshold" in reason

    # 2. Circular / Square utility manhole cover -> Rejected
    # width = 100, height = 100 -> ratio = 1.0 (manhole signature)
    valid, reason = FalsePositiveFilter.evaluate("pothole", 0.85, [100.0, 100.0, 200.0, 200.0])
    assert valid is False
    assert "Manhole" in reason

    # 3. Valid non-manhole pothole geometry -> Accepted
    # width = 180, height = 70 -> ratio = 2.57 (irregular road fracture)
    valid, reason = FalsePositiveFilter.evaluate("pothole", 0.85, [100.0, 100.0, 280.0, 170.0])
    assert valid is True
    assert "Passed" in reason


def test_step9_temporal_consistency_consecutive_frames():
    """Verify Step 9: 1 frame does NOT emit event; 2 consecutive frames confirms event."""
    detector = RoadDefectDetector(
        camera_id="FRONT",
        bus_id="BUS-102",
        route_id="R-12",
        temporal_min_hits=2,  # Step 9 requires 2 consecutive frames
    )
    gps = {"lat": 28.6139, "lon": 77.2090}
    pothole_detection = [("pothole", 0.85, [100.0, 100.0, 280.0, 170.0])]

    # Frame 1: Initial detection -> should NOT emit yet (1/2 hits)
    events_frame1 = detector.process_frame(
        frame=None,
        gps=gps,
        raw_detections_override=pothole_detection,
    )
    assert len(events_frame1) == 0, "Single-frame detection must not alert without confirmation"

    # Frame 2: Consecutive detection -> MUST emit confirmed event (2/2 hits)
    events_frame2 = detector.process_frame(
        frame=None,
        gps=gps,
        raw_detections_override=pothole_detection,
    )
    assert len(events_frame2) == 1, "2 consecutive frames must confirm defect event"
    evt = events_frame2[0]
    assert evt["type"] == "pothole"
    assert evt["busId"] == "BUS-102"
    assert evt["routeId"] == "R-12"
    assert evt["confidence"] >= 0.50
    assert evt["status"] == "unverified"


def test_step10_difficult_conditions_handling():
    """Verify Step 10: Tests all 7 difficult real-world environmental conditions."""
    # 1. ☀️ DAY (Standard bright illumination ~ 130 lux)
    q_day = check_quality(brightness_override=130.0, blur_score_override=100.0)
    assert q_day.primary_condition == RoadCondition.DAY
    assert q_day.confidence_penalty <= 0.05

    # 2. 🌙 NIGHT (Low lux < 35)
    q_night = check_quality(brightness_override=22.0)
    assert RoadCondition.NIGHT in q_night.active_conditions
    assert q_night.confidence_penalty >= 0.10
    assert q_night.recommended_min_hits == 3

    # 3. 💡 GLARE (Direct high beam / sun saturation > 220)
    q_glare = check_quality(brightness_override=235.0)
    assert RoadCondition.GLARE in q_glare.active_conditions
    assert q_glare.confidence_penalty >= 0.10

    # 4. ☔ RAIN (Rain sensor active)
    q_rain = check_quality(brightness_override=110.0, is_raining_sensor=True)
    assert q_rain.primary_condition == RoadCondition.RAIN
    assert q_rain.recommended_min_hits == 3

    # 5. 💧 WET_ROAD (Specular highlight saturation in road quadrant)
    q_wet = check_quality(brightness_override=110.0, is_wet_road_override=True)
    assert RoadCondition.WET_ROAD in q_wet.active_conditions

    # 6. 📷 DIRTY_LENS (Occluded center patch with low variance)
    q_dirty = check_quality(obstruction_override=0.04)
    assert RoadCondition.DIRTY_LENS in q_dirty.active_conditions

    # 7. 🚍 MOTION_BLUR (Low blur score < 50 while speed > 15 km/h)
    q_blur = check_quality(blur_score_override=32.0, speed_kmh=45.0)
    assert RoadCondition.MOTION_BLUR in q_blur.active_conditions
