"""
Unit & Integration Tests for Phase 33: Load Testing
===================================================
Validates simulated multi-bus fleets:
  - 10 buses
  - 50 buses
  - 100 buses
  - 500 buses
Measures throughput, latency percentiles (p50, p95, p99), error rate (< 0.1%), and queue stability.
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.testing.load_test_engine import LoadTestEngine


@pytest.fixture
def client():
    return TestClient(app)


def test_load_test_ten_buses(client):
    engine = LoadTestEngine(client=client)
    report = engine.run_load_test(num_buses=10, events_per_bus=2, concurrency_workers=4)

    assert report.simulated_buses == 10
    assert report.total_events_generated == 20
    assert report.successful_ingestions == 20
    assert report.failed_ingestions == 0
    assert report.error_rate_pct == 0.0
    assert report.throughput_eps > 10.0
    assert report.latency_p95_ms <= 100.0


def test_load_test_fifty_buses(client):
    engine = LoadTestEngine(client=client)
    report = engine.run_load_test(num_buses=50, events_per_bus=2, concurrency_workers=8)

    assert report.simulated_buses == 50
    assert report.total_events_generated == 100
    assert report.successful_ingestions == 100
    assert report.error_rate_pct == 0.0
    assert report.throughput_eps > 20.0


def test_load_test_one_hundred_buses(client):
    engine = LoadTestEngine(client=client)
    report = engine.run_load_test(num_buses=100, events_per_bus=1, concurrency_workers=8)

    assert report.simulated_buses == 100
    assert report.total_events_generated == 100
    assert report.successful_ingestions == 100
    assert report.error_rate_pct == 0.0


def test_load_test_five_hundred_buses(client):
    # Simulates mega-city scale: 500 buses emitting events
    engine = LoadTestEngine(client=client)
    report = engine.run_load_test(num_buses=500, events_per_bus=1, concurrency_workers=10)

    assert report.simulated_buses == 500
    assert report.total_events_generated == 500
    assert report.successful_ingestions == 500
    assert report.error_rate_pct == 0.0
    assert report.passed_slo is True
