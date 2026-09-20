"""
Maintenance Tickets Router & Service (Phase 11)
===============================================
Official municipal repair ticket pipeline connecting confirmed AI road detections
to PWD, BBMP, and NHAI municipal work orders.

Rules:
- Weak detection (<0.50 confidence or unconfirmed) -> No ticket created
- Confirmed low severity -> Optional / logged as observation only
- Confirmed medium/high severity -> Eligible for maintenance ticket
- Critical conditions -> High-priority ticket + immediate alert dispatch

Statuses:
- OPEN
- ACKNOWLEDGED
- ASSIGNED
- IN_PROGRESS
- RESOLVED

Spatial Deduplication:
- Deduplicates persistent hazards within a 20-meter radius.
- If multiple buses detect the same road issue, associates observations with
  the same underlying ticket rather than spawning duplicate work orders.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from ..database.session import get_session
from ..models.ai_scan_entities import MaintenanceTicket, RoadDetection

logger = logging.getLogger("novaflow.maintenance")

router = APIRouter()

VALID_STATUSES = {"OPEN", "ACKNOWLEDGED", "ASSIGNED", "IN_PROGRESS", "RESOLVED"}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance between two GPS coordinates in meters."""
    r = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2.0) ** 2 +
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def create_or_associate_ticket(
    db: Session,
    detection: RoadDetection,
    source_bus: Optional[str] = None,
    city: str = "Bengaluru",
) -> Optional[MaintenanceTicket]:
    """
    Evaluates a confirmed detection against Phase 11 rules:
    - Weak detection (< 0.50) -> returns None
    - Low severity -> returns None (logged as observation only)
    - Medium / High / Critical -> searches for existing ticket within 20m.
      If existing active ticket found: associates detection and increments observation count.
      Otherwise: creates a new MaintenanceTicket.
    """
    # 1. Rule: Weak detection -> No ticket
    if detection.confidence < 0.50 or detection.status == "DISMISSED":
        logger.debug(f"Detection {detection.id} weak ({detection.confidence:.2f}); no ticket created.")
        return None

    # 2. Rule: Confirmed low severity -> optionally record (no ticket)
    sev_upper = detection.severity.upper()
    if sev_upper == "LOW":
        logger.debug(f"Detection {detection.id} low severity; recorded as observation only.")
        return None

    # 3. Spatial deduplication check: 20-meter radius among open/active tickets
    active_statuses = ["OPEN", "ACKNOWLEDGED", "ASSIGNED", "IN_PROGRESS", "PENDING"]
    stmt = select(MaintenanceTicket).where(col(MaintenanceTicket.status).in_(active_statuses))
    existing_tickets = db.exec(stmt).all()

    bus_id = source_bus or detection.bus_id or "BUS-UNKNOWN"
    now = datetime.now(timezone.utc)

    for ticket in existing_tickets:
        dist = haversine_distance(detection.latitude, detection.longitude, ticket.latitude, ticket.longitude)
        if dist <= 20.0:
            # Match found! Associate this observation with the existing ticket
            logger.info(
                f"Associating detection {detection.id} with existing ticket {ticket.ticket_code} "
                f"(distance: {dist:.1f}m, bus: {bus_id})"
            )
            ticket.observation_count = getattr(ticket, "observation_count", 1) + 1
            if bus_id and bus_id not in (ticket.source_bus or ""):
                ticket.source_bus = f"{ticket.source_bus}, {bus_id}" if ticket.source_bus else bus_id
            additional_note = f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] Confirmed by bus {bus_id} (conf {detection.confidence:.2f})"
            ticket.field_notes = (ticket.field_notes or "") + additional_note
            ticket.updated_at = now

            # If new detection is CRITICAL and ticket was only MEDIUM, upgrade ticket
            if sev_upper == "CRITICAL" and ticket.severity != "CRITICAL":
                ticket.severity = "CRITICAL"
                ticket.priority = "P1"

            # Update detection linkage
            detection.ticket_id = ticket.ticket_code
            detection.status = "TICKET_CREATED"

            db.add(ticket)
            db.add(detection)
            db.commit()
            db.refresh(ticket)
            return ticket

    # 4. No matching ticket found within 20m: Create a new ticket
    ticket_code = f"WO-{city[:3].upper()}-{now.year}-{int(now.timestamp()) % 10000:04d}"
    priority = "P1" if sev_upper == "CRITICAL" else ("P2" if sev_upper == "HIGH" else "P3")
    evidence_url = detection.annotated_evidence_path or detection.evidence_path or ""

    agency_map = {
        "POTHOLE": "BBMP Road Infrastructure & Rapid Pothole Cell",
        "ROAD_DAMAGE": "NHAI Road Works & Asphalt Maintenance",
        "ROAD_CRACK": "City Municipal Works Department",
        "WATERLOGGING": "Stormwater Drainage & Emergency De-silting",
        "DEBRIS": "Municipal Road Cleansing & Hazard Team",
        "MISSING_SIGN": "Traffic Transit Signage Division",
        "DAMAGED_ZEBRA_CROSSING": "Pedestrian Safety & Road Markings Bay",
    }
    agency = agency_map.get(detection.type.upper(), "Municipal Public Works Department")

    new_ticket = MaintenanceTicket(
        ticket_code=ticket_code,
        detection_id=detection.id,
        hazard_type=detection.type,
        title=f"Repair Work Order: {detection.type.replace('_', ' ').title()}",
        location_description=f"Auto-generated via NovaFlow Edge Vision from {bus_id} at ({detection.latitude:.5f}, {detection.longitude:.5f})",
        latitude=detection.latitude,
        longitude=detection.longitude,
        city=city,
        severity=sev_upper,
        priority=priority,
        agency=agency,
        status="OPEN",
        evidence=evidence_url,
        source_bus=bus_id,
        observation_count=1,
        field_notes=f"Initial AI detection by bus {bus_id} (confidence: {detection.confidence:.2f}).",
        target_sla_hours=12 if sev_upper == "CRITICAL" else (24 if sev_upper == "HIGH" else 48),
        created_at=now,
        updated_at=now,
    )

    detection.ticket_id = ticket_code
    detection.status = "TICKET_CREATED"

    db.add(new_ticket)
    db.add(detection)
    db.commit()
    db.refresh(new_ticket)

    logger.info(f"Created new maintenance ticket {ticket_code} for detection {detection.id} ({sev_upper})")
    return new_ticket


