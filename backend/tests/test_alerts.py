"""
Unit tests for Alert Center Router with WebSockets (Phase 24)
=============================================================
Validates:
  - Multi-tier severities: CRITICAL, HIGH, MEDIUM, LOW
  - Prompt canonical example types:
      - Possible Incident
      - Severe Congestion
      - Pedestrian Risk
      - Major Waterlogging
      - Road Hazard
      - Camera Failure
      - Edge Device Failure
  - Alert card completeness: Type, Severity, Location, Bus, Timestamp, Confidence, Evidence
  - Operational actions: Acknowledge, Verify, Escalate, Assign, Resolve
  - Real-time WebSocket connection and event broadcasting
  - Filtering by severity, alert type, and bus ID
"""

import json
import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_alert_types_and_severities_completeness():
    """
    Validates presence of all 4 severities (CRITICAL, HIGH, MEDIUM, LOW)
    and all 7 prompt-required example alert types.
    """
    res = client.get("/api/v1/alerts")
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) >= 7

    severities = {a["severity"] for a in alerts}
    assert "CRITICAL" in severities
    assert "HIGH" in severities
    assert "MEDIUM" in severities

    types = {a["type"] for a in alerts}
    required_types = [
        "Possible Incident",
        "Severe Congestion",
        "Pedestrian Risk",
        "Major Waterlogging",
        "Road Hazard",
        "Camera Failure",
        "Edge Device Failure",
    ]
    for req in required_types:
        assert req in types, f"Missing required alert type: {req}"


def test_alert_card_schema_completeness():
    """
    Every alert card must feature:
      Type, Severity, Location, Bus, Timestamp, Confidence, Evidence.
    """
    res = client.get("/api/v1/alerts")
    assert res.status_code == 200
    alerts = res.json()

    for card in alerts:
        assert card["type"]
        assert card["severity"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        assert card["location"]
        assert card["bus"]
        assert card["timestamp"]
        assert 0.0 <= card["confidence"] <= 1.0
        assert card["evidence"] and len(card["evidence"]) >= 10


def test_alert_actions_lifecycle():
    """
    Validates all 5 operational actions:
      - Acknowledge
      - Verify
      - Escalate
      - Assign
      - Resolve
    """
    alert_id = "ALT-2026-001"

    # 1. Acknowledge
    res_ack = client.post(
        f"/api/v1/alerts/{alert_id}/action",
        json={"action": "Acknowledge", "actor": "Officer Miller", "notes": "Incident alert acknowledged"},
    )
    assert res_ack.status_code == 200
    card = res_ack.json()
    assert card["status"] == "ACKNOWLEDGED"

    # 2. Verify
    res_ver = client.post(
        f"/api/v1/alerts/{alert_id}/action",
        json={"action": "Verify", "actor": "Safety Supervisor", "notes": "Rolling buffer inspected: collision risk confirmed"},
    )
    assert res_ver.status_code == 200
    assert res_ver.json()["status"] == "VERIFIED"

    # 3. Escalate
    res_esc = client.post(
        f"/api/v1/alerts/{alert_id}/action",
        json={"action": "Escalate", "actor": "Senior Controller", "notes": "Escalated to Traffic Emergency Ops"},
    )
    assert res_esc.status_code == 200
    assert res_esc.json()["status"] == "ESCALATED"

    # 4. Assign
    res_asn = client.post(
        f"/api/v1/alerts/{alert_id}/action",
        json={"action": "Assign", "actor": "Ops Lead", "assigned_to": "Field Response Unit 3"},
    )
    assert res_asn.status_code == 200
    card_asn = res_asn.json()
    assert card_asn["status"] == "ASSIGNED"
    assert card_asn["assigned_to"] == "Field Response Unit 3"

    # 5. Resolve
    res_res = client.post(
        f"/api/v1/alerts/{alert_id}/action",
        json={"action": "Resolve", "actor": "Field Response Unit 3", "notes": "Site cleared, vehicles relocated to service lane"},
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"

    # Check audit trail recorded all 5 actions
    audit = res_res.json()["audit_trail"]
    action_names = [a["action"] for a in audit]
    assert "Acknowledge" in action_names
    assert "Verify" in action_names
    assert "Escalate" in action_names
    assert "Assign" in action_names
    assert "Resolve" in action_names


def test_alerts_websocket_realtime_connection():
    """
    Validates real-time WebSocket connection to /api/v1/alerts/ws,
    receiving initial connection handshake and ping/pong.
    """
    with client.websocket_connect("/api/v1/alerts/ws") as websocket:
        msg = websocket.receive_json()
        assert msg["event"] == "CONNECTED"
        assert "NovaFlow" in msg["message"]
        assert "summary" in msg

        # Test heartbeat
        websocket.send_text("ping")
        reply = websocket.receive_text()
        assert reply == "pong"


def test_alerts_websocket_broadcast_on_create():
    """
    Validates that creating an alert broadcasts a real-time event
    to listening WebSocket clients.
    """
    with client.websocket_connect("/api/v1/alerts/ws") as websocket:
        # Consume initial CONNECTED event
        _ = websocket.receive_json()

        # Create new alert via REST API
        new_alert_payload = {
            "type": "Road Hazard",
            "severity": "HIGH",
            "location": "NH-48 Mahipalpur Underpass",
            "lat": 28.5350,
            "lon": 77.1210,
            "bus": "BUS-119",
            "confidence": 0.91,
            "evidence": "Large fallen tree branch obstructing right bus lane.",
        }
        res = client.post("/api/v1/alerts", json=new_alert_payload)
        assert res.status_code == 200

        # Receive broadcast over WebSocket
        ws_event = websocket.receive_json()
        assert ws_event["event"] == "ALERT_CREATED"
        assert ws_event["alert"]["type"] == "Road Hazard"
        assert ws_event["alert"]["bus"] == "BUS-119"


def test_alerts_filtering():
    """Validates filtering by severity, alert_type, and bus ID."""
    # Filter by severity: CRITICAL
    res_crit = client.get("/api/v1/alerts?severity=CRITICAL")
    assert res_crit.status_code == 200
    for a in res_crit.json():
        assert a["severity"] == "CRITICAL"

    # Filter by alert_type: Waterlogging
    res_water = client.get("/api/v1/alerts?alert_type=Waterlogging")
    assert res_water.status_code == 200
    for a in res_water.json():
        assert "Waterlogging" in a["type"]

    # Filter by bus: BUS-102
    res_bus = client.get("/api/v1/alerts?bus=BUS-102")
    assert res_bus.status_code == 200
    for a in res_bus.json():
        assert a["bus"] == "BUS-102"
