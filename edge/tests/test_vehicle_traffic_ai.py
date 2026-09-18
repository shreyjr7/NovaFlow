"""
Phase 5 Comprehensive Automated Verification Suite
===================================================
Covers Steps 11 through 15:
  Step 11: Vehicle Detection (Car, Bus, Truck, Motorcycle, Auto-rickshaw) + Vehicle Counts
  Step 12: ByteTrack Multi-Object Tracking (Frame 1 -> Car #23, Frame 2 -> Car #23 ...)
  Step 13: Traffic Density Calculation (Vehicles / road area)
  Step 14: Average Speed Estimation from Tracked Centroids
  Step 15: Bottleneck Detection (HIGH DENSITY + LOW SPEED -> BOTTLENECK)
"""

import pytest
from datetime import datetime, timezone

from edge.vehicle.detector import VehicleDetector, VehicleDetectorMode, count_vehicles, PRIMARY_VEHICLE_CLASSES
from edge.vehicle.tracker import ByteTracker, TrackState
from edge.vehicle.speed_estimator import SpeedEstimator, EstimationMode
from edge.vehicle.counter import (
    CountingLine,
    CountingRegion,
    TrafficStats,
    calculate_traffic_density,
)
from edge.vehicle.processor import VehicleProcessor
from edge.traffic.congestion_detector import (
    CongestionDetector,
    check_bottleneck_condition,
    CongestionEvent,
    Severity,
)


# ── Step 11: Vehicle Detection & Counts ───────────────────────────────────────

def test_step11_vehicle_detection_and_counts():
    """
    Step 11: Detect at least:
      - Car
      - Bus
      - Truck
      - Motorcycle
      - Auto-rickshaw
    Then calculate:
      - Vehicle count
    """
    # Verify primary classes are defined
    expected_classes = {"car", "bus", "truck", "motorcycle", "auto_rickshaw"}
    assert expected_classes.issubset(set(PRIMARY_VEHICLE_CLASSES))

    # Mock detections containing all required vehicle types
    raw_detections = [
        ("car", 0.92, [100.0, 100.0, 200.0, 180.0]),
        ("bus", 0.89, [250.0, 100.0, 420.0, 220.0]),
        ("truck", 0.85, [500.0, 100.0, 680.0, 210.0]),
        ("motorcycle", 0.78, [700.0, 100.0, 750.0, 170.0]),
        ("auto_rickshaw", 0.94, [800.0, 100.0, 870.0, 175.0]),
        ("car", 0.91, [900.0, 100.0, 990.0, 170.0]),
    ]

    counts = count_vehicles(raw_detections)
    assert counts["car"] == 2
    assert counts["bus"] == 1
    assert counts["truck"] == 1
    assert counts["motorcycle"] == 1
    assert counts["auto_rickshaw"] == 1
    assert counts["total"] == 6

    # Test via VehicleDetector API
    detector = VehicleDetector(mode=VehicleDetectorMode.MODE_B)
    detector.reset()
    detector.inject_simulated_vehicle("auto_rickshaw", cx=300, cy=200, dx=0, dy=0)
    detector.inject_simulated_vehicle("car", cx=500, cy=200, dx=0, dy=0)

    dets, computed_counts = detector.detect_with_counts()
    assert len(dets) >= 2
    assert computed_counts["auto_rickshaw"] >= 1
    assert computed_counts["car"] >= 1
    assert computed_counts["total"] >= 2


# ── Step 12: ByteTrack Tracking (Persistent IDs) ──────────────────────────────

