"""
Unit and Integration tests for Duplicate Event Intelligence & Spatial-Temporal Clustering (Phase 19).
====================================================================================================
Tests:
  - Exact prompt-mandated scenario: Pothole #104 (Bus 102, Bus 117, Bus 143 | 18 obs | 92% conf | Confirmed)
  - Merging multiple bus observations into ONE DEFECT rather than creating separate entries
  - ST_DWithin / Geodesic Haversine spatial proximity threshold enforcement (25m)
  - Road segment map matching preventing false merges across incompatible corridors
  - Centroid refinement via observation-weighted center of gravity
  - Bayesian multi-bus consensus confidence calculation
  - API endpoints for listing clusters, retrieving single cluster, and ingestion
"""

import uuid
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.services.spatial_clustering_service import (
    SpatialClusteringService,
    get_spatial_clustering_service,
    haversine_distance_meters,
)
from backend.app.schemas.spatial_clustering import RawObservationIn

client = TestClient(app)


def test_prompt_mandated_pothole_104():
    """
    Validates the exact canonical example specified in the prompt:
      Pothole #104
      Detected by: Bus 102, Bus 117, Bus 143
      Observations: 18
      Confidence: 92%
      Status: Confirmed
    """
    service = get_spatial_clustering_service()
    cluster = service.get_cluster("Pothole #104")
    assert cluster is not None, "Pothole #104 canonical cluster not found"

    assert cluster.canonical_id == "Pothole #104"
    assert cluster.defect_type == "POTHOLE"
    assert "Bus 102" in cluster.detected_by
    assert "Bus 117" in cluster.detected_by
    assert "Bus 143" in cluster.detected_by
    assert cluster.number_of_buses == 3
    assert cluster.number_of_observations == 18
    assert cluster.confidence == 0.92  # Exactly 92%
    assert cluster.status == "Confirmed"
    assert cluster.road_segment == "CP_INNER_CIRCLE"
    assert len(cluster.observations) == 18


def test_combine_nearby_observations_into_one_defect():
    """
    Problem: Multiple buses may detect the same pothole.
    Do not create: Pothole #1, Pothole #2, Pothole #3, Pothole #4.
    Instead cluster them into ONE DEFECT.
    """
    service = SpatialClusteringService(radius_meters=25.0)

    # Base coordinates for the pothole
    base_lat = 28.6145
    base_lon = 77.2095
    seg = "CONNAUGHT_CIRCULAR"

    # Bus 1 detects -> creates initial canonical defect
    obs1 = RawObservationIn(
        bus_id="Bus 101",
        lat=base_lat,
        lon=base_lon,
        defect_type="POTHOLE",
        confidence=0.88,
        road_segment=seg,
    )
    c1, is_new1 = service.ingest_observation(obs1)
    assert is_new1 is True
    canon_id = c1.canonical_id
    assert c1.number_of_observations == 1
    assert c1.number_of_buses == 1
    assert c1.status == "Pending"

    # Bus 2 detects at 4m offset -> MUST MERGE into same defect, NOT create Pothole #2
    obs2 = RawObservationIn(
        bus_id="Bus 102",
        lat=base_lat + 0.00003,
        lon=base_lon + 0.00002,
        defect_type="POTHOLE",
        confidence=0.90,
        road_segment=seg,
    )
    c2, is_new2 = service.ingest_observation(obs2)
    assert is_new2 is False, "Must not create a new defect; must merge"
    assert c2.canonical_id == canon_id
    assert c2.number_of_observations == 2
    assert c2.number_of_buses == 2
    assert "Bus 101" in c2.detected_by
    assert "Bus 102" in c2.detected_by
    assert c2.status == "Confirmed"  # Multi-bus consensus auto-promotes to Confirmed

    # Bus 3 detects at 7m offset -> MERGES into same defect
    obs3 = RawObservationIn(
        bus_id="Bus 103",
        lat=base_lat - 0.00004,
        lon=base_lon + 0.00003,
        defect_type="POTHOLE",
        confidence=0.92,
        road_segment=seg,
    )
    c3, is_new3 = service.ingest_observation(obs3)
    assert is_new3 is False
    assert c3.canonical_id == canon_id
    assert c3.number_of_observations == 3
    assert c3.number_of_buses == 3

    # Bus 4 detects at 2m offset -> MERGES into same defect
    obs4 = RawObservationIn(
        bus_id="Bus 104",
        lat=base_lat + 0.00001,
        lon=base_lon - 0.00001,
        defect_type="POTHOLE",
        confidence=0.93,
        road_segment=seg,
    )
    c4, is_new4 = service.ingest_observation(obs4)
    assert is_new4 is False
    assert c4.canonical_id == canon_id
    assert c4.number_of_observations == 4
    assert c4.number_of_buses == 4
    assert c4.confidence >= 0.92  # Consensus boosts confidence


