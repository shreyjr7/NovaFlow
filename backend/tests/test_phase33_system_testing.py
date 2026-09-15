"""
Unit & Integration Tests for Phase 33: System Testing
=====================================================
Validates the complete 7-hop end-to-end trace:
  Video → Edge AI → Event → Network → Backend → Database → GIS Dashboard
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.testing.system_trace_tester import SystemTraceTester


@pytest.fixture
def client():
    return TestClient(app)


def test_full_system_trace_seven_hops(client):
    tester = SystemTraceTester(client=client)
    report = tester.run_trace(
        event_type="POTHOLE",
        bus_id="BUS_104",
        route_id="ROUTE_12",
        road_segment="ROUTE_12_SEG_4",
        lat=28.6322,
        lon=77.2198,
    )

    assert report.overall_status == "PASSED"
    assert len(report.hops) == 7

    # Verify each hop in exact sequence
    hop_names = [h.name for h in report.hops]
    assert hop_names == [
        "Video",
        "Edge AI",
        "Event",
        "Network",
        "Backend",
        "Database",
        "GIS Dashboard",
    ]

    for hop in report.hops:
        assert hop.status == "SUCCESS"
        assert hop.latency_ms >= 0.0

    assert report.verified_in_gis is True
    assert report.total_pipeline_latency_ms > 0.0


def test_system_trace_congestion_event(client):
    tester = SystemTraceTester(client=client)
    report = tester.run_trace(
        event_type="CONGESTION_EVENT",
        bus_id="BUS_104",
        route_id="ROUTE_12",
        road_segment="ROUTE_12_SEG_2",
        lat=28.6340,
        lon=77.2215,
    )

    assert report.overall_status == "PASSED"
    assert report.verified_in_gis is True