def test_step12_bytetrack_tracking_continuity():
    """
    Step 12: Implement YOLO -> ByteTrack
      Frame 1 -> Car #23
      Frame 2 -> Car #23
      Frame 3 -> Car #23
      Frame 4 -> Car #23
    This prevents repeatedly counting the same vehicle.
    """
    tracker = ByteTracker(min_hits=2, max_age=10)

    # Frame 1: Car appears at [100, 100, 200, 180]
    frame1_dets = [("car", 0.92, [100.0, 100.0, 200.0, 180.0])]
    tracks_f1 = tracker.update(frame1_dets)
    # With min_hits=2, track is TENTATIVE on frame 1
    assert tracker.all_tracks[0].track_id == 1
    car_track_id = tracker.all_tracks[0].track_id
    assert tracker.all_tracks[0].display_name == f"Car #{car_track_id}"

    # Frame 2: Car moves slightly to [104, 108, 204, 188]
    frame2_dets = [("car", 0.91, [104.0, 108.0, 204.0, 188.0])]
    tracks_f2 = tracker.update(frame2_dets)
    assert len(tracks_f2) == 1
    assert tracks_f2[0].track_id == car_track_id
    assert tracks_f2[0].state == TrackState.CONFIRMED
    assert tracks_f2[0].display_name == f"Car #{car_track_id}"

    # Frame 3: Car moves to [108, 116, 208, 196]
    frame3_dets = [("car", 0.88, [108.0, 116.0, 208.0, 196.0])]
    tracks_f3 = tracker.update(frame3_dets)
    assert len(tracks_f3) == 1
    assert tracks_f3[0].track_id == car_track_id

    # Frame 4: Car moves to [112, 124, 212, 204]
    frame4_dets = [("car", 0.89, [112.0, 124.0, 212.0, 204.0])]
    tracks_f4 = tracker.update(frame4_dets)
    assert len(tracks_f4) == 1
    assert tracks_f4[0].track_id == car_track_id
    assert tracks_f4[0].hits == 4


def test_step12_tracker_prevents_duplicate_line_counting():
    """
    Verifies that tracker-assisted counting counts a vehicle exactly once
    even as it passes through the line across multiple frames.
    """
    tracker = ByteTracker(min_hits=1)
    line = CountingLine(name="TestLine", x1=0, y1=200, x2=1280, y2=200, direction="any")

    # Frame 1: Vehicle above line (cy = 185, line is at y=200)
    t1 = tracker.update([("auto_rickshaw", 0.90, [300.0, 160.0, 360.0, 210.0])])
    events1 = line.update(t1)
    assert len(events1) == 0
    assert line.counts["total"] == 0

    # Frame 2: Vehicle crosses line (cy = 205, line is at y=200)
    t2 = tracker.update([("auto_rickshaw", 0.90, [300.0, 180.0, 360.0, 230.0])])
    events2 = line.update(t2)
    assert len(events2) == 1
    assert line.counts["total"] == 1
    assert line.counts["auto_rickshaw"] == 1

    # Frame 3: Vehicle continues below line (cy = 225, MUST NOT BE COUNTED AGAIN)
    t3 = tracker.update([("auto_rickshaw", 0.90, [300.0, 200.0, 360.0, 250.0])])
    events3 = line.update(t3)
    assert len(events3) == 0
    assert line.counts["total"] == 1


# ── Step 13: Traffic Density (Vehicles / road area) ───────────────────────────

def test_step13_traffic_density_calculation():
    """
    Step 13: Calculate traffic density:
      Vehicles / road area
    """
    road_area = 200.0  # 200 m²

    # Low density scenario (2 vehicles on 200 m² -> 0.01 veh/m²)
    low_density = calculate_traffic_density(vehicle_count=2, road_area_sqm=road_area)
    assert low_density["vehicle_count"] == 2
    assert low_density["road_area_sqm"] == 200.0
    assert low_density["vehicles_per_sqm"] == 0.01
    assert low_density["density_level"] == "low"

    # High density scenario (24 vehicles on 200 m² -> 0.12 veh/m², bumper to bumper)
    high_density = calculate_traffic_density(vehicle_count=24, road_area_sqm=road_area)
    assert high_density["vehicle_count"] == 24
    assert high_density["vehicles_per_sqm"] == 0.12
    assert high_density["density_level"] == "high"
    assert high_density["density_score"] >= 0.70

    # CountingRegion density calculation
    region = CountingRegion(
        name="TestZone",
        polygon=[(0, 0), (1000, 0), (1000, 500), (0, 500)],
        road_area_sqm=250.0,
    )
    # Create 8 dummy tracks inside region
    class DummyTrack:
        def __init__(self, tid, cx, cy, label="car"):
            self.track_id = tid
            self.centroid = [cx, cy]
            self.label = label

    tracks = [DummyTrack(i, 200 + i * 40, 250) for i in range(10)]
    reg_snap = region.update(tracks)
    assert reg_snap["vehicle_count"] == 10
    assert reg_snap["road_area_sqm"] == 250.0
    assert reg_snap["vehicles_per_sqm"] == 10 / 250.0
    assert reg_snap["density_score"] > 0


