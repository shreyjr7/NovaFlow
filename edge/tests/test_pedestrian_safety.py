"""
Unit tests for Pedestrian Safety & Vulnerable User Risk Detection (Phase 12)
"""

from datetime import datetime, time, timezone
import pytest

from edge.pedestrian import (
    SchoolZone,
    SchoolZoneDatabase,
    PedestrianTrajectoryTracker,
    PedestrianRiskDetector,
    PedestrianRiskEvent,
    DEFAULT_SCHOOL_ZONES,
)


def test_school_zone_geofence_containment():
    db = SchoolZoneDatabase()

    # R.K. Puram coordinates (inside SCH_DEL_01, radius 300m)
    # DPS R.K. Puram is at (28.5672, 77.1720)
    match = db.check_location(28.5675, 77.1722, dt=datetime(2026, 9, 15, 8, 30, tzinfo=timezone.utc))
    assert match is not None
    school, dist_m, is_active = match
    assert school.school_id == "SCH_DEL_01"
    assert dist_m <= 300.0

    # Point far away in Connaught Place (not near R.K. Puram)
    no_match = db.check_location(28.6320, 77.2180)
    assert no_match is None


def test_school_bell_hours_active_and_inactive():
    db = SchoolZoneDatabase()
    # Tuesday 08:30 UTC (inside 07:30-09:30 range) -> active
    t_morning = datetime(2026, 9, 15, 8, 30, tzinfo=timezone.utc)
    match_morning = db.check_location(28.5672, 77.1720, dt=t_morning)
    assert match_morning is not None
    assert match_morning[2] is True  # is_active_hours

    # Tuesday 02:00 UTC (outside bell hours) -> inactive
    t_night = datetime(2026, 9, 15, 2, 0, tzinfo=timezone.utc)
    match_night = db.check_location(28.5672, 77.1720, dt=t_night)
    assert match_night is not None
    assert match_night[2] is False

    # Saturday 08:30 UTC (Weekend) -> inactive
    t_weekend = datetime(2026, 9, 19, 8, 30, tzinfo=timezone.utc)
    match_weekend = db.check_location(28.5672, 77.1720, dt=t_weekend)
    assert match_weekend is not None
    assert match_weekend[2] is False


def test_pedestrian_trajectory_towards_road():
    tracker = PedestrianTrajectoryTracker(road_center_x=640.0)

    # Simulate person on right sidewalk (x ~ 850) moving left towards road (dx < 0)
    t0 = 1000.0
    tracker.update([(0.88, [850, 400, 900, 550])], current_time=t0)
    tracker.update([(0.88, [835, 405, 885, 555])], current_time=t0 + 0.1)
    tracks = tracker.update([(0.88, [820, 410, 870, 560])], current_time=t0 + 0.2)

    assert len(tracks) == 1
    t = tracks[0]
    assert t.trajectory is not None
    assert t.trajectory.dx < 0  # Moved to the left (towards center road)
    assert t.trajectory.moving_toward_road is True


def test_pedestrian_trajectory_away_from_road():
    tracker = PedestrianTrajectoryTracker(road_center_x=640.0)

    # Simulate person on right sidewalk moving further right (away from road)
    t0 = 1000.0
    tracker.update([(0.85, [850, 400, 900, 550])], current_time=t0)
    tracker.update([(0.85, [865, 400, 915, 550])], current_time=t0 + 0.1)
    tracks = tracker.update([(0.85, [880, 400, 930, 550])], current_time=t0 + 0.2)

    assert len(tracks) == 1
    t = tracks[0]
    assert t.trajectory is not None
    assert t.trajectory.moving_toward_road is False


def test_crowd_density_reporting():
    """
    CRITICAL RULE:
    For crowded areas report zone-level pedestrian density rather than
    claiming perfect individual counts or age classification.
    """
    detector = PedestrianRiskDetector()
    dense_metric = detector.compute_crowd_density(person_count=9)
    assert dense_metric["level"] == "HIGH"
    assert dense_metric["is_crowded"] is True

    moderate_metric = detector.compute_crowd_density(person_count=4)
    assert moderate_metric["level"] == "MEDIUM"
    assert moderate_metric["is_crowded"] is False


