"""
Unit tests for Backend Congestion & Bottleneck Router (Phase 11 & Phase 20)
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_list_monitored_segments():
    response = client.get("/api/v1/congestion/segments")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "segments" in data
    assert data["count"] >= 15
    # Check that polylines, speeds, deficit, route delay, and colors are present
    seg = data["segments"][0]
    assert "segment_id" in seg
    assert "current_speed" in seg
    assert "baseline_speed" in seg
    assert "route_delay_minutes" in seg
    assert "severity_color" in seg
    assert seg["severity_color"] in ("green", "yellow", "orange", "red")
    assert "polyline" in seg
    assert len(seg["polyline"]) >= 2


def test_active_bottlenecks():
    response = client.get("/api/v1/congestion/bottlenecks")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "bottlenecks" in data
    assert data["count"] > 0
    # Every returned item should be HIGH or SEVERE or flagged bottleneck
    for b in data["bottlenecks"]:
        assert b["severity"] in ("HIGH", "SEVERE") or b.get("is_bottleneck")


def test_congestion_heatmap_points():
    response = client.get("/api/v1/congestion/heatmap")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "points" in data
    assert "palette" in data
    assert data["count"] > 0
    # Verify point attributes
    pt = data["points"][0]
    assert "lat" in pt
    assert "lon" in pt
    assert "intensity" in pt
    assert 0.0 <= pt["intensity"] <= 1.0
    assert "severity" in pt
    assert "color" in pt
    assert pt["color"] in ("green", "yellow", "orange", "red")
    assert "score" in pt


def test_congestion_heatmap_temporal_filters():
    """Validates Phase 20 date range and time of day heatmap filtering."""
    # 1. Morning rush
    res_morning = client.get("/api/v1/congestion/heatmap?date_range=today&time_of_day=morning")
    assert res_morning.status_code == 200
    m_data = res_morning.json()
    assert m_data["filters"]["time_of_day"] == "morning"
    assert len(m_data["points"]) > 0

    # 2. Night lull (should have lower intensity / higher speeds)
    res_night = client.get("/api/v1/congestion/heatmap?date_range=last_7_days&time_of_day=night")
    assert res_night.status_code == 200
    n_data = res_night.json()
    assert n_data["filters"]["time_of_day"] == "night"
    assert n_data["filters"]["date_range"] == "last_7_days"

    # Compare average intensity: morning rush should be higher than night
    avg_m_int = sum(p["intensity"] for p in m_data["points"]) / len(m_data["points"])
    avg_n_int = sum(p["intensity"] for p in n_data["points"]) / len(n_data["points"])
    assert avg_m_int > avg_n_int


def test_top_congested_segments_leaderboard():
    """Validates Phase 20 Top 10 congested road segments."""
    response = client.get("/api/v1/congestion/top-segments?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 10
    assert "top_segments" in data
    top_10 = data["top_segments"]
    assert len(top_10) == 10

    # Verify descending sort by congestion_score
    scores = [s["congestion_score"] for s in top_10]
    assert scores == sorted(scores, reverse=True)

    # Verify attributes of top segment
    worst = top_10[0]
    assert worst["rank"] == 1
    assert "segment_id" in worst
    assert "name" in worst
    assert "congestion_score" in worst
    assert "severity" in worst
    assert "severity_color" in worst
    assert worst["severity_color"] in ("green", "yellow", "orange", "red")
    assert "route_delay_minutes" in worst
    assert worst["route_delay_minutes"] >= 0.0
    assert "peak_hours" in worst


def test_congestion_analytics_endpoint():
    """Validates Phase 20 analytics: diurnal peak hours, KPIs, and 24h progression."""
    response = client.get("/api/v1/congestion/analytics")
    assert response.status_code == 200
    data = response.json()

    assert "kpis" in data
    kpis = data["kpis"]
    assert "average_speed_kmh" in kpis
    assert "average_vehicle_density" in kpis
    assert "total_route_delay_minutes" in kpis
    assert "network_congestion_score" in kpis
    assert "active_bottlenecks_count" in kpis

    assert "peak_hours" in data
    peaks = data["peak_hours"]
    assert "morning_peak" in peaks
    assert "evening_peak" in peaks
    assert "08:30" in peaks["morning_peak"]["window"]
    assert "18:00" in peaks["evening_peak"]["window"]

    assert "hourly_diurnal_profile" in data
    profile = data["hourly_diurnal_profile"]
    assert len(profile) == 24
    assert profile[9]["is_peak"] is True   # 09:00 AM rush
    assert profile[19]["is_peak"] is True  # 19:00 PM rush

    assert "top_10_congested_segments" in data
    assert len(data["top_10_congested_segments"]) <= 10


def test_ingest_and_list_congestion_events():
    event_payload = {
        "road_segment": "DEL_01",
        "segment_name": "Ring Road – Dhaula Kuan to Mahipalpur",
        "density": 0.82,
        "average_speed": 11.5,
        "congestion_score": 88.5,
        "severity": "SEVERE",
        "timestamp": "2026-09-15T04:30:00Z",
        "location": {"lat": 28.5842, "lon": 77.1545},
        "vehicle_count": 32,
        "duration_seconds": 120.0,
        "is_bottleneck": True,
        "bus_id": "BUS_DEL_101",
        "camera_id": "FRONT",
    }

    post_resp = client.post("/api/v1/congestion/events", json=event_payload)
    assert post_resp.status_code == 201
    post_data = post_resp.json()
    assert post_data["ok"] is True
    assert "event_id" in post_data

    # List events and check filter
    list_resp = client.get("/api/v1/congestion/events?severity=SEVERE")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] > 0
    found = any(e["road_segment"] == "DEL_01" for e in list_data["items"])
    assert found


def test_congestion_stats():
    response = client.get("/api/v1/congestion/stats")
    assert response.status_code == 200
    data = response.json()
    assert "monitored_segments" in data
    assert "active_bottlenecks" in data
    assert "average_congestion_score" in data
    assert "average_route_delay_minutes" in data
    assert "worst_segment" in data
