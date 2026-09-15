"""
Unit tests for Camera & Edge Device Health Router (Phase 25)
=============================================================
Validates:
  - Monitored metrics completeness:
      Camera status, FPS, Blur score, Brightness, Lens obstruction,
      Temperature, CPU, GPU, RAM, Storage, Network, Last heartbeat
  - All 4 operational states: HEALTHY, WARNING, DEGRADED, OFFLINE
  - Critical Fail-Safe rule:
      If camera is dirty/obstructed:
        1. Do NOT silently continue producing unreliable detections (unreliable_detections_halted=True).
        2. Generate: CAMERA DEGRADED.
        3. Create maintenance ticket automatically.
  - Telemetry heartbeat ingestion.
  - Maintenance ticket retrieval.
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_monitored_metrics_completeness():
    """
    Validates that every camera device monitors all prompt-required metrics:
      Camera status, FPS, Blur score, Brightness, Lens obstruction,
      Temperature, CPU, GPU, RAM, Storage, Network, Last heartbeat.
    """
    res = client.get("/api/v1/cameras")
    assert res.status_code == 200
    cameras = res.json()
    assert len(cameras) >= 4

    for cam in cameras:
        # Prompt-mandated metrics
        assert cam["camera_status"] in ["HEALTHY", "WARNING", "DEGRADED", "OFFLINE"]
        assert "fps" in cam and isinstance(cam["fps"], (int, float))
        assert "blur_score" in cam and isinstance(cam["blur_score"], (int, float))
        assert "brightness" in cam and isinstance(cam["brightness"], (int, float))
        assert "lens_obstruction_pct" in cam and 0.0 <= cam["lens_obstruction_pct"] <= 100.0
        assert "temperature_celsius" in cam and isinstance(cam["temperature_celsius"], (int, float))
        assert "cpu_usage_pct" in cam and isinstance(cam["cpu_usage_pct"], (int, float))
        assert "gpu_usage_pct" in cam and isinstance(cam["gpu_usage_pct"], (int, float))
        assert "ram_usage_pct" in cam and isinstance(cam["ram_usage_pct"], (int, float))
        assert "storage_usage_pct" in cam and isinstance(cam["storage_usage_pct"], (int, float))
        assert "network_status" in cam and cam["network_status"]
        assert "last_heartbeat" in cam and cam["last_heartbeat"]


def test_health_states_coverage():
    """Validates presence of HEALTHY, WARNING, DEGRADED, and OFFLINE devices."""
    res = client.get("/api/v1/cameras")
    assert res.status_code == 200
    cameras = res.json()

    statuses = {c["camera_status"] for c in cameras}
    assert "HEALTHY" in statuses
    assert "WARNING" in statuses
    assert "DEGRADED" in statuses
    assert "OFFLINE" in statuses


def test_dirty_obstructed_lens_failsafe_and_auto_ticketing():
    """
    Validates critical prompt rule:
      "If camera is dirty/obstructed:
       Do NOT silently continue producing unreliable detections.
       Generate: CAMERA DEGRADED
       Create maintenance ticket automatically."
    """
    camera_id = "CAM-102-FRONT"

    # Initially healthy
    initial_res = client.get(f"/api/v1/cameras/{camera_id}")
    assert initial_res.status_code == 200
    assert initial_res.json()["camera_status"] == "HEALTHY"
    assert initial_res.json()["unreliable_detections_halted"] is False

    # Simulate dirty / heavily obstructed lens (e.g. 70% mud splatter)
    obstruction_payload = {
        "obstruction_pct": 72.5,
        "reason": "Heavy mud and street dust coating front optical glass element",
    }
    sim_res = client.post(f"/api/v1/cameras/{camera_id}/simulate-obstruction", json=obstruction_payload)
    assert sim_res.status_code == 200
    degraded_cam = sim_res.json()

    # Rule 1: Generate CAMERA DEGRADED
    assert degraded_cam["camera_status"] == "DEGRADED"
    assert degraded_cam["is_lens_obstructed"] is True
    assert degraded_cam["lens_obstruction_pct"] == 72.5

    # Rule 2: Do NOT silently continue producing unreliable detections
    assert degraded_cam["unreliable_detections_halted"] is True

    # Rule 3: Create maintenance ticket automatically
    ticket_id = degraded_cam["active_maintenance_ticket_id"]
    assert ticket_id and ticket_id.startswith("TKT-CAM-")

    # Verify ticket exists in maintenance tickets registry
    tickets_res = client.get("/api/v1/cameras/maintenance-tickets")
    assert tickets_res.status_code == 200
    tickets = tickets_res.json()
    matched = [t for t in tickets if t["ticket_id"] == ticket_id]
    assert len(matched) == 1
    ticket = matched[0]
    assert ticket["camera_id"] == camera_id
    assert ticket["bus_id"] == "BUS-102"
    assert ticket["halted_detections"] is True
    assert "CAMERA DEGRADED" in ticket["reason"]


def test_camera_telemetry_heartbeat_ingestion():
    """Validates edge node telemetry submission via POST."""
    camera_id = "CAM-124-FRONT"
    telemetry_payload = {
        "camera_id": camera_id,
        "bus_id": "BUS-124",
        "camera_name": "Front Telephoto Lens",
        "camera_status": "HEALTHY",
        "fps": 29.9,
        "target_fps": 30.0,
        "blur_score": 142.0,
        "brightness": 128.0,
        "lens_obstruction_pct": 2.0,
        "is_lens_obstructed": False,
        "unreliable_detections_halted": False,
        "temperature_celsius": 47.0,
        "cpu_usage_pct": 39.0,
        "gpu_usage_pct": 61.0,
        "ram_usage_pct": 50.0,
        "storage_usage_pct": 32.0,
        "network_status": "ONLINE_5G",
        "network_latency_ms": 22.0,
        "last_heartbeat": "2026-09-15T00:30:00Z",
    }
    res = client.post(f"/api/v1/cameras/{camera_id}/telemetry", json=telemetry_payload)
    assert res.status_code == 200
    assert res.json()["camera_status"] == "HEALTHY"


def test_camera_fleet_health_summary():
    """Validates /health diagnostic summary."""
    res = client.get("/api/v1/cameras/health")
    assert res.status_code == 200
    data = res.json()

    assert data["total_monitored_cameras"] >= 4
    assert data["healthy_count"] >= 1
    assert data["degraded_count"] >= 1
    assert data["offline_count"] >= 1
    assert data["detections_halted_count"] >= 1
    assert data["active_maintenance_tickets"] >= 1
    assert data["fleet_average_fps"] > 0
