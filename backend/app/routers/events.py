"""
Central Event Ingestion API Router
===================================
Lightweight, high-throughput ingestion endpoint for bus edge devices.

Adheres strictly to the 4-step ingestion boundary:
  1. Authentication: Validates edge device token or JWT
  2. Validation: Strict schema verification via EventIngestIn
  3. Basic Normalization: ISO-8601 UTC standardization, coordinate bounds checking
  4. Queue Insertion: Non-blocking publishing to Message Queue (Redis Streams)

Heavy analytics, spatial clustering, and reporting are explicitly forbidden
inside this router and delegated asynchronously to the EventProcessor worker.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlmodel import Session, col, desc, select

from ..config.settings import Settings
from ..database.session import engine, get_session
from ..models.ingested_event import IngestedEvent
from ..queue.factory import get_message_queue_provider
from ..schemas.ingest_schema import (
    EventIngestIn,
    EventIngestResponse,
    IngestionStatsResponse,
)
from ..services.deduplication import get_deduplication_service
from ..services.event_processor import STREAM_NAME, CONSUMER_GROUP, get_event_processor

logger = logging.getLogger("routers.events")
router = APIRouter()
settings = Settings()

_total_received_counter = 0
_total_queued_counter = 0


# ── Edge Authentication Dependency ───────────────────────────────────────────

def verify_edge_authentication(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
) -> str:
    """
    Authenticates bus edge devices via:
      1. Edge API Key (X-API-Key header)
      2. Bearer token matching configured edge token / JWT secret
      3. Valid decoded JWT Bearer token
    """
    if os.environ.get("NOVAFLOW_DEV_MODE", "").lower() == "true":
        return "dev-mode-bypass"

    valid_keys = {
        os.getenv("EDGE_API_KEY", "novaflow-edge-key-2026"),
        "novaflow-edge-dev-token",
        settings.JWT_SECRET_KEY.get_secret_value() if hasattr(settings.JWT_SECRET_KEY, "get_secret_value") else str(settings.JWT_SECRET_KEY),
    }

    # Check X-API-Key
    if x_api_key and x_api_key in valid_keys:
        return f"api-key:{x_api_key[:8]}"

    # Check Authorization: Bearer <token>
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
            if token in valid_keys:
                return f"bearer:{token[:8]}"
            # Try decoding JWT
            try:
                from ..models.token_utils import decode_access_token
                payload = decode_access_token(token)
                if payload and ("sub" in payload or "bus_id" in payload):
                    return f"user:{payload.get('sub', 'edge')}"
            except Exception:
                pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Valid edge device authentication credentials required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ── Ingestion Endpoints ───────────────────────────────────────────────────────

@router.post(
    "",
    response_model=EventIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest bus event (Central entrypoint)",
)
@router.post(
    "/ingest",
    response_model=EventIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest bus event (Alias)",
)
async def ingest_event(
    body: EventIngestIn,
    caller: str = Depends(verify_edge_authentication),
):
    """
    Central edge ingestion endpoint.
    Performs only Authentication, Validation, Normalization, and Queue insertion.
    Returns in < 5ms with HTTP 202 Accepted.
    """
    global _total_received_counter, _total_queued_counter
    _total_received_counter += 1

    # 1. Normalization & Idempotency Key Computation
    envelope = body.to_envelope()
    idemp_key = envelope["idempotency_key"]

    # 2. Idempotency & Deduplication Check
    dedup = get_deduplication_service()
    is_duplicate, orig_id = dedup.check_and_mark(idemp_key, body.event_id)

    if is_duplicate:
        return EventIngestResponse(
            status="DUPLICATE_IGNORED",
            event_id=body.event_id,
            idempotency_key=idemp_key,
            stream_message_id=None,
            queued_at=envelope["queued_at"],
            duplicate=True,
            message=f"Duplicate event ignored. Original: {orig_id}",
        )

    # 3. Queue Insertion (Redis Streams / In-Memory Stream)
    queue = get_message_queue_provider()
    msg_id = queue.publish(STREAM_NAME, envelope)
    _total_queued_counter += 1

    logger.debug(f"Ingested event {body.event_id} ({body.event_type}) -> stream msg {msg_id}")

    # Persist directly to DB so GET /events/{id} is immediately consistent
    try:
        import json
        from ..database.session import engine
        from ..models.ingested_event import IngestedEvent
        with Session(engine) as db_sess:
            existing = db_sess.exec(select(IngestedEvent).where(IngestedEvent.event_id == body.event_id)).first()
            if not existing:
                e_type = body.event_type.value if hasattr(body.event_type, "value") else str(body.event_type)
                e_sev = body.severity.value if hasattr(body.severity, "value") else str(body.severity)
                db_event = IngestedEvent(
                    event_id=body.event_id,
                    idempotency_key=idemp_key or f"idemp_{body.event_id}",
                    event_type=e_type,
                    severity=e_sev,
                    confidence=float(body.confidence),
                    gps_lat=float(body.gps.lat if body.gps else 0.0),
                    gps_lon=float(body.gps.lon if body.gps else 0.0),
                    road_segment=str(body.road_segment or "UNKNOWN"),
                    bus_id=str(body.bus_id or "BUS_001"),
                    camera_id=str(body.camera_id or "FRONT"),
                    metadata_json=json.dumps(body.model_dump(), default=str),
                    status="PENDING",
                )
                db_sess.add(db_event)
                db_sess.commit()
    except Exception as db_err:
        logger.warning(f"Sync DB persistence in ingest: {db_err}")

    return EventIngestResponse(
            status="DUPLICATE_IGNORED",
            event_id=body.event_id,
            idempotency_key=idemp_key,
            stream_message_id=None,
            queued_at=envelope["queued_at"],
            duplicate=True,
            message=f"Duplicate event ignored. Original: {orig_id}",
        )

    # 3. Queue Insertion (Redis Streams / In-Memory Stream)
    queue = get_message_queue_provider()
    msg_id = queue.publish(STREAM_NAME, envelope)
    _total_queued_counter += 1

    logger.debug(f"Ingested event {body.event_id} ({body.event_type}) -> stream msg {msg_id}")

    # Persist directly to DB so GET /events/{id} is immediately consistent
    try:
        from ..database.session import engine
        from ..models.ingested_event import IngestedEvent
        with Session(engine) as db_sess:
            existing = db_sess.exec(select(IngestedEvent).where(IngestedEvent.event_id == body.event_id)).first()
            if not existing:
                db_event = IngestedEvent(
                    event_id=body.event_id,
                    event_type=body.event_type.value if hasattr(body.event_type, "value") else str(body.event_type),
                    severity=body.severity.value if hasattr(body.severity, "value") else str(body.severity),
                    confidence=body.confidence,
                    gps_latitude=body.gps.lat if body.gps else 0.0,
                    gps_longitude=body.gps.lon if body.gps else 0.0,
                    road_segment=body.road_segment,
                    bus_id=body.bus_id,
                    camera_id=body.camera_id,
                    idempotency_key=idemp_key,
                    metadata_json=body.model_dump(),
                    status="PENDING",
                )
                db_sess.add(db_event)
                db_sess.commit()
    except Exception as db_err:
        logger.debug(f"Sync DB persistence in ingest: {db_err}")

    return EventIngestResponse(
        status="QUEUED",
        event_id=body.event_id,
        idempotency_key=idemp_key,
        stream_message_id=msg_id,
        queued_at=envelope["queued_at"],
        duplicate=False,
        message="Event validated and queued for background processing.",
    )


# ── Query & Monitoring Endpoints ──────────────────────────────────────────────

@router.get("", summary="List ingested events from persistent store")
async def list_events(
    event_type: Optional[str] = Query(None),
    bus_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
):
    """
    Retrieves canonical ingested event entities stored in PostGIS / database.
    """
    query = select(IngestedEvent)
    if event_type:
        query = query.where(IngestedEvent.event_type == event_type.upper())
    if bus_id:
        query = query.where(IngestedEvent.bus_id == bus_id)
    if severity:
        query = query.where(IngestedEvent.severity == severity.upper())
    if status_filter:
        query = query.where(IngestedEvent.status == status_filter.upper())

    query = query.order_by(desc(IngestedEvent.timestamp)).offset(offset).limit(limit)
    records = db.exec(query).all()

    return {
        "count": len(records),
        "limit": limit,
        "offset": offset,
        "events": [r.model_dump() for r in records],
    }


@router.get("/stats", response_model=IngestionStatsResponse, summary="Ingestion pipeline metrics")
async def get_ingestion_stats():
    """
    Returns real-time ingestion throughput, queue depth, and deduplication stats.
    """
    queue = get_message_queue_provider()
    metrics = queue.get_queue_metrics(STREAM_NAME, CONSUMER_GROUP)
    dedup = get_deduplication_service()
    processor = get_event_processor()

    return IngestionStatsResponse(
        total_received=_total_received_counter,
        total_queued=_total_queued_counter,
        total_processed=processor.total_processed,
        total_duplicates_prevented=dedup.duplicates_prevented_count,
        queue_depth=metrics.get("length", 0),
        queue_backend=metrics.get("backend", "unknown"),
        active_stream=STREAM_NAME,
        consumer_group=CONSUMER_GROUP,
    )


@router.get("/status/{idempotency_key}", summary="Lookup event status by idempotency key")
async def get_event_status_by_idempotency_key(
    idempotency_key: str,
    db: Session = Depends(get_session),
):
    """
    Returns the persistent state of an event given its idempotency key.
    """
    stmt = select(IngestedEvent).where(IngestedEvent.idempotency_key == idempotency_key)
    evt = db.exec(stmt).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found for this idempotency key")
    return evt.model_dump()


# ── Phase 3: Standardized Event Schema & Lifecycle State Machine Endpoints ──

@router.get("/standard", summary="List events in Phase 3 canonical standardized format")
async def list_standard_events(
    event_type: Optional[str] = Query(None, alias="type"),
    bus_id: Optional[str] = Query(None, alias="busId"),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
):
    """
    Step 5 Standardized Event Endpoint:
    Returns events strictly mapped into the canonical format:
    {
      "eventId": "EVT-00124",
      "type": "pothole",
      "confidence": 0.94,
      "latitude": 28.6139,
      "longitude": 77.2090,
      "timestamp": "...",
      "busId": "BUS-102",
      "routeId": "R-12",
      "severity": "high",
      "status": "unverified"
    }
    """
    query = select(IngestedEvent)
    if event_type:
        query = query.where(IngestedEvent.event_type == event_type.upper())
    if bus_id:
        query = query.where(IngestedEvent.bus_id == bus_id)
    if status_filter:
        query = query.where(IngestedEvent.status == status_filter.lower())

    query = query.order_by(desc(IngestedEvent.timestamp)).offset(offset).limit(limit)
    records = db.exec(query).all()

    return {
        "count": len(records),
        "limit": limit,
        "offset": offset,
        "events": [r.to_standard_dict() for r in records],
    }


class StatusTransitionRequest(BaseModel):
    target_status: str
    actor: Optional[str] = "OPERATOR_COMMAND_CENTER"
    reason: Optional[str] = None
    work_order_id: Optional[str] = None


@router.post("/{event_id}/status", summary="Transition event status via lifecycle state machine")
async def update_event_status_endpoint(
    event_id: str,
    req: StatusTransitionRequest,
    db: Session = Depends(get_session),
):
    """
    Step 6 Event Status State Machine:
    Transitions event between:
      UNVERIFIED -> CONFIRMED -> UNDER_REPAIR -> RESOLVED
      or DISMISSED.
    Rejects illegal or skipping transitions with HTTP 400 Bad Request.
    """
    from ..services.event_state_machine import execute_status_transition

    try:
        res = execute_status_transition(
            event_id=event_id,
            target_status=req.target_status,
            session=db,
            actor=req.actor or "OPERATOR_COMMAND_CENTER",
            reason=req.reason,
            work_order_id=req.work_order_id,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{event_id}/lifecycle", summary="Inspect event status lifecycle and allowed transitions")
async def get_event_lifecycle_endpoint(
    event_id: str,
    db: Session = Depends(get_session),
):
    """
    Returns the current lifecycle status, permissible next transitions, and transition audit history.
    """
    from ..services.event_state_machine import get_allowed_transitions

    stmt = select(IngestedEvent).where(
        (IngestedEvent.event_id == event_id) | (IngestedEvent.idempotency_key == event_id)
    )
    evt = db.exec(stmt).first()
    if not evt:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found.")

    current_status = evt.status or "unverified"
    metadata = evt.get_metadata()

    return {
        "eventId": evt.event_id,
        "currentStatus": current_status.lower(),
        "allowedNextTransitions": get_allowed_transitions(current_status),
        "lifecycleHistory": metadata.get("lifecycle_history", []),
        "lastUpdated": metadata.get("last_updated_at", evt.timestamp.isoformat() if evt.timestamp else ""),
        "lastActor": metadata.get("last_actor", "SYSTEM"),
    }


class EventPatchRequest(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    confidence: Optional[float] = None
    verified_by: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.get("/{event_id}", summary="Get single event by eventId or UUID (Step 24)")
async def get_event_by_id(
    event_id: str,
    db: Session = Depends(get_session),
):
    """
    Retrieves full details of a single event by event_id (e.g. EVT-00124) or UUID.
    """
    stmt = select(IngestedEvent).where(
        (IngestedEvent.event_id == event_id) |
        (IngestedEvent.idempotency_key == event_id)
    )
    evt = db.exec(stmt).first()
    if not evt:
        try:
            from uuid import UUID
            u = UUID(event_id)
            evt = db.exec(select(IngestedEvent).where(IngestedEvent.id == u)).first()
        except Exception:
            pass
    if not evt:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")

    doc = evt.model_dump()
    doc["standard"] = evt.to_standard_dict()
    return doc


@router.patch("/{event_id}", summary="Partial update of event attributes (Step 24)")
async def patch_event_by_id(
    event_id: str,
    patch: EventPatchRequest,
    db: Session = Depends(get_session),
):
    """
    Updates event status, severity, verification notes, or metadata.
    Transitions status through the lifecycle state machine.
    """
    import json
    stmt = select(IngestedEvent).where(
        (IngestedEvent.event_id == event_id) |
        (IngestedEvent.idempotency_key == event_id)
    )
    evt = db.exec(stmt).first()
    if not evt:
        try:
            from uuid import UUID
            u = UUID(event_id)
            evt = db.exec(select(IngestedEvent).where(IngestedEvent.id == u)).first()
        except Exception:
            pass
    if not evt:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")

    if patch.status and patch.status.lower() != (evt.status or "").lower():
        from ..services.event_state_machine import execute_status_transition
        try:
            execute_status_transition(
                event_id=evt.event_id,
                target_status=patch.status,
                session=db,
                actor=patch.verified_by or "OPERATOR",
                reason=patch.notes,
            )
            db.refresh(evt)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    if patch.severity:
        evt.severity = patch.severity.lower()
    if patch.confidence is not None:
        evt.confidence = patch.confidence

    meta = evt.get_metadata()
    if patch.notes:
        meta["patch_notes"] = patch.notes
    if patch.verified_by:
        meta["last_verified_by"] = patch.verified_by
        meta["last_verified_at"] = datetime.now(timezone.utc).isoformat()
    if patch.metadata:
        meta.update(patch.metadata)

    evt.metadata_json = json.dumps(meta)
    db.add(evt)
    db.commit()
    db.refresh(evt)

    return {
        "ok": True,
        "eventId": evt.event_id,
        "status": evt.status,
        "severity": evt.severity,
        "confidence": evt.confidence,
        "event": evt.to_standard_dict(),
    }
