"""
Local Buffer (SQLite Store-and-Forward Implementation)
======================================================
Onboard transactional SQLite buffer for edge bus events during network disconnects.
Ensures zero data loss while enforcing storage quotas and oldest-event eviction.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .sqlite_queue import SqliteEventQueue

logger = logging.getLogger("edge.local_buffer")

_DEFAULT_STORE = Path("edge_store/event_buffer.db")


class LocalBuffer:
    """
    Store-and-forward event buffer backed by SQLite.
    Provides backward-compatible push(), pending_count(), and flush_to_api() methods.
    """

    def __init__(
        self,
        store_path: Path = _DEFAULT_STORE,
        max_events: int = 2000,
        sqlite_queue: Optional[SqliteEventQueue] = None,
    ):
        self._queue = sqlite_queue or SqliteEventQueue(db_path=store_path, max_events=max_events)

    @property
    def queue(self) -> SqliteEventQueue:
        return self._queue

    def push(self, event: Dict[str, Any]) -> bool:
        """Pushes an event into the local SQLite store-and-forward queue."""
        return self._queue.enqueue(event)

    def pending_count(self) -> int:
        """Returns number of events currently queued and awaiting delivery."""
        return self._queue.pending_count()

    def get_status(self) -> Dict[str, Any]:
        """Returns detailed queue metrics."""
        return self._queue.get_queue_status()

    def flush_to_api(self, send_fn: Callable[[Dict[str, Any]], bool], batch_size: int = 20) -> int:
        """
        Attempts to drain queued events using `send_fn(event) -> bool`.
        Removes acknowledged events from the database upon success.
        """
        sent = 0
        while True:
            batch = self._queue.peek_batch(batch_size=batch_size)
            if not batch:
                break
            for item in batch:
                eid = item["event_id"]
                payload = item["event"] or item
                try:
                    if send_fn(payload):
                        self._queue.acknowledge(eid)
                        sent += 1
                    else:
                        self._queue.record_failure(eid, "Central API delivery failed")
                except Exception as exc:
                    self._queue.record_failure(eid, str(exc))
        return sent

    def clear(self):
        """Clears all buffered records."""
        self._queue.clear()
