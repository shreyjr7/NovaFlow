"""
Unit & Integration Tests for Phase 3:
Step 5 (Standardized Event Format) & Step 6 (Event Status Lifecycle State Machine)
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.app.main import app
from backend.app.database.session import engine
from backend.app.models.ingested_event import IngestedEvent
from backend.app.schemas.standard_event import StandardEvent
from backend.app.services.event_state_machine import (
    EventStatus,
    normalize_status,
    validate_transition,
    execute_status_transition,
    get_allowed_transitions,
)
from edge.event import StandardEvent as EdgeStandardEvent, Event as EdgeEvent


def test_standard_event_schema_exact_keys():
    """Verify Step 5: Every AI event adheres to the exact 10-key standard structure."""
    event = StandardEvent(
        eventId="EVT-00124",
        type="pothole",
        confidence=0.94,
        latitude=28.6139,
        longitude=77.2090,
        timestamp="2026-09-15T04:22:00Z",
        busId="BUS-102",
        routeId="R-12",
        severity="high",
        status="unverified",
    )
    std_dict = event.to_standard_dict()

    expected_keys = {
        "eventId", "type", "confidence", "latitude", "longitude",
        "timestamp", "busId", "routeId", "severity", "status"
    }
    assert set(std_dict.keys()) == expected_keys
    assert std_dict["eventId"] == "EVT-00124"
    assert std_dict["type"] == "pothole"
    assert std_dict["confidence"] == 0.94
    assert std_dict["latitude"] == 28.6139
    assert std_dict["longitude"] == 77.2090
    assert std_dict["busId"] == "BUS-102"
    assert std_dict["routeId"] == "R-12"
    assert std_dict["severity"] == "high"
    assert std_dict["status"] == "unverified"


def test_edge_event_generates_standard_format():
    """Verify Edge generates the Step 5 standardized event format."""
    edge_evt = EdgeEvent(
        gps={"lat": 28.6139, "lon": 77.2090},
        event_type="pothole",
        bus_id="BUS-102",
        route_id="R-12",
        severity="high",
        status="unverified",
    )
    d = edge_evt.to_standard_dict()
    assert d["type"] == "pothole"
    assert d["busId"] == "BUS-102"
    assert d["routeId"] == "R-12"
    assert d["status"] == "unverified"
    assert "eventId" in d


def test_state_machine_valid_transitions():
    """Verify Step 6: Strict progression UNVERIFIED -> CONFIRMED -> UNDER_REPAIR -> RESOLVED."""
    # 1. UNVERIFIED -> CONFIRMED
    valid, _ = validate_transition("unverified", "confirmed")
    assert valid is True

    # 2. CONFIRMED -> UNDER_REPAIR
    valid, _ = validate_transition("confirmed", "under_repair")
    assert valid is True

    # 3. UNDER_REPAIR -> RESOLVED
    valid, _ = validate_transition("under_repair", "resolved")
    assert valid is True

    # 4. Dismissal is allowed from UNVERIFIED, CONFIRMED, or UNDER_REPAIR
    valid, _ = validate_transition("unverified", "dismissed")
    assert valid is True
    valid, _ = validate_transition("confirmed", "dismissed")
    assert valid is True
    valid, _ = validate_transition("under_repair", "dismissed")
    assert valid is True


def test_state_machine_invalid_skipping_transitions():
    """Verify state machine prevents skipping phases or illegal transitions."""
    # Cannot jump UNVERIFIED directly to RESOLVED without verification and repair
    valid, err = validate_transition("unverified", "resolved")
    assert valid is False
    assert "Invalid transition" in err

    # Cannot jump UNVERIFIED directly to UNDER_REPAIR without confirmation
    valid, err = validate_transition("unverified", "under_repair")
    assert valid is False

    # Cannot jump CONFIRMED backwards to UNVERIFIED
    valid, err = validate_transition("confirmed", "unverified")
    assert valid is False


def test_api_standard_events_endpoint():
    """Test GET /api/v1/events/standard returns list with exact keys."""
    client = TestClient(app)
    response = client.get("/api/v1/events/standard?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert isinstance(data["events"], list)
    if len(data["events"]) > 0:
        first = data["events"][0]
        for k in ["eventId", "type", "confidence", "latitude", "longitude", "busId", "routeId", "severity", "status"]:
            assert k in first


def test_api_status_transition_workflow():
    """Test POST /api/v1/events/{id}/status progresses through lifecycle."""
    client = TestClient(app)

    # 1. Ingest a new event
    payload = {
        "event_id": "EVT-TEST-LIFECYCLE-999",
        "event_type": "POTHOLE",
        "bus_id": "BUS_001",
        "gps": {"lat": 28.6139, "lon": 77.2090},
        "confidence": 0.95,
        "severity": "HIGH",
    }
    headers = {"X-API-Key": "novaflow-edge-key-2026"}
    res = client.post("/api/v1/events", json=payload, headers=headers)
    assert res.status_code == 202

    import uuid
    unique_key = f"idemp_{uuid.uuid4().hex[:12]}"
    unique_event_id = f"EVT-TEST-{uuid.uuid4().hex[:8].upper()}"

    # Verify event exists in DB or create a test event
    with Session(engine) as session:
        evt = IngestedEvent(
            idempotency_key=unique_key,
            event_id=unique_event_id,
            event_type="POTHOLE",
            bus_id="BUS-102",
            route_id="R-12",
            gps_lat=28.6139,
            gps_lon=77.2090,
            confidence=0.94,
            severity="high",
            status="unverified",
        )
        session.add(evt)
        session.commit()

    # Step A: Transition UNVERIFIED -> CONFIRMED
    res = client.post(f"/api/v1/events/{unique_event_id}/status", json={"target_status": "confirmed", "reason": "Engineer site verification"})
    assert res.status_code == 200
    assert res.json()["newStatus"] == "confirmed"

    # Step B: Transition CONFIRMED -> UNDER_REPAIR
    res = client.post(f"/api/v1/events/{unique_event_id}/status", json={"target_status": "under_repair", "work_order_id": "WO-DEL-2026-44"})
    assert res.status_code == 200
    assert res.json()["newStatus"] == "under_repair"

    # Step C: Transition UNDER_REPAIR -> RESOLVED
    res = client.post(f"/api/v1/events/{unique_event_id}/status", json={"target_status": "resolved", "reason": "Compacted bitumen verified"})
    assert res.status_code == 200
    assert res.json()["newStatus"] == "resolved"

    # Step D: Test illegal transition from RESOLVED to UNDER_REPAIR directly (rejected)
    res = client.post(f"/api/v1/events/{unique_event_id}/status", json={"target_status": "under_repair"})
    assert res.status_code == 400

    # Step E: Inspect lifecycle endpoint
    res = client.get(f"/api/v1/events/{unique_event_id}/lifecycle")
    assert res.status_code == 200
    hist = res.json()["lifecycleHistory"]
    assert len(hist) >= 3
    assert hist[0]["to_status"] == "confirmed"
    assert hist[1]["to_status"] == "under_repair"
    assert hist[2]["to_status"] == "resolved"
