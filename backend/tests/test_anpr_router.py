"""
Integration Tests for ANPR Backend Router
=========================================
Tests:
  - ANPR candidate recognition and storage
  - Filtering by operational state (READABLE, LOW_CONFIDENCE, NOT_READABLE, NOT_PRESENT)
  - Quarantine enforcement ("Human verification required", auto_publish=False)
  - Human verification workflows (APPROVE, EDIT, REJECT)
  - Statistical summaries & safety guardrail checks
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_list_anpr_records():
    """Verify listing seed ANPR records."""
    response = client.get("/api/v1/anpr/records")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 6
    assert len(data["items"]) >= 6

    # Verify essential fields
    first = data["items"][0]
    assert "registration_number" in first
    assert "confidence" in first
    assert "evidence_reference" in first
    assert "state" in first


def test_filter_records_by_state():
    """Verify filtering records by state."""
    res_readable = client.get("/api/v1/anpr/records?state=READABLE")
    assert res_readable.status_code == 200
    for it in res_readable.json()["items"]:
        assert it["state"] == "READABLE"

    res_low = client.get("/api/v1/anpr/records?state=LOW_CONFIDENCE")
    assert res_low.status_code == 200
    for it in res_low.json()["items"]:
        assert it["state"] == "LOW_CONFIDENCE"
        assert it["human_verification_required"] is True
        assert it["quarantined"] is True
        assert "Human verification required" in it["verification_notice"]


def test_execute_anpr_pipeline_endpoint():
    """Test POST /api/v1/anpr/recognize endpoint."""
    payload = {
        "bus_id": "BUS_501",
        "camera_id": "FRONT",
        "gps": {"lat": 28.6139, "lon": 77.2090, "road_segment": "DEL_01"},
        "candidate_frames": [
            {
                "frame_idx": 1,
                "sharpness": 180.0,
                "detection_confidence": 0.95,
                "ocr_text": "MH 12 RN 5678",
                "plate_present": True,
            }
        ],
    }

    response = client.post("/api/v1/anpr/recognize", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["registration_number"] == "MH 12 RN 5678"
    assert data["state"] == "READABLE"
    assert data["auto_publish"] is True
    assert data["quarantined"] is False


def test_quarantine_enforced_on_low_confidence():
    """Verify that a degraded candidate is quarantined and blocked from publishing."""
    payload = {
        "bus_id": "BUS_502",
        "camera_id": "REAR",
        "gps": {"lat": 28.5000, "lon": 77.1000},
        "candidate_frames": [
            {
                "frame_idx": 5,
                "sharpness": 40.0,
                "detection_confidence": 0.65,
                "ocr_text": "HR 26 BC 3456",
                "simulate_low_confidence": True,
                "plate_present": True,
            }
        ],
    }

    response = client.post("/api/v1/anpr/recognize", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["state"] == "LOW_CONFIDENCE"
    assert data["auto_publish"] is False
    assert data["quarantined"] is True
    assert data["human_verification_required"] is True
    assert data["verification_notice"] == "Human verification required"


def test_human_verification_approve_unquarantines():
    """Verify human officer APPROVE action un-quarantines plate and sets READABLE."""
    payload = {
        "action": "APPROVE",
        "officer_id": "officer_delhi_99",
        "notes": "Plate visually inspected against RAW frame. Clear HR 26 BC 3456.",
    }
    response = client.patch("/api/v1/anpr/records/anpr_rec_002/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "READABLE"
    assert data["quarantined"] is False
    assert data["verified_by"] == "officer_delhi_99"


def test_human_verification_edit_plate():
    """Verify human officer can edit OCR transcription errors."""
    payload = {
        "action": "EDIT",
        "verified_plate": "HR 26 BC 3458",
        "officer_id": "officer_delhi_99",
        "notes": "Corrected last digit from 6 to 8 after zooming into raw crop.",
    }
    response = client.patch("/api/v1/anpr/records/anpr_rec_002/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "READABLE"
    assert data["registration_number"] == "HR 26 BC 3458"
    assert data["quarantined"] is False


def test_human_verification_reject():
    """Verify human officer can reject unreadable plate."""
    payload = {
        "action": "REJECT",
        "officer_id": "officer_delhi_99",
        "notes": "Too obscured by mud to transcribe accurately.",
    }
    response = client.patch("/api/v1/anpr/records/anpr_rec_003/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "NOT_READABLE"
    assert data["registration_number"] == "NOT_READABLE"
    assert data["quarantined"] is False


def test_anpr_stats():
    """Verify statistical aggregation and guardrail audit report."""
    response = client.get("/api/v1/anpr/stats")
    assert response.status_code == 200
    stats = response.json()
    assert "total_scanned" in stats
    assert "readable_count" in stats
    assert "low_confidence_count" in stats
    assert "readability_rate_pct" in stats
    assert "safety_guardrails" in stats
    assert stats["safety_guardrails"]["auto_publish_low_confidence_blocked"] is True
    assert stats["safety_guardrails"]["human_verification_mandated"] is True