# ── Step 14: Average Speed Estimation ─────────────────────────────────────────

def test_step14_average_speed_estimation():
    """
    Step 14: Track vehicles over time and estimate:
      Average speed + Vehicle density
    """
    speed_est = SpeedEstimator(fps=25.0, sample_rate=5, pixels_per_meter=40.0, min_track_len=2)

    class MockTrack:
        def __init__(self, tid, label="car"):
            self.track_id = tid
            self.label = label
            self.centroids = []

    # Vehicle moving 20 pixels per sample step
    # dt_sec = 5 / 25.0 = 0.20 sec
    # dist_m = 20 px / 40 px/m = 0.50 m
    # speed_ms = 0.50 m / 0.20 s = 2.5 m/s = 9.0 km/h
    track1 = MockTrack(1, "car")
    track1.centroids = [[100, 100], [100, 120]]

    spd1 = speed_est.estimate(track1)
    assert spd1 is not None
    assert 8.0 <= spd1 <= 10.0

    # Combined stats tracking average speed
    stats = TrafficStats(lines=[], regions=[])
    stats.update([track1], {1: spd1})
    snap = stats.snapshot()
    assert snap["avg_speed_kmh"]["car"] == spd1
    assert snap["avg_speed_kmh"]["all"] == spd1


# ── Step 15: Bottleneck Detection (HIGH DENSITY + LOW SPEED) ──────────────────

def test_step15_bottleneck_detection_logic():
    """
    Step 15: Detect bottlenecks:
      HIGH DENSITY + LOW SPEED -> BOTTLENECK

    Verification:
      1. High density + Low speed => Bottleneck TRUE
      2. High density + High speed => Flowing traffic, Bottleneck FALSE
      3. Low density + Low speed => Isolated slow vehicle, Bottleneck FALSE
      4. Low density + High speed => Free flow, Bottleneck FALSE
    """
    # 1. High Density (0.85) + Low Speed (10 km/h) -> BOTTLENECK
    assert check_bottleneck_condition(
        density=0.85,
        average_speed=10.0,
        vehicle_count=15,
        density_threshold=0.55,
        low_speed_threshold=18.0,
        min_vehicles=3,
    ) is True

    # 2. High Density (0.80) + High Speed (55 km/h) -> Busy highway flow, NOT bottleneck!
    assert check_bottleneck_condition(
        density=0.80,
        average_speed=55.0,
        vehicle_count=20,
        density_threshold=0.55,
        low_speed_threshold=18.0,
        min_vehicles=3,
    ) is False

    # 3. Single slow vehicle (e.g. stopped bus or turning car) -> Guarded, NOT bottleneck!
    assert check_bottleneck_condition(
        density=0.85,
        average_speed=5.0,
        vehicle_count=1,
        min_vehicles=3,
    ) is False

    # 4. Low density + High speed -> Normal free flow
    assert check_bottleneck_condition(
        density=0.15,
        average_speed=65.0,
        vehicle_count=5,
    ) is False


def test_step15_bottleneck_standard_event_schema():
    """
    Step 15: Persistent bottleneck creates alert in standardized event format.
    """
    detector = CongestionDetector(
        min_bottleneck_vehicles=3,
        density_bottleneck_thresh=0.55,
        absolute_low_speed_kmh=18.0,
        persistence_window_sec=20.0,
        min_persistent_samples=3,
        cooldown_sec=0.0,
    )

    event = None
    # Feed 4 consecutive bottleneck frames
    for _ in range(4):
        event = detector.evaluate(
            vehicle_count=18,
            density=0.85,
            average_speed=8.5,
            road_segment="DEL_01",
            gps={"lat": 28.5918, "lon": 77.1675},
            bus_id="BUS-102",
        )

    assert event is not None
    assert event.is_bottleneck is True
    assert event.average_speed == 8.5
    assert event.density == 0.85

    # Check canonical standard event dictionary format
    std = event.to_standard_dict()
    assert "eventId" in std
    assert std["type"] == "bottleneck"
    assert std["confidence"] >= 0.65
    assert std["latitude"] == 28.5918
    assert std["longitude"] == 77.1675
    assert std["busId"] == "BUS-102"
    assert std["routeId"] == "DEL_01"
    assert std["severity"] in ("high", "severe")
    assert std["status"] == "unverified"
