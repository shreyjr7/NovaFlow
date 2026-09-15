"""
Unit tests for Privacy & Security Architecture Router (Phase 26)
================================================================
Validates:
  - 13 Core Privacy & Security Principles compliance scorecard
  - Configurable retention policy retrieval and modification
  - RBAC evidence access control (SAFETY_OFFICER allowed, DISPATCHER blocked from raw clips)
  - Immutable access audit logging on every evidence access request
  - Zero continuous raw video upload guarantee & local passenger cabin privacy
  - On-demand retention purge execution
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_privacy_dashboard_and_13_rules_compliance():
    """
    Validates that the Privacy Dashboard reports 100% compliance across
    all 13 prompt-mandated Privacy & Security rules.
    """
    res = client.get("/api/v1/privacy/dashboard")
    assert res.status_code == 200
    data = res.json()

    assert data["overall_compliance"] == "100% COMPLIANT"
    assert data["rules_enforced_count"] == 13
    assert data["rules_total_count"] == 13

    checklist = data["compliance_checklist"]
    assert len(checklist) == 13

    rule_names = [r["rule"] for r in checklist]
    assert any("continuously upload" in r or "continuous upload" in r for r in rule_names)
    assert any("normal video locally" in r for r in rule_names)
    assert any("Discard non-incident" in r for r in rule_names)
    assert any("access control" in r for r in rule_names)
    assert any("audit logs" in r for r in rule_names)
    assert any("encryption in transit" in r for r in rule_names)
    assert any("encryption at rest" in r for r in rule_names)
    assert any("RBAC" in r for r in rule_names)
    assert any("Minimize" in r for r in rule_names)
    assert any("punish or accuse drivers" in r for r in rule_names)
    assert any("human verification" in r for r in rule_names)
    assert any("Passenger cabin" in r for r in rule_names)


def test_zero_raw_upload_and_cabin_privacy_guarantees():
    """
    Rule 1 & Rule 13 validation:
      - 0.0 GB raw stream to cloud
      - 100% video processed locally on edge Jetson nodes
      - Passenger cabin count local aggregation only
    """
    res = client.get("/api/v1/privacy/dashboard")
    assert res.status_code == 200
    proc = res.json()["camera_processing"]

    assert proc["cloud_raw_stream_gb"] == 0.0
    assert proc["edge_processed_pct"] == 100.0
    assert "Zero Passenger PII" in proc["cabin_passenger_privacy"]


def test_configurable_retention_policies():
    """
    Validates retrieving and updating configurable retention policies:
      - Raw frame buffer seconds
      - Unverified anomaly retention days
      - Confirmed evidence clip retention days
      - Audit log retention days
    """
    # 1. Get current config
    get_res = client.get("/api/v1/privacy/retention-policies")
    assert get_res.status_code == 200
    config = get_res.json()
    assert config["raw_frame_buffer_seconds"] >= 5
    assert config["confirmed_evidence_clip_retention_days"] >= 7

    # 2. Update config
    update_payload = {
        "raw_frame_buffer_seconds": 20,
        "unverified_anomaly_retention_days": 5,
        "confirmed_evidence_clip_retention_days": 60,
        "access_audit_log_retention_days": 180,
        "passenger_cabin_telemetry_retention_hours": 48,
    }
    put_res = client.put("/api/v1/privacy/retention-policies", json=update_payload)
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["raw_frame_buffer_seconds"] == 20
    assert updated["confirmed_evidence_clip_retention_days"] == 60


def test_rbac_evidence_access_control_and_denial():
    """
    Rule 5 & Rule 9 validation:
      - SAFETY_OFFICER is granted raw evidence access.
      - DISPATCHER is denied raw evidence access (HTTP 403 Forbidden).
    """
    # 1. Authorized access (SAFETY_OFFICER)
    auth_req = {
        "user_id": "officer.miller",
        "user_role": "SAFETY_OFFICER",
        "action": "VIEW_EVIDENCE_CLIP",
        "resource_id": "EV_BUF_102_987",
        "justification": "Authorized collision incident track inspection",
    }
    res_auth = client.post("/api/v1/privacy/evidence-access", json=auth_req)
    assert res_auth.status_code == 200
    assert res_auth.json()["allowed"] is True
    assert res_auth.json()["access_level"] == "FULL_RAW"

    # 2. Unauthorized access (DISPATCHER attempting to view unredacted raw clip)
    denied_req = {
        "user_id": "dispatcher.singh",
        "user_role": "DISPATCHER",
        "action": "VIEW_RAW_EVIDENCE_CLIP",
        "resource_id": "EV_BUF_102_987",
        "justification": "Unauthorized raw clip inspection attempt",
    }
    res_denied = client.post("/api/v1/privacy/evidence-access", json=denied_req)
    assert res_denied.status_code == 403
    assert "Access Denied" in res_denied.json()["detail"]


def test_immutable_access_audit_logging():
    """
    Rule 6 validation:
      Verifies that every evidence access attempt is recorded in the immutable audit ledger.
    """
    # Trigger an access
    req = {
        "user_id": "auditor.patel",
        "user_role": "LEGAL_AUDITOR",
        "action": "VERIFY_CHAIN_OF_CUSTODY",
        "resource_id": "EV_BUF_102_987",
        "justification": "Legal audit compliance review",
    }
    _ = client.post("/api/v1/privacy/evidence-access", json=req)

    # Query audit logs
    logs_res = client.get("/api/v1/privacy/access-logs?user_id=auditor.patel")
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) >= 1
    assert logs[0]["user_id"] == "auditor.patel"
    assert logs[0]["user_role"] == "LEGAL_AUDITOR"
    assert logs[0]["resource_id"] == "EV_BUF_102_987"


def test_retention_purge_execution():
    """Validates the manual/scheduled retention purge cycle endpoint."""
    res = client.post("/api/v1/privacy/purge-expired")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "PURGE_COMPLETE"
    assert data["raw_frames_purged_count"] > 0
    assert "policy_applied" in data
