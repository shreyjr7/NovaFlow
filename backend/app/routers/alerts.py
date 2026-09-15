"""
Alert Center API Router with WebSockets (Phase 24)
==================================================
Endpoints for real-time fleet alerting:
  - WebSocket: /api/v1/alerts/ws
  - REST: Query, create, and execute operational actions (Acknowledge, Verify, Escalate, Assign, Resolve)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..services.alert_manager import (
    AlertActionType,
    AlertCard,
    AlertSeverity,
    AlertStatus,
    get_alert_manager,
)

router = APIRouter()


class AlertActionIn(BaseModel):
    action: AlertActionType
    actor: str = Field("Dispatcher", description="Name/Role of the operating officer")
    notes: Optional[str] = Field(None, description="Operational notes or justification")
    assigned_to: Optional[str] = Field(None, description="Target team or officer for Assign action")


class CreateAlertIn(BaseModel):
    type: str
    severity: AlertSeverity
    location: str
    lat: float
    lon: float
    bus: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: str
    evidence_snapshot_url: Optional[str] = None
    road_segment: Optional[str] = None


@router.websocket("/ws")
async def alerts_websocket_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket endpoint streaming instant alert creations,
    action dispatches, and status updates to connected command center clients.
    """
    manager = get_alert_manager()
    await manager.ws_manager.connect(websocket)
    try:
        # Send initial hello & current summary
        summary = manager.get_summary()
        await websocket.send_json({
            "event": "CONNECTED",
            "message": "NovaFlow Transport Real-Time Alert Stream Established",
            "summary": summary,
        })
        while True:
            # Keep socket alive and receive client heartbeats/pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.ws_manager.disconnect(websocket)
    except Exception:
        manager.ws_manager.disconnect(websocket)


@router.get("/summary")
async def get_alerts_summary():
    """Returns high-level KPI summary of fleet alerts."""
    manager = get_alert_manager()
    return manager.get_summary()


@router.get("", response_model=List[AlertCard])
async def list_alerts(
    severity: Optional[AlertSeverity] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type keyword"),
    status: Optional[AlertStatus] = Query(None, description="Filter by status (NEW, ACKNOWLEDGED, VERIFIED, etc.)"),
    bus: Optional[str] = Query(None, description="Filter by bus ID"),
):
    """
    Returns list of fleet alerts sorted by severity and recency.
    """
    manager = get_alert_manager()
    return manager.list_alerts(
        severity=severity,
        alert_type=alert_type,
        status=status,
        bus=bus,
    )


@router.get("/{alert_id}", response_model=AlertCard)
async def get_alert_detail(alert_id: str):
    """Retrieves full details and evidentiary audit trail for an alert."""
    manager = get_alert_manager()
    alert = manager.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
    return alert


@router.post("", response_model=AlertCard)
async def create_alert(alert_in: CreateAlertIn):
    """
    Ingests a new alert from edge or backend subsystems and immediately
    broadcasts it over WebSockets to all connected dashboard dispatchers.
    """
    import uuid
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    new_card = AlertCard(
        alert_id=f"ALT-{uuid.uuid4().hex[:6].upper()}",
        type=alert_in.type,
        severity=alert_in.severity,
        location=alert_in.location,
        lat=alert_in.lat,
        lon=alert_in.lon,
        road_segment=alert_in.road_segment,
        bus=alert_in.bus,
        timestamp=now_iso,
        confidence=alert_in.confidence,
        evidence=alert_in.evidence,
        evidence_snapshot_url=alert_in.evidence_snapshot_url,
        status=AlertStatus.NEW,
    )
    manager = get_alert_manager()
    return await manager.create_alert(new_card)


@router.post("/{alert_id}/action", response_model=AlertCard)
async def execute_alert_action(alert_id: str, action_in: AlertActionIn):
    """
    Executes an operational action on an alert:
      - Acknowledge
      - Verify
      - Escalate
      - Assign (with assignee)
      - Resolve (with resolution notes)
    Broadcasts the state transition live over WebSockets.
    """
    manager = get_alert_manager()
    updated = await manager.execute_action(
        alert_id=alert_id,
        action=action_in.action,
        actor=action_in.actor,
        notes=action_in.notes,
        assigned_to=action_in.assigned_to,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
    return updated
