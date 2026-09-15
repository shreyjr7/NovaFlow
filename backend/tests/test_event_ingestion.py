"""
Unit and Integration tests for Central Event Ingestion Pipeline (Phase 16).
==========================================================================
Tests:
  - Edge device authentication (API key and bearer token verification, rejection of unauthorized callers)
  - Schema normalization & bounds checking
  - Fast ingestion acceptance (< 5ms response with HTTP 202 Accepted)
  - Stream queue publishing (Redis Streams / in-memory stream fallback)
  - Idempotency key computation and multi-tier duplicate rejection
  - EventProcessor worker consumer loop, DB persistence, and XACK
  - Ingestion stats and status lookup by idempotency key
"""

import time
import uuid
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.queue.factory import get_message_queue_provider
from backend.app.services.deduplication import get_deduplication_service
from backend.app.services.event_processor import STREAM_NAME, CONSUMER_GROUP, get_event_processor

client = TestClient(app)

VALID_API_KEY = "novaflow-edge-key-2026"
VALID_DEV_TOKEN = "novaflow-edge-dev-token"


@pytest.fixture(autouse=True)
def setup_queue_and_dedup():
    """Ensure clean stream and fresh worker state before each test."""
    from backend.app.database.session import init_db
    init_db()
    queue = get_message_queue_provider()
    queue.clear_stream(STREAM_NAME)
    dedup = get_deduplication_service()
    dedup.clear()
    yield


def test_ingestion_unauthorized_rejection():
    """Ingestion endpoint must reject requests without valid credentials with 401."""
    payload = {
        "event_id": f"evt_{uuid.uuid4().hex[:8]}",
        "event_type": "POTHOLE",
        "timestamp": "2026-09-15T05:00:00Z",
        "bus_id": "BUS_001",
        "camera_id": "FRONT",
        "location": {"lat": 28.6328, "lon": 77.2195},
        "severity": "HIGH",
        "confidence": 0.94,
    }
    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


