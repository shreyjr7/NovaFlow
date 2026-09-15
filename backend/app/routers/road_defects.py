"""
Road Defects API Router – FastAPI (Phase 18 Enhanced)
======================================================
Endpoints for the central platform to receive, query, and manage road
defect lifecycles:
  AI DETECTED -> UNVERIFIED -> CONFIRMED -> ASSIGNED -> UNDER REPAIR -> RESOLVED
  (with autonomous post-closure re-detection watchdog -> REOPENED_UNDER_REVIEW)

Endpoints:
  POST  /api/v1/road-defects                          – Ingest defect from edge device
  GET   /api/v1/road-defects                          – List & filter defects (with priority scores)
  GET   /api/v1/road-defects/{id}                     – Get detailed defect record & audit trail
  GET   /api/v1/road-defects/summary                  – Aggregated summary counts
  GET   /api/v1/road-defects/stats/lifecycle          – Full lifecycle & priority breakdown
  POST  /api/v1/road-defects/{id}/confirm             – Confirm defect (Field Engineer)
  POST  /api/v1/road-defects/{id}/reject              – Reject defect / false positive
  POST  /api/v1/road-defects/{id}/assign              – Assign authority & create maintenance ticket
  POST  /api/v1/road-defects/{id}/update              – Update repair progress (UNDER_REPAIR)
  POST  /api/v1/road-defects/{id}/upload-evidence     – Upload before/after repair evidence
  POST  /api/v1/road-defects/{id}/close               – Close maintenance ticket (RESOLVED)
  POST  /api/v1/road-defects/{id}/simulate-redetection – Test post-closure watchdog (reopen/review)
  PATCH /api/v1/road-defects/{id}/status              – Backward-compatible status updater
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, status, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..database.session import get_session
from ..models.ingested_event import IngestedEvent

from ..schemas.defect_management import (
    AssignDefectIn,
    CloseDefectIn,
    ConfirmDefectIn,
    DefectRecord,
    RejectDefectIn,
    SimulateRedetectionIn,
    UpdateRepairIn,
    UploadRepairEvidenceIn,
)
from ..services.defect_service import get_road_defect_service

router = APIRouter()


# ── Schemas for Ingestion & Legacy Compatibility ─────────────────────────────

class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class GpsPoint(BaseModel):
    lat: float
    lon: float
    bearing_deg: Optional[float] = None
    road_segment: Optional[str] = None
    address: Optional[str] = None


class RoadDefectEventIn(BaseModel):
    """Payload submitted by the edge device."""
    event_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "road_defect"
    cls: Optional[str] = Field(default="pothole", alias="class")
    defect_type: Optional[str] = None
    label: Optional[str] = None
    confidence: float = 0.90
    severity: Optional[str] = "MEDIUM"
    bounding_box: Optional[List[float]] = None
    camera_id: str = "FRONT"
    bus_id: str = "BUS_001"
    timestamp: Optional[str] = None
    gps: GpsPoint
    frame_b64: Optional[str] = None
    quality: Optional[Dict[str, Any]] = None
    road_segment: Optional[str] = None
    status: Optional[str] = "AI_DETECTED"

    model_config = {"populate_by_name": True}


class StatusUpdate(BaseModel):
    status: Literal["OPEN", "IN_PROGRESS", "RESOLVED", "FALSE_POSITIVE", "CONFIRMED", "ASSIGNED", "UNDER_REPAIR", "REJECTED"]


class RoadDefectSummary(BaseModel):
    total: int
    by_class: Dict[str, int]
    by_severity: Dict[str, int]
    by_status: Dict[str, int]


# ── Ingestion Endpoint ───────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED, summary="Ingest road defect event from edge device")
@router.post("/ingest", status_code=status.HTTP_201_CREATED, summary="Alias: Ingest road defect")
async def create_defect(event: RoadDefectEventIn):
    service = get_road_defect_service()
    now_iso = event.timestamp or datetime.now(timezone.utc).isoformat()
    d_type = event.defect_type or event.cls or "POTHOLE"
    seg = event.road_segment or event.gps.road_segment or "UNKNOWN_SEGMENT"

    defect = service.register_or_cluster_edge_event(
        event_id=event.event_id or str(uuid.uuid4()),
        defect_type=d_type,
        severity=event.severity or "MEDIUM",
        lat=event.gps.lat,
        lon=event.gps.lon,
        bus_id=event.bus_id,
        camera_id=event.camera_id,
        confidence=event.confidence,
        road_segment=seg,
        address=event.gps.address,
        frame_b64=event.frame_b64,
        timestamp_iso=now_iso,
    )

    return {
        "ok": True,
        "defect_id": defect.defect_id,
        "event_id": event.event_id,
        "status": defect.status.value,
        "priority_score": defect.priority_score,
        "number_of_buses_confirming": defect.number_of_buses_confirming,
    }


# ── Query & Filter Endpoints ─────────────────────────────────────────────────

@router.get("", summary="List road defects with multi-parameter filtering & priority scores")
async def list_defects(
    status_filter: Optional[str] = Query(None, alias="status", description="Lifecycle state filter"),
    defect_type: Optional[str] = Query(None, alias="type", description="POTHOLE, DAMAGED_ROAD, WATERLOGGING, etc."),
    cls: Optional[str] = Query(None, description="Legacy alias for defect class"),
    severity: Optional[str] = Query(None, description="LOW, MEDIUM, HIGH, SEVERE"),
    assigned_authority: Optional[str] = Query(None, description="Filter by authority (PWD, NHAI, BBMP, etc.)"),
    road_segment: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    min_priority: Optional[int] = Query(None, ge=0, le=100),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session)
):
    service = get_road_defect_service()
    filter_type = defect_type or cls

    # Query DB
    db_query = select(IngestedEvent).where(
        IngestedEvent.event_type.in_([
            'POTHOLE', 'DAMAGED_ROAD', 'WATERLOGGING',
            'MISSING_TRAFFIC_SIGN', 'MISSING_ROAD_DIVIDER',
            'MISSING_ZEBRA_CROSSING', 'DAMAGED_SIGN'
        ])
    )
    if status_filter:
        db_query = db_query.where(IngestedEvent.status == status_filter.upper())
    if filter_type:
        db_query = db_query.where(IngestedEvent.event_type == filter_type.upper())
    if severity:
        db_query = db_query.where(IngestedEvent.severity == severity.upper())
    if road_segment:
        db_query = db_query.where(IngestedEvent.road_segment == road_segment)
    if district:
        db_query = db_query.where(IngestedEvent.district == district)

    db_events = db.exec(db_query).all()
    formatted_items = []
    
    _prio_map = {"SEVERE": 88, "HIGH": 76, "MEDIUM": 55, "LOW": 35}
    for e in db_events:
        score = _prio_map.get(e.severity.upper(), 50) if e.severity else 50
        if min_priority is not None and score < min_priority:
            continue
        formatted_items.append({
            "event_id": e.event_id,
            "cls": e.event_type.lower(),
            "type": e.event_type,
            "severity": e.severity,
            "status": e.status,
            "gps": {
                "lat": e.gps_lat,
                "lon": e.gps_lon,
                "bearing_deg": e.bearing_deg,
            },
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "priority_score": score,
            "assigned_authority": None
        })

    items, total_mem = service.list_defects(
        status=status_filter,
        defect_type=filter_type,
        severity=severity,
        assigned_authority=assigned_authority,
        road_segment=road_segment,
        district=district,
        min_priority=min_priority,
        limit=limit,
        offset=offset,
    )

    for d in items:
        dump = d.model_dump()
        dump["event_id"] = d.defect_id
        dump["cls"] = d.type.lower()
        dump["gps"] = {
            "lat": d.location.lat,
            "lon": d.location.lon,
            "bearing_deg": d.location.bearing_deg,
        }
        dump["timestamp"] = d.last_detected
        formatted_items.append(dump)

    return {
        "total": len(formatted_items),
        "offset": offset,
        "limit": limit,
        "items": formatted_items[offset:offset+limit] if len(formatted_items) > limit else formatted_items,
    }


@router.get("/summary", summary="Aggregated defect counts")
async def defect_summary(db: Session = Depends(get_session)) -> RoadDefectSummary:
    service = get_road_defect_service()
    stats = service.get_lifecycle_stats()
    
    db_events = db.exec(
        select(IngestedEvent).where(
            IngestedEvent.event_type.in_([
                'POTHOLE', 'DAMAGED_ROAD', 'WATERLOGGING',
                'MISSING_TRAFFIC_SIGN', 'MISSING_ROAD_DIVIDER',
                'MISSING_ZEBRA_CROSSING', 'DAMAGED_SIGN'
            ])
        )
    ).all()
    
    total = stats["total_defects"] + len(db_events)
    by_class = dict(stats["by_type"])
    by_severity = dict(stats["by_severity"])
    by_status = dict(stats["by_status"])
    
    for e in db_events:
        cls_key = e.event_type.lower()
        by_class[cls_key] = by_class.get(cls_key, 0) + 1
        sev_key = e.severity.upper() if e.severity else "UNKNOWN"
        by_severity[sev_key] = by_severity.get(sev_key, 0) + 1
        stat_key = e.status.upper() if e.status else "UNKNOWN"
        by_status[stat_key] = by_status.get(stat_key, 0) + 1
        
    return RoadDefectSummary(
        total=total,
        by_class=by_class,
        by_severity=by_severity,
        by_status=by_status,
    )


@router.get("/stats/lifecycle", summary="Lifecycle state and priority tier analytics")
async def defect_lifecycle_stats():
    service = get_road_defect_service()
    return service.get_lifecycle_stats()


@router.get("/{defect_id}", summary="Get detailed road defect record by ID")
async def get_defect(defect_id: str):
    service = get_road_defect_service()
    defect = service.get_defect(defect_id)
    if not defect:
        raise HTTPException(status_code=404, detail=f"Defect {defect_id} not found")
    dump = defect.model_dump()
    dump["event_id"] = defect.defect_id
    dump["cls"] = defect.type.lower()
    dump["gps"] = {
        "lat": defect.location.lat,
        "lon": defect.location.lon,
        "bearing_deg": defect.location.bearing_deg,
    }
    dump["timestamp"] = defect.last_detected
    return dump


# ── Field Engineer Workflow Actions ──────────────────────────────────────────

@router.post("/{defect_id}/confirm", summary="Confirm unverified defect (Field Engineer)")
async def confirm_defect(defect_id: str, body: ConfirmDefectIn = ConfirmDefectIn()):
    service = get_road_defect_service()
    try:
        updated = service.confirm_defect(defect_id, body.engineer_id, body.notes)
        return {"ok": True, "defect_id": defect_id, "status": updated.status.value, "priority_score": updated.priority_score}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Defect {defect_id} not found")


@router.post("/{defect_id}/reject", summary="Reject / dismiss defect (Field Engineer)")
async def reject_defect(defect_id: str, body: RejectDefectIn = RejectDefectIn()):
    service = get_road_defect_service()
    try:
        updated = service.reject_defect(defect_id, body.engineer_id, body.reason)
        return {"ok": True, "defect_id": defect_id, "status": updated.status.value}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Defect {defect_id} not found")


@router.post("/{defect_id}/assign", summary="Assign authority & create maintenance ticket")
async def assign_defect(defect_id: str, body: AssignDefectIn):
    service = get_road_defect_service()
    try:
        updated = service.assign_defect(
            defect_id=defect_id,
            engineer_id=body.engineer_id,
            assigned_authority=body.assigned_authority,
            contractor=body.assigned_contractor,
            target_date=body.target_completion_date,
            notes=body.notes,
        )
        return {
            "ok": True,
            "defect_id": defect_id,
            "status": updated.status.value,
            "assigned_authority": updated.assigned_authority,
            "ticket": updated.maintenance_ticket.model_dump() if updated.maintenance_ticket else None,
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Defect {defect_id} not found")


@router.post("/{defect_id}/update", summary="Update repair progress (UNDER_REPAIR)")
async def update_repair_progress(defect_id: str, body: UpdateRepairIn):
    service = get_road_defect_service()
    try:
        updated = service.update_repair(
            defect_id=defect_id,
            engineer_id=body.engineer_id,
            progress_percent=body.progress_percent,
            notes=body.notes,
        )
        return {
            "ok": True,
            "defect_id": defect_id,
            "status": updated.status.value,
            "progress_percent": body.progress_percent,
            "ticket_status": updated.maintenance_ticket.status if updated.maintenance_ticket else None,
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Defect {defect_id} not found")


@router.post("/{defect_id}/upload-evidence", summary="Upload before/after repair evidence")
async def upload_repair_evidence(defect_id: str, body: UploadRepairEvidenceIn):
    service = get_road_defect_service()
    try:
        updated = service.upload_repair_evidence(
            defect_id=defect_id,
            engineer_id=body.engineer_id,
            after_image_b64=body.after_image_b64,
            completion_notes=body.completion_notes,
            contractor=body.contractor,
            completion_certificate_url=body.completion_certificate_url,
        )
        return {
            "ok": True,
            "defect_id": defect_id,
            "evidence_id": updated.repair_evidence.evidence_id if updated.repair_evidence else None,
            "status": updated.status.value,
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Defect {defect_id} not found")


@router.post("/{defect_id}/close", summary="Close maintenance ticket (RESOLVED)")
async def close_defect_ticket(defect_id: str, body: CloseDefectIn = CloseDefectIn()):
    service = get_road_defect_service()
    try:
        updated = service.close_ticket(
            defect_id=defect_id,
            engineer_id=body.engineer_id,
            closure_notes=body.closure_notes,
        )
        return {
            "ok": True,
            "defect_id": defect_id,
            "status": updated.status.value,
            "closed_at": updated.closed_at,
            "closed_by": updated.closed_by,
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Defect {defect_id} not found")


@router.post("/{defect_id}/simulate-redetection", summary="Simulate bus re-detection to test post-closure watchdog")
async def simulate_defect_redetection(defect_id: str, body: SimulateRedetectionIn = SimulateRedetectionIn()):
    """
    Simulates a transit bus edge sensor detecting a defect at this exact location.
    If the defect was previously RESOLVED, triggers the autonomous watchdog,
    reopening the ticket as REOPENED_UNDER_REVIEW.
    """
    service = get_road_defect_service()
    try:
        updated = service.simulate_redetection(
            defect_id=defect_id,
            bus_id=body.bus_id,
            confidence=body.confidence,
            timestamp=body.timestamp,
            notes=body.notes,
        )
        return {
            "ok": True,
            "defect_id": defect_id,
            "status": updated.status.value,
            "priority_score": updated.priority_score,
            "reopen_count": updated.reopen_count,
            "reopen_reason": updated.reopen_reason,
            "watchdog_triggered": updated.status.value == "REOPENED_UNDER_REVIEW",
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Defect {defect_id} not found")


# ── Legacy Status Updater ────────────────────────────────────────────────────

@router.patch("/{defect_id}/status", summary="Update defect event status (Legacy)")
async def update_status(defect_id: str, body: StatusUpdate):
    service = get_road_defect_service()
    try:
        st_upper = body.status.upper()
        if st_upper in ("CONFIRMED", "OPEN"):
            d = service.confirm_defect(defect_id, "OPERATOR")
        elif st_upper in ("REJECTED", "FALSE_POSITIVE"):
            d = service.reject_defect(defect_id, "OPERATOR", "Marked via status endpoint")
        elif st_upper == "RESOLVED":
            d = service.close_ticket(defect_id, "OPERATOR", "Closed via status endpoint")
        else:
            d = service._get_or_raise(defect_id)
            d.status = d.status  # preserve
        return {"ok": True, "event_id": defect_id, "defect_id": defect_id, "status": d.status.value}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Defect {defect_id} not found")
