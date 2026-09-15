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
