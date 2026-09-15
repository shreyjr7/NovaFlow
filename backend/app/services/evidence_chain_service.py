"""
Evidence Chain of Custody Service (Phase 27)
============================================
Cryptographic evidence management engine ensuring:
  - Generation of SHA-256 hash, Timestamp, Bus ID, Camera ID, Event ID on storage.
  - Immutable audit trail covering: Created, Accessed, Downloaded, Reviewed, Exported.
  - Integrity verification: Displays "Evidence Integrity: VERIFIED" or "Evidence Integrity: INTEGRITY CHECK FAILED".
  - Strict anti-overwrite guardrail: Prohibits silent overwriting of evidence files.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class CustodyStage(str, Enum):
    CREATED = "Created"
    ACCESSED = "Accessed"
    DOWNLOADED = "Downloaded"
    REVIEWED = "Reviewed"
    EXPORTED = "Exported"


class IntegrityStatus(str, Enum):
    VERIFIED = "VERIFIED"
    INTEGRITY_CHECK_FAILED = "INTEGRITY CHECK FAILED"


class CustodyAuditEvent(BaseModel):
    audit_id: str
    stage: CustodyStage
    timestamp: str
    actor: str
    actor_role: str
    ip_address: str
    notes: Optional[str] = None


class EvidenceRecord(BaseModel):
    evidence_id: str
    sha256_hash: str
    timestamp: str
    bus_id: str
    camera_id: str
    event_id: str
    file_name: str
    file_size_bytes: int
    binary_payload: str  # Simulated payload content for cryptographic hashing
    is_immutable: bool = True
    integrity_status: IntegrityStatus = IntegrityStatus.VERIFIED
    audit_history: List[CustodyAuditEvent] = Field(default_factory=list)


class EvidenceChainService:
    """Manages cryptographic chain of custody, tamper detection, and anti-overwrite guarantees."""

    def __init__(self):
        self._records: Dict[str, EvidenceRecord] = {}
        self._seed_canonical_evidence()

    def _seed_canonical_evidence(self):
        now_iso = datetime.now(timezone.utc).isoformat()

        # Seed Evidence Clip 1: AIIMS Flyover Collision Anomaly
        payload_1 = "VIDEO_FRAME_STREAM_AIIMS_COLLISION_BUFFER_BUS102_CAM01_TIMESTAMP_20260915"
        hash_1 = hashlib.sha256(payload_1.encode("utf-8")).hexdigest()

        rec_1 = EvidenceRecord(
            evidence_id="EV_BUF_102_987",
            sha256_hash=hash_1,
            timestamp=now_iso,
            bus_id="BUS-102",
            camera_id="CAM-102-FRONT",
            event_id="INC-2026-001",
            file_name="ev_buf_102_aiims_collision.mp4",
            file_size_bytes=14285600,  # ~14.2 MB
            binary_payload=payload_1,
            is_immutable=True,
            integrity_status=IntegrityStatus.VERIFIED,
            audit_history=[
                CustodyAuditEvent(
                    audit_id="CUST-001",
                    stage=CustodyStage.CREATED,
                    timestamp=now_iso,
                    actor="Edge Rolling Buffer Watchdog",
                    actor_role="SYSTEM",
                    ip_address="10.14.22.102",
                    notes="Clip captured on-bus and SHA-256 manifest computed.",
                ),
                CustodyAuditEvent(
                    audit_id="CUST-002",
                    stage=CustodyStage.ACCESSED,
                    timestamp=now_iso,
                    actor="Officer Miller",
                    actor_role="SAFETY_OFFICER",
                    ip_address="10.14.30.15",
                    notes="Viewed rolling buffer for collision track verification.",
                ),
                CustodyAuditEvent(
                    audit_id="CUST-003",
                    stage=CustodyStage.REVIEWED,
                    timestamp=now_iso,
                    actor="Supervisor Vance",
                    actor_role="SAFETY_OFFICER",
                    ip_address="10.14.30.18",
                    notes="Flagged as verified near-miss collision anomaly.",
                ),
            ],
        )

        # Seed Evidence Clip 2: Waterlogging Underpass
        payload_2 = "VIDEO_FRAME_STREAM_MINTO_WATERLOGGING_BUFFER_BUS108_CAM02_TIMESTAMP_20260915"
        hash_2 = hashlib.sha256(payload_2.encode("utf-8")).hexdigest()

        rec_2 = EvidenceRecord(
            evidence_id="EV_BUF_108_412",
            sha256_hash=hash_2,
            timestamp=now_iso,
            bus_id="BUS-108",
            camera_id="CAM-108-FRONT",
            event_id="INC-2026-005",
            file_name="ev_buf_108_minto_waterlogging.mp4",
            file_size_bytes=9850400,
            binary_payload=payload_2,
            is_immutable=True,
            integrity_status=IntegrityStatus.VERIFIED,
            audit_history=[
                CustodyAuditEvent(
                    audit_id="CUST-004",
                    stage=CustodyStage.CREATED,
                    timestamp=now_iso,
                    actor="Edge Waterlogging Detector",
                    actor_role="SYSTEM",
                    ip_address="10.14.22.108",
                    notes="Underpass inundation sequence preserved.",
                ),
            ],
        )

        self._records[rec_1.evidence_id] = rec_1
        self._records[rec_2.evidence_id] = rec_2

    def list_evidence(self) -> List[EvidenceRecord]:
        return list(self._records.values())

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceRecord]:
        return self._records.get(evidence_id)

    def store_evidence(
        self,
        evidence_id: str,
        bus_id: str,
        camera_id: str,
        event_id: str,
        file_name: str,
        file_size_bytes: int,
        binary_payload: str,
        actor: str = "Edge Agent",
        ip_address: str = "127.0.0.1",
    ) -> EvidenceRecord:
        """
        Stores a new incident evidence clip:
          - Generates SHA-256 hash, Timestamp, Bus ID, Camera ID, Event ID.
          - Enforces Anti-Overwrite Rule: strictly prohibits silent overwriting of existing files.
        """
        # Anti-Overwrite Guardrail
        if evidence_id in self._records:
            raise FileExistsError(
                f"IMMUTABLE_EVIDENCE_OVERWRITE_PROHIBITED: Evidence record '{evidence_id}' already exists. Silent overwrites are strictly prohibited."
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        computed_hash = hashlib.sha256(binary_payload.encode("utf-8")).hexdigest()

        record = EvidenceRecord(
            evidence_id=evidence_id,
            sha256_hash=computed_hash,
            timestamp=now_iso,
            bus_id=bus_id,
            camera_id=camera_id,
            event_id=event_id,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            binary_payload=binary_payload,
            is_immutable=True,
            integrity_status=IntegrityStatus.VERIFIED,
            audit_history=[
                CustodyAuditEvent(
                    audit_id=f"CUST-{uuid.uuid4().hex[:6].upper()}",
                    stage=CustodyStage.CREATED,
                    timestamp=now_iso,
                    actor=actor,
                    actor_role="SYSTEM",
                    ip_address=ip_address,
                    notes="Clip genesis created and immutable SHA-256 cryptographic manifest recorded.",
                )
            ],
        )
        self._records[evidence_id] = record
        return record

    def record_custody_action(
        self,
        evidence_id: str,
        stage: CustodyStage,
        actor: str,
        actor_role: str,
        notes: Optional[str] = None,
        ip_address: str = "127.0.0.1",
    ) -> Optional[EvidenceRecord]:
        """
        Records an immutable chain-of-custody audit lifecycle event:
          - Created
          - Accessed
          - Downloaded
          - Reviewed
          - Exported
        """
        rec = self._records.get(evidence_id)
        if not rec:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        audit_event = CustodyAuditEvent(
            audit_id=f"CUST-{uuid.uuid4().hex[:6].upper()}",
            stage=stage,
            timestamp=now_iso,
            actor=actor,
            actor_role=actor_role,
            ip_address=ip_address,
            notes=notes or f"Custody lifecycle stage {stage.value} recorded.",
        )
        rec.audit_history.append(audit_event)
        return rec

    def verify_integrity(self, evidence_id: str) -> Dict[str, Any]:
        """
        Cryptographic verification:
          Recomputes SHA-256 hash over binary payload and verifies against stored manifest hash.
          Returns:
            Evidence Integrity: VERIFIED
            or
            Evidence Integrity: INTEGRITY CHECK FAILED
        """
        rec = self._records.get(evidence_id)
        if not rec:
            raise KeyError(f"Evidence '{evidence_id}' not found")

        recalculated_hash = hashlib.sha256(rec.binary_payload.encode("utf-8")).hexdigest()
        is_match = (recalculated_hash == rec.sha256_hash)

        status = IntegrityStatus.VERIFIED if is_match else IntegrityStatus.INTEGRITY_CHECK_FAILED
        rec.integrity_status = status

        return {
            "evidence_id": rec.evidence_id,
            "evidence_integrity": status.value,
            "is_valid": is_match,
            "stored_hash": rec.sha256_hash,
            "computed_hash": recalculated_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "chain_of_custody_events_count": len(rec.audit_history),
        }

    def simulate_tamper(self, evidence_id: str) -> Dict[str, Any]:
        """
        Simulates malicious tampering or bit rot:
          Appends altered payload bytes to demonstrate real-time failure detection.
        """
        rec = self._records.get(evidence_id)
        if not rec:
            raise KeyError(f"Evidence '{evidence_id}' not found")

        # Tamper payload
        rec.binary_payload += "_MALICIOUS_TAMPER_PAYLOAD_BYTE_CORRUPTION"
        return self.verify_integrity(evidence_id)

    def restore_tamper(self, evidence_id: str, original_payload: str) -> Dict[str, Any]:
        """Restores original payload to demonstrate returning to VERIFIED state."""
        rec = self._records.get(evidence_id)
        if not rec:
            raise KeyError(f"Evidence '{evidence_id}' not found")

        rec.binary_payload = original_payload
        return self.verify_integrity(evidence_id)


# Singleton
_evidence_service: Optional[EvidenceChainService] = None


def get_evidence_chain_service() -> EvidenceChainService:
    global _evidence_service
    if _evidence_service is None:
        _evidence_service = EvidenceChainService()
    return _evidence_service
