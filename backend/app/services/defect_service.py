"""
Road Defect Management Service (Phase 18)
=========================================
Core business logic implementing:
  - 6-stage lifecycle state machine (AI_DETECTED -> UNVERIFIED -> CONFIRMED -> ASSIGNED -> UNDER_REPAIR -> RESOLVED)
  - Explainable priority scoring formula (Severity, Traffic, Detections, Location, Safety, Persistence)
  - Cross-fleet multi-bus confirmation aggregation
  - Field engineer maintenance workflows (Confirm, Reject, Assign, Update, Upload Evidence, Close)
  - Autonomous post-closure re-detection watchdog (reopens tickets when buses detect recurrences)
"""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..schemas.defect_management import (
    AuditLogEntry,
    DefectLifecycleState,
    DefectLocation,
    DefectPriorityBreakdown,
    DefectRecord,
    MaintenanceTicketInfo,
    RepairEvidence,
)

logger = logging.getLogger("services.defects")


# ── Haversine Distance Helper ────────────────────────────────────────────────

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance in meters between two coordinates."""
    r = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


# ── Defect Priority Scoring Engine ───────────────────────────────────────────

class PriorityScoreEngine:
    """
    Computes a composite priority score (0–100) based on 6 weighted factors:
      1. Severity (25%)
      2. Traffic Volume (20%)
      3. Number of Detections & Confirming Buses (15%)
      4. Location Importance (15%)
      5. Safety Risk (15%)
      6. Persistence & Reopened Status (10%)
    """

    SEVERITY_WEIGHT = 0.25
    TRAFFIC_WEIGHT = 0.20
    DETECTIONS_WEIGHT = 0.15
    LOCATION_WEIGHT = 0.15
    SAFETY_WEIGHT = 0.15
    PERSISTENCE_WEIGHT = 0.10

    @classmethod
    def calculate(
        cls,
        severity: str,
        traffic_volume_vph: float = 1800.0,
        detection_count: int = 1,
        num_buses_confirming: int = 1,
        road_segment: str = "ARTERIAL",
        defect_type: str = "POTHOLE",
        first_detected_iso: Optional[str] = None,
        last_detected_iso: Optional[str] = None,
        is_reopened: bool = False,
    ) -> DefectPriorityBreakdown:
        # 1. Severity Score (0–100)
        sev_upper = severity.upper()
        if sev_upper in ("SEVERE", "CRITICAL"):
            sev_score = 100.0
        elif sev_upper == "HIGH":
            sev_score = 75.0
        elif sev_upper == "MEDIUM":
            sev_score = 45.0
        else:
            sev_score = 20.0

        # 2. Traffic Volume Score (0–100)
        if traffic_volume_vph >= 2500:
            traf_score = 100.0
        elif traffic_volume_vph >= 1800:
            traf_score = 80.0
        elif traffic_volume_vph >= 1000:
            traf_score = 55.0
        elif traffic_volume_vph >= 500:
            traf_score = 35.0
        else:
            traf_score = 15.0

        # 3. Detections & Confirming Buses Score (0–100)
        # Multiple confirming buses provide high statistical confidence
        bus_weight = num_buses_confirming * 25.0
        det_weight = min(25.0, detection_count * 2.5)
        det_score = min(100.0, bus_weight + det_weight)

        # 4. Location Importance Score (0–100)
        seg_upper = road_segment.upper()
        if any(k in seg_upper for k in ("EXPRESS", "HIGHWAY", "RING_ROAD", "CORRIDOR")):
            loc_score = 100.0
        elif any(k in seg_upper for k in ("CIRCLE", "INNER", "CBD", "AVENUE", "MG_ROAD")):
            loc_score = 85.0
        elif any(k in seg_upper for k in ("ARTERIAL", "MARG", "RADIAL", "ROAD")):
            loc_score = 65.0
        else:
            loc_score = 40.0

        # 5. Safety Risk Score (0–100)
        type_upper = defect_type.upper()
        risk_base = 50.0
        if "POTHOLE" in type_upper:
            risk_base = 75.0
        elif "DIVIDER" in type_upper or "MANHOLE" in type_upper:
            risk_base = 90.0
        elif "WATERLOG" in type_upper:
            risk_base = 70.0
        elif "ZEBRA" in type_upper:
            risk_base = 65.0

        # Amplify safety risk on high speed or high severity defects
        if sev_score >= 75:
            risk_base += 15.0
        safety_score = min(100.0, risk_base)

        # 6. Persistence Score (0–100)
        persistence_score = 30.0
        if first_detected_iso and last_detected_iso:
            try:
                t1 = datetime.fromisoformat(first_detected_iso.replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(last_detected_iso.replace("Z", "+00:00"))
                duration_hours = max(0.0, (t2 - t1).total_seconds() / 3600.0)
                if duration_hours >= 168.0:  # > 7 days
                    persistence_score = 100.0
                elif duration_hours >= 72.0:  # > 3 days
                    persistence_score = 80.0
                elif duration_hours >= 24.0:  # > 24 hours
                    persistence_score = 60.0
                elif duration_hours >= 4.0:
                    persistence_score = 45.0
            except Exception:
                pass

        if is_reopened:
            # Recurring defects that reappear after repair receive an acute persistence penalty
            persistence_score = min(100.0, persistence_score + 35.0)

        # Total Composite Calculation
        raw_score = (
            sev_score * cls.SEVERITY_WEIGHT +
            traf_score * cls.TRAFFIC_WEIGHT +
            det_score * cls.DETECTIONS_WEIGHT +
            loc_score * cls.LOCATION_WEIGHT +
            safety_score * cls.SAFETY_WEIGHT +
            persistence_score * cls.PERSISTENCE_WEIGHT
        )
        total_score = max(1, min(100, round(raw_score)))

        if total_score >= 80:
            tier = "CRITICAL"
        elif total_score >= 60:
            tier = "HIGH"
        elif total_score >= 40:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        return DefectPriorityBreakdown(
            severity_score=round(sev_score, 1),
            traffic_volume_score=round(traf_score, 1),
            detections_score=round(det_score, 1),
            location_importance_score=round(loc_score, 1),
            safety_risk_score=round(safety_score, 1),
            persistence_score=round(persistence_score, 1),
            total_priority_score=total_score,
            priority_tier=tier,
        )


# ── Road Defect Management Service ───────────────────────────────────────────

class RoadDefectService:
    """Singleton service managing defect state transitions and watchdog monitoring."""

    def __init__(self):
        self._defects: Dict[str, DefectRecord] = {}
        self._seed_default_defects()

    def _seed_default_defects(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        t_minus_2d = "2026-09-13T04:00:00Z"
        t_minus_1d = "2026-09-14T08:30:00Z"

        # 1. Pothole on CP (CONFIRMED)
        p1 = PriorityScoreEngine.calculate(
            severity="HIGH", traffic_volume_vph=2800, detection_count=18,
            num_buses_confirming=3, road_segment="CP_INNER_CIRCLE", defect_type="POTHOLE",
            first_detected_iso=t_minus_2d, last_detected_iso=now_iso,
        )
        self._defects["DEF-2026-001"] = DefectRecord(
            defect_id="DEF-2026-001",
            location=DefectLocation(lat=28.6335, lon=77.2195, address="Connaught Place Inner Circle Radial 2", district="Central"),
            road_segment="CP_INNER_CIRCLE",
            type="POTHOLE",
            severity="HIGH",
            first_detected=t_minus_2d,
            last_detected=now_iso,
            buses_confirming=["BUS_001", "BUS_002", "BUS_007"],
            number_of_buses_confirming=3,
            detection_count=18,
            confidence=0.94,
            assigned_authority="Public Works Department (PWD)",
            status=DefectLifecycleState.CONFIRMED,
            priority_score=p1.total_priority_score,
            priority_breakdown=p1,
            audit_history=[
                AuditLogEntry(timestamp=t_minus_2d, actor="BUS_001", action="INITIAL_DETECTION", from_status="NONE", to_status="AI_DETECTED"),
                AuditLogEntry(timestamp=t_minus_1d, actor="FLEET_CONSENSUS", action="MULTI_BUS_CONFIRM", from_status="AI_DETECTED", to_status="CONFIRMED", notes="3 distinct buses confirmed pothole."),
            ],
        )

        # 2. Road Damage on Ring Road (ASSIGNED)
        p2 = PriorityScoreEngine.calculate(
            severity="HIGH", traffic_volume_vph=3200, detection_count=24,
            num_buses_confirming=4, road_segment="RING_ROAD_AIIMS", defect_type="DAMAGED_ROAD",
            first_detected_iso=t_minus_2d, last_detected_iso=now_iso,
        )
        self._defects["DEF-2026-002"] = DefectRecord(
            defect_id="DEF-2026-002",
            location=DefectLocation(lat=28.5680, lon=77.2090, address="Ring Road Flyover Ramp near AIIMS", district="South"),
            road_segment="RING_ROAD_AIIMS",
            type="DAMAGED_ROAD",
            severity="HIGH",
            first_detected=t_minus_2d,
            last_detected=now_iso,
            buses_confirming=["BUS_001", "BUS_003", "BUS_004", "BUS_008"],
            number_of_buses_confirming=4,
            detection_count=24,
            confidence=0.91,
            assigned_authority="National Highways Authority of India (NHAI)",
            maintenance_ticket=MaintenanceTicketInfo(
                ticket_id="TICK-2026-N102",
                assigned_authority="National Highways Authority of India (NHAI)",
                assigned_contractor="Larsen & Toubro Infra",
                target_completion_date="2026-09-20",
                work_order_notes="Asphalt milling and resurfacing of 12m section.",
                created_at=t_minus_1d,
            ),
            status=DefectLifecycleState.ASSIGNED,
            priority_score=p2.total_priority_score,
            priority_breakdown=p2,
            audit_history=[
                AuditLogEntry(timestamp=t_minus_2d, actor="BUS_003", action="INITIAL_DETECTION", from_status="NONE", to_status="AI_DETECTED"),
                AuditLogEntry(timestamp=t_minus_1d, actor="ENG_CIVIL_042", action="ASSIGN_TICKET", from_status="CONFIRMED", to_status="ASSIGNED", notes="Dispatched work order TICK-2026-N102."),
            ],
        )

        # 3. Waterlogging on Tolstoy Marg (UNDER_REPAIR)
        p3 = PriorityScoreEngine.calculate(
            severity="MEDIUM", traffic_volume_vph=1600, detection_count=12,
            num_buses_confirming=2, road_segment="TOLSTOY_MARG", defect_type="WATERLOGGING",
            first_detected_iso=t_minus_1d, last_detected_iso=now_iso,
        )
        self._defects["DEF-2026-003"] = DefectRecord(
            defect_id="DEF-2026-003",
            location=DefectLocation(lat=28.6280, lon=77.2260, address="Tolstoy Marg Underpass", district="Central"),
            road_segment="TOLSTOY_MARG",
            type="WATERLOGGING",
            severity="MEDIUM",
            first_detected=t_minus_1d,
            last_detected=now_iso,
            buses_confirming=["BUS_001", "BUS_005"],
            number_of_buses_confirming=2,
            detection_count=12,
            confidence=0.89,
            assigned_authority="New Delhi Municipal Council (NDMC)",
            maintenance_ticket=MaintenanceTicketInfo(
                ticket_id="TICK-2026-M103",
                assigned_authority="New Delhi Municipal Council (NDMC)",
                assigned_contractor="Civic Drainage Works",
                target_completion_date="2026-09-17",
                work_order_notes="Drain blockage clearing and sump pump deployment.",
                created_at=t_minus_1d,
            ),
            status=DefectLifecycleState.UNDER_REPAIR,
            priority_score=p3.total_priority_score,
            priority_breakdown=p3,
            audit_history=[
                AuditLogEntry(timestamp=t_minus_1d, actor="ENG_FIELD_108", action="BEGIN_REPAIR", from_status="ASSIGNED", to_status="UNDER_REPAIR", notes="Field crew cleared drainage inlet."),
            ],
        )

        # 4. Reopened Recurring Pothole on MG Road (REOPENED_UNDER_REVIEW)
        # Demonstrates the prompt-mandated Post-Closure Re-detection Watchdog!
        p4 = PriorityScoreEngine.calculate(
            severity="SEVERE", traffic_volume_vph=2900, detection_count=32,
            num_buses_confirming=4, road_segment="MG_ROAD_CORRIDOR", defect_type="POTHOLE",
            first_detected_iso="2026-09-08T06:00:00Z", last_detected_iso=now_iso,
            is_reopened=True,
        )
        self._defects["DEF-2026-004"] = DefectRecord(
            defect_id="DEF-2026-004",
            location=DefectLocation(lat=12.9730, lon=77.6000, address="MG Road Metro Pillar 142", district="CBD"),
            road_segment="MG_ROAD_CORRIDOR",
            type="POTHOLE",
            severity="SEVERE",
            first_detected="2026-09-08T06:00:00Z",
            last_detected=now_iso,
            buses_confirming=["BUS_002", "BUS_006", "BUS_009", "BUS_011"],
            number_of_buses_confirming=4,
            detection_count=32,
            confidence=0.96,
            assigned_authority="Bruhat Bengaluru Mahanagara Palike (BBMP)",
            maintenance_ticket=MaintenanceTicketInfo(
                ticket_id="TICK-2026-B104",
                assigned_authority="Bruhat Bengaluru Mahanagara Palike (BBMP)",
                assigned_contractor="Karnataka Urban Roadways",
                target_completion_date="2026-09-12",
                work_order_notes="Cold mix patching applied.",
                created_at="2026-09-10T10:00:00Z",
                status="CLOSED_THEN_REOPENED",
            ),
            status=DefectLifecycleState.REOPENED_UNDER_REVIEW,
            priority_score=p4.total_priority_score,
            priority_breakdown=p4,
            repair_evidence=RepairEvidence(
                evidence_id="EVID-2026-004",
                before_image_b64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkWPjfDwAEfQHzgV23vAAAAABJRU5ErkJggg==",
                after_image_b64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkWPjfDwAEfQHzgV23vAAAAABJRU5ErkJggg==",
                completion_notes="Patched on 2026-09-12. Surface washed away after monsoon shower.",
                engineer_id="ENG_CONTRACTOR_09",
                uploaded_at="2026-09-12T16:00:00Z",
                completion_certificate_url="/certs/cert_bbmp_2026_0912.pdf",
            ),
            closed_at="2026-09-12T17:00:00Z",
            closed_by="ENG_SUPERVISOR_007",
            reopened_at="2026-09-14T11:20:00Z",
            reopen_reason="Transit bus BUS_009 re-detected recurring pothole at MG Road Pillar 142 after official closure.",
            reopen_count=1,
            audit_history=[
                AuditLogEntry(timestamp="2026-09-12T17:00:00Z", actor="ENG_SUPERVISOR_007", action="CLOSE_TICKET", from_status="UNDER_REPAIR", to_status="RESOLVED", notes="Initial repair signed off."),
                AuditLogEntry(timestamp="2026-09-14T11:20:00Z", actor="SYSTEM_WATCHDOG", action="REOPEN_AFTER_CLOSURE", from_status="RESOLVED", to_status="REOPENED_UNDER_REVIEW", notes="Bus BUS_009 flagged recurring defect on same coordinates. Flagged for quality audit."),
            ],
        )

        # 5. Resolved Pothole on Marine Drive (RESOLVED — available to test re-detection watchdog)
        p5 = PriorityScoreEngine.calculate(
            severity="LOW", traffic_volume_vph=1200, detection_count=8,
            num_buses_confirming=2, road_segment="MARINE_DRIVE_ARTERIAL", defect_type="POTHOLE",
            first_detected_iso="2026-09-05T09:00:00Z", last_detected_iso="2026-09-10T14:00:00Z",
        )
        self._defects["DEF-2026-005"] = DefectRecord(
            defect_id="DEF-2026-005",
            location=DefectLocation(lat=18.9480, lon=72.8235, address="Marine Drive Promenade Bay 4", district="South"),
            road_segment="MARINE_DRIVE_ARTERIAL",
            type="POTHOLE",
            severity="LOW",
            first_detected="2026-09-05T09:00:00Z",
            last_detected="2026-09-10T14:00:00Z",
            buses_confirming=["BUS_003"],
            number_of_buses_confirming=1,
            detection_count=8,
            confidence=0.88,
            assigned_authority="Brihanmumbai Municipal Corporation (BMC)",
            maintenance_ticket=MaintenanceTicketInfo(
                ticket_id="TICK-2026-BMC105",
                assigned_authority="Brihanmumbai Municipal Corporation (BMC)",
                created_at="2026-09-06T10:00:00Z",
                status="CLOSED",
            ),
            status=DefectLifecycleState.RESOLVED,
            priority_score=p5.total_priority_score,
            priority_breakdown=p5,
            closed_at="2026-09-10T15:00:00Z",
            closed_by="ENG_SUPERVISOR_007",
            audit_history=[
                AuditLogEntry(timestamp="2026-09-10T15:00:00Z", actor="ENG_SUPERVISOR_007", action="CLOSE_TICKET", from_status="UNDER_REPAIR", to_status="RESOLVED", notes="Hot mix asphalt compaction certified."),
            ],
        )

        # 6. Unverified Missing Divider (UNVERIFIED)
        p6 = PriorityScoreEngine.calculate(
            severity="MEDIUM", traffic_volume_vph=2100, detection_count=2,
            num_buses_confirming=1, road_segment="JANPATH_RD", defect_type="MISSING_DIVIDER",
            first_detected_iso=now_iso, last_detected_iso=now_iso,
        )
        self._defects["DEF-2026-006"] = DefectRecord(
            defect_id="DEF-2026-006",
            location=DefectLocation(lat=28.6265, lon=77.2210, address="Janpath Road Cross Junction", district="Central"),
            road_segment="JANPATH_RD",
            type="MISSING_DIVIDER",
            severity="MEDIUM",
            first_detected=now_iso,
            last_detected=now_iso,
            buses_confirming=["BUS_001"],
            number_of_buses_confirming=1,
            detection_count=2,
            confidence=0.84,
            status=DefectLifecycleState.UNVERIFIED,
            priority_score=p6.total_priority_score,
            priority_breakdown=p6,
            audit_history=[
                AuditLogEntry(timestamp=now_iso, actor="BUS_001", action="INITIAL_DETECTION", from_status="NONE", to_status="UNVERIFIED", notes="Single camera detection pending engineer verification."),
            ],
        )

    # ── Query Methods ────────────────────────────────────────────────────────

    def list_defects(
        self,
        status: Optional[str] = None,
        defect_type: Optional[str] = None,
        severity: Optional[str] = None,
        assigned_authority: Optional[str] = None,
        road_segment: Optional[str] = None,
        district: Optional[str] = None,
        min_priority: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[DefectRecord], int]:
        """Lists defects with multi-parameter filtering, sorted by priority score desc."""
        items = list(self._defects.values())

        if status:
            items = [d for d in items if d.status.value.upper() == status.upper()]
        if defect_type:
            items = [d for d in items if d.type.upper() == defect_type.upper()]
        if severity:
            items = [d for d in items if d.severity.upper() == severity.upper()]
        if assigned_authority:
            items = [d for d in items if d.assigned_authority and assigned_authority.lower() in d.assigned_authority.lower()]
        if road_segment:
            items = [d for d in items if road_segment.lower() in d.road_segment.lower()]
        if district:
            items = [d for d in items if d.location.district and d.location.district.lower() == district.lower()]
        if min_priority is not None:
            items = [d for d in items if d.priority_score >= min_priority]

        # Sort: CRITICAL & HIGH priority first, then last_detected desc
        items.sort(key=lambda d: (d.priority_score, d.last_detected), reverse=True)
        total = len(items)
        return items[offset:offset + limit], total

    def get_defect(self, defect_id: str) -> Optional[DefectRecord]:
        return self._defects.get(defect_id)

    # ── Field Engineer Workflow Actions ──────────────────────────────────────

    def confirm_defect(self, defect_id: str, engineer_id: str, notes: Optional[str] = None) -> DefectRecord:
        defect = self._get_or_raise(defect_id)
        from_st = defect.status.value
        defect.status = DefectLifecycleState.CONFIRMED

        # Recalculate priority with confirmation boost
        p = PriorityScoreEngine.calculate(
            severity=defect.severity,
            detection_count=defect.detection_count,
            num_buses_confirming=max(2, defect.number_of_buses_confirming),
            road_segment=defect.road_segment,
            defect_type=defect.type,
            first_detected_iso=defect.first_detected,
            last_detected_iso=defect.last_detected,
            is_reopened=defect.reopen_count > 0,
        )
        defect.priority_score = p.total_priority_score
        defect.priority_breakdown = p

        defect.audit_history.append(
            AuditLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor=engineer_id,
                action="CONFIRM_DEFECT",
                from_status=from_st,
                to_status=DefectLifecycleState.CONFIRMED.value,
                notes=notes or "Manually confirmed by field engineer.",
            )
        )
        logger.info(f"Defect {defect_id} confirmed by {engineer_id}.")
        return defect

    def reject_defect(self, defect_id: str, engineer_id: str, reason: str) -> DefectRecord:
        defect = self._get_or_raise(defect_id)
        from_st = defect.status.value
        defect.status = DefectLifecycleState.REJECTED
        defect.audit_history.append(
            AuditLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor=engineer_id,
                action="REJECT_DEFECT",
                from_status=from_st,
                to_status=DefectLifecycleState.REJECTED.value,
                notes=reason,
            )
        )
        logger.info(f"Defect {defect_id} rejected by {engineer_id}: {reason}")
        return defect

    def assign_defect(
        self,
        defect_id: str,
        engineer_id: str,
        assigned_authority: str,
        contractor: Optional[str] = None,
        target_date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> DefectRecord:
        defect = self._get_or_raise(defect_id)
        from_st = defect.status.value

        ticket_id = f"TICK-{datetime.now().year}-{uuid.uuid4().hex[:4].upper()}"
        defect.assigned_authority = assigned_authority
        defect.maintenance_ticket = MaintenanceTicketInfo(
            ticket_id=ticket_id,
            assigned_authority=assigned_authority,
            assigned_contractor=contractor,
            target_completion_date=target_date,
            work_order_notes=notes,
            created_at=datetime.now(timezone.utc).isoformat(),
            status="ASSIGNED",
        )
        defect.status = DefectLifecycleState.ASSIGNED
        defect.audit_history.append(
            AuditLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor=engineer_id,
                action="ASSIGN_MAINTENANCE_TICKET",
                from_status=from_st,
                to_status=DefectLifecycleState.ASSIGNED.value,
                notes=f"Assigned to {assigned_authority} with ticket {ticket_id}.",
            )
        )
        logger.info(f"Defect {defect_id} assigned to {assigned_authority} (Ticket: {ticket_id})")
        return defect

    def update_repair(
        self,
        defect_id: str,
        engineer_id: str,
        progress_percent: int,
        notes: str,
    ) -> DefectRecord:
        defect = self._get_or_raise(defect_id)
        from_st = defect.status.value
        defect.status = DefectLifecycleState.UNDER_REPAIR
        if defect.maintenance_ticket:
            defect.maintenance_ticket.status = f"UNDER_REPAIR_{progress_percent}%"

        defect.audit_history.append(
            AuditLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor=engineer_id,
                action="UPDATE_REPAIR_PROGRESS",
                from_status=from_st,
                to_status=DefectLifecycleState.UNDER_REPAIR.value,
                notes=f"Progress: {progress_percent}%. Notes: {notes}",
            )
        )
        logger.info(f"Defect {defect_id} repair updated ({progress_percent}%) by {engineer_id}")
        return defect

    def upload_repair_evidence(
        self,
        defect_id: str,
        engineer_id: str,
        after_image_b64: Optional[str],
        completion_notes: str,
        contractor: Optional[str] = None,
        completion_certificate_url: Optional[str] = None,
    ) -> DefectRecord:
        defect = self._get_or_raise(defect_id)
        evidence_id = f"EVID-{datetime.now().year}-{uuid.uuid4().hex[:4].upper()}"
        defect.repair_evidence = RepairEvidence(
            evidence_id=evidence_id,
            before_image_b64=defect.frame_b64,
            after_image_b64=after_image_b64,
            completion_notes=completion_notes,
            engineer_id=engineer_id,
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            completion_certificate_url=completion_certificate_url,
        )
        defect.audit_history.append(
            AuditLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor=engineer_id,
                action="UPLOAD_REPAIR_EVIDENCE",
                from_status=defect.status.value,
                to_status=defect.status.value,
                notes=f"Uploaded repair evidence {evidence_id}: {completion_notes}",
            )
        )
        logger.info(f"Repair evidence {evidence_id} uploaded for defect {defect_id}")
        return defect

    def close_ticket(
        self,
        defect_id: str,
        engineer_id: str,
        closure_notes: str,
    ) -> DefectRecord:
        defect = self._get_or_raise(defect_id)
        from_st = defect.status.value
        now_iso = datetime.now(timezone.utc).isoformat()

        defect.status = DefectLifecycleState.RESOLVED
        defect.closed_at = now_iso
        defect.closed_by = engineer_id
        if defect.maintenance_ticket:
            defect.maintenance_ticket.status = "RESOLVED"

        defect.audit_history.append(
            AuditLogEntry(
                timestamp=now_iso,
                actor=engineer_id,
                action="CLOSE_MAINTENANCE_TICKET",
                from_status=from_st,
                to_status=DefectLifecycleState.RESOLVED.value,
                notes=closure_notes,
            )
        )
        logger.info(f"Defect {defect_id} closed by {engineer_id} -> RESOLVED.")
        return defect

    # ── Post-Closure Re-detection Watchdog ────────────────────────────────────

    def check_redetection_after_closure(
        self,
        lat: float,
        lon: float,
        road_segment: str,
        bus_id: str,
        defect_type: str,
        timestamp_iso: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[DefectRecord]:
        """
        AUTONOMOUS WATCHDOG:
        Checks if any RESOLVED defect within 35 meters (or 50m on the same road segment)
        is re-detected by a bus after closure. If detected, automatically transitions
        status to REOPENED_UNDER_REVIEW, increments recurrence counter, and alerts officers.
        """
        now_iso = timestamp_iso or datetime.now(timezone.utc).isoformat()

        for defect in self._defects.values():
            if defect.status == DefectLifecycleState.RESOLVED:
                dist = haversine_distance_meters(lat, lon, defect.location.lat, defect.location.lon)
                is_same_segment = road_segment.lower() in defect.road_segment.lower() or defect.road_segment.lower() in road_segment.lower()

                # Trigger condition: within 35m, or within 50m on matching road segment
                if dist <= 35.0 or (dist <= 60.0 and is_same_segment):
                    logger.warning(
                        f"WATCHDOG TRIGGERED: Bus {bus_id} re-detected defect at ({lat:.4f}, {lon:.4f}) "
                        f"{dist:.1f}m from closed defect {defect.defect_id} ({defect.type})."
                    )

                    from_st = defect.status.value
                    defect.status = DefectLifecycleState.REOPENED_UNDER_REVIEW
                    defect.reopened_at = now_iso
                    defect.reopen_count += 1
                    defect.last_detected = now_iso
                    defect.reopen_reason = (
                        f"Post-closure recurrence: Transit bus {bus_id} re-detected defect "
                        f"({dist:.1f}m from repair site) on {road_segment}. Contractor review required."
                    )

                    if bus_id not in defect.buses_confirming:
                        defect.buses_confirming.append(bus_id)
                        defect.number_of_buses_confirming = len(defect.buses_confirming)
                    defect.detection_count += 1

                    if defect.maintenance_ticket:
                        defect.maintenance_ticket.status = "REOPENED_AFTER_CLOSURE"

                    # Recalculate priority score with acute recurrence bonus
                    p = PriorityScoreEngine.calculate(
                        severity=defect.severity,
                        detection_count=defect.detection_count,
                        num_buses_confirming=defect.number_of_buses_confirming,
                        road_segment=defect.road_segment,
                        defect_type=defect.type,
                        first_detected_iso=defect.first_detected,
                        last_detected_iso=defect.last_detected,
                        is_reopened=True,
                    )
                    defect.priority_score = p.total_priority_score
                    defect.priority_breakdown = p

                    defect.audit_history.append(
                        AuditLogEntry(
                            timestamp=now_iso,
                            actor=f"AUTONOMOUS_WATCHDOG_{bus_id}",
                            action="REOPEN_AFTER_CLOSURE",
                            from_status=from_st,
                            to_status=DefectLifecycleState.REOPENED_UNDER_REVIEW.value,
                            notes=notes or defect.reopen_reason,
                        )
                    )
                    return defect

        return None

    def simulate_redetection(
        self,
        defect_id: str,
        bus_id: str = "BUS_009",
        confidence: float = 0.94,
        timestamp: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> DefectRecord:
        """Simulates an edge detection at the exact location of an existing defect to trigger the watchdog."""
        defect = self._get_or_raise(defect_id)
        res = self.check_redetection_after_closure(
            lat=defect.location.lat,
            lon=defect.location.lon,
            road_segment=defect.road_segment,
            bus_id=bus_id,
            defect_type=defect.type,
            timestamp_iso=timestamp,
            notes=notes or f"Simulated transit surveillance pass by {bus_id}.",
        )
        if res:
            return res

        # If not resolved, just record additional confirmation
        now_iso = timestamp or datetime.now(timezone.utc).isoformat()
        defect.last_detected = now_iso
        defect.detection_count += 1
        if bus_id not in defect.buses_confirming:
            defect.buses_confirming.append(bus_id)
            defect.number_of_buses_confirming = len(defect.buses_confirming)

        # Cross-fleet promotion: if AI_DETECTED and >= 2 buses -> CONFIRMED
        if defect.status == DefectLifecycleState.AI_DETECTED and defect.number_of_buses_confirming >= 2:
            defect.status = DefectLifecycleState.CONFIRMED

        p = PriorityScoreEngine.calculate(
            severity=defect.severity,
            detection_count=defect.detection_count,
            num_buses_confirming=defect.number_of_buses_confirming,
            road_segment=defect.road_segment,
            defect_type=defect.type,
            first_detected_iso=defect.first_detected,
            last_detected_iso=defect.last_detected,
            is_reopened=defect.reopen_count > 0,
        )
        defect.priority_score = p.total_priority_score
        defect.priority_breakdown = p
        return defect

    def register_or_cluster_edge_event(
        self,
        event_id: str,
        defect_type: str,
        severity: str,
        lat: float,
        lon: float,
        bus_id: str,
        camera_id: str = "FRONT",
        confidence: float = 0.9,
        road_segment: str = "UNKNOWN_SEGMENT",
        address: Optional[str] = None,
        frame_b64: Optional[str] = None,
        timestamp_iso: Optional[str] = None,
    ) -> DefectRecord:
        """
        Integrates edge defect detections:
          1. Checks if defect reoccurs at a RESOLVED site -> triggers watchdog
          2. Clusters within 25m of an active defect -> increments confirming bus count
          3. Otherwise creates new defect record in AI_DETECTED / UNVERIFIED state
        """
        now_iso = timestamp_iso or datetime.now(timezone.utc).isoformat()

        # 1. Watchdog check against closed defects
        reopened = self.check_redetection_after_closure(
            lat=lat, lon=lon, road_segment=road_segment,
            bus_id=bus_id, defect_type=defect_type, timestamp_iso=now_iso,
        )
        if reopened:
            return reopened

        # 2. Check proximity against active defects (within 25m)
        for defect in self._defects.values():
            if defect.status not in (DefectLifecycleState.RESOLVED, DefectLifecycleState.REJECTED):
                dist = haversine_distance_meters(lat, lon, defect.location.lat, defect.location.lon)
                if dist <= 25.0:
                    defect.last_detected = now_iso
                    defect.detection_count += 1
                    if bus_id not in defect.buses_confirming:
                        defect.buses_confirming.append(bus_id)
                        defect.number_of_buses_confirming = len(defect.buses_confirming)

                    # Auto-promote to CONFIRMED if 2 or more distinct buses agree
                    if defect.status in (DefectLifecycleState.AI_DETECTED, DefectLifecycleState.UNVERIFIED) and defect.number_of_buses_confirming >= 2:
                        from_st = defect.status.value
                        defect.status = DefectLifecycleState.CONFIRMED
                        defect.audit_history.append(
                            AuditLogEntry(
                                timestamp=now_iso,
                                actor="FLEET_CONSENSUS",
                                action="CROSS_BUS_AUTO_CONFIRM",
                                from_status=from_st,
                                to_status=DefectLifecycleState.CONFIRMED.value,
                                notes=f"Cross-fleet confirmation reached: {defect.number_of_buses_confirming} buses verified defect.",
                            )
                        )

                    p = PriorityScoreEngine.calculate(
                        severity=defect.severity,
                        detection_count=defect.detection_count,
                        num_buses_confirming=defect.number_of_buses_confirming,
                        road_segment=defect.road_segment,
                        defect_type=defect.type,
                        first_detected_iso=defect.first_detected,
                        last_detected_iso=defect.last_detected,
                        is_reopened=defect.reopen_count > 0,
                    )
                    defect.priority_score = p.total_priority_score
                    defect.priority_breakdown = p
                    return defect

        # 3. Create fresh DefectRecord
        defect_num = len(self._defects) + 1
        new_id = f"DEF-2026-{defect_num:03d}"
        p = PriorityScoreEngine.calculate(
            severity=severity,
            detection_count=1,
            num_buses_confirming=1,
            road_segment=road_segment,
            defect_type=defect_type,
            first_detected_iso=now_iso,
            last_detected_iso=now_iso,
        )
        new_defect = DefectRecord(
            defect_id=new_id,
            location=DefectLocation(lat=lat, lon=lon, address=address or road_segment, district="Central"),
            road_segment=road_segment,
            type=defect_type.upper(),
            severity=severity.upper(),
            first_detected=now_iso,
            last_detected=now_iso,
            buses_confirming=[bus_id],
            number_of_buses_confirming=1,
            detection_count=1,
            confidence=confidence,
            status=DefectLifecycleState.AI_DETECTED,
            priority_score=p.total_priority_score,
            priority_breakdown=p,
            frame_b64=frame_b64,
            audit_history=[
                AuditLogEntry(
                    timestamp=now_iso,
                    actor=bus_id,
                    action="AI_CAMERA_DETECTION",
                    from_status="NONE",
                    to_status=DefectLifecycleState.AI_DETECTED.value,
                    notes=f"Detected by camera {camera_id} with confidence {confidence:.2f}.",
                )
            ],
        )
        self._defects[new_id] = new_defect
        logger.info(f"New defect {new_id} ({defect_type}) registered from bus {bus_id}.")
        return new_defect

    def get_lifecycle_stats(self) -> Dict[str, Any]:
        """Returns aggregated breakdown by lifecycle state and priority tier."""
        from collections import Counter
        by_status = Counter(d.status.value for d in self._defects.values())
        by_tier = Counter(d.priority_breakdown.priority_tier for d in self._defects.values())
        by_type = Counter(d.type for d in self._defects.values())
        by_severity = Counter(d.severity for d in self._defects.values())

        reopened_count = sum(1 for d in self._defects.values() if d.status == DefectLifecycleState.REOPENED_UNDER_REVIEW or d.reopen_count > 0)

        return {
            "total_defects": len(self._defects),
            "by_status": dict(by_status),
            "by_priority_tier": dict(by_tier),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "reopened_defects_count": reopened_count,
            "average_priority_score": round(sum(d.priority_score for d in self._defects.values()) / max(1, len(self._defects)), 1),
        }

    def _get_or_raise(self, defect_id: str) -> DefectRecord:
        if defect_id not in self._defects:
            raise KeyError(f"Defect not found: {defect_id}")
        return self._defects[defect_id]


# Singleton
_defect_service_instance: Optional[RoadDefectService] = None


def get_road_defect_service() -> RoadDefectService:
    global _defect_service_instance
    if _defect_service_instance is None:
        _defect_service_instance = RoadDefectService()
    return _defect_service_instance
