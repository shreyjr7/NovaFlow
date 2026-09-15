"""
Unit Tests for SQLite Store-and-Forward Event Queue
===================================================
Tests:
  1. Transactional initialization & schema creation
  2. Enqueue, metadata JSON serialization, GPS stamping, and peek_batch
  3. Acknowledgment and removal from queue upon central delivery
  4. Retry recording, retry limits, and dead-letter isolation
  5. Configurable storage capacity and oldest-event FIFO cleanup
  6. Queue status metrics and diagnostics
  7. LocalBuffer adapter backward compatibility
"""

import time
import pytest
from pathlib import Path
from edge.sqlite_queue import SqliteEventQueue
from edge.local_buffer import LocalBuffer


def test_sqlite_queue_init_and_table_creation(tmp_path: Path):
    db_file = tmp_path / "test_events.db"
    q = SqliteEventQueue(db_path=db_file, max_events=100)

    assert db_file.exists()
    status = q.get_queue_status()
    assert status["pending_count"] == 0
    assert status["dead_letter_count"] == 0
    assert status["max_events"] == 100


def test_enqueue_and_peek_batch(tmp_path: Path):
    db_file = tmp_path / "test_events.db"
    q = SqliteEventQueue(db_path=db_file)

    event_payload = {
        "event_id": "evt_pothole_001",
        "event_type": "POTHOLE",
        "confidence": 0.92,
        "gps": {"lat": 12.9716, "lon": 77.5946, "bearing_deg": 90.0, "road_segment": "SEG_1"},
        "evidence_reference": "sha256:abc123hash",
        "details": {"depth_cm": 5.2},
    }

    ok = q.enqueue(event_payload)
    assert ok is True
    assert q.pending_count() == 1

    batch = q.peek_batch(batch_size=10)
    assert len(batch) == 1
    item = batch[0]
    assert item["event_id"] == "evt_pothole_001"
    assert item["event_type"] == "POTHOLE"
    assert item["confidence"] == 0.92
    assert item["gps"]["lat"] == 12.9716
    assert item["evidence_reference"] == "sha256:abc123hash"
    assert item["event"]["details"]["depth_cm"] == 5.2


def test_acknowledgment_removes_from_queue(tmp_path: Path):
    db_file = tmp_path / "test_events.db"
    q = SqliteEventQueue(db_path=db_file)

    q.enqueue({"event_id": "evt_ack_01", "event_type": "TEST_1"})
    q.enqueue({"event_id": "evt_ack_02", "event_type": "TEST_2"})
    assert q.pending_count() == 2

    batch = q.peek_batch(batch_size=5, mark_in_flight=False)
    assert len(batch) == 2

    # Acknowledge first event
    acked = q.acknowledge("evt_ack_01")
    assert acked is True
    assert q.pending_count() == 1

    remaining = q.peek_batch(batch_size=5, mark_in_flight=False)
    assert len(remaining) == 1
    assert remaining[0]["event_id"] == "evt_ack_02"


def test_record_failure_and_dead_letter(tmp_path: Path):
    db_file = tmp_path / "test_events.db"
    # max retries set to 3
    q = SqliteEventQueue(db_path=db_file, default_max_retries=3)

    q.enqueue({"event_id": "evt_fail_01", "event_type": "FAIL_TEST"})
    assert q.pending_count() == 1

    # Retry 1
    q.record_failure("evt_fail_01", error="500 Internal Error")
    status = q.get_queue_status()
    assert status["pending_count"] == 1
    assert status["dead_letter_count"] == 0

    # Retry 2
    q.record_failure("evt_fail_01", error="503 Service Unavailable")
    status = q.get_queue_status()
    assert status["pending_count"] == 1
    assert status["dead_letter_count"] == 0

    # Retry 3 (reaches max_retries -> DEAD_LETTER)
    q.record_failure("evt_fail_01", error="Connection reset by peer")
    status = q.get_queue_status()
    assert status["pending_count"] == 0
    assert status["dead_letter_count"] == 1

    # Dead letter events are isolated and not returned in normal peek_batch
    batch = q.peek_batch()
    assert len(batch) == 0


def test_storage_limit_and_oldest_event_fifo_cleanup(tmp_path: Path):
    db_file = tmp_path / "test_events.db"
    # Set capacity to exactly 3 events
    q = SqliteEventQueue(db_path=db_file, max_events=3)

    q.enqueue({"event_id": "evt_oldest", "timestamp": "2026-09-15T00:00:01Z"})
    time.sleep(0.01)
    q.enqueue({"event_id": "evt_middle", "timestamp": "2026-09-15T00:00:02Z"})
    time.sleep(0.01)
    q.enqueue({"event_id": "evt_newest", "timestamp": "2026-09-15T00:00:03Z"})

    assert q.pending_count() == 3

    # Enqueue a 4th event exceeding max_events
    time.sleep(0.01)
    q.enqueue({"event_id": "evt_overflow", "timestamp": "2026-09-15T00:00:04Z"})

    # Capacity must still be 3
    assert q.pending_count() == 3

    # Oldest event should have been dropped
    batch = q.peek_batch(batch_size=10)
    eids = [item["event_id"] for item in batch]
    assert "evt_oldest" not in eids
    assert "evt_middle" in eids
    assert "evt_newest" in eids
    assert "evt_overflow" in eids


def test_local_buffer_adapter(tmp_path: Path):
    db_file = tmp_path / "test_buffer.db"
    buf = LocalBuffer(store_path=db_file, max_events=50)

    buf.push({"event_id": "b_01", "event_type": "PEDESTRIAN_RISK"})
    buf.push({"event_id": "b_02", "event_type": "POSSIBLE_INCIDENT"})

    assert buf.pending_count() == 2
    metrics = buf.get_status()
    assert metrics["pending_count"] == 2

    # Flush with a mock send_fn
    sent_items = []
    def mock_sender(evt):
        sent_items.append(evt["event_id"])
        return True

    sent_count = buf.flush_to_api(mock_sender)
    assert sent_count == 2
    assert buf.pending_count() == 0
    assert sent_items == ["b_01", "b_02"]
