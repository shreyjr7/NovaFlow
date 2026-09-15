"""
Unit and Integration tests for Road Defect Management (Phase 18).
================================================================
Tests:
  - Explainable Priority Scoring formula (Severity, Traffic, Detections, Location, Safety, Persistence)
  - 6-stage lifecycle state machine transitions
  - Field engineer actions: Confirm, Reject, Assign, Update Repair, Upload Evidence, Close Ticket
  - Multi-bus cross-fleet confirmation clustering
  - Autonomous post-closure re-detection watchdog (reopen/review)
  - Edge ingestion endpoint & lifecycle statistics
"""

import uuid
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.services.defect_service import (
    PriorityScoreEngine,
    get_road_defect_service,
)
from backend.app.schemas.defect_management import DefectLifecycleState

client = TestClient(app)


def test_priority_scoring_formula():
    """Validates multi-factor priority score calculation and component weights."""
    # Critical scenario: SEVERE defect, high traffic volume, multiple confirming buses, highway
    breakdown_crit = PriorityScoreEngine.calculate(
        severity="SEVERE",
        traffic_volume_vph=3000,
        detection_count=20,
        num_buses_confirming=4,
        road_segment="EXPRESS_HIGHWAY_CORRIDOR",
        defect_type="POTHOLE",
        first_detected_iso="2026-09-10T00:00:00Z",
        last_detected_iso="2026-09-15T00:00:00Z",
        is_reopened=True,
    )

    assert breakdown_crit.total_priority_score >= 85
    assert breakdown_crit.priority_tier == "CRITICAL"
    assert breakdown_crit.severity_score == 100.0
    assert breakdown_crit.traffic_volume_score == 100.0
    assert breakdown_crit.detections_score == 100.0
    assert breakdown_crit.persistence_score >= 80.0

    # Low scenario: LOW severity, low traffic, single detection, local street
    breakdown_low = PriorityScoreEngine.calculate(
        severity="LOW",
        traffic_volume_vph=400,
        detection_count=1,
        num_buses_confirming=1,
        road_segment="LOCAL_LANE_SECTOR_9",
        defect_type="SURFACE_EROSION",
    )

    assert breakdown_low.total_priority_score < 40
    assert breakdown_low.priority_tier == "LOW"
    assert breakdown_low.severity_score == 20.0


def test_list_defects_and_filters():
    """Lists defects with multi-parameter filtering."""
    # List all
    res = client.get("/api/v1/road-defects")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] >= 5

    # Filter by status: CONFIRMED
    res_conf = client.get("/api/v1/road-defects?status=CONFIRMED")
    assert res_conf.status_code == 200
    for item in res_conf.json()["items"]:
        assert item["status"] == "CONFIRMED"

    # Filter by defect type: POTHOLE
    res_pothole = client.get("/api/v1/road-defects?type=POTHOLE")
    assert res_pothole.status_code == 200
    for item in res_pothole.json()["items"]:
        assert item["type"] == "POTHOLE" or item["cls"] == "pothole"

    # Filter by min_priority
    res_prio = client.get("/api/v1/road-defects?min_priority=75")
    assert res_prio.status_code == 200
    for item in res_prio.json()["items"]:
        assert item["priority_score"] >= 75


def test_get_defect_details():
    """Retrieves full defect record with priority breakdown and audit history."""
    res = client.get("/api/v1/road-defects/DEF-2026-001")
    assert res.status_code == 200
    data = res.json()
    assert data["defect_id"] == "DEF-2026-001"
    assert data["road_segment"] == "CP_INNER_CIRCLE"
    assert data["severity"] == "HIGH"
    assert data["number_of_buses_confirming"] >= 2
    assert "priority_breakdown" in data
    assert "audit_history" in data
    assert len(data["audit_history"]) >= 1


