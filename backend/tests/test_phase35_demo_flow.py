"""
Unit & Integration Tests for Phase 35: End-to-End Demo Flow
============================================================
Verifies:
  1. The canonical 17-step scenario execution for Bus 104 on Route 12:
     - Step 1: Video processing begins
     - Step 2: Vehicle detection (Cars, Motorcycles, Buses, Trucks)
     - Step 3: Tracking (Count, Density, Speed)
     - Step 4: High density + low speed -> TRAFFIC BOTTLENECK
     - Step 5: Road-facing camera pothole with temporal confirmation -> ROAD DEFECT
     - Step 6: GPS attaches location
     - Step 7: Network disconnect -> local buffering
     - Step 8: Network reconnect -> event transmission
     - Step 9: Central backend ingestion
     - Step 10: Duplicate detection nearby
     - Step 11: Appearance on GIS map
     - Step 12: Maintenance authority receives alert
     - Step 13: Authority verifies pothole
     - Step 14: Maintenance ticket created
     - Step 15: Second bus confirmation -> increases confidence, no duplicate
     - Step 16: Analytics dashboard updates
     - Step 17: Post-repair resolution -> marks RESOLVED
  2. Vehicle incident investigation pipeline:
     Vehicle anomaly -> Track -> Buffered clip -> Plate detection -> OCR -> Confidence -> Human verification -> Incident report.
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.services.demo_flow_service import get_demo_flow_service


@pytest.fixture
def client():
    return TestClient(app)


def test_step_by_step_canonical_seventeen_steps(client):
    svc = get_demo_flow_service()
    svc.reset_scenario()

    # Step 1: Video processing
    r1 = client.post("/api/v1/demo-flow/step/1")
    assert r1.status_code == 200
    assert r1.json()["current_step"] == 1

    # Step 2: Vehicle detection
    r2 = client.post("/api/v1/demo-flow/step/2")
    assert r2.status_code == 200
    details2 = r2.json()["latest_log"]["details"]["detected_entities"]
    assert "Cars" in details2 and "Motorcycles" in details2 and "Buses" in details2 and "Trucks" in details2

    # Step 3: Tracking
    r3 = client.post("/api/v1/demo-flow/step/3")
    assert r3.status_code == 200
    details3 = r3.json()["latest_log"]["details"]
    assert details3["vehicle_count"] == 38
    assert details3["density_per_km"] == 152.0
    assert details3["average_speed_kmh"] == 8.5

    # Step 4: Traffic Bottleneck
    r4 = client.post("/api/v1/demo-flow/step/4")
    assert r4.status_code == 200
    assert r4.json()["latest_log"]["details"]["event_type"] == "TRAFFIC BOTTLENECK"

    # Step 5: Pothole & Temporal confirmation -> ROAD DEFECT
    r5 = client.post("/api/v1/demo-flow/step/5")
    assert r5.status_code == 200
    details5 = r5.json()["latest_log"]["details"]
    assert details5["event_type"] == "ROAD DEFECT"
    assert "PASSED" in details5["temporal_confirmation"]

    # Step 6: GPS attaches location
    r6 = client.post("/api/v1/demo-flow/step/6")
    assert r6.status_code == 200
    assert r6.json()["latest_log"]["details"]["road_segment"] == "ROUTE_12_SEG_4"

    # Step 7: Network disconnected -> Stored locally
    r7 = client.post("/api/v1/demo-flow/step/7")
    assert r7.status_code == 200
    assert r7.json()["latest_log"]["details"]["network_state"] == "OFFLINE"
    assert r7.json()["latest_log"]["details"]["buffered_events_count"] == 1

    # Step 8: Network reconnects -> Event transmitted
    r8 = client.post("/api/v1/demo-flow/step/8")
    assert r8.status_code == 200
    assert r8.json()["latest_log"]["details"]["network_state"] == "ONLINE"

    # Step 9: Central backend receives event
    r9 = client.post("/api/v1/demo-flow/step/9")
    assert r9.status_code == 200
    assert "ev_demo_flow" in r9.json()["latest_log"]["details"]["event_id"]

    # Step 10: Duplicate detection
    r10 = client.post("/api/v1/demo-flow/step/10")
    assert r10.status_code == 200
    assert r10.json()["latest_log"]["details"]["status"] in ("NEW_CLUSTER_INITIALIZED", "EXISTING_CLUSTER_REINFORCED")

    # Step 11: GIS Map appearance
    r11 = client.post("/api/v1/demo-flow/step/11")
    assert r11.status_code == 200
    assert r11.json()["latest_log"]["details"]["layer"] == "potholes"

    # Step 12: Alert received
    r12 = client.post("/api/v1/demo-flow/step/12")
    assert r12.status_code == 200
    assert "ALT-2026-R12-04" in r12.json()["latest_log"]["details"]["alert_id"]

    # Step 13: Authority verifies pothole
    r13 = client.post("/api/v1/demo-flow/step/13")
    assert r13.status_code == 200
    assert r13.json()["latest_log"]["details"]["action"] == "VERIFIED_BY_OFFICER"

    # Step 14: Maintenance ticket created
    r14 = client.post("/api/v1/demo-flow/step/14")
    assert r14.status_code == 200
    assert "TICK-2026-R12-01" in r14.json()["latest_log"]["details"]["ticket_id"]

    # Step 15: Second bus (BUS_109) confirms pothole -> Increases confidence, no duplicate
    r15 = client.post("/api/v1/demo-flow/step/15")
    assert r15.status_code == 200
    details15 = r15.json()["latest_log"]["details"]
    assert details15["second_bus"] == "BUS_109"
    assert details15["duplicate_created"] is False
    assert details15["total_observations"] >= 2

    # Step 16: Analytics updates
    r16 = client.post("/api/v1/demo-flow/step/16")
    assert r16.status_code == 200
    assert len(r16.json()["latest_log"]["details"]["updated_charts"]) >= 3

    # Step 17: Repaired and resolved
    r17 = client.post("/api/v1/demo-flow/step/17")
    assert r17.status_code == 200
    assert r17.json()["latest_log"]["details"]["authority_action"] == "RESOLVED"
    assert r17.json()["scenario_state"]["defect_status"] == "RESOLVED"


def test_autonomous_run_all_demo_steps(client):
    res = client.post("/api/v1/demo-flow/run-all")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ALL_17_STEPS_COMPLETED"
    assert data["total_steps"] == 17
    assert len(data["timeline"]) == 17
    assert data["final_scenario_state"]["defect_status"] == "RESOLVED"


def test_incident_investigation_flow(client):
    res = client.post("/api/v1/demo-flow/incident-run?vehicle_id=TRACK_VEH_842&plate_text=DL+01+AB+1234")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "INCIDENT_FLOW_COMPLETED"
    assert len(data["stages"]) == 8

    stage_names = [s["name"] for s in data["stages"]]
    assert stage_names == [
        "Vehicle Anomaly",
        "Track Vehicle",
        "Retrieve Buffered Clip",
        "Plate Detection",
        "OCR",
        "Confidence",
        "Human Verification",
        "Incident Report",
    ]

    report = data["report"]
    assert report["vehicle_track_id"] == "TRACK_VEH_842"
    assert report["license_plate"] == "DL 01 AB 1234"
    assert report["confidence"] >= 0.90
    assert report["chain_of_custody_status"] == "VERIFIED_IMMUTABLE"
