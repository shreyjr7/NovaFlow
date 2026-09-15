"""
Unit Tests for Incident & Hit-and-Run Anomaly Detection Engine
=============================================================
Tests:
  1. Solitary hard-braking suppression (compound condition enforcement)
  2. Compound collision risk detection
  3. Hit-and-run anomaly signature detection
  4. 10-step incident capture workflow completeness
  5. ANPR plate recognition & crop generation
  6. Rolling buffer evidence sequence extraction
  7. Strict legal compliance (no fault attribution, strictly POSSIBLE_INCIDENT)
"""

import time
import pytest
from datetime import datetime, timezone

from edge.incident.signals import (
    TrajectorySignalEvaluator,
    VehicleTrackState,
)
from edge.incident.rolling_buffer import RollingFrameBuffer
from edge.incident.anpr import NumberPlateRecognizer
from edge.incident.anomaly_detector import IncidentAnomalyDetector, LEGAL_DISCLAIMER


def test_solitary_hard_braking_suppressed():
    """
    CRITICAL REQUIREMENT: A single hard-braking event alone MUST NOT trigger an incident.
    """
    evaluator = TrajectorySignalEvaluator()
    detector = IncidentAnomalyDetector(camera_id="FRONT", bus_id="BUS_101")

    # Primary track experiencing sudden deceleration (-6.0 m/s^2), but isolated
    primary = VehicleTrackState(
        track_id=101,
        class_name="car",
        speed_kmh=15.0,
        bbox=[200, 200, 300, 300],
        heading_deg=90.0,
        prev_speed_kmh=45.0,
        prev_heading_deg=90.0,
        prev_bbox=[190, 200, 290, 300],
        acceleration_m_s2=-6.0,
    )

    signals = evaluator.evaluate_signals(primary_track=primary, nearby_tracks=[], dt=0.2)
    assert signals["sudden_deceleration"].triggered is True
    assert signals["nearby_vehicle_interaction"].triggered is False
    assert signals["vehicle_leaving_scene"].triggered is False

    is_incident, category, conf = evaluator.evaluate_compound_condition(signals)
    assert is_incident is False
    assert category == "HARD_BRAKING_NORMAL"
    assert conf == 0.0

    # Also test via full detector
    gps = {"lat": 28.6139, "lon": 77.2090}
    tracks = [{
        "track_id": 101,
        "class": "car",
        "speed_kmh": 15.0,
        "bbox": [200, 200, 300, 300],
        "heading_deg": 90.0,
    }]
    # Run two frames so previous speed is registered
    detector.process_frame(frame=None, tracks=[{"track_id": 101, "class": "car", "speed_kmh": 45.0, "bbox": [190, 200, 290, 300]}], gps=gps)
    events = detector.process_frame(frame=None, tracks=tracks, gps=gps)
    assert len(events) == 0, "Solitary hard braking must not generate an incident alert"


def test_compound_collision_risk_detected():
    """
    Tests compound condition: Sudden Deceleration + Close Vehicle Interaction
    flags a POSSIBLE_INCIDENT with COLLISION_RISK.
    """
    evaluator = TrajectorySignalEvaluator()

    primary = VehicleTrackState(
        track_id=201,
        class_name="car",
        speed_kmh=10.0,
        bbox=[200, 200, 300, 300],
        heading_deg=90.0,
        prev_speed_kmh=40.0,
        prev_heading_deg=90.0,
        prev_bbox=[190, 200, 290, 300],
        acceleration_m_s2=-5.2,
    )

    neighbor = VehicleTrackState(
        track_id=202,
        class_name="truck",
        speed_kmh=12.0,
        bbox=[220, 210, 320, 310],  # Overlapping bbox
        heading_deg=88.0,
    )

    signals = evaluator.evaluate_signals(primary_track=primary, nearby_tracks=[neighbor], dt=0.2)
    assert signals["sudden_deceleration"].triggered is True
    assert signals["nearby_vehicle_interaction"].triggered is True

    is_incident, category, conf = evaluator.evaluate_compound_condition(signals)
    assert is_incident is True
    assert category == "COLLISION_RISK"
    assert conf >= 0.70


def test_hit_and_run_signature_detected():
    """
    Tests Hit-and-Run signature:
      Vehicle interaction + disappearing interacting object + vehicle leaving scene.
    """
    evaluator = TrajectorySignalEvaluator()

    # Surviving car speeding away post interaction
    primary = VehicleTrackState(
        track_id=301,
        class_name="car",
        speed_kmh=48.0,
        bbox=[200, 150, 350, 280],
        heading_deg=120.0,
        prev_speed_kmh=20.0,
        prev_heading_deg=90.0,
        acceleration_m_s2=4.5,
        had_recent_interaction=True,
        interaction_track_id=302,
    )

    # Disappeared motorcycle
    neighbor = VehicleTrackState(
        track_id=302,
        class_name="motorcycle",
        speed_kmh=0.0,
        bbox=[190, 220, 250, 290],
        disappeared=True,
        had_recent_interaction=True,
        interaction_track_id=301,
    )

    signals = evaluator.evaluate_signals(primary_track=primary, nearby_tracks=[neighbor], dt=0.2)
    assert signals["nearby_vehicle_interaction"].triggered is True
    assert signals["object_disappearance_after_interaction"].triggered is True
    assert signals["vehicle_leaving_scene"].triggered is True

    is_incident, category, conf = evaluator.evaluate_compound_condition(signals)
    assert is_incident is True
    assert category == "HIT_AND_RUN_SIGNATURE"
    assert conf >= 0.80


