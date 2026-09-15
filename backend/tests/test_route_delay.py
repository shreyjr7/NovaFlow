"""
Unit tests for Route Delay Analytics Router (Phase 22)
======================================================
Validates:
  - Canonical Route 12 prompt benchmark:
      Scheduled: 42 min
      Observed: 57 min
      Average Delay: 15 min
      Main contributing factors: Congestion, Road damage, Waterlogging
  - Route map sections & delayed section highlighting (is_delayed_section=True)
  - List delay analysis with city & minimum delay filters
  - Route details lookup with URL encoding & case-insensitivity
  - Network-wide route delay summary KPIs
  - 404 error handling for non-existent routes
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_route_delay_canonical_route_12():
    """
    Validates the exact canonical benchmark for Route 12 as specified in prompt:
      Scheduled: 42 min
      Observed: 57 min
      Average Delay: 15 min
      Main contributing factors: Congestion, Road damage, Waterlogging
    """
    res = client.get("/api/v1/routes/Route 12/delay-details")
    assert res.status_code == 200
    data = res.json()

    assert data["route_id"] == "Route 12"
    assert "Route 12" in data["name"]

    # Exact Prompt Benchmark
    assert data["scheduled_travel_time_minutes"] == 42.0
    assert data["observed_travel_time_minutes"] == 57.0
    assert data["average_delay_minutes"] == 15.0
    assert data["maximum_delay_minutes"] >= 15.0

    # Events and defects
    assert data["number_of_congestion_events"] == 7
    assert data["number_of_road_defects"] == 5

    # Main contributing factors
    factors = data["main_contributing_factors"]
    assert "Congestion" in factors
    assert "Road damage" in factors
    assert "Waterlogging" in factors

    # Factor percentage attribution
    percentages = data["factor_percentages"]
    assert "Congestion" in percentages
    assert "Road damage" in percentages
    assert "Waterlogging" in percentages
    assert sum(percentages.values()) == 100.0


def test_route_12_delayed_sections_highlighting():
    """
    Validates that Route 12 contains sections flagged with is_delayed_section = True
    and coordinates for highlighting delayed sections on the GIS map.
    """
    res = client.get("/api/v1/routes/Route 12/delay-details")
    assert res.status_code == 200
    data = res.json()

    sections = data["sections"]
    assert len(sections) >= 4

    delayed_sections = [s for s in sections if s["is_delayed_section"]]
    assert len(delayed_sections) >= 2

    # Check delayed section IDs and factors
    delayed_ids = [s["section_id"] for s in delayed_sections]
    assert "SEC_12_02" in delayed_ids
    assert "SEC_12_03" in delayed_ids

    # Check polyline coordinates structure
    for section in sections:
        assert len(section["polyline"]) >= 2
        for pt in section["polyline"]:
            assert "lat" in pt and "lon" in pt
            assert 20.0 < pt["lat"] < 35.0  # valid Delhi latitude
            assert 70.0 < pt["lon"] < 85.0  # valid Delhi longitude

    # Verify stops list
    stops = data["stops"]
    assert len(stops) >= 5
    assert stops[0]["name"] == "CP Radial 2 (Palika Bazar)"
    assert stops[-1]["name"] == "Anand Vihar ISBT Terminal"


def test_list_routes_delay_analysis():
    """Validates the delay-analysis endpoint listing all monitored routes."""
    res = client.get("/api/v1/routes/delay-analysis")
    assert res.status_code == 200
    data = res.json()

    assert data["count"] >= 5
    route_ids = [r["route_id"] for r in data["routes"]]
    assert "Route 12" in route_ids
    assert "Route 403" in route_ids
    assert "Route 543" in route_ids

    # Find Route 12 in list and verify calculated delay percentage
    r12 = next(r for r in data["routes"] if r["route_id"] == "Route 12")
    assert r12["scheduled_travel_time_minutes"] == 42.0
    assert r12["observed_travel_time_minutes"] == 57.0
    assert r12["average_delay_minutes"] == 15.0
    assert r12["delay_percentage"] == round((15.0 / 42.0) * 100.0, 1)


def test_list_routes_delay_filtering():
    """Validates filtering by city and minimum delay minutes."""
    # Filter by city: Bangalore
    res_blr = client.get("/api/v1/routes/delay-analysis?city=Bangalore")
    assert res_blr.status_code == 200
    blr_data = res_blr.json()
    assert blr_data["count"] == 1
    assert blr_data["routes"][0]["route_id"] == "Route 543"

    # Filter by min_delay_minutes: >= 16 min
    res_delayed = client.get("/api/v1/routes/delay-analysis?min_delay_minutes=16.0")
    assert res_delayed.status_code == 200
    delayed_routes = res_delayed.json()["routes"]
    for r in delayed_routes:
        assert r["average_delay_minutes"] >= 16.0


def test_network_route_delay_summary():
    """Validates network-wide KPI summary endpoint."""
    res = client.get("/api/v1/routes/summary")
    assert res.status_code == 200
    summary = res.json()

    assert summary["total_monitored_routes"] >= 5
    assert summary["network_average_delay_minutes"] > 0
    assert summary["network_maximum_delay_minutes"] >= summary["network_average_delay_minutes"]
    assert 0.0 <= summary["on_time_performance_pct"] <= 100.0
    assert summary["total_affecting_road_defects"] > 0
    assert summary["total_affecting_congestion_events"] > 0

    worst = summary["worst_delayed_route"]
    assert "route_id" in worst
    assert worst["average_delay_minutes"] >= 15.0


def test_route_delay_details_not_found():
    """Validates 404 response when querying an unknown route ID."""
    res = client.get("/api/v1/routes/UNKNOWN_ROUTE_999/delay-details")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()
