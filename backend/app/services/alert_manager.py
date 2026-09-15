"""
Alert Center Manager & Real-Time WebSocket Service (Phase 24)
=============================================================
Centralized alert dispatch service supporting:
  - Alert types: Possible Incident, Severe Congestion, Pedestrian Risk,
                 Major Waterlogging, Road Hazard, Camera Failure, Edge Device Failure
  - Severities: CRITICAL, HIGH, MEDIUM, LOW
  - Alert Card fields: Type, Severity, Location, Bus, Timestamp, Confidence, Evidence
  - Operational actions: Acknowledge, Verify, Escalate, Assign, Resolve
  - Real-time event broadcasting over WebSockets
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Dict, List, Optional
from fastapi import WebSocket
from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AlertType(str, Enum):
    POSSIBLE_INCIDENT = "Possible Incident"
    SEVERE_CONGESTION = "Severe Congestion"
    PEDESTRIAN_RISK = "Pedestrian Risk"
    MAJOR_WATERLOGGING = "Major Waterlogging"
    ROAD_HAZARD = "Road Hazard"
    CAMERA_FAILURE = "Camera Failure"
    EDGE_DEVICE_FAILURE = "Edge Device Failure"


class AlertStatus(str, Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    VERIFIED = "VERIFIED"
    ESCALATED = "ESCALATED"
    ASSIGNED = "ASSIGNED"
    RESOLVED = "RESOLVED"


class AlertActionType(str, Enum):
    ACKNOWLEDGE = "Acknowledge"
    VERIFY = "Verify"
    ESCALATE = "Escalate"
    ASSIGN = "Assign"
    RESOLVE = "Resolve"


class AuditAction(BaseModel):
    timestamp: str
    action: str
    actor: str
    notes: Optional[str] = None


class AlertCard(BaseModel):
    alert_id: str
    type: str  # e.g., "Possible Incident", "Severe Congestion", etc.
    severity: AlertSeverity
    location: str
    lat: float
    lon: float
    road_segment: Optional[str] = None
    bus: str  # e.g., "BUS-102"
    timestamp: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: str
    evidence_snapshot_url: Optional[str] = None
    evidence_video_clip: Optional[str] = None
    status: AlertStatus = AlertStatus.NEW
    assigned_to: Optional[str] = None
    audit_trail: List[AuditAction] = Field(default_factory=list)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts real-time alert events."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        payload = json.dumps(message)
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)


class AlertManager:
    """Central store and operational dispatch engine for real-time fleet alerts."""

    def __init__(self):
        self._alerts: Dict[str, AlertCard] = {}
        self.ws_manager = ConnectionManager()
        self._seed_canonical_alerts()

    def _seed_canonical_alerts(self):
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. CRITICAL: Possible Incident
        alt_1 = AlertCard(
            alert_id="ALT-2026-001",
            type=AlertType.POSSIBLE_INCIDENT.value,
            severity=AlertSeverity.CRITICAL,
            location="Ring Road AIIMS Flyover (Southbound)",
            lat=28.5672,
            lon=77.2100,
            road_segment="SEG_AIIMS_01",
            bus="BUS-102",
            timestamp=now_iso,
            confidence=0.96,
            evidence="Rolling buffer clip EV_BUF_102_987: sudden -4.5 m/s² deceleration, abrupt 24° heading deflection, and adjacent motorcycle track divergence.",
            evidence_snapshot_url="/evidence/incident_102_aiims.jpg",
            evidence_video_clip="/evidence/clips/clip_102_collision.mp4",
            status=AlertStatus.NEW,
            audit_trail=[AuditAction(timestamp=now_iso, action="CREATED", actor="Incident Anomaly Engine", notes="Compound kinematic anomaly detected")],
        )

        # 2. HIGH: Severe Congestion
        alt_2 = AlertCard(
            alert_id="ALT-2026-002",
            type=AlertType.SEVERE_CONGESTION.value,
            severity=AlertSeverity.HIGH,
            location="Vikas Marg ITO Bridge to Laxmi Nagar",
            lat=28.6295,
            lon=77.2420,
            road_segment="SEC_12_02",
            bus="BUS-117",
            timestamp=now_iso,
            confidence=0.92,
            evidence="Transit speed sustained below 5.2 km/h over 3.8 km corridor for > 20 minutes (scheduled travel time 10 min vs observed 19 min).",
            evidence_snapshot_url="/evidence/congestion_ito_bridge.jpg",
            status=AlertStatus.ACKNOWLEDGED,
            audit_trail=[
                AuditAction(timestamp=now_iso, action="CREATED", actor="Traffic Congestion Engine"),
                AuditAction(timestamp=now_iso, action="Acknowledge", actor="Dispatcher-04", notes="Notified central traffic police control room"),
            ],
        )

        # 3. CRITICAL: Pedestrian Risk
        alt_3 = AlertCard(
            alert_id="ALT-2026-003",
            type=AlertType.PEDESTRIAN_RISK.value,
            severity=AlertSeverity.CRITICAL,
            location="Model Town Road – Delhi Public School Zone",
            lat=28.7020,
            lon=77.1930,
            road_segment="SEG_SCH_01",
            bus="BUS-143",
            timestamp=now_iso,
            confidence=0.94,
            evidence="38 pedestrians detected within 2.5m roadway boundary during 13:30–14:30 dismissal window; vehicle speed recorded at 44 km/h (Limit: 25 km/h).",
            evidence_snapshot_url="/evidence/pedestrian_school_risk.jpg",
            status=AlertStatus.NEW,
            audit_trail=[AuditAction(timestamp=now_iso, action="CREATED", actor="Pedestrian Safety Engine")],
        )

        # 4. HIGH: Major Waterlogging
        alt_4 = AlertCard(
            alert_id="ALT-2026-004",
            type=AlertType.MAJOR_WATERLOGGING.value,
            severity=AlertSeverity.HIGH,
            location="Minto Bridge Underpass Connaught Place",
            lat=28.6360,
            lon=77.2250,
            road_segment="SEG_MINTO_01",
            bus="BUS-108",
            timestamp=now_iso,
            confidence=0.95,
            evidence="Acoustic sonar and optical reflection sensors indicate standing water depth of 35cm across both underpass lanes.",
            evidence_snapshot_url="/evidence/waterlogging_minto.jpg",
            status=AlertStatus.NEW,
            audit_trail=[AuditAction(timestamp=now_iso, action="CREATED", actor="Environmental Sensing Subsystem")],
        )

        # 5. MEDIUM: Road Hazard
        alt_5 = AlertCard(
            alert_id="ALT-2026-005",
            type=AlertType.ROAD_HAZARD.value,
            severity=AlertSeverity.MEDIUM,
            location="Mathura Road near Ashram Chowk Flyover Ramp",
            lat=28.5710,
            lon=77.2580,
            road_segment="SEG_ASHRAM_03",
            bus="BUS-124",
            timestamp=now_iso,
            confidence=0.89,
            evidence="Cluster of 3 sharp potholes (> 8cm depth) causing heavy lane divergence and tire puncture risk for two-wheelers.",
            evidence_snapshot_url="/evidence/hazard_ashram.jpg",
            status=AlertStatus.NEW,
            audit_trail=[AuditAction(timestamp=now_iso, action="CREATED", actor="Defect Detection Model")],
        )

        # 6. MEDIUM: Camera Failure
        alt_6 = AlertCard(
            alert_id="ALT-2026-006",
            type=AlertType.CAMERA_FAILURE.value,
            severity=AlertSeverity.MEDIUM,
            location="Aurobindo Marg near Green Park Metro",
            lat=28.5580,
            lon=77.2050,
            bus="BUS-115",
            timestamp=now_iso,
            confidence=0.98,
            evidence="Camera Cam-02 (Front Telephoto) video stream loss: 0 FPS, MIPI CSI-2 transmission error, black frame count > 150 frames.",
            status=AlertStatus.NEW,
            audit_trail=[AuditAction(timestamp=now_iso, action="CREATED", actor="Edge Hardware Watchdog")],
        )

        # 7. CRITICAL: Edge Device Failure
        alt_7 = AlertCard(
            alert_id="ALT-2026-007",
            type=AlertType.EDGE_DEVICE_FAILURE.value,
            severity=AlertSeverity.CRITICAL,
            location="Dhaula Kuan Ring Road Bypass",
            lat=28.5918,
            lon=77.1675,
            bus="BUS-131",
            timestamp=now_iso,
            confidence=0.99,
            evidence="Jetson Orin edge unit missed 4 consecutive keepalive telemetry heartbeats (> 120s timeout); local buffer status unknown.",
            status=AlertStatus.NEW,
            audit_trail=[AuditAction(timestamp=now_iso, action="CREATED", actor="Fleet Ingestion Monitor")],
        )

        for alt in [alt_1, alt_2, alt_3, alt_4, alt_5, alt_6, alt_7]:
            self._alerts[alt.alert_id] = alt

    def list_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[str] = None,
        status: Optional[AlertStatus] = None,
        bus: Optional[str] = None,
    ) -> List[AlertCard]:
        results = list(self._alerts.values())
        if severity:
            results = [a for a in results if a.severity == severity]
        if alert_type:
            results = [a for a in results if alert_type.lower() in a.type.lower()]
        if status:
            results = [a for a in results if a.status == status]
        if bus:
            results = [a for a in results if bus.lower() in a.bus.lower()]

        # Sort: CRITICAL first, then HIGH, MEDIUM, LOW; within same severity, newest first
        sev_rank = {AlertSeverity.CRITICAL: 0, AlertSeverity.HIGH: 1, AlertSeverity.MEDIUM: 2, AlertSeverity.LOW: 3}
        results.sort(key=lambda x: (sev_rank.get(x.severity, 4), x.timestamp), reverse=False)
        return results

    def get_alert(self, alert_id: str) -> Optional[AlertCard]:
        return self._alerts.get(alert_id)

    async def create_alert(self, alert_in: AlertCard) -> AlertCard:
        self._alerts[alert_in.alert_id] = alert_in
        await self.ws_manager.broadcast({
            "event": "ALERT_CREATED",
            "alert": alert_in.model_dump(),
        })
        return alert_in

    async def execute_action(
        self,
        alert_id: str,
        action: AlertActionType,
        actor: str = "Dispatcher",
        notes: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> Optional[AlertCard]:
        alert = self._alerts.get(alert_id)
        if not alert:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()

        # Map action to status
        action_status_map = {
            AlertActionType.ACKNOWLEDGE: AlertStatus.ACKNOWLEDGED,
            AlertActionType.VERIFY: AlertStatus.VERIFIED,
            AlertActionType.ESCALATE: AlertStatus.ESCALATED,
            AlertActionType.ASSIGN: AlertStatus.ASSIGNED,
            AlertActionType.RESOLVE: AlertStatus.RESOLVED,
        }

        new_status = action_status_map.get(action, alert.status)
        alert.status = new_status

        if action == AlertActionType.ASSIGN and assigned_to:
            alert.assigned_to = assigned_to

        alert.audit_trail.append(
            AuditAction(
                timestamp=now_iso,
                action=action.value,
                actor=actor,
                notes=notes or f"Action {action.value} recorded successfully.",
            )
        )

        # Broadcast update over WebSocket
        await self.ws_manager.broadcast({
            "event": "ALERT_UPDATED",
            "action": action.value,
            "alert": alert.model_dump(),
        })

        return alert

    def get_summary(self) -> Dict[str, Any]:
        alerts = list(self._alerts.values())
        total = len(alerts)
        critical = sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL)
        high = sum(1 for a in alerts if a.severity == AlertSeverity.HIGH)
        medium = sum(1 for a in alerts if a.severity == AlertSeverity.MEDIUM)
        low = sum(1 for a in alerts if a.severity == AlertSeverity.LOW)
        unresolved = sum(1 for a in alerts if a.status != AlertStatus.RESOLVED)

        by_type = {}
        for a in alerts:
            by_type[a.type] = by_type.get(a.type, 0) + 1

        return {
            "total_alerts": total,
            "unresolved_alerts": unresolved,
            "critical_count": critical,
            "high_count": high,
            "medium_count": medium,
            "low_count": low,
            "by_type": by_type,
            "active_ws_subscribers": len(self.ws_manager.active_connections),
        }


# Singleton manager
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
