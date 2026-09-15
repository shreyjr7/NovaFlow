"""
SQLite Store-and-Forward Event Queue
====================================
Onboard persistent queue for bus edge devices storing events during network outages.

Schema & Stored Fields:
  - Event metadata (full JSON payload)
  - GPS (lat, lon, bearing, road_segment)
  - Timestamp (ISO 8601 UTC)
  - Confidence score
  - Evidence reference hash

Guarantees:
  - Transactional SQLite persistence
  - Configurable storage limits (max events)
  - Automatic oldest-event FIFO cleanup upon limit exhaustion
  - Retry counter with exponential backoff & dead-letter isolation on max_retries
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("edge.sqlite_queue")

DEFAULT_DB_PATH = Path("edge_store/event_buffer.db")


class SqliteEventQueue:
    """
    Thread-safe SQLite store-and-forward FIFO event queue.
    """

    def __init__(
        self,
        db_path: Path = DEFAULT_DB_PATH,
        max_events: int = 2000,
        default_max_retries: int = 5,
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_events = max_events
        self.default_max_retries = default_max_retries
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes database schema and indexes."""
        with self._lock:
            with self._get_conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS event_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT UNIQUE,
                        event_type TEXT,
                        metadata_json TEXT,
                        gps_lat REAL,
                        gps_lon REAL,
                        gps_bearing REAL,
                        gps_segment TEXT,
                        timestamp TEXT,
                        confidence REAL,
                        evidence_reference TEXT,
                        retry_count INTEGER DEFAULT 0,
                        max_retries INTEGER DEFAULT 5,
                        status TEXT DEFAULT 'PENDING',
                        created_at REAL,
                        last_retry_at REAL,
                        error_message TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_status_id ON event_queue(status, id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON event_queue(created_at)")
                conn.commit()

    def enqueue(self, event: Dict[str, Any]) -> bool:
        """
        Pushes an event to the local SQLite queue.
        Enforces storage limit: if reached, drops oldest event(s) first.
        """
        event_id = str(event.get("event_id") or f"ev_{int(time.time()*1000)}_{os.urandom(4).hex()}")
        event_type = str(event.get("event_type", "GENERIC_EVENT"))
        ts = str(event.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        conf = float(event.get("confidence", 1.0))
        ev_ref = str(event.get("evidence_reference") or event.get("evidence_ref") or "")

        gps_data = event.get("gps") or event.get("location") or {}
        lat = float(gps_data.get("lat", 0.0))
        lon = float(gps_data.get("lon", 0.0))
        bearing = float(gps_data.get("bearing_deg", gps_data.get("bearing", 0.0)))
        segment = str(gps_data.get("road_segment", ""))

        metadata_json = json.dumps(event)
        now_epoch = time.time()

        with self._lock:
            with self._get_conn() as conn:
                # Check current storage limit
                cur = conn.execute("SELECT COUNT(*) FROM event_queue WHERE status = 'PENDING'")
                pending_count = cur.fetchone()[0]

                if pending_count >= self.max_events:
                    # Evict oldest event to respect storage limit
                    self._evict_oldest_locked(conn, count=(pending_count - self.max_events + 1))

                # Insert event
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO event_queue (
                            event_id, event_type, metadata_json,
                            gps_lat, gps_lon, gps_bearing, gps_segment,
                            timestamp, confidence, evidence_reference,
                            retry_count, max_retries, status,
                            created_at, last_retry_at, error_message
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event_id, event_type, metadata_json,
                        lat, lon, bearing, segment,
                        ts, conf, ev_ref,
                        0, self.default_max_retries, "PENDING",
                        now_epoch, 0.0, None
                    ))
                    conn.commit()
                    return True
                except Exception as exc:
                    logger.error(f"Failed to enqueue event {event_id}: {exc}")
                    return False

    def _evict_oldest_locked(self, conn: sqlite3.Connection, count: int = 1) -> int:
        """Drops the oldest pending events to prevent disk exhaustion."""
        cur = conn.execute(
            "SELECT id FROM event_queue WHERE status = 'PENDING' ORDER BY id ASC LIMIT ?",
            (count,)
        )
        ids_to_drop = [r[0] for r in cur.fetchall()]
        if ids_to_drop:
            placeholders = ",".join("?" for _ in ids_to_drop)
            conn.execute(f"DELETE FROM event_queue WHERE id IN ({placeholders})", ids_to_drop)
            conn.commit()
            logger.warning(f"Storage limit reached: evicted {len(ids_to_drop)} oldest buffered events")
            return len(ids_to_drop)
        return 0

    def evict_oldest(self, count: int = 1) -> int:
        """Public method to evict oldest events."""
        with self._lock:
            with self._get_conn() as conn:
                return self._evict_oldest_locked(conn, count)

    def peek_batch(self, batch_size: int = 10, mark_in_flight: bool = True) -> List[Dict[str, Any]]:
        """
        Fetches the next FIFO batch of PENDING events for retransmission.
        Optionally sets their status to 'IN_FLIGHT'.
        """
        with self._lock:
            with self._get_conn() as conn:
                cur = conn.execute("""
                    SELECT id, event_id, event_type, metadata_json,
                           gps_lat, gps_lon, gps_bearing, gps_segment,
                           timestamp, confidence, evidence_reference,
                           retry_count, max_retries
                    FROM event_queue
                    WHERE status = 'PENDING'
                    ORDER BY id ASC
                    LIMIT ?
                """, (batch_size,))
                rows = cur.fetchall()
                if not rows:
                    return []

                if mark_in_flight:
                    ids = [r["id"] for r in rows]
                    placeholders = ",".join("?" for _ in ids)
                    conn.execute(
                        f"UPDATE event_queue SET status = 'IN_FLIGHT', last_retry_at = ? WHERE id IN ({placeholders})",
                        [time.time()] + ids
                    )
                    conn.commit()

                results = []
                for r in rows:
                    try:
                        ev_meta = json.loads(r["metadata_json"])
                    except Exception:
                        ev_meta = {}
                    results.append({
                        "id": r["id"],
                        "event_id": r["event_id"],
                        "event_type": r["event_type"],
                        "event": ev_meta,
                        "gps": {
                            "lat": r["gps_lat"],
                            "lon": r["gps_lon"],
                            "bearing_deg": r["gps_bearing"],
                            "road_segment": r["gps_segment"],
                        },
                        "timestamp": r["timestamp"],
                        "confidence": r["confidence"],
                        "evidence_reference": r["evidence_reference"],
                        "retry_count": r["retry_count"],
                        "max_retries": r["max_retries"],
                    })
                return results

    def acknowledge(self, event_id: str) -> bool:
        """
        Removes an acknowledged event from the SQLite queue upon successful Central API delivery.
        """
        with self._lock:
            with self._get_conn() as conn:
                cur = conn.execute("DELETE FROM event_queue WHERE event_id = ?", (event_id,))
                conn.commit()
                return cur.rowcount > 0

    def record_failure(self, event_id: str, error_message: str = "", error: Optional[str] = None):
        """
        Increments retry count on failure.
        If retry_count >= max_retries, transitions to DEAD_LETTER so it does not block the queue.
        """
        err_text = str(error if error is not None else error_message)
        with self._lock:
            with self._get_conn() as conn:
                cur = conn.execute(
                    "SELECT retry_count, max_retries FROM event_queue WHERE event_id = ?",
                    (event_id,)
                )
                row = cur.fetchone()
                if not row:
                    return

                new_retries = row["retry_count"] + 1
                max_retries = row["max_retries"]
                new_status = "DEAD_LETTER" if new_retries >= max_retries else "PENDING"

                conn.execute("""
                    UPDATE event_queue
                    SET retry_count = ?, status = ?, error_message = ?, last_retry_at = ?
                    WHERE event_id = ?
                """, (new_retries, new_status, err_text[:255], time.time(), event_id))
                conn.commit()

                if new_status == "DEAD_LETTER":
                    logger.warning(f"Event {event_id} exceeded max retries ({max_retries}) -> moved to DEAD_LETTER")

    def pending_count(self) -> int:
        """Returns the count of events currently queued and awaiting delivery."""
        with self._lock:
            with self._get_conn() as conn:
                cur = conn.execute("SELECT COUNT(*) FROM event_queue WHERE status IN ('PENDING', 'IN_FLIGHT')")
                return int(cur.fetchone()[0])

    def get_queue_status(self) -> Dict[str, Any]:
        """Returns complete queue status metrics and storage stats."""
        with self._lock:
            with self._get_conn() as conn:
                cur = conn.execute("""
                    SELECT
                        COUNT(CASE WHEN status = 'PENDING' THEN 1 END) as pending,
                        COUNT(CASE WHEN status = 'IN_FLIGHT' THEN 1 END) as in_flight,
                        COUNT(CASE WHEN status = 'DEAD_LETTER' THEN 1 END) as dead_letter,
                        COUNT(*) as total,
                        MIN(created_at) as oldest_epoch
                    FROM event_queue
                """)
                row = cur.fetchone()

                db_size = 0
                if self.db_path.exists():
                    db_size = self.db_path.stat().st_size

                oldest_iso = None
                if row["oldest_epoch"]:
                    oldest_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(row["oldest_epoch"]))

                return {
                    "pending_count": row["pending"],
                    "in_flight_count": row["in_flight"],
                    "dead_letter_count": row["dead_letter"],
                    "total_buffered": row["pending"] + row["in_flight"],
                    "oldest_timestamp": oldest_iso,
                    "db_size_bytes": db_size,
                    "max_events": self.max_events,
                    "storage_limit_reached": (row["pending"] >= self.max_events),
                }

    def clear(self):
        """Clears all records in the queue."""
        with self._lock:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM event_queue")
                conn.commit()
