"""
Unit tests for Administration Panel (Phase 31)
==============================================
Validates:
  1. Admin Dashboard KPIs:
       - Total users
       - Active buses
       - Online devices
       - Events today
       - System health
       - API health
       - Queue health
       - Storage
       - AI service health
  2. Live System Monitoring:
       - CPU, GPU, RAM, Disk, Temperature, Latency, FPS, Service statuses
  3. Coverage of all 14 Administration Modules:
       - Users, Roles, Buses, Routes, Devices, Cameras, AI Models, Events,
         GIS Layers, Data Sources, Retention Policies, System Logs, Audit Logs, Reports
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_admin_dashboard_kpis():
    """Validates the executive admin dashboard KPI payload."""
    res = client.get("/api/v1/admin/dashboard")
    assert res.status_code == 200
    data = res.json()

    assert data["total_users"] > 0
    assert data["active_buses"] > 0
    assert data["total_buses"] >= data["active_buses"]
    assert data["online_devices"] > 0
    assert data["events_today"] > 1000
    assert "Healthy" in data["system_health"]
    assert "Uptime" in data["api_health"]
    assert "Backlog" in data["queue_health"]
    assert "GB" in data["storage"]
    assert "FPS" in data["ai_service_health"]


def test_system_monitoring_telemetry():
    """Validates real-time hardware telemetry and backend subsystem statuses."""
    res = client.get("/api/v1/admin/system-monitoring")
    assert res.status_code == 200
    data = res.json()

    assert 0.0 < data["cpu_percent"] < 100.0
    assert 0.0 < data["gpu_percent"] < 100.0
    assert 0.0 < data["ram_percent"] < 100.0
    assert 0.0 < data["disk_percent"] < 100.0
    assert 20.0 < data["temperature_celsius"] < 90.0
    assert data["network_latency_ms"] > 0
    assert data["ai_inference_fps"] > 20.0
    assert data["services_status"]["fastapi_backend"] == "HEALTHY"
    assert data["services_status"]["sqlite_database"] == "HEALTHY"


def test_all_fourteen_admin_modules():
    """Validates that all 14 administration module endpoints return valid collections."""
    modules = [
        "users",
        "roles",
        "buses",
        "routes",
        "devices",
        "cameras",
        "ai-models",
        "events",
        "gis-layers",
        "data-sources",
        "retention-policies",
        "system-logs",
        "audit-logs",
        "reports",
    ]

    for m in modules:
        res = client.get(f"/api/v1/admin/{m}")
        assert res.status_code == 200, f"Failed module endpoint: /api/v1/admin/{m}"
        items = res.json()
        assert isinstance(items, list), f"Module {m} did not return a list"
        assert len(items) > 0, f"Module {m} returned an empty list"