# ── REST API ENDPOINTS ───────────────────────────────────────────────────────

class TicketCreateRequest(BaseModel):
    detection_id: Optional[str] = None
    issue_type: str = Field(..., description="POTHOLE, ROAD_DAMAGE, WATERLOGGING, etc.")
    severity: str = Field("MEDIUM", description="LOW, MEDIUM, HIGH, CRITICAL")
    latitude: float
    longitude: float
    evidence: Optional[str] = None
    source_bus: Optional[str] = "BUS-001"
    city: Optional[str] = "Bengaluru"
    title: Optional[str] = None
    notes: Optional[str] = None


class TicketStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="OPEN, ACKNOWLEDGED, ASSIGNED, IN_PROGRESS, RESOLVED")
    notes: Optional[str] = None
    assigned_crew: Optional[str] = None
    assigned_contractor: Optional[str] = None


@router.get("/tickets", summary="List all maintenance work orders and tickets")
async def list_tickets(
    status: Optional[str] = Query(None, description="Filter: OPEN, ACKNOWLEDGED, ASSIGNED, IN_PROGRESS, RESOLVED"),
    severity: Optional[str] = Query(None, description="Filter: CRITICAL, HIGH, MEDIUM, LOW"),
    source_bus: Optional[str] = Query(None, description="Filter by reporting bus"),
    city: Optional[str] = Query(None, description="Filter by city"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_session),
) -> List[Dict[str, Any]]:
    """Retrieves maintenance tickets with optional status, severity, and bus filters."""
    query = select(MaintenanceTicket).order_by(MaintenanceTicket.created_at.desc())

    if status:
        query = query.where(MaintenanceTicket.status == status.upper())
    if severity:
        query = query.where(MaintenanceTicket.severity == severity.upper())
    if source_bus:
        query = query.where(MaintenanceTicket.source_bus == source_bus)
    if city:
        query = query.where(MaintenanceTicket.city == city)

    results = db.exec(query.limit(limit)).all()
    return [t.to_dict() for t in results]


