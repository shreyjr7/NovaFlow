"""
Spatial-Temporal Deduplication & Clustering Schemas (Phase 19)
==============================================================
Defines schemas for merging raw transit defect detections across
multiple buses into canonical clustered defects.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RawObservationIn(BaseModel):
    """Raw edge detection submitted by a bus sensor."""
    event_id: Optional[str] = None
    bus_id: str = Field(..., description="e.g. Bus 102 or BUS_102")
    camera_id: str = "FRONT"
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    timestamp: Optional[str] = None
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    defect_type: str = "POTHOLE"
    severity: str = "HIGH"
    road_segment: Optional[str] = None
    frame_b64: Optional[str] = None


class ObservationRecord(BaseModel):
    """Individual sighting attached to a canonical cluster."""
    observation_id: str
    event_id: str
    bus_id: str
    camera_id: str
    lat: float
    lon: float
    timestamp: str
    confidence: float
    distance_to_centroid_m: float = 0.0


class ClusterCentroid(BaseModel):
    lat: float
    lon: float
    address: Optional[str] = None


class CanonicalClusteredDefect(BaseModel):
    """
    Combined canonical defect representing multiple observations across buses.
    Example:
      Pothole #104
      Detected by: Bus 102, Bus 117, Bus 143
      Observations: 18
      Confidence: 92%
      Status: Confirmed
    """
    canonical_id: str = Field(..., description="e.g. Pothole #104 or DEF-CLUST-104")
    defect_type: str = "POTHOLE"
    severity: str = "HIGH"
    road_segment: str
    centroid: ClusterCentroid
    detected_by: List[str] = Field(default_factory=list, description="Unique bus identifiers")
    number_of_buses: int = 1
    number_of_observations: int = 1
    confidence: float = Field(..., ge=0.0, le=1.0, description="Aggregate consensus confidence")
    status: str = Field("Confirmed", description="Confirmed | Pending")
    first_detected: str
    last_detected: str
    observations: List[ObservationRecord] = Field(default_factory=list)
    map_matched_segment_id: Optional[str] = None
    radius_meters: float = 25.0


class BatchClusteringRequest(BaseModel):
    observations: List[RawObservationIn]


class BatchClusteringResponse(BaseModel):
    total_ingested: int
    clusters_affected: int
    new_clusters_created: int
    clusters: List[CanonicalClusteredDefect]


class ClusteringStatsResponse(BaseModel):
    total_raw_observations: int
    total_canonical_defects: int
    deduplication_ratio: float
    average_observations_per_defect: float
    confirmed_clusters_count: int
    pending_clusters_count: int
    multi_bus_consensus_rate: float
