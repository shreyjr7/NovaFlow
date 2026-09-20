"""
NovaFlow AI Road Intelligence Domain Entities
=============================================
SQLModel entities for Supabase PostgreSQL (and SQLite fallback):
  1. ScanJob            (scan_jobs)
  2. RoadDetection      (road_detections)
  3. MaintenanceTicket  (maintenance_tickets)
  4. EvidenceReference  (evidence_references)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ScanJob(SQLModel, table=True):
    """Lifecycle tracking for uploaded videos and live dashcam scanning sessions."""
    __tablename__ = "scan_jobs"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    job_type: str = Field(default="OFFLINE_VIDEO", max_length=32)  # OFFLINE_VIDEO, LIVE_STREAM
    status: str = Field(default="QUEUED", index=True, max_length=32)  # QUEUED, PROCESSING, COMPLETED, FAILED, CANCELLED
    bus_id: str = Field(default="BUS-027", index=True, max_length=64)
    route_id: str = Field(default="ROUTE-17", max_length=64)
    city: str = Field(default="Bengaluru", index=True, max_length=64)
    video_file_name: Optional[str] = Field(default=None, max_length=255)
    video_storage_path: Optional[str] = Field(default=None)  # Path in 'uploaded-videos' bucket
    video_duration_sec: float = Field(default=0.0)
    sample_fps: float = Field(default=1.0)
    confidence_threshold: float = Field(default=0.70)
    total_frames: int = Field(default=0)
    processed_frames: int = Field(default=0)
    detections_count: int = Field(default=0)
    confirmed_count: int = Field(default=0)
    progress_pct: float = Field(default=0.0)
    error_message: Optional[str] = None
    metadata_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def get_metadata(self) -> Dict[str, Any]:
        try:
            return json.loads(self.metadata_json)
        except Exception:
            return {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "job_type": self.job_type,
            "status": self.status,
            "bus_id": self.bus_id,
            "route_id": self.route_id,
            "city": self.city,
            "video_file_name": self.video_file_name,
            "video_storage_path": self.video_storage_path,
            "video_duration_sec": self.video_duration_sec,
            "sample_fps": self.sample_fps,
            "confidence_threshold": self.confidence_threshold,
            "total_frames": self.total_frames,
            "processed_frames": self.processed_frames,
            "detections_count": self.detections_count,
            "confirmed_count": self.confirmed_count,
            "progress_pct": round(self.progress_pct, 1),
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class RoadDetection(SQLModel, table=True):
    """Computer vision detections with ByteTracker persistent IDs and spatial coordinates."""
    __tablename__ = "road_detections"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    scan_id: Optional[UUID] = Field(default=None, index=True)
    bus_id: str = Field(default="BUS-027", index=True, max_length=64)
    type: str = Field(index=True, max_length=64)  # POTHOLE, DAMAGED_ROAD, WATERLOGGING, ROAD_DEBRIS, MISSING_SIGN, etc.
    confidence: float = Field(default=0.85)
    severity: str = Field(default="MEDIUM", index=True, max_length=32)  # CRITICAL, HIGH, MEDIUM, LOW
    latitude: Optional[float] = Field(default=None, nullable=True, index=True)
    longitude: Optional[float] = Field(default=None, nullable=True, index=True)
    location_status: str = Field(default="available", max_length=32)
    location_accuracy: Optional[float] = Field(default=2.50, nullable=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    frame_number: int = Field(default=0)
    track_id: int = Field(default=0, index=True)  # ByteTracker ID
    bounding_box_json: str = Field(default="{}")  # {"x1": 0.1, "y1": 0.2, "x2": 0.5, "y2": 0.6}
    segmentation_json: str = Field(default="[]")  # Polygon points
    evidence_path: Optional[str] = Field(default=None)  # In 'evidence-frames' bucket
    annotated_evidence_path: Optional[str] = Field(default=None)  # In 'annotated-frames' bucket
    thumbnail_path: Optional[str] = Field(default=None)  # In 'thumbnails' bucket
    source_model: str = Field(default="YOLOv8s-RDD2022", max_length=128)
    status: str = Field(default="DETECTED", index=True, max_length=32)  # DETECTED, CONFIRMED, DISMISSED, TICKET_CREATED
    condition_type: str = Field(default="DIRECT", index=True, max_length=32)  # DIRECT vs POTENTIAL
    is_multimodal_verified: bool = Field(default=False)
    observation_count: int = Field(default=1)
    ticket_id: Optional[str] = Field(default=None, max_length=64)
    verification_notes: Optional[str] = None
    persistent_hazard_id: Optional[UUID] = Field(default=None, index=True)
    independent_buses_count: int = Field(default=1)
    contributing_buses: Optional[str] = Field(default=None, max_length=512)
    persistence_badge: Optional[str] = Field(default=None, max_length=64)
    last_detected_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_bounding_box(self) -> Dict[str, float]:
        try:
            return json.loads(self.bounding_box_json)
        except Exception:
            return {}

    def get_segmentation(self) -> List[Dict[str, float]]:
        try:
            return json.loads(self.segmentation_json)
        except Exception:
            return []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detection_id": str(self.id),
            "id": str(self.id),
            "scan_id": str(self.scan_id) if self.scan_id else None,
            "bus_id": self.bus_id,
            "type": self.type,
            "confidence": round(self.confidence, 4),
            "severity": self.severity,
            "latitude": round(self.latitude, 6) if self.latitude is not None else None,
            "longitude": round(self.longitude, 6) if self.longitude is not None else None,
            "lat": round(self.latitude, 6) if self.latitude is not None else None,
            "lng": round(self.longitude, 6) if self.longitude is not None else None,
            "location_status": self.location_status or ("available" if self.latitude is not None else "unavailable"),
            "location_accuracy": self.location_accuracy,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "frame_number": self.frame_number,
            "track_id": self.track_id,
            "bounding_box": self.get_bounding_box(),
            "segmentation": self.get_segmentation(),
            "evidence_path": self.evidence_path,
            "annotated_evidence_path": self.annotated_evidence_path,
            "thumbnail_path": self.thumbnail_path,
            "source_model": self.source_model,
            "status": self.status,
            "condition_type": self.condition_type,
            "is_multimodal_verified": self.is_multimodal_verified,
            "observation_count": self.observation_count,
            "ticket_id": self.ticket_id,
            "verification_notes": self.verification_notes,
            "persistent_hazard_id": str(self.persistent_hazard_id) if self.persistent_hazard_id else None,
            "independent_buses_count": self.independent_buses_count,
            "contributing_buses": self.contributing_buses,
            "persistence_badge": self.persistence_badge or (f"CONFIRMED BY {self.independent_buses_count} BUSES" if self.independent_buses_count >= 2 else "SINGLE OBSERVATION"),
            "last_detected_at": self.last_detected_at.isoformat() if self.last_detected_at else (self.timestamp.isoformat() if self.timestamp else None),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_geojson_feature(self) -> Dict[str, Any]:
        """Directly integrates into existing LiveGisMap / GeoJSON FeatureCollection."""
        badge = self.persistence_badge or (f"CONFIRMED BY {self.independent_buses_count} BUSES" if self.independent_buses_count >= 2 else "SINGLE OBSERVATION")
        last_time = self.last_detected_at.isoformat() if self.last_detected_at else (self.timestamp.isoformat() if self.timestamp else "")
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.longitude, self.latitude],
            },
            "properties": {
                "event_id": str(self.id),
                "event_type": self.type,
                "confidence": round(self.confidence, 3),
                "severity": self.severity,
                "status": self.status,
                "condition_type": self.condition_type,
                "bus_id": self.bus_id,
                "frame_number": self.frame_number,
                "track_id": self.track_id,
                "evidence_url": self.annotated_evidence_path or self.evidence_path,
                "thumbnail_url": self.thumbnail_path,
                "is_multimodal_verified": self.is_multimodal_verified,
                "observation_count": self.observation_count,
                "independent_buses_count": self.independent_buses_count,
                "contributing_buses": self.contributing_buses,
                "persistence_badge": badge,
                "last_detected_at": last_time,
                "ticket_id": self.ticket_id,
                "timestamp": self.timestamp.isoformat() if self.timestamp else "",
            }
        }


class MaintenanceTicket(SQLModel, table=True):
    """Official PWD, BBMP, or NHAI Municipal Repair Work Order."""
    __tablename__ = "maintenance_tickets"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    ticket_code: str = Field(unique=True, index=True, max_length=64)  # e.g. 'WO-BLR-2026-105'
    detection_id: Optional[UUID] = Field(default=None, index=True)
    hazard_type: str = Field(max_length=64)
    title: str = Field(max_length=255)
    location_description: str
    latitude: float
    longitude: float
    city: str = Field(default="Bengaluru", index=True, max_length=64)
    severity: str = Field(default="HIGH", index=True, max_length=32)
    priority: str = Field(default="P1", max_length=32)  # P1, P2, P3
    agency: str = Field(default="BBMP Road Infrastructure Division", max_length=128)
    assigned_contractor: Optional[str] = Field(default=None, max_length=128)
    assigned_crew: Optional[str] = Field(default=None, max_length=128)
    status: str = Field(default="OPEN", index=True, max_length=32)  # OPEN, ACKNOWLEDGED, ASSIGNED, IN_PROGRESS, RESOLVED
    evidence: Optional[str] = Field(default=None)  # Frame storage path or URL
    source_bus: Optional[str] = Field(default=None, max_length=64, index=True)
    observation_count: int = Field(default=1)
    estimated_cost_inr: float = Field(default=0.0)
    field_notes: Optional[str] = None
    target_sla_hours: int = Field(default=24)
    target_completion: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        ts = self.created_at.isoformat() if self.created_at else datetime.now(timezone.utc).isoformat()
        t_id = self.ticket_code or str(self.id)
        return {
            # Canonical 11 fields for Phase 11
            "ticket_id": t_id,
            "detection_id": str(self.detection_id) if self.detection_id else None,
            "issue_type": self.hazard_type,
            "severity": self.severity,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "evidence": self.evidence or "",
            "source_bus": self.source_bus or "UNKNOWN",
            "timestamp": ts,
            "status": self.status,
            "created_at": ts,

            # Legacy & schema compatibility
            "id": str(self.id),
            "ticket_code": self.ticket_code,
            "hazard_type": self.hazard_type,
            "title": self.title,
            "location_description": self.location_description,
            "city": self.city,
            "priority": self.priority,
            "agency": self.agency,
            "assigned_contractor": self.assigned_contractor,
            "assigned_crew": self.assigned_crew,
            "observation_count": getattr(self, "observation_count", 1),
            "estimated_cost_inr": self.estimated_cost_inr,
            "field_notes": self.field_notes,
            "target_sla_hours": self.target_sla_hours,
            "target_completion": self.target_completion.isoformat() if self.target_completion else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EvidenceReference(SQLModel, table=True):
    """Direct reference to objects stored in Supabase Storage buckets."""
    __tablename__ = "evidence_references"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    detection_id: Optional[UUID] = Field(default=None, index=True)
    scan_id: Optional[UUID] = Field(default=None, index=True)
    bucket_name: str = Field(index=True, max_length=64)  # uploaded-videos, evidence-frames, annotated-frames, thumbnails
    storage_path: str = Field()
    public_url: Optional[str] = None
    mime_type: str = Field(default="image/jpeg", max_length=64)
    file_size_bytes: int = Field(default=0)
    sha256_hash: Optional[str] = Field(default=None, max_length=64)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata_json: str = Field(default="{}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "detection_id": str(self.detection_id) if self.detection_id else None,
            "scan_id": str(self.scan_id) if self.scan_id else None,
            "bucket_name": self.bucket_name,
            "storage_path": self.storage_path,
            "public_url": self.public_url,
            "mime_type": self.mime_type,
            "file_size_bytes": self.file_size_bytes,
            "sha256_hash": self.sha256_hash,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
        }


class PersistentHazard(SQLModel, table=True):
    """
    Persistent road defect confirmed across multiple transit buses and repeated observations.
    Maintains spatial consensus without altering raw model detection confidence.
    """
    __tablename__ = "persistent_hazards"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    hazard_code: str = Field(index=True, unique=True, max_length=64)  # e.g. HAZ-BLR-2026-0042
    hazard_type: str = Field(index=True, max_length=64)  # POTHOLE, ROAD_DAMAGE, WATERLOGGING, etc.
    severity: str = Field(default="MEDIUM", index=True, max_length=32)  # CRITICAL, HIGH, MEDIUM, LOW
    latitude: float = Field(index=True)
    longitude: float = Field(index=True)
    road_segment: Optional[str] = Field(default=None, max_length=256)
    city: str = Field(default="Bengaluru", index=True, max_length=64)
    initial_confidence: float = Field(default=0.85)  # Raw AI confidence of the first detection
    persistence_score: float = Field(default=0.40)  # Multi-bus persistence consensus (0.0 to 1.0)
    persistence_status: str = Field(default="SINGLE OBSERVATION", max_length=64)  # "CONFIRMED BY 3 BUSES"
    total_observations: int = Field(default=1)  # Total frames/detections logged
    independent_buses_count: int = Field(default=1)  # Count of distinct fleet edge nodes
    contributing_buses: str = Field(default="", max_length=512)  # e.g. "BUS-027, BUS-014, BUS-031"
    first_detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    ticket_id: Optional[str] = Field(default=None, max_length=64)
    status: str = Field(default="ACTIVE", index=True, max_length=32)  # ACTIVE, VERIFIED, RESOLVED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        buses = [b.strip() for b in self.contributing_buses.split(",") if b.strip()] if self.contributing_buses else []
        return {
            "id": str(self.id),
            "hazard_code": self.hazard_code,
            "hazard_type": self.hazard_type,
            "severity": self.severity,
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
            "road_segment": self.road_segment,
            "city": self.city,
            "initial_confidence": round(self.initial_confidence, 4),
            "persistence_score": round(self.persistence_score, 3),
            "persistence_status": self.persistence_status,
            "total_observations": self.total_observations,
            "independent_buses_count": self.independent_buses_count,
            "contributing_buses": buses,
            "first_detected_at": self.first_detected_at.isoformat() if self.first_detected_at else None,
            "last_detected_at": self.last_detected_at.isoformat() if self.last_detected_at else None,
            "ticket_id": self.ticket_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_geojson_feature(self) -> Dict[str, Any]:
        buses_list = [b.strip() for b in self.contributing_buses.split(",") if b.strip()] if self.contributing_buses else []
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.longitude, self.latitude],
            },
            "properties": {
                "event_id": self.hazard_code,
                "hazard_id": str(self.id),
                "event_type": self.hazard_type,
                "layer": "potholes" if "POTHOLE" in self.hazard_type else "road_damage",
                "category": "ROAD_DAMAGE",
                "severity": self.severity,
                "confidence": round(self.initial_confidence, 3),
                "persistence_status": self.persistence_status,
                "persistence_score": round(self.persistence_score, 3),
                "independent_buses_count": self.independent_buses_count,
                "contributing_buses": buses_list,
                "total_observations": self.total_observations,
                "road_segment": self.road_segment or f"Corridor ({self.latitude:.4f}, {self.longitude:.4f})",
                "city": self.city,
                "ticket_id": self.ticket_id,
                "status": self.status,
                "first_detected_at": self.first_detected_at.isoformat() if self.first_detected_at else None,
                "last_detected_at": self.last_detected_at.isoformat() if self.last_detected_at else None,
                "timestamp": self.last_detected_at.isoformat() if self.last_detected_at else None,
            }
        }


class HazardObservation(SQLModel, table=True):
    """
    Individual detection observation of a persistent road hazard by an edge transit node.
    Maintains full historical observation log across multiple buses.
    """
    __tablename__ = "hazard_observations"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    hazard_id: UUID = Field(foreign_key="persistent_hazards.id", index=True)
    detection_id: Optional[UUID] = Field(default=None, index=True)
    bus_id: str = Field(index=True, max_length=64)  # e.g. BUS-027
    route_id: Optional[str] = Field(default=None, max_length=64)
    road_segment: Optional[str] = Field(default=None, max_length=256)
    model_confidence: float = Field(default=0.85)  # Raw AI model confidence for this observation
    severity: str = Field(default="MEDIUM", max_length=32)
    latitude: float
    longitude: float
    evidence_path: Optional[str] = Field(default=None)
    thumbnail_path: Optional[str] = Field(default=None)
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "hazard_id": str(self.hazard_id),
            "detection_id": str(self.detection_id) if self.detection_id else None,
            "bus_id": self.bus_id,
            "route_id": self.route_id,
            "road_segment": self.road_segment,
            "model_confidence": round(self.model_confidence, 4),
            "severity": self.severity,
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
            "evidence_path": self.evidence_path,
            "thumbnail_path": self.thumbnail_path,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
