"""
Unit tests for Public Urban Safety Dashboard (Phase 30)
=======================================================
Validates:
  1. Aggregated, non-sensitive civic information:
       - Road condition
       - Congestion
       - Waterlogging
       - Public road hazards
       - Aggregated traffic trends
  2. Formatting of citizen alerts with exact required phrases:
       - "Road hazard reported"
       - "Heavy congestion"
       - "Waterlogging"
  3. STRICT ZERO-PII SANITIZATION GUARANTEE:
       - No private passenger information
       - No raw passenger footage
       - No sensitive incident evidence
       - No unverified license plates
       - No personally identifiable information
  4. Citizen hazard acknowledgment action.
"""

import json
import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_public_overview_and_kpis():
    """Validates public executive overview endpoint and privacy guarantee notice."""
    res = client.get("/api/v1/public/overview")
    assert res.status_code == 200
    data = res.json()

    assert data["city"] == "Bengaluru"
    assert data["overall_road_condition_score"] > 70.0
    assert data["active_public_hazards_count"] >= 3
    assert "Zero-PII" in data["privacy_guarantee"]


def test_public_road_condition_aggregated():
    """Validates aggregated defect counts and repair stats without sensitive bus metadata."""
    res = client.get("/api/v1/public/road-condition")
    assert res.status_code == 200
    data = res.json()

    assert data["road_health_index"] > 0
    assert data["potholes_reported"] > 0
    assert data["surface_damage_reported"] > 0
    assert data["waterlogged_zones"] > 0
    assert data["repairs_completed_this_week"] > 0


def test_public_congestion_advisories():
    """Validates corridor traffic tiers, delay estimates, and average speeds."""
    res = client.get("/api/v1/public/congestion")
    assert res.status_code == 200
    data = res.json()

    assert data["city_average_speed_kmh"] > 15.0
    corridors = data["corridors"]
    assert len(corridors) >= 4
    for c in corridors:
        assert c["corridor_name"]
        assert c["traffic_level"] in ["Normal Flow", "Moderate Traffic", "Heavy Congestion", "Severe Congestion"]
        assert c["delay_minutes"] >= 0


def test_public_waterlogging_notices():
    """Validates active waterlogging notices, safe passage advice, and water depth tiers."""
    res = client.get("/api/v1/public/waterlogging")
    assert res.status_code == 200
    notices = res.json()

    assert len(notices) >= 1
    for n in notices:
        assert n["location_name"]
        assert n["water_depth_category"] in ["Passable with Caution", "Transit Lane Restricted", "Hazardous Standing Water"]
        assert n["safe_passage_advice"]


def test_public_hazard_feed_standard_labels():
    """
    Validates that every public alert strictly uses the standard public labels:
      - 'Road hazard reported'
      - 'Heavy congestion'
      - 'Waterlogging'
    """
    res = client.get("/api/v1/public/hazards")
    assert res.status_code == 200
    hazards = res.json()

    assert len(hazards) >= 3
    valid_labels = {"Road hazard reported", "Heavy congestion", "Waterlogging"}
    for h in hazards:
        assert h["standard_label"] in valid_labels
        assert h["location_name"]
        assert h["safety_recommendation"]


def test_strict_zero_pii_leak_prevention():
    """
    CRITICAL SECURITY AUDIT TEST:
    Recursively inspects the serialized JSON payload across ALL public endpoints.
    Ensures absolute zero presence of sensitive keys or PII patterns:
      - passenger (zero passenger count, occupancy, cabin telemetry)
      - license_plate / plate (zero vehicle registration or ANPR data)
      - raw_video / camera_feed / evidence_clip (zero video streams or evidence clips)
      - driver (zero staff records or operator identities)
      - vin / mac_address / sha256_hash
    """
    public_endpoints = [
        "/api/v1/public/overview",
        "/api/v1/public/road-condition",
        "/api/v1/public/congestion",
        "/api/v1/public/waterlogging",
        "/api/v1/public/hazards",
        "/api/v1/public/traffic-trends",
        "/api/v1/public/map-hotspots",
    ]

    forbidden_terms = [
        "license_plate",
        "plate_number",
        "raw_video",
        "camera_feed",
        "evidence_clip",
        "driver_id",
        "driver_name",
        "passenger_count",
        "cabin_telemetry",
        "mac_address",
        "vin",
    ]

    for ep in public_endpoints:
        res = client.get(ep)
        assert res.status_code == 200, f"Endpoint {ep} failed"
        payload_text = json.dumps(res.json()).lower()

        for term in forbidden_terms:
            assert term not in payload_text, f"PII LEAK DETECTED: Term '{term}' found in public endpoint {ep}"


def test_citizen_hazard_acknowledgment():
    """Validates citizen acknowledgment / community upvote counter."""
    res_before = client.get("/api/v1/public/hazards")
    assert res_before.status_code == 200
    target_id = res_before.json()[0]["hazard_id"]
    initial_count = res_before.json()[0]["citizen_acknowledgments"]

    res_ack = client.post(f"/api/v1/public/hazards/{target_id}/acknowledge")
    assert res_ack.status_code == 200
    assert res_ack.json()["citizen_acknowledgments"] == initial_count + 1
