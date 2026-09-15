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