def test_spatial_distance_threshold_separation():
    """Observations beyond spatial clustering radius (e.g. 80m away) must create a separate defect."""
    service = SpatialClusteringService(radius_meters=25.0)
    base_lat = 28.6145
    base_lon = 77.2095

    # First pothole
    c1, is_new1 = service.ingest_observation(
        RawObservationIn(bus_id="Bus 101", lat=base_lat, lon=base_lon, defect_type="POTHOLE", road_segment="SEG_A")
    )
    assert is_new1 is True

    # Distant pothole (80 meters north)
    distant_lat = base_lat + 0.00075  # ~83 meters
    dist = haversine_distance_meters(base_lat, base_lon, distant_lat, base_lon)
    assert dist > 50.0

    c2, is_new2 = service.ingest_observation(
        RawObservationIn(bus_id="Bus 102", lat=distant_lat, lon=base_lon, defect_type="POTHOLE", road_segment="SEG_A")
    )
    assert is_new2 is True, "Distant observation must create distinct canonical defect"
    assert c2.canonical_id != c1.canonical_id


def test_map_matching_prevents_cross_corridor_conflation():
    """Different road segment classifications prevent conflation across distinct roadways."""
    service = SpatialClusteringService(radius_meters=25.0)

    # Observation on Ring Road Flyover
    c1, is_new1 = service.ingest_observation(
        RawObservationIn(
            bus_id="Bus 101",
            lat=28.5680,
            lon=77.2090,
            defect_type="POTHOLE",
            road_segment="RING_ROAD_AIIMS",
        )
    )
    assert is_new1 is True

    # Observation on Chandni Chowk (different segment and city quadrant)
    c2, is_new2 = service.ingest_observation(
        RawObservationIn(
            bus_id="Bus 102",
            lat=28.6500,
            lon=77.2300,
            defect_type="POTHOLE",
            road_segment="CHANDNI_CHOWK_RD",
        )
    )
    assert is_new2 is True
    assert c1.canonical_id != c2.canonical_id


def test_centroid_recomputation():
    """Adding sightings progressively refines the weighted center of gravity."""
    service = SpatialClusteringService(radius_meters=30.0)
    lat1, lon1 = 28.63000, 77.22000
    lat2, lon2 = 28.63010, 77.22010

    c1, _ = service.ingest_observation(
        RawObservationIn(bus_id="Bus 101", lat=lat1, lon=lon1, confidence=0.80, road_segment="TEST_SEG")
    )
    assert c1.centroid.lat == lat1
    assert c1.centroid.lon == lon1

    # Second sighting pulls the centroid toward lat2, lon2
    c2, _ = service.ingest_observation(
        RawObservationIn(bus_id="Bus 102", lat=lat2, lon=lon2, confidence=0.80, road_segment="TEST_SEG")
    )
    assert lat1 < c2.centroid.lat < lat2
    assert lon1 < c2.centroid.lon < lon2


def test_clustering_api_endpoints():
    """Validates REST endpoints for clusters, single cluster retrieval, and stats."""
    # 1. GET /api/v1/clustering/clusters
    res_list = client.get("/api/v1/clustering/clusters")
    assert res_list.status_code == 200
    clusters = res_list.json()
    assert isinstance(clusters, list)
    assert len(clusters) >= 3
    assert any(c["canonical_id"] == "Pothole #104" for c in clusters)

    # 2. GET /api/v1/clustering/clusters/{id}
    from urllib.parse import quote
    res_single = client.get(f"/api/v1/clustering/clusters/{quote('Pothole #104')}")
    assert res_single.status_code == 200
    single = res_single.json()
    assert single["canonical_id"] == "Pothole #104"
    assert single["number_of_observations"] == 18
    assert single["status"] == "Confirmed"
    assert "observations" in single

    # 3. POST /api/v1/clustering/observe
    res_obs = client.post(
        "/api/v1/clustering/observe",
        json={
            "bus_id": "Bus 199",
            "lat": 28.6328,
            "lon": 77.2195,
            "defect_type": "POTHOLE",
            "confidence": 0.95,
            "road_segment": "CP_INNER_CIRCLE",
        },
    )
    assert res_obs.status_code == 201
    updated = res_obs.json()
    assert updated["canonical_id"] == "Pothole #104"
    assert updated["number_of_observations"] >= 19
    assert "Bus 199" in updated["detected_by"]

    # 4. GET /api/v1/clustering/stats
    res_stats = client.get("/api/v1/clustering/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["total_canonical_defects"] >= 4
    assert stats["total_raw_observations"] >= 50
    assert stats["deduplication_ratio"] > 1.0
