"""
Unit tests for Traffic Bottleneck Detection (Phase 11)
"""

import time
import pytest
from datetime import datetime, timezone

from edge.traffic import (
    RoadSegmentManager,
    HistoricalTrafficBaseline,
    CongestionDetector,
    CongestionEvent,
    Severity,
    ROAD_SEGMENTS,
)


def test_road_segment_manager_lookup():
    mgr = RoadSegmentManager()
    # Dhaula Kuan coordinate
    seg = mgr.nearest(28.5918, 77.1675)
    assert seg is not None
    assert seg.segment_id == "DEL_01"
    assert seg.city == "Delhi"

    # Silk Board coordinate
    seg_blr = mgr.nearest(12.9170, 77.6233)
    assert seg_blr is not None
    assert seg_blr.segment_id == "BLR_02"


def test_historical_baseline():
    baseline = HistoricalTrafficBaseline()
    metric_noon = baseline.get_baseline("DEL_01", dt=datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc))
    assert metric_noon.free_flow_speed_kmh == 70.0
    assert metric_noon.baseline_speed_kmh > 0
    assert metric_noon.hour_of_day == 12
    assert not metric_noon.is_peak_hour

    metric_rush = baseline.get_baseline("DEL_01", dt=datetime(2026, 9, 15, 9, 0, 0, tzinfo=timezone.utc))
    assert metric_rush.is_peak_hour
    # Peak hour baseline speed should be lower due to expected congestion
    assert metric_rush.baseline_speed_kmh < metric_noon.baseline_speed_kmh


def test_congestion_score_categories():
    detector = CongestionDetector()

    # Low score test
    score_low = detector.calculate_congestion_score(
        vehicle_count=10,
        density=0.15,
        average_speed=65.0,
        baseline=detector.baseline_provider.get_baseline("DEL_01"),
    )
    assert detector.score_to_severity(score_low) == Severity.LOW

    # Severe score test (many vehicles, high density, crawling speed)
    score_severe = detector.calculate_congestion_score(
        vehicle_count=35,
        density=0.92,
        average_speed=8.0,
        baseline=detector.baseline_provider.get_baseline("DEL_01"),
    )
    assert detector.score_to_severity(score_severe) in (Severity.HIGH, Severity.SEVERE)


def test_single_vehicle_suppression_guard():
    """
    CRITICAL RULE:
    Do NOT classify a single slow vehicle (or isolated tracks) as a bottleneck.
    """
    detector = CongestionDetector(min_bottleneck_vehicles=3)

    # 1 slow vehicle (e.g. turning car or stopped bus)
    for _ in range(5):
        event = detector.evaluate(
            vehicle_count=1,
            density=0.85,
            average_speed=4.0,  # very slow!
            road_segment="DEL_01",
            gps={"lat": 28.5918, "lon": 77.1675},
        )
        # MUST NEVER generate a bottleneck event!
        assert event is None

    # Verify that single vehicle score is strictly dampened
    score = detector.calculate_congestion_score(
        vehicle_count=1,
        density=0.85,
        average_speed=4.0,
        baseline=detector.baseline_provider.get_baseline("DEL_01"),
    )
    assert score < 30.0  # Must remain in LOW range


def test_persistent_bottleneck_detection_and_schema():
    """
    Persistent condition:
    High vehicle density AND Low average speed AND Persistent across samples.
    """
    detector = CongestionDetector(
        min_bottleneck_vehicles=3,
        density_bottleneck_thresh=0.55,
        speed_drop_ratio_thresh=0.45,
        persistence_window_sec=30.0,
        min_persistent_samples=3,
        cooldown_sec=0.0,
    )

    event = None
    # Feed 4 consecutive congested samples
    for i in range(4):
        event = detector.evaluate(
            vehicle_count=18,
            density=0.88,
            average_speed=9.5,
            road_segment="DEL_01",
            gps={"lat": 28.5918, "lon": 77.1675},
            bus_id="BUS_DEL_101",
            camera_id="FRONT",
        )

    # 4th sample satisfies persistence threshold
    assert event is not None
    assert isinstance(event, CongestionEvent)

    # Verify exact required schema fields
    d = event.to_dict()
    assert "road_segment" in d
    assert "density" in d
    assert "average_speed" in d
    assert "congestion_score" in d
    assert "severity" in d
    assert "timestamp" in d
    assert "location" in d
    assert d["road_segment"] == "DEL_01"
    assert d["density"] == 0.88
    assert d["average_speed"] == 9.5
    assert d["severity"] in ("HIGH", "SEVERE")
    assert d["is_bottleneck"] is True
    assert d["location"]["lat"] == 28.5918
