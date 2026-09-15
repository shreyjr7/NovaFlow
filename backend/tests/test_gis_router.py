"""
Unit and Integration tests for GIS Command Center Router (Phase 17).
===================================================================
Tests:
  - GeoJSON FeatureCollection export across all 12 map layers
  - Layer-level, severity, district, and bus filtering
  - Live bus fleet telemetry feed
  - Transit route geometry polylines
  - Operator workflow actions: Confirm, Dismiss, Escalate, Create Ticket
  - Validation of maintenance ticket work orders
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.database.session import init_db

init_db()

client = TestClient(app)

REQUIRED_LAYERS = [
    "bus_locations",
    "bus_routes",
    "potholes",
    "road_damage",
    "waterlogging",
    "missing_signs",
    "missing_dividers",
    "zebra_crossing_issues",
    "traffic_congestion",
    "incidents",
    "pedestrian_risk",
    "maintenance_tickets",
]


def test_gis_features_all_layers_and_metadata():
    """Validates GeoJSON FeatureCollection output and confirms 12 layers available."""
    response = client.get("/api/v1/gis/features")
    assert response.status_code == 200
    data = response.json()

    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert isinstance(data["features"], list)
    assert len(data["features"]) > 0

    meta = data.get("metadata", {})
    assert "total_features" in meta
    assert "layers_available" in meta

    for req_layer in REQUIRED_LAYERS:
        assert req_layer in meta["layers_available"], f"Missing layer in metadata: {req_layer}"

    # Verify standard GeoJSON Feature structure
    sample_feat = data["features"][0]
    assert sample_feat["type"] == "Feature"
    assert "geometry" in sample_feat
    assert sample_feat["geometry"]["type"] == "Point"
    assert len(sample_feat["geometry"]["coordinates"]) == 2
    assert "properties" in sample_feat
    assert "layer" in sample_feat["properties"]
    assert "event_id" in sample_feat["properties"]


def test_gis_features_layer_filtering():
    """Filters GeoJSON features by layer (e.g. potholes, road_damage)."""
    response = client.get("/api/v1/gis/features?layer=potholes,road_damage")
    assert response.status_code == 200
    data = response.json()

    for feat in data["features"]:
        assert feat["properties"]["layer"] in ("potholes", "road_damage")


def test_gis_features_severity_and_district_filtering():
    """Filters GeoJSON features by severity and district."""
    response = client.get("/api/v1/gis/features?severity=HIGH&district=Central")
    assert response.status_code == 200
    data = response.json()

    for feat in data["features"]:
        assert feat["properties"]["severity"] == "HIGH"
        if feat["properties"].get("district"):
            assert feat["properties"]["district"].upper() == "CENTRAL"


def test_gis_live_buses_telemetry():
    """Retrieves live bus coordinates, speeds, bearings, and passenger load."""
    response = client.get("/api/v1/gis/buses")
    assert response.status_code == 200
    data = response.json()
    assert "buses" in data
    assert len(data["buses"]) >= 3

    bus = data["buses"][0]
    assert "bus_id" in bus
    assert "lat" in bus
    assert "lon" in bus
    assert "speed_kmh" in bus
    assert "bearing_deg" in bus
    assert "route_id" in bus
    assert "status" in bus


def test_gis_route_polylines():
    """Retrieves LineString route geometries for GIS map overlay."""
    response = client.get("/api/v1/gis/routes")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 3

    route = data["features"][0]
    assert route["type"] == "Feature"
    assert route["geometry"]["type"] == "LineString"
    assert len(route["geometry"]["coordinates"]) >= 2
    assert route["properties"]["layer"] == "bus_routes"


def test_gis_event_actions_confirm_and_dismiss():
    """Operator can confirm or dismiss flagged events."""
    event_id = "ev_pothole_101"

    # 1. Confirm
    conf_res = client.patch(
        f"/api/v1/gis/events/{event_id}/action",
        json={"action": "CONFIRM", "officer_id": "OFFICER_42", "notes": "Verified by inspection"},
    )
    assert conf_res.status_code == 200
    assert conf_res.json()["ok"] is True
    assert conf_res.json()["new_status"] == "CONFIRMED"

    # 2. Dismiss
    diss_res = client.patch(
        f"/api/v1/gis/events/{event_id}/action",
        json={"action": "DISMISS", "officer_id": "OFFICER_42", "notes": "False positive light shadow"},
    )
    assert diss_res.status_code == 200
    assert diss_res.json()["new_status"] == "DISMISSED"


def test_gis_event_action_escalate_and_create_ticket():
    """Operator can escalate or dispatch maintenance tickets."""
    event_id = "ev_damage_102"

    # 1. Escalate
    esc_res = client.patch(
        f"/api/v1/gis/events/{event_id}/action",
        json={"action": "ESCALATE", "notes": "Risk of vehicle axle damage"},
    )
    assert esc_res.status_code == 200
    assert esc_res.json()["new_status"] == "ESCALATED"

    # 2. Create Maintenance Ticket
    tick_res = client.patch(
        f"/api/v1/gis/events/{event_id}/action",
        json={
            "action": "CREATE_MAINTENANCE_TICKET",
            "priority": "HIGH",
            "department": "Civil Road Maintenance",
            "notes": "Asphalt crack filling required immediately",
        },
    )
    assert tick_res.status_code == 200
    tick_data = tick_res.json()
    assert tick_data["new_status"] == "TICKET_CREATED"
    assert tick_data["ticket_id"] is not None
    assert tick_data["ticket_id"].startswith("TICK-")

    # 3. Verify ticket appears in maintenance work order endpoint
    orders_res = client.get("/api/v1/gis/maintenance-tickets")
    assert orders_res.status_code == 200
    orders = orders_res.json()["tickets"]
    matching = [t for t in orders if t["ticket_id"] == tick_data["ticket_id"]]
    assert len(matching) == 1
    assert matching[0]["event_id"] == event_id
    assert matching[0]["priority"] == "HIGH"


def test_gis_event_action_invalid_rejected():
    """Reject invalid operator actions with 400."""
    response = client.patch(
        "/api/v1/gis/events/ev_pothole_101/action",
        json={"action": "INVALID_ACTION_NAME"},
    )
    assert response.status_code == 400
    assert "Invalid action" in response.json()["detail"]
