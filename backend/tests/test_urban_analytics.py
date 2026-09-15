"""
Unit tests for Urban Analytics Dashboard API (Phase 28)
=======================================================
Validates the 5 foundational urban analytics domains:
  1. ROAD CONDITION: Potholes, Road damage, Waterlogging, Missing infrastructure, trends, severity.
  2. TRAFFIC: Vehicle count, density, speed, congestion score, bottlenecks, 24h diurnal curve.
  3. SAFETY: Incidents, pedestrian risks, high-risk zones, vulnerable spots.
  4. FLEET: Active vs offline buses, camera health, edge hardware health.
  5. ROUTES: Average delay, worst routes (Route 12 benchmark), factor attribution.
Also validates multi-tier filtering responsiveness across date ranges, times of day, and zones.
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_road_condition_analytics():
    """Validates road defects, categories, severity, trends, and corridor rankings."""
    res = client.get("/api/v1/urban-analytics/road-condition")
    assert res.status_code == 200
    data = res.json()

    # Base defect counts
    assert data["potholes"] > 0
    assert data["road_damage"] > 0
    assert data["waterlogging"] > 0
    assert data["missing_infrastructure"] > 0
    assert data["total_defects"] == (
        data["potholes"] + data["road_damage"] + data["waterlogging"] + data["missing_infrastructure"]
    )

    # Severity distribution
    severity = data["severity_breakdown"]
    for k in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        assert k in severity
        assert severity[k] >= 0

    # 7-day trend
    trend = data["seven_day_trend"]
    assert len(trend) == 7
    for day in trend:
        assert "date" in day
        assert day["discovered"] > 0
        assert day["repaired"] > 0
        assert day["active_backlog"] > 0

    # Top defect corridors ranking
    corridors = data["top_defect_corridors"]
    assert len(corridors) >= 3
    assert corridors[0]["total_defects"] >= corridors[-1]["total_defects"]
    assert corridors[0]["reported_by_buses_count"] >= 1
    assert 0.0 <= corridors[0]["highest_confidence"] <= 1.0


def test_traffic_analytics():
    """Validates traffic volume, density, network speed, diurnal 24h curve, and segment rankings."""
    res = client.get("/api/v1/urban-analytics/traffic")
    assert res.status_code == 200
    data = res.json()

    assert data["total_vehicle_count"] > 100000
    assert 0.0 < data["average_vehicle_density"] <= 1.0
    assert 10.0 <= data["network_average_speed_kmh"] <= 60.0
    assert 0.0 <= data["overall_congestion_score"] <= 100.0
    assert data["active_bottlenecks_count"] >= 1

    # Modal split
    modal = data["modal_split"]
    assert "Cars / Cabs" in modal
    assert "Two-Wheelers" in modal
    assert "Transit Buses" in modal

    # 24-hour diurnal curve
    curve = data["diurnal_curve"]
    assert len(curve) == 24
    assert curve[8]["congestion_index"] > curve[3]["congestion_index"]  # 08:00 rush hour > 03:00 night

    # Top congested segments
    segments = data["top_congested_segments"]
    assert len(segments) <= 10
    assert segments[0]["rank"] == 1
    assert segments[0]["congestion_score"] >= segments[-1]["congestion_score"]
    assert segments[0]["status"] in ["severe", "high", "moderate", "low"]


def test_safety_analytics():
    """Validates safety incidents, pedestrian risks, high-risk zones, and vulnerable spots."""
    res = client.get("/api/v1/urban-analytics/safety")
    assert res.status_code == 200
    data = res.json()

    assert data["total_incidents"] >= 1
    assert data["pedestrian_risks"] >= 1
    assert data["high_risk_zones_count"] >= 1

    # Incident types breakdown
    breakdown = data["incident_types_breakdown"]
    assert "Collision Risk / Near-Miss" in breakdown
    assert "Sudden Heavy Deceleration" in breakdown

    # Pedestrian risk spots
    spots = data["vulnerable_pedestrian_spots"]
    assert len(spots) >= 3
    assert spots[0]["risk_level"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    assert spots[0]["conflict_events_count"] > 0
    assert spots[0]["observed_pedestrians_per_hour"] > 0

    # Zone safety indices
    zone_indices = data["zone_safety_indices"]
    assert len(zone_indices) >= 4


def test_fleet_analytics():
    """Validates bus fleet status, camera optical health, and edge device diagnostics."""
    res = client.get("/api/v1/urban-analytics/fleet")
    assert res.status_code == 200
    data = res.json()

    assert data["total_buses"] == data["active_buses"] + data["offline_buses"]
    assert data["active_buses"] > 100
    assert data["offline_buses"] >= 0

    # Camera health states
    cam = data["camera_health_summary"]
    assert cam["HEALTHY"] > 0
    assert "DEGRADED" in cam
    assert "WARNING" in cam
    assert "OFFLINE" in cam

    # Edge device diagnostics
    edge = data["edge_device_health"]
    assert 0.0 < edge["average_cpu_percent"] < 100.0
    assert 0.0 < edge["average_gpu_percent"] < 100.0
    assert 0.0 < edge["average_ram_percent"] < 100.0
    assert 20.0 < edge["average_temperature_celsius"] < 90.0
    assert edge["inference_fps_average"] > 15.0


def test_routes_analytics():
    """Validates route delays, worst routes ranking featuring Route 12 benchmark, and factors."""
    res = client.get("/api/v1/urban-analytics/routes")
    assert res.status_code == 200
    data = res.json()

    assert data["network_average_delay_minutes"] > 0
    assert data["total_monitored_routes"] >= 5

    # Worst delayed routes ranking
    routes = data["worst_delayed_routes"]
    assert len(routes) >= 4
    assert routes[0]["rank"] == 1
    assert routes[0]["average_delay_minutes"] >= routes[-1]["average_delay_minutes"]

    # Canonical benchmark verification: Route 12
    route_12 = next((r for r in routes if r["route_id"] == "ROUTE-12"), None)
    assert route_12 is not None
    assert route_12["scheduled_travel_time_minutes"] == 42.0
    assert route_12["observed_travel_time_minutes"] == 57.0
    assert route_12["average_delay_minutes"] == 15.0
    assert "Congestion" in route_12["contributing_factors"]
    assert "Road damage" in route_12["contributing_factors"]
    assert "Waterlogging" in route_12["contributing_factors"]

    # Factor attribution
    factors = data["aggregate_contributing_factors"]
    assert "Congestion" in factors
    assert "Road damage" in factors
    assert "Waterlogging" in factors


def test_filter_parameter_responsiveness():
    """Verifies that date_range, time_of_day, and zone filters dynamically adjust analytics."""
    # 1. Date Range filter scaling
    res_today = client.get("/api/v1/urban-analytics/road-condition?date_range=today")
    res_30days = client.get("/api/v1/urban-analytics/road-condition?date_range=last_30_days")
    assert res_today.status_code == 200
    assert res_30days.status_code == 200
    assert res_30days.json()["total_defects"] > res_today.json()["total_defects"]

    # 2. Time of Day filter impact on traffic
    res_morning = client.get("/api/v1/urban-analytics/traffic?time_of_day=morning_peak")
    res_night = client.get("/api/v1/urban-analytics/traffic?time_of_day=night")
    assert res_morning.status_code == 200
    assert res_night.status_code == 200
    morning_traffic = res_morning.json()
    night_traffic = res_night.json()
    assert morning_traffic["overall_congestion_score"] > night_traffic["overall_congestion_score"]
    assert morning_traffic["network_average_speed_kmh"] < night_traffic["network_average_speed_kmh"]

    # 3. Zone filter isolation
    res_zone_a = client.get("/api/v1/urban-analytics/traffic?zone=zone_a")
    assert res_zone_a.status_code == 200
    top_seg_a = res_zone_a.json()["top_congested_segments"]
    assert all(s["zone"] == "zone_a" for s in top_seg_a)


def test_executive_summary_endpoint():
    """Validates the unified executive summary endpoint returning all 5 domain KPIs."""
    res = client.get("/api/v1/urban-analytics/summary")
    assert res.status_code == 200
    data = res.json()

    assert "generated_at" in data
    assert "filter_context" in data
    assert "road_condition" in data
    assert "traffic" in data
    assert "safety" in data
    assert "fleet" in data
    assert "routes" in data

    assert data["road_condition"]["potholes"] > 0
    assert data["traffic"]["vehicle_count"] > 0
    assert data["safety"]["incidents"] > 0
    assert data["fleet"]["active_buses"] > 0
    assert data["routes"]["average_delay_minutes"] > 0
