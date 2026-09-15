"""
Evidence Chain of Custody API Router (Phase 27)
================================================
Endpoints for cryptographic evidence management:
  - Generation of SHA-256 hash, Timestamp, Bus ID, Camera ID, Event ID on store.
  - Immutable audit history: Created, Accessed, Downloaded, Reviewed, Exported.
  - Integrity verification: Returns "Evidence Integrity: VERIFIED" or "Evidence Integrity: INTEGRITY CHECK FAILED".
  - Anti-overwrite guarantee: HTTP 409 Conflict if attempting to overwrite existing evidence files.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ..services.evidence_chain_service import (
    CustodyAuditEvent,
    CustodyStage,
    EvidenceRecord,
    IntegrityStatus,
    get_evidence_chain_service,
)

router = APIRouter()


class StoreEvidenceIn(BaseModel):
    evidence_id: str = Field(..., description="Unique immutable evidence clip ID")
    bus_id: str = Field(..., description="Originating bus ID")
    camera_id: str = Field(..., description="Originating camera ID")
    event_id: str = Field(..., description="Associated incident / anomaly ID")
    file_name: str = Field(..., description="Evidence video clip file name")
    file_size_bytes: int = Field(..., description="Size in bytes")
    binary_payload: str = Field(..., description="Raw binary/base64 payload content for cryptographic hashing")


class RecordCustodyActionIn(BaseModel):
    stage: CustodyStage
    actor: str = Field("Officer Miller", description="Name/ID of operating actor")
    actor_role: str = Field("SAFETY_OFFICER", description="Role of the actor")
    notes: Optional[str] = Field(None, description="Operational justification or export recipient")


@router.get("", response_model=List[EvidenceRecord])
async def list_all_evidence():
    """Lists all stored incident evidence records with cryptographic manifests."""
    service = get_evidence_chain_service()
    return service.list_evidence()


@router.get("/{evidence_id}", response_model=EvidenceRecord)
async def get_evidence_record(evidence_id: str):
    """Retrieves full manifest and complete chain-of-custody audit history for an evidence file."""
    service = get_evidence_chain_service()
    rec = service.get_evidence(evidence_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Evidence record '{evidence_id}' not found")
    return rec


@router.post("", response_model=EvidenceRecord, status_code=status.HTTP_201_CREATED)
async def store_incident_evidence(body: StoreEvidenceIn, request: Request):
    """
    Stores an incident clip and computes its immutable cryptographic manifest:
      - Generates: SHA-256 hash, Timestamp, Bus ID, Camera ID, Event ID.
      - Records genesis audit stage: 'Created'.
      - Strict Anti-Overwrite Rule: Returns HTTP 409 Conflict if file already exists.
    """
    service = get_evidence_chain_service()
    client_ip = request.client.host if request.client else "127.0.0.1"

    try:
        return service.store_evidence(
            evidence_id=body.evidence_id,
            bus_id=body.bus_id,
            camera_id=body.camera_id,
            event_id=body.event_id,
            file_name=body.file_name,
            file_size_bytes=body.file_size_bytes,
            binary_payload=body.binary_payload,
            actor="Edge Video Buffer Engine",
            ip_address=client_ip,
        )
    except FileExistsError as exc:
        # Anti-Overwrite Guardrail
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.post("/{evidence_id}/custody-action", response_model=EvidenceRecord)
async def record_evidence_custody_action(evidence_id: str, body: RecordCustodyActionIn, request: Request):
    """
    Records an immutable chain-of-custody lifecycle audit stage:
      - Created, Accessed, Downloaded, Reviewed, Exported.
    """
    service = get_evidence_chain_service()
    client_ip = request.client.host if request.client else "127.0.0.1"

    updated = service.record_custody_action(
        evidence_id=evidence_id,
        stage=body.stage,
        actor=body.actor,
        actor_role=body.actor_role,
        notes=body.notes,
        ip_address=client_ip,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Evidence record '{evidence_id}' not found")
    return updated


@router.get("/{evidence_id}/verify-integrity")
async def verify_evidence_integrity(evidence_id: str):
    """
    Cryptographically verifies evidence integrity by re-hashing binary payload:
      Returns:
        Evidence Integrity: VERIFIED
        or
        Evidence Integrity: INTEGRITY CHECK FAILED
    """
    service = get_evidence_chain_service()
    try:
        return service.verify_integrity(evidence_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Evidence record '{evidence_id}' not found")


@router.post("/{evidence_id}/simulate-tamper")
async def simulate_evidence_tampering(evidence_id: str):
    """
    Simulates malicious payload alteration or bit-rot:
      Demonstrates that altering even a single byte triggers 'Evidence Integrity: INTEGRITY CHECK FAILED'.
    """
    service = get_evidence_chain_service()
    try:
        return service.simulate_tamper(evidence_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Evidence record '{evidence_id}' not found")


@router.post("/{evidence_id}/restore-tamper")
async def restore_evidence_integrity(evidence_id: str, payload_in: Dict[str, str]):
    """Restores original payload and re-verifies integrity back to VERIFIED."""
    service = get_evidence_chain_service()
    try:
        return service.restore_tamper(evidence_id, payload_in.get("original_payload", ""))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Evidence record '{evidence_id}' not found")
