"""
Unit & Integration Tests for Edge Local Buffer / Offline Mode (Phase 15)
========================================================================
Tests:
  1. Network state machine (ONLINE, OFFLINE, RECONNECTING, AUTO)
  2. Exact prompt-mandated UI indicator formatting:
       Network:
       ONLINE
       vs
       NETWORK:
       OFFLINE
       17 EVENTS BUFFERED
  3. Offline diversion to local SQLite queue
  4. Reconnection queue drain and acknowledgement
  5. Simulator control plane REST endpoints (/network/mode, /network/status, /network/flush)
"""

import pytest
from pathlib import Path
from starlette.testclient import TestClient

from edge.sqlite_queue import SqliteEventQueue
from edge.network_manager import NetworkManager
from edge.pipeline.manager import CameraPipeline, SimulatorManager
from edge.main import app


def test_network_manager_state_transitions(tmp_path: Path):
    queue = SqliteEventQueue(db_path=tmp_path / "net_test.db")
    nm = NetworkManager(sqlite_queue=queue, initial_state="ONLINE")

    assert nm.is_online() is True
    assert nm.is_offline() is False

    nm.set_mode("OFFLINE")
    assert nm.is_offline() is True
    assert nm.current_state == "OFFLINE"

    nm.set_mode("RECONNECTING")
    assert nm.is_reconnecting() is True
    assert nm.current_state == "RECONNECTING"

    nm.set_mode("ONLINE")
    assert nm.is_online() is True

    nm.set_mode("AUTO")
    assert nm.current_state == "ONLINE"

    with pytest.raises(ValueError):
        nm.set_mode("INVALID_MODE")


def test_exact_prompt_mandated_ui_indicator(tmp_path: Path):
    """
    CRITICAL REQUIREMENT from prompt:
    Create a UI indicator showing:
    Network:
    ONLINE

    or

    NETWORK:
    OFFLINE
    17 EVENTS BUFFERED
    """
    queue = SqliteEventQueue(db_path=tmp_path / "indicator_test.db")
    nm = NetworkManager(sqlite_queue=queue)

    # 1. Online indicator
    nm.set_mode("ONLINE")
    assert nm.get_status_text() == "Network:\nONLINE"

    # 2. Enqueue exactly 17 events in offline mode
    nm.set_mode("OFFLINE")
    for i in range(17):
        queue.enqueue({"event_id": f"ev_{i}", "event_type": "POTHOLE"})

    assert queue.pending_count() == 17
    offline_text = nm.get_status_text()
    assert offline_text == "NETWORK:\nOFFLINE\n17 EVENTS BUFFERED"

    # 3. Reconnecting indicator
    nm.set_mode("RECONNECTING")
    reconn_text = nm.get_status_text()
    assert reconn_text == "NETWORK:\nRECONNECTING\n17 EVENTS BUFFERED"


def test_offline_buffering_and_reconnection_drain(tmp_path: Path):
    queue = SqliteEventQueue(db_path=tmp_path / "drain_test.db")
    nm = NetworkManager(sqlite_queue=queue)

    # Put in OFFLINE mode
    nm.set_mode("OFFLINE")

    # While offline, events go to queue
    queue.enqueue({"event_id": "off_01", "event_type": "POSSIBLE_INCIDENT"})
    queue.enqueue({"event_id": "off_02", "event_type": "PEDESTRIAN_RISK"})
    assert queue.pending_count() == 2

    # In OFFLINE mode, draining should be suppressed
    transmitted = []
    def mock_sender(evt):
        transmitted.append(evt["event_id"])
        return True

    drained = nm.drain_queue_batch(send_fn=mock_sender)
    assert drained == 0
    assert len(transmitted) == 0
    assert queue.pending_count() == 2

    # Switch to RECONNECTING mode -> drain proceeds
    nm.set_mode("RECONNECTING")
    drained = nm.drain_queue_batch(send_fn=mock_sender)
    assert drained == 2
    assert transmitted == ["off_01", "off_02"]
    assert queue.pending_count() == 0


def test_rest_control_network_endpoints():
    client = TestClient(app)

    # 1. Set mode to OFFLINE
    r = client.post("/api/simulator/network/mode", json={"mode": "OFFLINE"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["mode"] == "OFFLINE"
    assert "OFFLINE" in data["indicator"]

    # 2. Inject a test event in OFFLINE mode (must be buffered)
    r = client.post("/api/simulator/network/test-event", json={
        "event_type": "POTHOLE_DETECTED",
        "confidence": 0.95,
        "details": {"test": True},
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["buffered"] is True

    # 3. Query network status
    r = client.get("/api/simulator/network/status")
    assert r.status_code == 200
    status = r.json()
    assert status["state"] == "OFFLINE"
    assert status["pending_count"] >= 1

    # 4. Set mode back to ONLINE
    r = client.post("/api/simulator/network/mode", json={"mode": "ONLINE"})
    assert r.status_code == 200
    assert r.json()["mode"] == "ONLINE"
    assert r.json()["indicator"] == "Network:\nONLINE"

    # 5. Flush buffer endpoint
    r = client.post("/api/simulator/network/flush")
    assert r.status_code == 200
    assert r.json()["ok"] is True
