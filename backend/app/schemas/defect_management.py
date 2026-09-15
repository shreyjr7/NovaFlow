"""
Defect Management Schemas and Lifecycle Models (Phase 18)
=========================================================
Defines the 6-stage lifecycle, priority scoring breakdown,
cross-fleet confirmation fields, and field engineer actions.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DefectLifecycleState(str, Enum):
    AI_DETECTED = "AI_DETECTED"
    UNVERIFIED = "UNVERIFIED"
    CONFIRMED = "CONFIRMED"
    ASSIGNED = "ASSIGNED"
    UNDER_REPAIR = "UNDER_REPAIR"
    RESOLVED = "RESOLVED"
    REOPENED_UNDER_REVIEW = "REOPENED_UNDER_REVIEW"
    REJECTED = "REJECTED"


class DefectPriorityBreakdown(BaseModel):
    severity_score: float = Field(..., ge=0, le=100)
    traffic_volume_score: float = Field(..., ge=0, le=100)
    detections_score: float = Field(..., ge=0, le=100)
    location_importance_score: float = Field(..., ge=0, le=100)
    safety_risk_score: float = Field(..., ge=0, le=100)
    persistence_score: float = Field(..., ge=0, le=100)
    total_priority_score: int = Field(..., ge=0, le=100)
    priority_tier: str = Field(..., description="CRITICAL | HIGH | MEDIUM | LOW")


class MaintenanceTicketInfo(BaseModel):
    ticket_id: str
    assigned_authority: str
    assigned_contractor: Optional[str] = None
    target_completion_date: Optional[str] = None
    work_order_notes: Optional[str] = None
    created_at: str
    status: str = "ISSUED"


class RepairEvidence(BaseModel):
    evidence_id: str
    before_image_b64: Optional[str] = None
    after_image_b64: Optional[str] = None
    completion_notes: str
    engineer_id: str
    uploaded_at: str
    completion_certificate_url: Optional[str] = None


class AuditLogEntry(BaseModel):
    timestamp: str
    actor: str
    action: str
    from_status: str
    to_status: str
    notes: Optional[str] = None


class DefectLocation(BaseModel):
    lat: float
    lon: float
    bearing_deg: Optional[float] = None
    address: Optional[str] = None
    district: Optional[str] = "Central"


class DefectRecord(BaseModel):
    defect_id: str
    location: DefectLocation
    road_segment: str
    type: str
    severity: str
    first_detected: str
    last_detected: str
    buses_confirming: List[str] = Field(default_factory=list)
    number_of_buses_confirming: int = 1
    detection_count: int = 1
    confidence: float = 1.0
    assigned_authority: Optional[str] = None
    maintenance_ticket: Optional[MaintenanceTicketInfo] = None
    status: DefectLifecycleState = DefectLifecycleState.AI_DETECTED
    priority_score: int = 50
    priority_breakdown: DefectPriorityBreakdown
    repair_evidence: Optional[RepairEvidence] = None
    frame_b64: Optional[str] = None
    closed_at: Optional[str] = None
    closed_by: Optional[str] = None
    reopened_at: Optional[str] = None
    reopen_reason: Optional[str] = None
    reopen_count: int = 0
    audit_history: List[AuditLogEntry] = Field(default_factory=list)


# ── Action Request Payloads ──────────────────────────────────────────────────

class ConfirmDefectIn(BaseModel):
    engineer_id: str = "ENG_CIVIL_042"
    notes: Optional[str] = "Defect verified on site via transit telemetry cross-confirmation."


class RejectDefectIn(BaseModel):
    engineer_id: str = "ENG_CIVIL_042"
    reason: str = "Visual artifact / road surface shadow – false positive."


class AssignDefectIn(BaseModel):
    engineer_id: str = "ENG_CIVIL_042"
    assigned_authority: str = "Public Works Department (PWD)"
    assigned_contractor: Optional[str] = "Larsen & Toubro Urban Infra"
    target_completion_date: Optional[str] = "2026-09-22"
    notes: Optional[str] = "High-priority asphalt resurfacing work order."


class UpdateRepairIn(BaseModel):
    engineer_id: str = "ENG_FIELD_108"
    progress_percent: int = Field(50, ge=0, le=100)
    notes: str = "Cold mix asphalt patching initiated on site with active traffic diversion."


class UploadRepairEvidenceIn(BaseModel):
    engineer_id: str = "ENG_FIELD_108"
    after_image_b64: Optional[str] = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkWPjfDwAEfQHzgV23vAAAAABJRU5ErkJggg=="
    completion_notes: str = "Hot bitumen compaction completed, road surface leveled and tested."
    contractor: Optional[str] = None
    completion_certificate_url: Optional[str] = "/certs/cert_pwd_2026_0915.pdf"


class CloseDefectIn(BaseModel):
    engineer_id: str = "ENG_SUPERVISOR_007"
    closure_notes: str = "Repair inspected against municipal quality standards. Ticket closed."


class SimulateRedetectionIn(BaseModel):
    bus_id: str = "BUS_009"
    confidence: float = 0.94
    timestamp: Optional[str] = None
    notes: Optional[str] = "Transit bus edge camera re-detected defect signature."
