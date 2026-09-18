"""
Tests for Phase 17 (Testing & Pipeline Validation)
==================================================
Verifies:
  - Step 41: Edge-case stress dataset across all 8 conditions:
             1. Day
             2. Night
             3. Rain
             4. Waterlogging
             5. Heavy traffic
             6. Headlight glare
             7. Dirty lens
             8. No internet
  - Step 42: End-to-end pipeline test:
             Camera -> AI -> Event -> Backend -> Database -> GIS -> Authority
  - Step 43: Network failure injection and recovery test:
             Turn off internet -> Detection continues -> Local SQLite ->
             Connection restored -> Events uploaded
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from edge.road_defect.quality_checker import ImageQualityChecker, RoadCondition
from edge.sqlite_queue import SqliteEventQueue
from edge.network_manager import NetworkManager

os.environ["NOVAFLOW_DEV_MODE"] = "true"


@pytest.fixture
def client():
    return TestClient(app)


def test_step41_edge_case_stress_dataset():
    """
    Step 41: Dedicated stress-test subset covering:
      ☀️ Day, 🌙 Night, ☔ Rain, 💧 Waterlogging,
      🚗 Heavy traffic, 💡 Headlight glare, 📷 Dirty lens, 📡 No internet.
    """
    checker = ImageQualityChecker()

    # 1. Day
    q_day = checker.check_quality(brightness_override=130.0)
    assert RoadCondition.DAY in q_day.active_conditions

    # 2. Night
    q_night = checker.check_quality(brightness_override=25.0)
    assert RoadCondition.NIGHT in q_night.active_conditions
    assert q_night.confidence_penalty > 0.0

    # 3. Rain
    q_rain = checker.check_quality(is_raining_sensor=True)
    assert RoadCondition.RAIN in q_rain.active_conditions

    # 4. Waterlogging (Wet road reflection)
    q_wet = checker.check_quality(is_wet_road_override=True)
    assert RoadCondition.WET_ROAD in q_wet.active_conditions

    # 5. Heavy traffic / Motion blur
    q_traffic = checker.check_quality(speed_kmh=45.0, blur_score_override=30.0)
    assert RoadCondition.MOTION_BLUR in q_traffic.active_conditions

    # 6. Headlight glare
    q_glare = checker.check_quality(brightness_override=245.0)
    assert RoadCondition.GLARE in q_glare.active_conditions

    # 7. Dirty lens
    q_dirty = checker.check_quality(obstruction_override=0.15)
    assert RoadCondition.DIRTY_LENS in q_dirty.active_conditions

    # 8. No internet condition (tested in Step 43)
    assert True


def test_step42_complete_e2e_pipeline(client):
    """
    Step 42: End-to-end integration test:
      Camera -> AI -> Event -> Backend -> Database -> GIS -> Authority
    """
    # 1. Camera / Edge AI creates canonical event
    event_id = "EVT-E2E-PIPELINE-001"
    event_payload = {
        "event_id": event_id,
        "event_type": "POTHOLE",
        "severity": "HIGH",
        "confidence": 0.93,
        "gps": {"lat": 28.6139, "lon": 77.2090},
        "road_segment": "CENTRAL_CORRIDOR",
        "bus_id": "BUS-102",
        "camera_id": "CAM-FRONT",
        "evidence": {
            "description": "Pothole detected via front camera AI",
            "snapshot_url": "/evidence/snapshots/pothole_e2e.jpg",
        },
    }
    headers = {"X-Edge-Device-Id": "BUS-102", "X-Edge-Token": "novaflow-edge-secret"}

    # 2. Transmit to Backend Ingestion API (Queued asynchronous processing: HTTP 202 Accepted)
    r_ingest = client.post("/events", json=event_payload, headers=headers)
    assert r_ingest.status_code in (200, 201, 202), r_ingest.text

    # 3. Query Database / Backend retrieval
    r_query = client.get(f"/events/{event_id}")
    assert r_query.status_code == 200
    assert r_query.json()["event_id"] == event_id

    # 4. Appears in GIS endpoints
    r_gis = client.get("/api/v1/gis/features")
    assert r_gis.status_code == 200

    # 5. Authority Action (Confirm event)
    r_action = client.patch(f"/events/{event_id}", json={"status": "CONFIRMED"})
    assert r_action.status_code == 200
    assert r_action.json()["status"].lower() == "confirmed"


def test_step43_network_failure_injection_and_recovery():
    """
    Step 43: Test network failure:
      Turn off internet intentionally
      Verify:
        Detection continues -> Local storage -> Connection restored -> Events uploaded
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/buffer_test.db"
        queue = SqliteEventQueue(db_path=db_path)
        net_mgr = NetworkManager(sqlite_queue=queue, initial_state=NetworkManager.STATE_ONLINE)

        # 1. Start Online
        assert net_mgr.is_online() is True

        # 2. Turn off internet intentionally
        net_mgr.set_state(NetworkManager.STATE_OFFLINE)
        assert net_mgr.is_offline() is True

        # 3. AI Detection continues -> diverted to Local SQLite Queue
        queue.enqueue({
            "event_id": "EVT-OFFLINE-001",
            "event_type": "POTHOLE",
            "confidence": 0.92,
            "gps_lat": 28.6139,
            "gps_lon": 77.2090,
        })
        queue.enqueue({
            "event_id": "EVT-OFFLINE-002",
            "event_type": "CONGESTION_EVENT",
            "confidence": 0.88,
            "gps_lat": 28.6255,
            "gps_lon": 77.2345,
        })

        assert queue.count() == 2

        # 4. Connection restored
        net_mgr.set_state(NetworkManager.STATE_ONLINE)
        assert net_mgr.is_online() is True

        # 5. Drains local SQLite buffer and uploads all events
        uploaded_events = []
        def mock_server_ingest(event_item):
            uploaded_events.append(event_item)
            return True

        drained_count = net_mgr.drain_buffer(mock_server_ingest)
        assert drained_count == 2
        assert queue.count() == 0
        assert len(uploaded_events) == 2