def test_field_engineer_workflow_lifecycle():
    """Executes the complete field engineer workflow: Confirm -> Assign -> Update -> Evidence -> Close."""
    defect_id = "DEF-2026-006"  # Unverified defect in default seeds

    # 1. Confirm
    conf_res = client.post(
        f"/api/v1/road-defects/{defect_id}/confirm",
        json={"engineer_id": "ENG_042", "notes": "Verified missing divider block."},
    )
    assert conf_res.status_code == 200
    assert conf_res.json()["status"] == "CONFIRMED"

    # 2. Assign authority & issue maintenance ticket
    assign_res = client.post(
        f"/api/v1/road-defects/{defect_id}/assign",
        json={
            "engineer_id": "ENG_042",
            "assigned_authority": "Public Works Department (PWD)",
            "assigned_contractor": "Apex Highway Maintenance",
            "target_completion_date": "2026-09-25",
            "notes": "Urgent median divider replacement.",
        },
    )
    assert assign_res.status_code == 200
    assign_data = assign_res.json()
    assert assign_data["status"] == "ASSIGNED"
    assert assign_data["ticket"]["ticket_id"].startswith("TICK-")

    # 3. Update repair progress (UNDER_REPAIR)
    update_res = client.post(
        f"/api/v1/road-defects/{defect_id}/update",
        json={
            "engineer_id": "ENG_FIELD_108",
            "progress_percent": 60,
            "notes": "Concrete barriers brought to site and positioned.",
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "UNDER_REPAIR"

    # 4. Upload repair completion evidence
    evid_res = client.post(
        f"/api/v1/road-defects/{defect_id}/upload-evidence",
        json={
            "engineer_id": "ENG_FIELD_108",
            "completion_notes": "All median divider blocks anchored and painted with reflective stripes.",
            "after_image_b64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkWPjfDwAEfQHzgV23vAAAAABJRU5ErkJggg==",
            "completion_certificate_url": "/certs/cert_pwd_2026.pdf",
        },
    )
    assert evid_res.status_code == 200
    assert evid_res.json()["evidence_id"].startswith("EVID-")

    # 5. Close ticket (RESOLVED)
    close_res = client.post(
        f"/api/v1/road-defects/{defect_id}/close",
        json={"engineer_id": "ENG_SUPERVISOR_007", "closure_notes": "Repair certified compliant."},
    )
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "RESOLVED"
    assert close_res.json()["closed_at"] is not None


def test_reject_defect_workflow():
    """Field engineer can reject / dismiss false positive defect."""
    service = get_road_defect_service()
    new_defect = service.register_or_cluster_edge_event(
        event_id=f"evt_fake_{uuid.uuid4().hex[:6]}",
        defect_type="POTHOLE",
        severity="LOW",
        lat=28.6100,
        lon=77.2000,
        bus_id="BUS_001",
    )

    reject_res = client.post(
        f"/api/v1/road-defects/{new_defect.defect_id}/reject",
        json={"engineer_id": "ENG_042", "reason": "Tree shadow mistaken for pothole."},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"


def test_post_closure_redetection_watchdog():
    """
    CRITICAL PROMPT REQUIREMENT:
    If buses continue detecting the defect after closure: reopen/review the ticket.
    """
    defect_id = "DEF-2026-005"  # Pre-seeded defect in RESOLVED state

    # Check initially RESOLVED
    res_before = client.get(f"/api/v1/road-defects/{defect_id}")
    assert res_before.status_code == 200
    assert res_before.json()["status"] == "RESOLVED"

    # Simulate a transit bus surveillance re-detection at the closed site
    sim_res = client.post(
        f"/api/v1/road-defects/{defect_id}/simulate-redetection",
        json={"bus_id": "BUS_009", "confidence": 0.95, "notes": "Bus camera re-detected recurring crater."},
    )
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["status"] == "REOPENED_UNDER_REVIEW"
    assert sim_data["watchdog_triggered"] is True
    assert sim_data["reopen_count"] >= 1
    assert "Post-closure" in sim_data["reopen_reason"] or "Transit bus" in sim_data["reopen_reason"]

    # Verify audit history records the watchdog intervention
    res_after = client.get(f"/api/v1/road-defects/{defect_id}")
    assert res_after.status_code == 200
    after_data = res_after.json()
    assert after_data["status"] == "REOPENED_UNDER_REVIEW"
    assert any(a["action"] == "REOPEN_AFTER_CLOSURE" for a in after_data["audit_history"])


def test_edge_ingestion_and_cross_fleet_clustering():
    """Edge defect ingestion clusters into nearby defects and triggers auto-confirmation."""
    # 1. First bus reports defect at a new location
    lat = 28.6500
    lon = 77.2300
    payload_1 = {
        "event_id": f"evt_cluster_{uuid.uuid4().hex[:6]}",
        "defect_type": "POTHOLE",
        "severity": "HIGH",
        "gps": {"lat": lat, "lon": lon},
        "bus_id": "BUS_001",
        "confidence": 0.91,
        "road_segment": "CHANDNI_CHOWK_RD",
    }
    res1 = client.post("/api/v1/road-defects", json=payload_1)
    assert res1.status_code == 201
    defect_id_1 = res1.json()["defect_id"]
    assert res1.json()["number_of_buses_confirming"] == 1

    # 2. Second bus reports at same location (within 10m) -> cross-fleet confirmation
    payload_2 = {
        "event_id": f"evt_cluster_{uuid.uuid4().hex[:6]}",
        "defect_type": "POTHOLE",
        "severity": "HIGH",
        "gps": {"lat": lat + 0.00005, "lon": lon + 0.00005},
        "bus_id": "BUS_002",
        "confidence": 0.93,
        "road_segment": "CHANDNI_CHOWK_RD",
    }
    res2 = client.post("/api/v1/road-defects", json=payload_2)
    assert res2.status_code == 201
    assert res2.json()["defect_id"] == defect_id_1  # Clustered into same defect!
    assert res2.json()["number_of_buses_confirming"] >= 2
    assert res2.json()["status"] == "CONFIRMED"  # Auto-promoted by fleet consensus!


def test_defect_lifecycle_stats():
    """Returns aggregated summary metrics across all lifecycle states and priority tiers."""
    res = client.get("/api/v1/road-defects/stats/lifecycle")
    assert res.status_code == 200
    stats = res.json()
    assert "total_defects" in stats
    assert "by_status" in stats
    assert "by_priority_tier" in stats
    assert "by_type" in stats
    assert "by_severity" in stats
    assert "reopened_defects_count" in stats
    assert stats["total_defects"] >= 5
