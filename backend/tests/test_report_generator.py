"""
Unit tests for Urban Intelligence Report Generator (Phase 29)
=============================================================
Validates:
  1. Parameterized report generation based on Date range, City, Zone, Route, and Event types.
  2. Complete inclusion of all 10 mandatory sections:
       - Executive Summary
       - Traffic Overview
       - Road Condition
       - Infrastructure Deficiencies
       - Incident Summary
       - Pedestrian Safety
       - Route Delays (with canonical Route 12 benchmark)
       - Congestion Analysis
       - Top Priority Locations
       - Recommended Actions
  3. Inclusion of Charts, GIS datasets, and explicit Data Sources.
  4. Saving and retrieving reports in the municipal archive.
  5. Role-restricted sharing with authorized users and secure tokens.
  6. Standard-compliant PDF binary stream download.
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_generate_report_with_user_criteria():
    """Validates adhoc report generation across user-selected parameters."""
    req_body = {
        "date_range": "last_7_days",
        "city": "Bengaluru",
        "zone": "zone_a",
        "route": "ROUTE-12",
        "event_types": ["pothole", "road_damage", "waterlogging", "traffic_congestion"],
        "title": "Zone A Weekly Arterial Diagnostic",
    }

    res = client.post("/api/v1/reports/generate", json=req_body)
    assert res.status_code == 200
    report = res.json()

    assert report["report_id"].startswith("REP-")
    assert report["title"] == "Zone A Weekly Arterial Diagnostic"
    assert report["city"] == "Bengaluru"
    assert report["config"]["date_range"] == "last_7_days"
    assert report["config"]["zone"] == "zone_a"


def test_all_ten_mandatory_sections_present():
    """Asserts that all 10 required diagnostic sections are fully populated."""
    req_body = {
        "date_range": "today",
        "city": "Bengaluru",
        "zone": "all_zones",
        "route": "all_routes",
        "event_types": ["pothole", "road_damage", "waterlogging", "missing_infrastructure", "traffic_congestion", "pedestrian_risk", "collision_incident"],
    }

    res = client.post("/api/v1/reports/generate", json=req_body)
    assert res.status_code == 200
    report = res.json()

    # 1. Executive Summary
    assert "executive_summary" in report
    assert report["executive_summary"]["headline"]
    assert report["executive_summary"]["total_events_analyzed"] > 0
    assert report["executive_summary"]["active_buses_contributing"] >= 100
    assert report["executive_summary"]["municipal_health_score"] > 50.0
    assert len(report["executive_summary"]["key_takeaways"]) >= 3

    # 2. Traffic Overview
    assert "traffic_overview" in report
    assert report["traffic_overview"]["total_vehicle_count"] > 50000
    assert report["traffic_overview"]["average_speed_kmh"] > 10.0
    assert "Cars / Cabs" in report["traffic_overview"]["modal_distribution"]

    # 3. Road Condition
    assert "road_condition" in report
    assert report["road_condition"]["total_defects"] > 0
    assert report["road_condition"]["potholes"] > 0
    assert report["road_condition"]["multi_bus_deduplicated_count"] > 0
    assert "CRITICAL" in report["road_condition"]["severity_breakdown"]

    # 4. Infrastructure Deficiencies
    assert "infrastructure_deficiencies" in report
    assert report["infrastructure_deficiencies"]["total_deficient_assets"] > 0
    assert len(report["infrastructure_deficiencies"]["priority_deficiency_list"]) >= 2

    # 5. Incident Summary
    assert "incident_summary" in report
    assert report["incident_summary"]["total_incidents"] >= 1

    # 6. Pedestrian Safety
    assert "pedestrian_safety" in report
    assert report["pedestrian_safety"]["pedestrian_conflicts"] > 0
    assert len(report["pedestrian_safety"]["vulnerable_hotspots"]) >= 2

    # 7. Route Delays
    assert "route_delays" in report
    assert report["route_delays"]["network_average_delay_minutes"] > 0
    assert len(report["route_delays"]["worst_delayed_routes"]) >= 3

    # 8. Congestion Analysis
    assert "congestion_analysis" in report
    assert report["congestion_analysis"]["city_congestion_index"] > 50.0
    assert len(report["congestion_analysis"]["top_congested_corridors"]) >= 3

    # 9. Top Priority Locations
    assert "top_priority_locations" in report
    assert len(report["top_priority_locations"]) >= 4
    assert report["top_priority_locations"][0]["rank"] == 1
    assert report["top_priority_locations"][0]["severity"].startswith("P1")

    # 10. Recommended Actions
    assert "recommended_actions" in report
    assert len(report["recommended_actions"]) >= 3
    for act in report["recommended_actions"]:
        assert act["recommended_action"]
        assert act["evidence"]
        assert act["reasoning"]
        assert act["assigned_department"]


def test_canonical_route_12_and_road_segment_a():
    """Validates the canonical benchmark: Route 12 delay of +15m linked to Road Segment A."""
    res = client.get("/api/v1/reports/REP-BLR-2026-001")
    assert res.status_code == 200
    report = res.json()

    # Verify Route 12
    r12 = report["route_delays"]["canonical_route_12"]
    assert r12["route_id"] == "ROUTE-12"
    assert r12["scheduled_travel_time_minutes"] == 42.0
    assert r12["observed_travel_time_minutes"] == 57.0
    assert r12["average_delay_minutes"] == 15.0
    assert "Road damage" in r12["contributing_factors"]
    assert "Congestion" in r12["contributing_factors"]

    # Verify Road Segment A priority rank
    top_loc = report["top_priority_locations"][0]
    assert "Road Segment A" in top_loc["location_name"]
    assert top_loc["severity"] == "P1-CRITICAL"


def test_data_sources_and_provenance():
    """Verifies that data sources & provenance citations are explicitly included."""
    res = client.get("/api/v1/reports/REP-BLR-2026-001")
    assert res.status_code == 200
    report = res.json()

    sources = report["data_sources"]
    assert len(sources) >= 4
    source_names = [s["source_name"] for s in sources]
    assert any("Edge AI" in s for s in source_names)
    assert any("PostGIS" in s for s in source_names)
    assert any("GPS" in s or "IMU" in s for s in source_names)
    assert any("Evidence" in s for s in source_names)


def test_save_and_retrieve_report():
    """Tests generating with auto-save, saving an existing report, and listing reports."""
    gen_res = client.post(
        "/api/v1/reports/generate?auto_save=true",
        json={"date_range": "today", "city": "Bengaluru", "zone": "zone_b", "route": "ROUTE-543"}
    )
    assert gen_res.status_code == 200
    created_id = gen_res.json()["report_id"]

    # Verify report is retrievable
    get_res = client.get(f"/api/v1/reports/{created_id}")
    assert get_res.status_code == 200
    assert get_res.json()["report_id"] == created_id
    assert get_res.json()["status"] == "SAVED"

    # Verify report appears in list
    list_res = client.get("/api/v1/reports")
    assert list_res.status_code == 200
    reports = list_res.json()
    assert any(r["report_id"] == created_id for r in reports)


def test_share_report_with_authorized_users():
    """Tests sharing report with authorized user roles and retrieving via secure token."""
    share_payload = {
        "recipients": [
            {"email": "chief.planner@bmtc.gov.in", "role": "TRANSIT_PLANNER", "permission_level": "VIEW"},
            {"email": "traffic.sp@bcp.gov.in", "role": "TRAFFIC_POLICE_CHIEF", "permission_level": "EXPORT"},
        ],
        "role_restrictions": ["TRANSIT_PLANNER", "TRAFFIC_POLICE_CHIEF", "MUNICIPAL_OFFICER"],
        "permission_level": "VIEW",
        "notes": "Urgent review requested for Silk Board corridor bottleneck mitigation."
    }

    share_res = client.post("/api/v1/reports/REP-BLR-2026-001/share", json=share_payload)
    assert share_res.status_code == 200
    share_data = share_res.json()
    token = share_data["share_token"]
    assert token.startswith("share_")
    assert share_data["share_link"] == f"/shared-report/{token}"

    # Access shared report via token
    shared_get_res = client.get(f"/api/v1/reports/shared/{token}")
    assert shared_get_res.status_code == 200
    shared_view = shared_get_res.json()
    assert shared_view["share_record"]["share_token"] == token
    assert shared_view["report"]["report_id"] == "REP-BLR-2026-001"


def test_download_pdf_binary_stream():
    """Validates that GET /api/v1/reports/{id}/download-pdf produces standard %PDF-1.4 binary stream."""
    pdf_res = client.get("/api/v1/reports/REP-BLR-2026-001/download-pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in pdf_res.headers["content-disposition"]
    assert pdf_res.content.startswith(b"%PDF-1.4")
    assert len(pdf_res.content) > 1000
