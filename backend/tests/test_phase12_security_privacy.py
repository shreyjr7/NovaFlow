"""
Tests for Phase 12 (Security and Privacy)
=========================================
Verifies:
  - Step 28: User Authentication (Login, JWT token generation and validation)
  - Step 29: Role-Based Access Control (ADMIN, TRAFFIC POLICE, ROAD ENGINEER, ANALYST)
  - Step 30: Personal Data Minimization (Limited retention, non-incident redaction)
  - Step 31: Evidence Protection (Video -> Hash -> Timestamp -> Audit Log -> Secure Storage)
"""

import hashlib
import time
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.auth import hash_password, verify_password, create_access_token, decode_access_token
from backend.app.services.privacy_service import get_privacy_service
from backend.app.services.evidence_chain_service import get_evidence_chain_service, CustodyStage


@pytest.fixture
def client():
    return TestClient(app)


def test_step28_authentication_login_flow(client):
    # Test valid credentials
    r = client.post("/api/v1/auth/login", json={"email": "admin@novaflow.gov.in", "password": "admin123"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert data["user"]["role"] == "ADMIN"
    assert "*" in data["permissions"]

    # Test invalid password
    r_bad = client.post("/api/v1/auth/login", json={"email": "admin@novaflow.gov.in", "password": "wrongpassword"})
    assert r_bad.status_code == 401


def test_step29_role_based_access_control(client):
    roles_tested = [
        ("admin@novaflow.gov.in", "admin123", "ADMIN"),
        ("police@novaflow.gov.in", "police123", "TRAFFIC POLICE"),
        ("engineer@novaflow.gov.in", "engineer123", "ROAD ENGINEER"),
        ("analyst@novaflow.gov.in", "analyst123", "ANALYST"),
    ]

    for email, pwd, expected_role in roles_tested:
        res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
        assert res.status_code == 200
        token = res.json()["access_token"]

        # Validate /me
        me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        assert me_res.json()["user"]["role"] == expected_role


def test_step30_privacy_data_minimization():
    svc = get_privacy_service()
    summary = svc.get_dashboard_summary()
    assert summary["overall_compliance"] == "100% COMPLIANT"
    assert summary["camera_processing"]["cloud_raw_stream_gb"] == 0.0
    assert summary["camera_processing"]["edge_processed_pct"] == 100.0

    retention = svc.get_retention_policies()
    assert retention.raw_frame_buffer_seconds <= 30
    assert retention.unverified_anomaly_retention_days <= 7


def test_step31_protect_incident_evidence_chain_of_custody():
    """
    Step 31: Video -> Hash -> Timestamp -> Immutable audit log -> Secure storage
    """
    svc = get_evidence_chain_service()

    evidence_id = "EV-STEP31-VAULT-001"
    raw_payload = "MOCK_INCIDENT_VIDEO_STREAM_UP65AB1234_TIMESTAMP"

    item = svc.store_evidence(
        evidence_id=evidence_id,
        bus_id="BUS-102",
        camera_id="CAM-FRONT",
        event_id="EVT-INCIDENT-STEP31",
        file_name="clip_step31.mp4",
        file_size_bytes=len(raw_payload.encode()),
        binary_payload=raw_payload,
        actor="Edge Incident Buffer",
    )

    assert item.evidence_id == evidence_id
    assert item.integrity_status == "VERIFIED"
    assert len(item.audit_history) >= 1
    assert item.audit_history[0].stage == CustodyStage.CREATED

    # Record review audit event
    svc.record_custody_action(
        evidence_id=evidence_id,
        stage=CustodyStage.REVIEWED,
        actor="Traffic Police Investigator",
        actor_role="SAFETY_OFFICER",
        notes="Reviewed clip collision signature for court evidence submission",
    )

    # Verify integrity check
    integrity = svc.verify_integrity(evidence_id)
    assert integrity["is_valid"] is True
    assert integrity["evidence_integrity"] == "VERIFIED"