def test_ten_step_workflow_completeness():
    """
    Verifies that when an anomaly occurs, the detector executes all 10 steps:
      1. Retrieve involved vehicle tracks
      2. Identify nearby vehicles
      3. Save event timestamp
      4. Save GPS
      5. Select relevant camera
      6. Retrieve rolling buffer
      7. Create evidence clip
      8. Run ANPR on best available frame
      9. Generate confidence score
      10. Send secure alert strictly as POSSIBLE_INCIDENT with PENDING_REVIEW
    """
    buffer = RollingFrameBuffer(capacity=20)
    for i in range(10):
        buffer.push(frame=None, timestamp_s=100.0 + i * 0.1, frame_idx=i, gps={"lat": 28.6139, "lon": 77.2090})

    detector = IncidentAnomalyDetector(
        camera_id="FRONT",
        bus_id="BUS_101",
        rolling_buffer=buffer,
        cooldown_seconds=0.0,
    )

    # Prime history with interaction
    f1_tracks = [
        {"track_id": 401, "class": "car", "speed_kmh": 40.0, "bbox": [100, 100, 200, 200], "heading_deg": 90.0},
        {"track_id": 402, "class": "motorcycle", "speed_kmh": 30.0, "bbox": [110, 110, 160, 170], "heading_deg": 90.0},
    ]
    detector.process_frame(frame=None, tracks=f1_tracks, gps={"lat": 28.6139, "lon": 77.2090})

    # Trigger frame: car accelerates away, motorcycle disappears
    f2_tracks = [
        {"track_id": 401, "class": "car", "speed_kmh": 50.0, "bbox": [150, 100, 250, 200], "heading_deg": 110.0},
        # 402 disappeared
        {"track_id": 403, "class": "bus", "speed_kmh": 25.0, "bbox": [400, 200, 600, 400], "heading_deg": 90.0},
    ]
    events = detector.process_frame(frame=None, tracks=f2_tracks, gps={"lat": 28.6139, "lon": 77.2090, "bearing_deg": 88.0})

    assert len(events) == 1
    ev = events[0]

    # Step 10 & Legal requirements
    assert ev["event_type"] == "POSSIBLE_INCIDENT"
    assert ev["event_type"] != "CONFIRMED CRIME"
    assert ev["event_type"] != "DRIVER AT FAULT"
    assert ev["verification_status"] == "PENDING_REVIEW"
    assert ev["requires_human_verification"] is True
    assert LEGAL_DISCLAIMER in ev["legal_disclaimer"]

    # Step 1: Involved tracks
    assert len(ev["involved_tracks"]) >= 1
    assert ev["involved_tracks"][0]["track_id"] == 401

    # Step 2: Nearby vehicles
    assert len(ev["nearby_vehicles"]) >= 1
    assert ev["nearby_vehicles"][0]["track_id"] == 403

    # Step 3: Timestamp
    assert "timestamp" in ev

    # Step 4: GPS
    assert ev["location"]["lat"] == 28.6139
    assert ev["location"]["lon"] == 77.2090

    # Step 5: Camera
    assert ev["camera_id"] == "FRONT"

    # Step 6 & 7: Evidence clip
    assert "evidence_clip" in ev
    clip = ev["evidence_clip"]
    assert clip["frame_count"] > 0
    assert len(clip["frames"]) > 0
    assert clip["key_frame_b64"] != ""

    # Step 8: ANPR
    assert "anpr" in ev
    anpr = ev["anpr"]
    assert anpr["detected"] is True
    assert len(anpr["plate_number"]) >= 8
    assert anpr["plate_crop_b64"] != ""

    # Step 9: Confidence score
    assert 0.0 < ev["confidence"] <= 1.0


def test_anpr_plate_generation():
    """Verifies that ANPR derives realistic Indian plate formats and valid confidence."""
    anpr_engine = NumberPlateRecognizer()
    res = anpr_engine.process_vehicle(frame=None, bbox=[100, 100, 200, 200], track_id=55, vehicle_class="car")

    assert res.detected is True
    assert res.confidence >= 0.80
    assert res.state_code in ["DL", "MH", "KA", "HR", "UP", "TS", "TN", "GJ", "WB"]
    parts = res.plate_number.split()
    assert len(parts) == 4, f"Plate '{res.plate_number}' must have 4 segments: [State] [RTO] [Series] [Number]"
    assert len(parts[3]) == 4 and parts[3].isdigit()


def test_rolling_buffer_evidence_sequence():
    """Verifies circular FIFO behavior and clip extraction."""
    buffer = RollingFrameBuffer(capacity=10)
    for i in range(15):
        buffer.push(frame=None, timestamp_s=100.0 + i, frame_idx=i)

    assert buffer.size() == 10
    clip = buffer.create_evidence_clip(pre_frames=3, post_frames=3)
    assert clip["frame_count"] <= 10
    phases = [f["phase"] for f in clip["frames"]]
    assert "PRE_IMPACT" in phases
    assert "IMPACT" in phases
    assert "POST_IMPACT" in phases