def test_full_pedestrian_risk_event_emission():
    detector = PedestrianRiskDetector(
        road_boundary_thresh_px=100.0,
        bus_id="BUS_DEL_101",
        camera_id="FRONT",
    )

    # Road boundary line (right curb in front bus view)
    boundary = ((800.0, 360.0), (1050.0, 700.0))

    # Feed 3 observations of a person approaching the road boundary near DPS R.K. Puram
    # during active school hours (08:15 AM on Tuesday)
    dt_str = "2026-09-15T08:15:00+00:00"
    gps = {"lat": 28.5672, "lon": 77.1720}

    t0 = 1000.0
    detector.process_frame(
        frame=None,
        detections=[("person", 0.92, [1000, 420, 1050, 570])],
        gps=gps,
        timestamp="2026-09-15T08:15:00.000+00:00",
        road_boundary_line=boundary,
    )
    detector.process_frame(
        frame=None,
        detections=[("person", 0.93, [980, 425, 1030, 575])],
        gps=gps,
        timestamp="2026-09-15T08:15:00.100+00:00",
        road_boundary_line=boundary,
    )
    events, density = detector.process_frame(
        frame=None,
        detections=[("person", 0.94, [960, 430, 1010, 580])],
        gps=gps,
        timestamp="2026-09-15T08:15:00.200+00:00",
        road_boundary_line=boundary,
    )

    # Risk event should be triggered!
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, PedestrianRiskEvent)
    d = ev.to_dict()

    # Verify all required schema fields
    assert d["event_type"] == "PEDESTRIAN_RISK"
    assert "location" in d
    assert "timestamp" in d
    assert "bus_id" in d
    assert "camera_id" in d
    assert "confidence" in d
    assert "trajectory" in d
    assert "school_zone" in d
    assert "road_boundary" in d
    assert "zone_density" in d
    assert d["school_zone"]["school_id"] == "SCH_DEL_01"
    assert d["trajectory"]["moving_toward_road"] is True
    assert d["road_boundary"]["is_near_boundary"] is True


# ── Step 16: Proxy Approach (No Child Age Claim) ──────────────────────────────

def test_step16_proxy_approach_no_child_age_claim():
    """
    Step 16: Detect pedestrians
    Use person detection.
    Don't claim: "Our AI identifies children."
    Instead use:
      Person + Approximate size/distance + School-zone GPS + School hours + Trajectory
    """
    from edge.pedestrian import CrossingBehavior, PedestrianRiskDetector

    # 1. Evaluate proxy components
    proxy = PedestrianRiskDetector.evaluate_vulnerable_proxy(
        person_detected=True,
        approx_size={"width_px": 50.0, "height_px": 120.0, "area_px": 6000.0, "aspect_ratio": 0.42},
        approx_distance_m=12.5,
        in_school_zone=True,
        in_school_hours=True,
        crossing_behavior=CrossingBehavior.POTENTIAL_RISK,
    )

    assert proxy["person_detected"] is True
    assert proxy["in_school_zone"] is True
    assert proxy["in_school_hours"] is True
    assert proxy["is_vulnerable_risk"] is True

    # MUST explicitly disclaim biometric child age estimation
    assert "child" not in proxy.get("claimed_age", "").lower()
    assert "Never claims facial/biometric child age" in proxy["no_age_claim"]

    # If outside school hours, proxy should NOT flag as active vulnerable school risk
    proxy_inactive = PedestrianRiskDetector.evaluate_vulnerable_proxy(
        person_detected=True,
        approx_size={"width_px": 50.0, "height_px": 120.0, "area_px": 6000.0, "aspect_ratio": 0.42},
        approx_distance_m=12.5,
        in_school_zone=True,
        in_school_hours=False,
        crossing_behavior=CrossingBehavior.POTENTIAL_RISK,
    )
    assert proxy_inactive["is_vulnerable_risk"] is False


# ── Step 17: Dangerous Crossing Behavior Multi-frame Analysis ─────────────────

