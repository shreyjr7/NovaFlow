"""
Unit & Integration Tests for Phase 34: Demo Data Environment
============================================================
Verifies:
  1. 20 buses generated and tracked (BUS_001 through BUS_020).
  2. 5 metropolitan transit routes.
  3. 100+ road segments (115 segments).
  4. 500+ historical events in database.
  5. Events cover all 7 mandatory types:
     Potholes, Waterlogging, Congestion, Road damage, Missing signs, Pedestrian risk, Possible incidents.
  6. Each event contains Bus, Route, GPS, Timestamp, Type, Confidence.
  7. Bus kinematics move along routes realistically.
  8. DEMO MODE indicator is present so judges know fleet data is simulated.
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.services.demo_seeder_service import get_demo_seeder_service


@pytest.fixture
def client():
    return TestClient(app)


def test_twenty_buses_specification(client):
    svc = get_demo_seeder_service()
    buses = svc.get_buses()

    assert len(buses) == 20
    bus_ids = {b["bus_id"] for b in buses}
    expected_ids = {f"BUS_{i:03d}" for i in range(1, 21)}
    assert bus_ids == expected_ids

    for b in buses:
        assert "route_id" in b
        assert "lat" in b and "lon" in b
        assert "speed_kmh" in b
        assert "bearing_deg" in b
        assert b["status"] == "IN_SERVICE"
        assert b["active_cameras"] == 4


def test_five_routes_and_over_one_hundred_segments(client):
    svc = get_demo_seeder_service()
    routes_data = svc.get_routes()

    assert len(routes_data["routes"]) == 5
    route_ids = [r["route_id"] for r in routes_data["routes"]]
    assert set(route_ids) == {"ROUTE_1", "ROUTE_2", "ROUTE_3", "ROUTE_4", "ROUTE_5"}

    assert routes_data["total_segments"] >= 100
    assert len(svc.segments) == 115

    for seg in svc.segments:
        assert "segment_id" in seg
        assert "route_id" in seg
        assert "speed_limit_kmh" in seg
        assert "lat" in seg and "lon" in seg


def test_five_hundred_plus_historical_events_seeded(client):
    svc = get_demo_seeder_service()
    count = svc.seed_historical_events(target_count=525)
    assert count >= 500

    # Query via REST endpoint
    res = client.get("/api/v1/demo/events?limit=200")
    assert res.status_code == 200
    data = res.json()
    assert data["demo_mode"] is True
    assert len(data["events"]) > 0

    for ev in data["events"]:
        assert ev["bus_id"].startswith("BUS_")
        assert ev["timestamp"] is not None
        assert ev["event_type"] in [
            "POTHOLE", "WATERLOGGING", "CONGESTION_EVENT",
            "DAMAGED_ROAD", "ROAD_DAMAGE", "MISSING_TRAFFIC_SIGN", "PEDESTRIAN_RISK", "POSSIBLE_INCIDENT", "INCIDENT"
        ]
        assert 0.0 <= ev["confidence"] <= 1.0
        assert "lat" in ev["gps"] and "lon" in ev["gps"]
        assert "road_segment" in ev["gps"]


def test_all_seven_event_types_present(client):
    client.post("/api/v1/demo/seed")
    required_types = [
        "POTHOLE",
        "WATERLOGGING",
        "CONGESTION_EVENT",
        "DAMAGED_ROAD",
        "MISSING_TRAFFIC_SIGN",
        "PEDESTRIAN_RISK",
        "POSSIBLE_INCIDENT",
    ]

    for ev_type in required_types:
        res = client.get(f"/api/v1/demo/events?event_type={ev_type}&limit=5")
        assert res.status_code == 200
        data = res.json()
        assert data["total_returned"] > 0
        for ev in data["events"]:
            assert ev["event_type"] == ev_type


def test_realistic_bus_movement_kinematics(client):
    svc = get_demo_seeder_service()
    buses_before = [dict(b) for b in svc.get_buses()]

    # Advance kinematics by 5 seconds
    res = client.post("/api/v1/demo/tick?dt_seconds=5.0")
    assert res.status_code == 200
    buses_after = res.json()["buses"]

    assert len(buses_after) == 20
    # Coordinates or progress should have updated
    moved_count = 0
    for b1, b2 in zip(buses_before, buses_after):
        if (b1["lat"] != b2["lat"]) or (b1["lon"] != b2["lon"]) or (b1["segment_progress"] != b2["segment_progress"]):
            moved_count += 1
    assert moved_count > 0


def test_demo_mode_indicator_for_judges(client):
    res = client.get("/api/v1/demo/status")
    assert res.status_code == 200
    data = res.json()
    assert data["demo_mode"] is True
    assert data["indicator"] == "DEMO MODE"
    assert "⚡ DEMO MODE" in data["banner_text"]
    assert data["buses_count"] == 20
    assert data["routes_count"] == 5
    assert data["road_segments_count"] == 115
