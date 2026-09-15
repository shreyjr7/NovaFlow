"""
Unit & Integration Tests for Phase 33: Failure Testing
======================================================
Verifies fault-tolerance across 6 mandatory failure modes:
  1. Network disconnected
  2. Camera disconnected
  3. Edge device restarted
  4. Backend unavailable
  5. Database temporarily unavailable
  6. Queue unavailable

Certifies Prompt Invariants:
  - Events are not lost
  - Local buffering works
  - System reconnects automatically
  - Duplicate events are prevented
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.testing.failure_injection_suite import FailureInjectionSuite


@pytest.fixture
def client():
    return TestClient(app)


def test_failure_mode_1_network_disconnected(client):
    suite = FailureInjectionSuite(client=client)
    res = suite.test_network_disconnected()
    assert res.status == "PASSED"
    assert res.events_buffered_locally == 5
    assert res.zero_data_loss_verified is True


def test_failure_mode_2_camera_disconnected(client):
    suite = FailureInjectionSuite(client=client)
    res = suite.test_camera_disconnected()
    assert res.status == "PASSED"
    assert res.details.get("ticket_created") is True


def test_failure_mode_3_edge_device_restarted(client):
    suite = FailureInjectionSuite(client=client)
    res = suite.test_edge_device_restarted()
    assert res.status == "PASSED"
    assert res.events_buffered_locally == 8
    assert res.zero_data_loss_verified is True


def test_failure_mode_4_backend_unavailable(client):
    suite = FailureInjectionSuite(client=client)
    res = suite.test_backend_unavailable()
    assert res.status == "PASSED"
    assert res.zero_data_loss_verified is True


def test_failure_mode_5_database_temporarily_unavailable(client):
    suite = FailureInjectionSuite(client=client)
    res = suite.test_database_temporarily_unavailable()
    assert res.status == "PASSED"
    assert res.zero_data_loss_verified is True


def test_failure_mode_6_queue_unavailable_and_deduplication(client):
    suite = FailureInjectionSuite(client=client)
    res = suite.test_queue_unavailable_and_deduplication()
    assert res.status == "PASSED"
    assert res.duplicate_prevention_verified is True
    assert res.reconnection_verified is True


def test_complete_failure_resilience_suite(client):
    suite = FailureInjectionSuite(client=client)
    report = suite.run_all_failure_tests()

    assert report.overall_resilience_status == "PASSED"
    assert report.scenarios_passed == 6
    assert report.scenarios_total == 6

    # Verify the 4 mandatory prompt invariants:
    assert report.events_are_not_lost is True
    assert report.local_buffering_works is True
    assert report.system_reconnects_automatically is True
    assert report.duplicate_events_prevented is True
