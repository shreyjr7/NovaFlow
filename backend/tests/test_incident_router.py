"""
Integration Tests for Incident Anomaly Backend Router
=====================================================
Tests:
  - Ingestion of POSSIBLE_INCIDENT events
  - Querying and filtering by verification status and category
  - Human review transitions (PENDING_REVIEW -> VERIFIED_INCIDENT / DISMISSED)
  - Enforcement that illegal fault determinations cannot be set
  - KPI summary statistics calculation
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_list_incidents_default_seeds():
    """Verify that seed incidents load with strict POSSIBLE_INCIDENT labeling."""
    response = client.get("/api/v1/incidents/events")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 4
    for item in data["items"]:
        assert item["event_type"] == "POSSIBLE_INCIDENT"
        assert item["event_type"] != "CONFIRMED CRIME"
        assert item["event_type"] != "DRIVER AT FAULT"
        assert "legal_disclaimer" in item
        assert "Human verification required" in item["legal_disclaimer"]


def test_ingest_incident_event():
    """Test edge event ingestion and persistence."""
    payload = {
        "event_id": "test_inc_999",
        "event_type": "POSSIBLE_INCIDENT",
        "incident_category": "COLLISION_RISK",
        "verification_status": "PENDING_REVIEW",
        "confidence": 0.89,
        "location": {"lat": 28.7041, "lon": 77.1025, "bearing_deg": 180.0},
        "bus_id": "BUS_99",
        "camera_id": "FRONT",
        "involved_tracks": [
            {
                "track_id": 991,
                "class_name": "car",
                "speed_kmh": 22.0,
                "heading_deg": 180.0,
                "bbox": [100, 100, 200, 200],
                "role": "primary",
            }
        ],
        "nearby_vehicles": [],
        "explainable_signals": {
            "sudden_deceleration": {
                "name": "sudden_deceleration",
                "triggered": True,
                "value": -5.1,
                "threshold": -4.5,
                "unit": "m/s^2",
                "description": "Hard stop",
            }
        },
        "is_hit_and_run": False,
    }

    response = client.post("/api/v1/incidents/events", json=payload)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["status"] == "ingested"
    assert res_data["event_id"] == "test_inc_999"
    assert res_data["event_type"] == "POSSIBLE_INCIDENT"
    assert res_data["verification_status"] == "PENDING_REVIEW"


def test_filter_incidents():
    """Test filtering by status and hit-and-run signature."""
    # Filter pending review
    res_pending = client.get("/api/v1/incidents/events?verification_status=PENDING_REVIEW")
    assert res_pending.status_code == 200
    items = res_pending.json()["items"]
    for it in items:
        assert it["verification_status"] == "PENDING_REVIEW"

    # Filter hit-and-run
    res_hnr = client.get("/api/v1/incidents/events?is_hit_and_run=true")
    assert res_hnr.status_code == 200
    items_hnr = res_hnr.json()["items"]
    for it in items_hnr:
        assert it["is_hit_and_run"] is True


def test_human_review_workflow_verified():
    """Human review action to verify an incident."""
    payload = {
        "status": "VERIFIED_INCIDENT",
        "reviewer_id": "officer_test_10",
        "notes": "Video reviewed; bumper contact confirmed with secondary vehicle.",
    }
    response = client.patch("/api/v1/incidents/events/inc_del_001/review", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verification_status"] == "VERIFIED_INCIDENT"
    assert data["reviewer_id"] == "officer_test_10"
    assert "bumper contact confirmed" in data["human_notes"]
    assert "reviewed_at" in data and data["reviewed_at"] is not None


def test_human_review_workflow_dismissed():
    """Human review action to dismiss a false positive."""
    payload = {
        "status": "DISMISSED",
        "reviewer_id": "officer_test_10",
        "notes": "False alarm; vehicle braked for dog on road with no contact.",
    }
    response = client.patch("/api/v1/incidents/events/inc_del_002/review", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verification_status"] == "DISMISSED"
    assert data["human_notes"] == payload["notes"]


def test_human_review_invalid_status_rejected():
    """System must reject illegal designations like 'CONFIRMED_CRIME' or 'GUILTY'."""
    payload = {
        "status": "DRIVER_AT_FAULT",
        "reviewer_id": "illegal_actor",
        "notes": "Attempting unauthorized legal assertion",
    }
    response = client.patch("/api/v1/incidents/events/inc_del_001/review", json=payload)
    assert response.status_code == 400
    assert "Permitted human review outcomes" in response.json()["detail"]


def test_incident_stats():
    """Verify aggregated metrics and legal compliance checks."""
    response = client.get("/api/v1/incidents/stats")
    assert response.status_code == 200
    stats = response.json()
    assert "total_anomalies" in stats
    assert "pending_review" in stats
    assert "verified_incidents" in stats
    assert "dismissed_count" in stats
    assert "hit_and_run_count" in stats
    assert "legal_compliance" in stats
    assert stats["legal_compliance"]["human_in_the_loop_enforced"] is True