@router.get("/tickets/{ticket_id}", summary="Get maintenance ticket details")
async def get_ticket(ticket_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    """Retrieves a single maintenance ticket by ticket_id or ticket_code."""
    stmt = select(MaintenanceTicket).where(
        (MaintenanceTicket.ticket_code == ticket_id) | (MaintenanceTicket.id == ticket_id)
    )
    ticket = db.exec(stmt).first()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found")
    return ticket.to_dict()


@router.post("/tickets", summary="Create or associate a maintenance ticket")
async def create_ticket(
    req: TicketCreateRequest,
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    Creates a new maintenance ticket or associates with an existing ticket within 20m.
    Enforces Phase 11 deduplication and validation rules.
    """
    clean_uuid = None
    if req.detection_id:
        try:
            clean_uuid = UUID(req.detection_id)
        except Exception:
            clean_uuid = None

    detection = None
    if clean_uuid:
        detection = db.get(RoadDetection, clean_uuid)

    if detection:
        ticket = create_or_associate_ticket(
            db=db,
            detection=detection,
            source_bus=req.source_bus,
            city=req.city or "Bengaluru",
        )
        if not ticket:
            return {
                "ticket_created": False,
                "reason": "Detection did not meet ticket severity/confidence thresholds",
                "detection_id": str(detection.id),
            }
        return {"ticket_created": True, "ticket": ticket.to_dict()}

    # Manual ticket creation if no detection record provided
    # Perform spatial deduplication
    active_statuses = ["OPEN", "ACKNOWLEDGED", "ASSIGNED", "IN_PROGRESS"]
    stmt = select(MaintenanceTicket).where(col(MaintenanceTicket.status).in_(active_statuses))
    existing_tickets = db.exec(stmt).all()

    now = datetime.now(timezone.utc)
    for t in existing_tickets:
        if haversine_distance(req.latitude, req.longitude, t.latitude, t.longitude) <= 20.0:
            t.observation_count = getattr(t, "observation_count", 1) + 1
            if req.notes:
                t.field_notes = (t.field_notes or "") + f"\n[{now.strftime('%H:%M:%S')}] {req.notes}"
            db.add(t)
            db.commit()
            db.refresh(t)
            return {"ticket_created": False, "associated_with_existing": True, "ticket": t.to_dict()}

    ticket_code = f"WO-{(req.city or 'BLR')[:3].upper()}-{now.year}-{int(now.timestamp()) % 10000:04d}"
    sev = req.severity.upper()
    priority = "P1" if sev == "CRITICAL" else ("P2" if sev == "HIGH" else "P3")

    new_t = MaintenanceTicket(
        ticket_code=ticket_code,
        hazard_type=req.issue_type,
        title=req.title or f"Manual Work Order: {req.issue_type}",
        location_description=req.notes or f"Manual dispatch near ({req.latitude:.4f}, {req.longitude:.4f})",
        latitude=req.latitude,
        longitude=req.longitude,
        city=req.city or "Bengaluru",
        severity=sev,
        priority=priority,
        agency="BBMP Road Infrastructure Division",
        status="OPEN",
        evidence=req.evidence,
        source_bus=req.source_bus or "MANUAL",
        observation_count=1,
        field_notes=req.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(new_t)
    db.commit()
    db.refresh(new_t)
    return {"ticket_created": True, "ticket": new_t.to_dict()}


@router.patch("/tickets/{ticket_id}/status", summary="Update maintenance ticket status")
async def update_ticket_status(
    ticket_id: str,
    req: TicketStatusUpdateRequest,
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """Transitions ticket status: OPEN -> ACKNOWLEDGED -> ASSIGNED -> IN_PROGRESS -> RESOLVED."""
    status_upper = req.status.upper()
    if status_upper not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{req.status}'. Must be one of: {sorted(list(VALID_STATUSES))}",
        )

    stmt = select(MaintenanceTicket).where(
        (MaintenanceTicket.ticket_code == ticket_id) | (MaintenanceTicket.id == ticket_id)
    )
    ticket = db.exec(stmt).first()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found")

    old_status = ticket.status
    ticket.status = status_upper
    ticket.updated_at = datetime.now(timezone.utc)

    if req.assigned_crew:
        ticket.assigned_crew = req.assigned_crew
    if req.assigned_contractor:
        ticket.assigned_contractor = req.assigned_contractor
    if req.notes:
        ticket.field_notes = (ticket.field_notes or "") + f"\n[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {req.notes}"

    if status_upper == "RESOLVED":
        ticket.resolved_at = datetime.now(timezone.utc)

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    logger.info(f"Ticket {ticket.ticket_code} status transitioned from {old_status} to {status_upper}")
    return {"ok": True, "ticket": ticket.to_dict()}