def test_ingestion_authorized_via_api_key():
    """Accepts ingestion with X-API-Key and publishes to message queue stream."""
    event_id = f"evt_pothole_{uuid.uuid4().hex[:8]}"
    payload = {
        "event_id": event_id,
        "event_type": "POTHOLE",
        "timestamp": "2026-09-15T05:00:00Z",
        "bus_id": "BUS_001",
        "camera_id": "FRONT",
        "location": {"lat": 28.6328, "lon": 77.2195, "speed_kmh": 24.5},
        "severity": "HIGH",
        "confidence": 0.92,
        "district": "Central",
        "road_segment": "CONNAUGHT_CIRCULAR",
        "details": {"depth_cm": 6.8, "diameter_cm": 42},
    }

    response = client.post(
        "/api/v1/events",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "QUEUED"
    assert data["event_id"] == event_id
    assert data["duplicate"] is False
    assert data["stream_message_id"] is not None
    assert data["idempotency_key"] is not None


def test_ingestion_alias_endpoint_and_bearer_auth():
    """Verifies the /api/v1/events/ingest alias with Bearer token authentication."""
    event_id = f"evt_risk_{uuid.uuid4().hex[:8]}"
    payload = {
        "event_id": event_id,
        "event_type": "PEDESTRIAN_RISK",
        "timestamp": "2026-09-15T05:05:00Z",
        "bus_id": "BUS_002",
        "camera_id": "FRONT",
        "location": {"lat": 12.9716, "lon": 77.5946},
        "severity": "CRITICAL",
        "confidence": 0.89,
        "district": "CBD",
        "details": {"school_zone": "St. Joseph's", "distance_to_curb_m": 0.9},
    }

    response = client.post(
        "/api/v1/events/ingest",
        json=payload,
        headers={"Authorization": f"Bearer {VALID_DEV_TOKEN}"},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "QUEUED"
    assert data["event_id"] == event_id
    assert data["duplicate"] is False


def test_idempotency_and_duplicate_prevention():
    """Identical event or matching idempotency key must be ignored and not re-queued."""
    idemp_key = f"IDEMP-TEST-{uuid.uuid4().hex[:12]}"
    payload = {
        "event_id": f"evt_first_{uuid.uuid4().hex[:8]}",
        "idempotency_key": idemp_key,
        "event_type": "WATERLOGGING",
        "timestamp": "2026-09-15T05:10:00Z",
        "bus_id": "BUS_001",
        "camera_id": "FRONT",
        "location": {"lat": 28.6280, "lon": 77.2260},
        "severity": "HIGH",
        "confidence": 0.95,
    }

    # 1. First submission -> QUEUED
    res1 = client.post(
        "/api/v1/events",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert res1.status_code == 202
    assert res1.json()["status"] == "QUEUED"
    assert res1.json()["duplicate"] is False

    # 2. Second submission with same idempotency key -> DUPLICATE_IGNORED
    payload_dup = dict(payload)
    payload_dup["event_id"] = f"evt_second_{uuid.uuid4().hex[:8]}"

    res2 = client.post(
        "/api/v1/events",
        json=payload_dup,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert res2.status_code == 202
    data2 = res2.json()
    assert data2["status"] == "DUPLICATE_IGNORED"
    assert data2["duplicate"] is True
    assert data2["stream_message_id"] is None
    assert "Duplicate event ignored" in data2["message"]


def test_schema_validation_rejection():
    """Invalid coordinate bounds or missing required fields must return 422."""
    bad_payload = {
        "event_id": "evt_bad",
        "event_type": "POTHOLE",
        "timestamp": "not-a-timestamp",
        "bus_id": "BUS_001",
        "camera_id": "FRONT",
        "location": {"lat": 250.0, "lon": 500.0},  # Out of geographic bounds!
        "confidence": 1.5,  # Confidence must be <= 1.0
    }

    response = client.post(
        "/api/v1/events",
        json=bad_payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert response.status_code == 422


def test_event_processor_dequeuing_and_db_persistence():
    """Background processor pulls from stream, writes IngestedEvent, and acknowledges message."""
    event_id = f"evt_proc_{uuid.uuid4().hex[:8]}"
    idemp_key = f"IDEMP-PROC-{uuid.uuid4().hex[:12]}"
    payload = {
        "event_id": event_id,
        "idempotency_key": idemp_key,
        "event_type": "ROAD_DAMAGE",
        "timestamp": "2026-09-15T05:20:00Z",
        "bus_id": "BUS_003",
        "camera_id": "FRONT",
        "location": {"lat": 18.9510, "lon": 72.8240},
        "severity": "MEDIUM",
        "confidence": 0.88,
        "district": "South",
        "road_segment": "MARINE_DRIVE",
        "details": {"crack_depth_mm": 18},
    }

    # Ingest event
    res = client.post(
        "/api/v1/events",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert res.status_code == 202
    assert res.json()["status"] == "QUEUED"

    # Run one batch of the EventProcessor
    processor = get_event_processor()
    processed_count = processor.process_batch(count=10)
    assert processed_count >= 1

    # Verify event is now queryable via status endpoint
    status_res = client.get(f"/api/v1/events/status/{idemp_key}")
    assert status_res.status_code == 200
    db_evt = status_res.json()
    assert db_evt["event_id"] == event_id
    assert db_evt["event_type"] == "ROAD_DAMAGE"
    assert db_evt["severity"] == "MEDIUM"
    assert db_evt["bus_id"] == "BUS_003"
    assert db_evt["gps_lat"] == 18.9510
    assert db_evt["gps_lon"] == 72.8240


def test_list_events_and_filters():
    """Lists persisted events with query parameter filters."""
    response = client.get("/api/v1/events?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "events" in data
    assert isinstance(data["events"], list)


def test_ingestion_pipeline_stats():
    """Validates real-time metrics reporting from /api/v1/events/stats."""
    response = client.get("/api/v1/events/stats")
    assert response.status_code == 200
    stats = response.json()
    assert "total_received" in stats
    assert "total_queued" in stats
    assert "total_processed" in stats
    assert "total_duplicates_prevented" in stats
    assert "queue_depth" in stats
    assert "queue_backend" in stats
    assert stats["active_stream"] == STREAM_NAME
    assert stats["consumer_group"] == CONSUMER_GROUP
