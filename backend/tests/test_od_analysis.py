"""
Unit tests for Origin-Destination (OD) Traffic Analytics Router (Phase 21)
==========================================================================
Validates:
  - Demonstration OD Analysis mandatory labeling & privacy statements
  - Geographic zone geometry & metadata (Zone A, B, C, D)
  - Aggregated cross-tabular 4x4 OD matrix
  - Flow map vectors (A->B, A->C, B->D, C->A)
  - Top OD pairs leaderboard
  - Peak movement periods & commuter tidal shift analysis
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_od_summary_and_privacy_compliance():
    """Validates privacy assurances, zero PII, and Demonstration OD Analysis label."""
    res = client.get("/api/v1/od/summary")
    assert res.status_code == 200
    data = res.json()

    # Mandatory Prompt requirement
    assert data["demonstration_label"] == "Demonstration OD Analysis"
    assert "Demonstration OD Analysis" in data["privacy_statement"]

    compliance = data["privacy_compliance"]
    assert compliance["individual_tracking_disabled"] is True
    assert compliance["license_plate_correlation"] is False
    assert compliance["anonymization_verified"] is True

    kpis = data["kpis"]
    assert kpis["total_geographic_zones"] == 4
    assert kpis["total_daily_movements"] > 150000
    assert kpis["transit_fleet_mode_share_pct"] > 35.0


def test_od_geographic_zones():
    """Validates retrieval of Zone A, Zone B, Zone C, Zone D with centroids and polygons."""
    res = client.get("/api/v1/od/zones")
    assert res.status_code == 200
    data = res.json()
    assert data["demonstration_label"] == "Demonstration OD Analysis"
    assert data["count"] == 4

    zone_ids = [z["zone_id"] for z in data["zones"]]
    assert "Zone A" in zone_ids
    assert "Zone B" in zone_ids
    assert "Zone C" in zone_ids
    assert "Zone D" in zone_ids

    # Validate coordinate centroid structure
    for z in data["zones"]:
        assert "centroid" in z
        assert "lat" in z["centroid"] and "lon" in z["centroid"]
        assert "polygon" in z and len(z["polygon"]) >= 4
        assert "primary_land_use" in z


def test_od_cross_tabular_matrix():
    """Validates complete 4x4 cross-tabular Origin-Destination matrix."""
    res = client.get("/api/v1/od/matrix")
    assert res.status_code == 200
    data = res.json()

    assert data["demonstration_label"] == "Demonstration OD Analysis"
    headers = data["zone_headers"]
    assert headers == ["Zone A", "Zone B", "Zone C", "Zone D"]

    matrix = data["matrix"]
    assert len(matrix) == 4  # 4 rows

    for row in matrix:
        assert row["origin_zone"] in headers
        assert len(row["destinations"]) == 4  # 4 columns
        assert row["total_origin_trips"] > 0
        for cell in row["destinations"]:
            assert "daily_volume" in cell
            assert cell["daily_volume"] > 0
            assert "avg_duration_minutes" in cell


def test_od_flow_map_vectors():
    """Validates directional flow vectors (A->B, A->C, B->D, C->A)."""
    res = client.get("/api/v1/od/flows")
    assert res.status_code == 200
    data = res.json()
    assert data["demonstration_label"] == "Demonstration OD Analysis"
    assert data["count"] >= 8

    pair_keys = [f["pair_key"] for f in data["flows"]]
    # Verify prompt-mandated movement flows
    assert "A → B" in pair_keys
    assert "A → C" in pair_keys
    assert "B → D" in pair_keys
    assert "C → A" in pair_keys

    # Check vector geometry attributes
    f0 = data["flows"][0]
    assert "origin_centroid" in f0
    assert "destination_centroid" in f0
    assert "bezier_control_point" in f0
    assert "flow_intensity" in f0
    assert 0.0 <= f0["flow_intensity"] <= 1.0
    assert "corridor_route" in f0
    assert "mode_split" in f0
    assert "public_bus" in f0["mode_split"]


def test_top_od_pairs_leaderboard():
    """Validates top origin-destination pairs ranked by volume."""
    res = client.get("/api/v1/od/top-pairs?limit=6")
    assert res.status_code == 200
    data = res.json()
    assert data["demonstration_label"] == "Demonstration OD Analysis"
    assert data["count"] == 6

    top_pairs = data["top_pairs"]
    assert len(top_pairs) == 6

    # Verify descending sort by daily_volume
    volumes = [p["daily_volume"] for p in top_pairs]
    assert volumes == sorted(volumes, reverse=True)

    # Rank 1 checks
    p1 = top_pairs[0]
    assert p1["rank"] == 1
    assert "pair_key" in p1
    assert "corridor_route" in p1
    assert "delay_minutes" in p1
    assert p1["delay_minutes"] >= 0.0


def test_od_peak_movement_periods():
    """Validates Morning, Evening, Midday, and Nocturnal commuter tidal shift analysis."""
    res = client.get("/api/v1/od/peak-periods")
    assert res.status_code == 200
    data = res.json()
    assert data["demonstration_label"] == "Demonstration OD Analysis"

    periods = data["peak_periods"]
    assert len(periods) >= 4
    period_ids = [p["period_id"] for p in periods]
    assert "MORNING_RUSH" in period_ids
    assert "EVENING_RUSH" in period_ids
    assert "MIDDAY_INTERZONAL" in period_ids
    assert "NIGHT_LOGISTICS" in period_ids

    for p in periods:
        assert "time_window" in p
        assert "primary_flow_direction" in p
        assert len(p["dominant_pairs"]) > 0
        assert p["total_period_volume"] > 0
