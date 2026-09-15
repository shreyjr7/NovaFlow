"""
Unit tests for Backend Pedestrian Safety & School Zone Router (Phase 12)
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_list_school_zones():
    response = client.get("/api/v1/pedestrian/schools")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "schools" in data
    assert data["count"] >= 3
    sch = data["schools"][0]
    assert "school_id" in sch
    assert "name" in sch
    assert "location" in sch
    assert "active_hours" in sch
    assert "radius_m" in sch


def test_zone_densities():
    response = client.get("/api/v1/pedestrian/density")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "zones" in data
    assert data["count"] > 0
    zone = data["zones"][0]
    assert "school_id" in zone
    assert "density_level" in zone
    assert zone["density_level"] in ("LOW", "MEDIUM", "HIGH")


def test_ingest_and_list_pedestrian_risk_events():
    payload = {
        "location": {"lat": 28.5672, "lon": 77.1720},
        "timestamp": "2026-09-15T08:30:00Z",
        "bus_id": "BUS_DEL_101",
        "camera_id": "FRONT",
        "confidence": 0.94,
        "trajectory": {
            "speed_px_s": 42.0,
            "heading_deg": 35.0,
            "moving_toward_road": True,
            "vector": [15.0, 10.0],
        },
        "school_zone": {
            "school_id": "SCH_DEL_01",
            "name": "Delhi Public School, R.K. Puram",
            "distance_m": 45.0,
            "active_now": True,
            "speed_limit_kmh": 25.0,
        },
        "road_boundary": {
            "distance_px": 28.0,
            "is_near_boundary": True,
        },
        "zone_density": {
            "level": "HIGH",
            "pedestrian_count": 9,
            "is_crowded": True,
            "density_score": 0.75,
        },
        "crowded_area": True,
        "frame_b64": "data:image/jpeg;base64,mockframe123",
    }

    # POST new event
    post_res = client.post("/api/v1/pedestrian/events", json=payload)
    assert post_res.status_code == 201
    post_data = post_res.json()
    assert post_data["ok"] is True
    assert "event_id" in post_data

    # GET events and verify presence
    get_res = client.get("/api/v1/pedestrian/events?school_id=SCH_DEL_01")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["total"] > 0
    items = get_data["items"]
    assert any(e["event_type"] == "PEDESTRIAN_RISK" for e in items)


def test_pedestrian_safety_stats():
    response = client.get("/api/v1/pedestrian/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_risk_alerts_today" in data
    assert "monitored_school_zones" in data
    assert "crowded_zones_count" in data
    assert "hourly_distribution" in data
    assert "methodology" in data
    assert "disclaimer" in data["methodology"]
