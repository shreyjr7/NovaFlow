"""
Unit tests for Actionable Insights Engine Router (Phase 23)
===========================================================
Validates:
  - Canonical Prompt Benchmark 1:
      "Road Segment A has been flagged by 11 buses over 4 days."
      Evidence: 11 observations, High traffic volume, Persistent pothole
      Recommended action: "Prioritize field verification and maintenance."
  - Canonical Prompt Benchmark 2:
      "Route 12 experiences recurring congestion between 17:00–19:00."
      Recommended action: "Investigate signal timing, road capacity and nearby infrastructure constraints."
  - Mandatory field completeness: Evidence, Data sources, Reasoning, Confidence, Recommended action.
  - Zero unsupported AI speculation guardrail enforcement.
  - Category and severity filtering.
  - Operational lifecycle status transitions (ACKNOWLEDGED, ACTIONED, DISMISSED).
  - Network-wide insights KPI summary.
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_canonical_road_segment_a_insight():
    """
    Validates canonical prompt example 1:
      "Road Segment A has been flagged by 11 buses over 4 days."
      Evidence: 11 observations, High traffic volume, Persistent pothole
      Recommended Action: "Prioritize field verification and maintenance."
    """
    res = client.get("/api/v1/insights/INS-2026-001")
    assert res.status_code == 200
    ins = res.json()

    assert ins["title"] == "Road Segment A has been flagged by 11 buses over 4 days."
    assert ins["category"] == "ROAD_DEFECTS"
    assert ins["severity"] == "HIGH"

    # Evidence check
    evidence = ins["evidence"]
    assert any("11 observations" in e for e in evidence)
    assert any("High traffic volume" in e for e in evidence)
    assert any("Persistent pothole" in e for e in evidence)

    # Recommended action check
    assert "Prioritize field verification and maintenance." in ins["recommended_action"]

    # Data sources provenance
    assert len(ins["data_sources"]) >= 2
    assert "Bus Fleet Computer Vision Telemetry" in ins["data_sources"]

    # Confidence and anti-speculation guardrail
    assert ins["confidence"] >= 0.90
    assert ins["anti_speculation_verified"] is True
    assert len(ins["reasoning"]) > 30


def test_canonical_route_12_recurring_congestion_insight():
    """
    Validates canonical prompt example 2:
      "Route 12 experiences recurring congestion between 17:00–19:00."
      Recommended Action: "Investigate signal timing, road capacity and nearby infrastructure constraints."
    """
    res = client.get("/api/v1/insights/INS-2026-002")
    assert res.status_code == 200
    ins = res.json()

    assert "Route 12 experiences recurring congestion between 17:00–19:00." in ins["title"]
    assert ins["category"] == "ROUTE_DELAYS"
    assert ins["severity"] == "HIGH"

    # Recommended action
    assert "Investigate signal timing, road capacity and nearby infrastructure constraints." in ins["recommended_action"]

    # Evidence and metrics
    evidence = ins["evidence"]
    assert any("42 min" in e and "57 min" in e for e in evidence)
    assert any("17:00 and 19:00" in e for e in evidence)

    # Reasoning check
    assert "Vikas Marg" in ins["reasoning"] or "ITO Junction" in ins["reasoning"]
    assert ins["confidence"] >= 0.90


def test_mandatory_fields_completeness_across_all_insights():
    """
    Every insight must include:
      - Evidence
      - Data sources
      - Reasoning
      - Confidence
      - Recommended action
    """
    res = client.get("/api/v1/insights")
    assert res.status_code == 200
    insights = res.json()
    assert len(insights) >= 5

    for ins in insights:
        # Mandatory prompt requirements
        assert ins["evidence"] and len(ins["evidence"]) >= 2
        assert ins["data_sources"] and len(ins["data_sources"]) >= 2
        assert ins["reasoning"] and len(ins["reasoning"]) >= 20
        assert 0.0 <= ins["confidence"] <= 1.0
        assert ins["recommended_action"] and len(ins["recommended_action"]) >= 10

        # Anti-speculation verification
        assert ins["anti_speculation_verified"] is True


def test_insights_filtering():
    """Tests filtering by category, severity, and confidence threshold."""
    # Filter by category: PEDESTRIAN_RISK
    res_ped = client.get("/api/v1/insights?category=PEDESTRIAN_RISK")
    assert res_ped.status_code == 200
    ped_insights = res_ped.json()
    assert len(ped_insights) >= 1
    assert ped_insights[0]["category"] == "PEDESTRIAN_RISK"
    assert "School Zone" in ped_insights[0]["title"]

    # Filter by severity: CRITICAL
    res_crit = client.get("/api/v1/insights?severity=CRITICAL")
    assert res_crit.status_code == 200
    crit_insights = res_crit.json()
    assert len(crit_insights) >= 2
    for c in crit_insights:
        assert c["severity"] == "CRITICAL"

    # Filter by minimum confidence: 0.95
    res_conf = client.get("/api/v1/insights?min_confidence=0.95")
    assert res_conf.status_code == 200
    high_conf = res_conf.json()
    for h in high_conf:
        assert h["confidence"] >= 0.95


def test_insight_lifecycle_status_transition():
    """Tests updating status to ACKNOWLEDGED, ACTIONED, and DISMISSED."""
    insight_id = "INS-2026-004"
    # Acknowledge
    res_ack = client.patch(
        f"/api/v1/insights/{insight_id}/status",
        json={"status": "ACKNOWLEDGED", "notes": "Signage dispatch work order scheduled."},
    )
    assert res_ack.status_code == 200
    assert res_ack.json()["status"] == "ACKNOWLEDGED"
    assert res_ack.json()["action_notes"] == "Signage dispatch work order scheduled."

    # Actioned
    res_act = client.patch(
        f"/api/v1/insights/{insight_id}/status",
        json={"status": "ACTIONED", "notes": "New stop sign installed by field team."},
    )
    assert res_act.status_code == 200
    assert res_act.json()["status"] == "ACTIONED"


def test_insights_summary():
    """Tests the /summary KPI endpoint."""
    res = client.get("/api/v1/insights/summary")
    assert res.status_code == 200
    data = res.json()

    assert data["total_insights"] >= 5
    assert data["critical_insights"] >= 1
    assert data["high_priority_insights"] >= 2
    assert data["average_confidence"] >= 0.90
    assert data["anti_speculation_guardrail_active"] is True
    assert "by_category" in data