def test_step17_dangerous_crossing_behavior_levels():
    """
    Step 17: Detect dangerous crossing behavior
    Analyze movement across multiple frames:
      Person walking parallel to road -> Normal
      Person moving toward road       -> Potential risk
      Person enters roadway           -> HIGH RISK
    """
    from edge.pedestrian import CrossingBehavior, PedestrianTrajectoryTracker

    # Road boundary line (right curb): (bx1, by1) -> (bx2, by2)
    # Right curb placed at x = 800
    boundary = ((800.0, 100.0), (800.0, 700.0))

    # Case 1: Walking parallel to road (x stays around 900 on sidewalk, moving y down)
    tracker_parallel = PedestrianTrajectoryTracker()
    t0 = 100.0
    tracker_parallel.update([(0.90, [880, 200, 920, 320])], current_time=t0, road_boundary_line=boundary)
    tracker_parallel.update([(0.90, [880, 220, 920, 340])], current_time=t0 + 0.1, road_boundary_line=boundary)
    tracks_p = tracker_parallel.update([(0.90, [880, 240, 920, 360])], current_time=t0 + 0.2, road_boundary_line=boundary)

    assert len(tracks_p) == 1
    traj_p = tracks_p[0].trajectory
    assert traj_p is not None
    # Parallel movement -> NORMAL
    assert traj_p.crossing_behavior == CrossingBehavior.NORMAL
    assert traj_p.moving_toward_road is False

    # Case 2: Moving toward road (x decreasing from 920 -> 880 -> 840 towards boundary at 800)
    tracker_moving = PedestrianTrajectoryTracker()
    tracker_moving.update([(0.92, [900, 200, 940, 320])], current_time=t0, road_boundary_line=boundary)
    tracker_moving.update([(0.92, [860, 210, 900, 330])], current_time=t0 + 0.1, road_boundary_line=boundary)
    tracks_m = tracker_moving.update([(0.92, [820, 220, 860, 340])], current_time=t0 + 0.2, road_boundary_line=boundary)

    assert len(tracks_m) == 1
    traj_m = tracks_m[0].trajectory
    assert traj_m is not None
    # Moving toward road -> POTENTIAL_RISK
    assert traj_m.crossing_behavior == CrossingBehavior.POTENTIAL_RISK
    assert traj_m.moving_toward_road is True

    # Case 3: Enters roadway (foot point crosses curb at x=800 into street at x=770)
    tracker_enters = PedestrianTrajectoryTracker()
    tracker_enters.update([(0.95, [830, 200, 870, 320])], current_time=t0, road_boundary_line=boundary)
    tracker_enters.update([(0.95, [800, 210, 840, 330])], current_time=t0 + 0.1, road_boundary_line=boundary)
    tracks_e = tracker_enters.update([(0.95, [760, 220, 800, 340])], current_time=t0 + 0.2, road_boundary_line=boundary)

    assert len(tracks_e) == 1
    traj_e = tracks_e[0].trajectory
    assert traj_e is not None
    # Enters roadway -> HIGH_RISK
    assert traj_e.crossing_behavior == CrossingBehavior.HIGH_RISK
    assert traj_e.in_roadway is True


def test_step17_risk_escalation_and_standard_event():
    """
    Verifies that:
      - Normal behavior suppresses alerts
      - Roadway entry generates high severity alert with standard 10-key schema
    """
    from edge.pedestrian import PedestrianRiskDetector

    detector = PedestrianRiskDetector(
        bus_id="BUS-102",
        camera_id="FRONT",
        cooldown_sec=0.0,
    )
    boundary = ((800.0, 100.0), (800.0, 700.0))
    gps = {"lat": 28.5672, "lon": 77.1720}  # DPS R.K. Puram

    # 1. Normal pedestrian (walking parallel to road)
    detector.process_frame(None, [("person", 0.90, [880, 200, 920, 320])], gps=gps, timestamp="2026-09-15T08:15:00.000+00:00", road_boundary_line=boundary)
    detector.process_frame(None, [("person", 0.90, [880, 220, 920, 340])], gps=gps, timestamp="2026-09-15T08:15:00.100+00:00", road_boundary_line=boundary)
    events_normal, _ = detector.process_frame(None, [("person", 0.90, [880, 240, 920, 360])], gps=gps, timestamp="2026-09-15T08:15:00.200+00:00", road_boundary_line=boundary)
    # Walking parallel MUST NOT create risk alert
    assert len(events_normal) == 0

    # 2. Reset and test pedestrian entering roadway
    detector.tracker.reset()
    detector.process_frame(None, [("person", 0.95, [830, 200, 870, 320])], gps=gps, timestamp="2026-09-15T08:15:00.000+00:00", road_boundary_line=boundary)
    detector.process_frame(None, [("person", 0.95, [800, 210, 840, 330])], gps=gps, timestamp="2026-09-15T08:15:00.100+00:00", road_boundary_line=boundary)
    events_high_risk, _ = detector.process_frame(None, [("person", 0.95, [760, 220, 800, 340])], gps=gps, timestamp="2026-09-15T08:15:00.200+00:00", road_boundary_line=boundary)

    assert len(events_high_risk) == 1
    event = events_high_risk[0]
    assert event.crossing_behavior == "HIGH_RISK"
    assert event.severity == "high"
    assert event.approx_distance_m > 0
    assert "height_px" in event.approx_size

    # Verify Phase 3 canonical 10-key standard event
    std = event.to_standard_dict()
    assert "eventId" in std
    assert std["type"] == "pedestrian_risk"
    assert std["confidence"] >= 0.90
    assert std["latitude"] == 28.5672
    assert std["longitude"] == 77.1720
    assert std["busId"] == "BUS-102"
    assert std["severity"] == "high"
    assert std["status"] == "unverified"
