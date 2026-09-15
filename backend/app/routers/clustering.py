"""
Spatial-Temporal Deduplication & Clustering Router (Phase 19)
=============================================================
Endpoints for querying canonical clustered defects, ingesting raw observations,
and monitoring cross-bus consensus metrics.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from ..schemas.spatial_clustering import (
    BatchClusteringRequest,
    BatchClusteringResponse,
    CanonicalClusteredDefect,
    ClusteringStatsResponse,
    RawObservationIn,
)
from ..services.spatial_clustering_service import get_spatial_clustering_service

router = APIRouter()


@router.get("/clusters", response_model=List[CanonicalClusteredDefect], summary="List canonical clustered defects")
async def list_canonical_clusters(
    status: Optional[str] = Query(None, description="Confirmed | Pending"),
    defect_type: Optional[str] = Query(None, alias="type", description="POTHOLE, DAMAGED_ROAD, WATERLOGGING, etc."),
    bus_id: Optional[str] = Query(None, description="Filter by bus that observed this defect"),
    road_segment: Optional[str] = Query(None, description="Road segment name filter"),
    min_observations: Optional[int] = Query(None, ge=1),
    min_buses: Optional[int] = Query(None, ge=1),
):
    """
    Returns canonical defects combined from multiple bus observations.
    Each defect contains the distinct buses that detected it, total observation count,
    aggregate consensus confidence, and status.
    """
    service = get_spatial_clustering_service()
    return service.list_clusters(
        status=status,
        defect_type=defect_type,
        bus_id=bus_id,
        road_segment=road_segment,
        min_observations=min_observations,
        min_buses=min_buses,
    )


@router.get("/clusters/{cluster_id:path}", response_model=CanonicalClusteredDefect, summary="Get single canonical cluster details")
async def get_canonical_cluster(cluster_id: str):
    """
    Retrieves full details of a canonical clustered defect, including
    every individual bus sighting and distance to refined centroid.
    """
    service = get_spatial_clustering_service()
    from urllib.parse import unquote
    decoded_id = unquote(cluster_id).strip()
    cluster = service.get_cluster(decoded_id) or service.get_cluster(cluster_id)
    if not cluster:
        # Try resilient matching: strip spaces, strip '#', match number, etc.
        clean_target = decoded_id.lower().replace("#", "").replace(" ", "").replace("-", "")
        clusters = service.list_clusters()
        for c in clusters:
            clean_cand = c.canonical_id.strip().lower().replace("#", "").replace(" ", "").replace("-", "")
            if (
                clean_cand == clean_target
                or (clean_target and clean_target in clean_cand)
                or (clean_target.isdigit() and f"#{clean_target}" in c.canonical_id)
            ):
                return c
        raise HTTPException(status_code=404, detail=f"Canonical cluster '{cluster_id}' not found")
    return cluster


@router.post("/observe", response_model=CanonicalClusteredDefect, status_code=status.HTTP_201_CREATED, summary="Ingest raw observation and update/create cluster")
async def ingest_single_observation(obs: RawObservationIn):
    """
    Ingests a raw edge defect observation.
    Deduplicates against existing clusters within 25m on the same road segment:
      - If matched: merges into existing canonical defect, refines centroid, updates confidence & status
      - If not matched: creates a new canonical defect
    """
    service = get_spatial_clustering_service()
    cluster, is_new = service.ingest_observation(obs)
    return cluster


@router.post("/batch", response_model=BatchClusteringResponse, status_code=status.HTTP_201_CREATED, summary="Batch deduplicate & cluster raw observations")
async def batch_cluster_observations(payload: BatchClusteringRequest):
    """
    Takes a batch of raw sightings from one or more buses and merges them into
    canonical defect clusters.
    """
    service = get_spatial_clustering_service()
    affected_clusters, new_count = service.batch_cluster_observations(payload.observations)
    return BatchClusteringResponse(
        total_ingested=len(payload.observations),
        clusters_affected=len(affected_clusters),
        new_clusters_created=new_count,
        clusters=affected_clusters,
    )


@router.get("/stats", response_model=ClusteringStatsResponse, summary="Deduplication efficiency statistics")
async def get_clustering_stats():
    """
    Reports deduplication ratio, compression performance, and multi-bus confirmation rates.
    """
    service = get_spatial_clustering_service()
    return service.get_stats()
