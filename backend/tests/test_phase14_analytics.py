"""
Tests for Phase 14 (Analytics)
==============================
Verifies:
  - Step 34: Congestion Heatmap (/api/v1/urban-analytics/heatmaps/congestion)
  - Step 35: Infrastructure Heatmap (/api/v1/urban-analytics/heatmaps/infrastructure)
  - Step 36: Route Delay Analytics (Route 12: Normal 38 min, Current average 51 min, Delay +13 min)
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_step34_congestion_heatmap(client):
    res = client.get("/api/v1/urban-analytics/heatmaps/congestion")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total_hotspots"] >= 4
    for spot in data["hotspots"]:
        assert "lat" in spot
        assert "lon" in spot
        assert "intensity" in spot
        assert spot["intensity"] >= 0.0


def test_step35_infrastructure_heatmap(client):
    res = client.get("/api/v1/urban-analytics/heatmaps/infrastructure")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total_clusters"] >= 4
    types = {c["defect_type"] for c in data["clusters"]}
    assert "POTHOLE" in types
    assert "WATERLOGGING" in types


def test_step36_route12_delay_calibration(client):
    """
    Step 36 Benchmark:
      Route 12
      Normal: 38 min
      Current average: 51 min
      Delay: +13 min
    """
    res = client.get("/routes/Route 12")
    assert res.status_code == 200, res.text
    d = res.json()
    assert d["scheduled_travel_time_minutes"] == 38.0
    assert d["observed_travel_time_minutes"] == 51.0
    assert d["average_delay_minutes"] == 13.0

    # Also test via route_delay detail endpoint
    res_detail = client.get("/api/v1/routes/Route 12/delay-details")
    assert res_detail.status_code == 200, res_detail.text
    d2 = res_detail.json()
    assert d2["scheduled_travel_time_minutes"] == 38.0
    assert d2["observed_travel_time_minutes"] == 51.0
    assert d2["average_delay_minutes"] == 13.0
