"""
Tests for Phase 9 (Backend API & Database) and Phase 10 (Deduplication)
======================================================================
Verifies:
  - Step 24: Backend API endpoints (POST /events, GET /events, GET /events/{id},
             PATCH /events/{id}, GET /buses, GET /routes, GET /analytics)
  - Step 25: PostGIS & relational database entities
  - Step 26: Deduplication and merging repeated defect reports
             (BUS 101, 205, 311 -> ONE POTHOLE, Reports: 3, Confidence: HIGH)
"""

import os
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.spatial_clustering_service import get_spatial_clustering_service
from backend.app.models.entities import (
    IngestedEvent,
    GpsTelemetry,
    RouteModel,
    BusModel,
    InfrastructureDefect,
    StatusAuditLog,
    EventVerification,
    UserModel,
)

os.environ["NOVAFLOW_DEV_MODE"] = "true"


@pytest.fixture
def client():
    return TestClient(app)


def test_step24_backend_api_endpoints(client):
    # 1. POST /events with edge headers
    payload = {
        "event_id": "EVT-PHASE9-001",
        "event_type": "POTHOLE",
        "severity": "HIGH",
        "confidence": 0.94,
        "gps": {"lat": 28.6139, "lon": 77.2090},
        "road_segment": "CENTRAL_CORRIDOR",
        "bus_id": "BUS-101",
        "camera_id": "CAM-FRONT",
        "evidence": {"description": "Pothole detected by optical sensor"},
    }
    headers = {"X-Edge-Device-Id": "BUS-101", "X-Edge-Token": "novaflow-edge-secret"}
    r_post = client.post("/events", json=payload, headers=headers)
    assert r_post.status_code in (200, 201, 202), r_post.text
    created = r_post.json()
    assert created["event_id"] == "EVT-PHASE9-001"

    # 2. GET /events
    r_get = client.get("/events")
    assert r_get.status_code == 200
    events_data = r_get.json()
    assert isinstance(events_data.get("events") if isinstance(events_data, dict) else events_data, list)

    # 3. GET /events/{id}
    r_single = client.get("/events/EVT-PHASE9-001")
    assert r_single.status_code == 200
    assert r_single.json()["event_id"] == "EVT-PHASE9-001"

    # 4. PATCH /events/{id}
    r_patch = client.patch("/events/EVT-PHASE9-001", json={"status": "CONFIRMED"})
    assert r_patch.status_code == 200
    assert r_patch.json()["status"].lower() == "confirmed"

    # 5. GET /buses
    r_buses = client.get("/buses")
    assert r_buses.status_code == 200

    # 6. GET /routes
    r_routes = client.get("/routes")
    assert r_routes.status_code == 200

    # 7. GET /analytics
    r_analytics = client.get("/analytics")
    assert r_analytics.status_code == 200


def test_step25_database_models_instantiation():
    # Verify all 8 domain models can be instantiated
    evt = IngestedEvent(event_id="EVT-DB-01", event_type="POTHOLE", confidence=0.92, status="PENDING")
    gps = GpsTelemetry(bus_id="BUS-101", latitude=28.6139, longitude=77.2090, speed_kmh=32.5)
    route = RouteModel(route_id="ROUTE_12", name="Route 12", city="Delhi NCR", total_distance_km=14.8)
    bus = BusModel(bus_id="BUS-101", bus_name="Delhi Electric DTC #101", current_route_id="ROUTE_12")
    defect = InfrastructureDefect(asset_id="ASSET-001", asset_type="POTHOLE", lat=28.6139, lon=77.2090)
    audit = StatusAuditLog(event_id="EVT-DB-01", previous_status="PENDING", new_status="CONFIRMED")
    verif = EventVerification(event_id="EVT-DB-01", authority_role="TRAFFIC POLICE", verification_status="CONFIRMED")
    user = UserModel(username="test_admin", email="test@novaflow.gov.in", hashed_password="hash", role="ADMIN")

    assert evt.event_id == "EVT-DB-01"
    assert gps.bus_id == "BUS-101"
    assert route.route_id == "ROUTE_12"
    assert bus.bus_id == "BUS-101"
    assert defect.asset_type == "POTHOLE"
    assert audit.new_status == "CONFIRMED"
    assert verif.verification_status == "CONFIRMED"
    assert user.role == "ADMIN"


def test_step26_merge_repeated_reports():
    """
    Step 26  Merge repeated reports
    Example:
      BUS 101, Pothole, GPS 28.61390
      BUS 205, Pothole, GPS 28.61394
      BUS 311, Pothole, GPS 28.61387
      ->
      ONE POTHOLE
      Reports: 3
      Confidence: HIGH
      Single GIS map pin
    """
    service = get_spatial_clustering_service()
    reports = [
        {"bus": "BUS 101", "type": "Pothole", "lat": 28.61390, "lon": 77.20900},
        {"bus": "BUS 205", "type": "Pothole", "lat": 28.61394, "lon": 77.20902},
        {"bus": "BUS 311", "type": "Pothole", "lat": 28.61387, "lon": 77.20898},
    ]

    result = service.merge_repeated_reports(reports)

    assert result["title"] == "ONE POTHOLE"
    assert result["reports"] == 3
    assert result["confidence"] == "HIGH"
    assert result["single_pin_representation"] is True
    assert result["duplicate_pins_suppressed"] == 2
    assert "BUS 101" in result["detected_by"]
    assert "BUS 205" in result["detected_by"]
    assert "BUS 311" in result["detected_by"]
