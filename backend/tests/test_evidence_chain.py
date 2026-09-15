"""
Unit tests for Evidence Chain of Custody Router (Phase 27)
===========================================================
Validates:
  - Cryptographic manifest generation on storage:
      SHA-256 hash, Timestamp, Bus ID, Camera ID, Event ID
  - Recording of immutable audit lifecycle stages:
      Created, Accessed, Downloaded, Reviewed, Exported
  - Real-time cryptographic integrity verification:
      Displays "Evidence Integrity: VERIFIED"
      Displays "Evidence Integrity: INTEGRITY CHECK FAILED"
  - Anti-overwrite guardrail:
      Rejection with HTTP 409 Conflict when attempting to silently overwrite existing files.
"""

import hashlib
import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_store_evidence_generates_cryptographic_manifest():
    """
    Validates that storing an incident clip generates:
      - SHA-256 hash
      - Timestamp
      - Bus ID
      - Camera ID
      - Event ID
      - Genesis audit stage 'Created'
    """
    payload_content = "TEST_EVIDENCE_CLIP_BINARY_STREAM_BUS_112_CAM_01"
    expected_hash = hashlib.sha256(payload_content.encode("utf-8")).hexdigest()

    evidence_in = {
        "evidence_id": "EV_BUF_112_555",
        "bus_id": "BUS-112",
        "camera_id": "CAM-112-FRONT",
        "event_id": "INC-2026-088",
        "file_name": "ev_buf_112_pedestrian_brake.mp4",
        "file_size_bytes": 12450000,
        "binary_payload": payload_content,
    }

    res = client.post("/api/v1/evidence", json=evidence_in)
    assert res.status_code == 201
    manifest = res.json()

    # Verify manifest fields
    assert manifest["evidence_id"] == "EV_BUF_112_555"
    assert manifest["sha256_hash"] == expected_hash
    assert manifest["bus_id"] == "BUS-112"
    assert manifest["camera_id"] == "CAM-112-FRONT"
    assert manifest["event_id"] == "INC-2026-088"
    assert manifest["timestamp"]

    # Verify genesis audit history stage
    history = manifest["audit_history"]
    assert len(history) == 1
    assert history[0]["stage"] == "Created"


def test_anti_overwrite_protection_guardrail():
    """
    Validates critical prompt rule:
      "Do not allow evidence files to be silently overwritten."
      Attempting to store an already-existing evidence_id returns HTTP 409 Conflict.
    """
    duplicate_payload = {
        "evidence_id": "EV_BUF_102_987",  # Already exists in database
        "bus_id": "BUS-102",
        "camera_id": "CAM-102-FRONT",
        "event_id": "INC-2026-001",
        "file_name": "malicious_overwrite_attempt.mp4",
        "file_size_bytes": 1000,
        "binary_payload": "FORGED_VIDEO_CONTENT",
    }

    res = client.post("/api/v1/evidence", json=duplicate_payload)
    assert res.status_code == 409
    assert "IMMUTABLE_EVIDENCE_OVERWRITE_PROHIBITED" in res.json()["detail"]


def test_immutable_custody_lifecycle_stages():
    """
    Validates recording of all 5 immutable custody lifecycle stages:
      - Created (recorded on store)
      - Accessed
      - Downloaded
      - Reviewed
      - Exported
    """
    evidence_id = "EV_BUF_108_412"

    # 1. Accessed
    res_acc = client.post(
        f"/api/v1/evidence/{evidence_id}/custody-action",
        json={"stage": "Accessed", "actor": "Officer Miller", "actor_role": "SAFETY_OFFICER", "notes": "Initial playback review"},
    )
    assert res_acc.status_code == 200

    # 2. Downloaded
    res_down = client.post(
        f"/api/v1/evidence/{evidence_id}/custody-action",
        json={"stage": "Downloaded", "actor": "Forensics Lab", "actor_role": "TECHNICAL_ANALYST", "notes": "Downloaded for optical enhancement"},
    )
    assert res_down.status_code == 200

    # 3. Reviewed
    res_rev = client.post(
        f"/api/v1/evidence/{evidence_id}/custody-action",
        json={"stage": "Reviewed", "actor": "Panel Lead Davis", "actor_role": "SAFETY_SUPERVISOR", "notes": "Incident verified valid"},
    )
    assert res_rev.status_code == 200

    # 4. Exported
    res_exp = client.post(
        f"/api/v1/evidence/{evidence_id}/custody-action",
        json={"stage": "Exported", "actor": "Legal Counsel", "actor_role": "LEGAL_AUDITOR", "notes": "Exported to Municipal Traffic Authority"},
    )
    assert res_exp.status_code == 200

    # Verify audit history
    rec = res_exp.json()
    stages = [a["stage"] for a in rec["audit_history"]]
    assert "Created" in stages
    assert "Accessed" in stages
    assert "Downloaded" in stages
    assert "Reviewed" in stages
    assert "Exported" in stages


def test_evidence_integrity_verification_and_tamper_detection():
    """
    Validates display of:
      Evidence Integrity: VERIFIED
      or
      Evidence Integrity: INTEGRITY CHECK FAILED
    """
    evidence_id = "EV_BUF_102_987"

    # 1. Verification on unaltered evidence -> Displays VERIFIED
    res_clean = client.get(f"/api/v1/evidence/{evidence_id}/verify-integrity")
    assert res_clean.status_code == 200
    clean_data = res_clean.json()
    assert clean_data["evidence_integrity"] == "VERIFIED"
    assert clean_data["is_valid"] is True
    assert clean_data["stored_hash"] == clean_data["computed_hash"]

    # 2. Simulate malicious payload bit tampering
    res_tamper = client.post(f"/api/v1/evidence/{evidence_id}/simulate-tamper")
    assert res_tamper.status_code == 200
    tampered_data = res_tamper.json()

    # Rule check: Displays INTEGRITY CHECK FAILED
    assert tampered_data["evidence_integrity"] == "INTEGRITY CHECK FAILED"
    assert tampered_data["is_valid"] is False
    assert tampered_data["stored_hash"] != tampered_data["computed_hash"]

    # 3. Restore clean payload
    original = "VIDEO_FRAME_STREAM_AIIMS_COLLISION_BUFFER_BUS102_CAM01_TIMESTAMP_20260915"
    res_restore = client.post(f"/api/v1/evidence/{evidence_id}/restore-tamper", json={"original_payload": original})
    assert res_restore.status_code == 200
    assert res_restore.json()["evidence_integrity"] == "VERIFIED"
