"""
Network State Manager & Store-and-Forward Reconnection Engine
=============================================================
Coordinates edge network availability state machine:
  - ONLINE:       Direct streaming to Central Server + background queue drainage
  - OFFLINE:      Zero-network transmission; all events divert to local SQLite queue
  - RECONNECTING: Connection established; draining local buffer with retry backoff

UI Indicator Formatting:
  - Online:
      Network:
      ONLINE
  - Offline:
      NETWORK:
      OFFLINE
      17 EVENTS BUFFERED
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .sqlite_queue import SqliteEventQueue

logger = logging.getLogger("edge.network_manager")


class NetworkManager:
    """
    Manages edge network status and coordinates the store-and-forward retransmission loop.
    """

    STATE_ONLINE       = "ONLINE"
    STATE_OFFLINE      = "OFFLINE"
    STATE_RECONNECTING = "RECONNECTING"

    def __init__(
        self,
        sqlite_queue: Optional[SqliteEventQueue] = None,
        initial_state: str = STATE_ONLINE,
        retry_interval_s: float = 3.0,
        batch_size: int = 15,
    ):
        self.queue = sqlite_queue or SqliteEventQueue()
        self._state = initial_state
        self._simulated_mode: Optional[str] = None
        self._retry_interval_s = retry_interval_s
        self._batch_size = batch_size
        self._lock = threading.Lock()

        self._stop_event = threading.Event()
        self._drain_thread: Optional[threading.Thread] = None
        self._send_fn: Optional[Callable[[Dict[str, Any]], bool]] = None

    @property
    def current_state(self) -> str:
        with self._lock:
            if self._simulated_mode is not None:
                return self._simulated_mode
            return self._state

    def set_mode(self, mode: str):
        """
        Manually forces network simulation mode: 'ONLINE', 'OFFLINE', 'RECONNECTING', or 'AUTO'.
        """
        mode_upper = mode.upper()
        with self._lock:
            if mode_upper in (self.STATE_ONLINE, self.STATE_OFFLINE, self.STATE_RECONNECTING):
                self._simulated_mode = mode_upper
                self._state = mode_upper
                logger.info(f"Network simulation mode set to: {mode_upper}")
            elif mode_upper == "AUTO":
                self._simulated_mode = None
                logger.info("Network simulation mode set to AUTO (live probe)")
            else:
                raise ValueError(f"Invalid network mode: {mode}")

    def is_online(self) -> bool:
        return self.current_state == self.STATE_ONLINE

    def is_offline(self) -> bool:
        return self.current_state == self.STATE_OFFLINE

    def is_reconnecting(self) -> bool:
        return self.current_state == self.STATE_RECONNECTING

    def get_status_text(self) -> str:
        """
        Generates standard UI indicator text matching prompt requirements:
          Network:
          ONLINE
          or
          NETWORK:
          OFFLINE
          17 EVENTS BUFFERED
        """
        st = self.current_state
        buffered = self.queue.pending_count()

        if st == self.STATE_ONLINE:
            return "Network:\nONLINE"
        elif st == self.STATE_RECONNECTING:
            return f"NETWORK:\nRECONNECTING\n{buffered} EVENTS BUFFERED"
        else:
            return f"NETWORK:\nOFFLINE\n{buffered} EVENTS BUFFERED"

    def get_status_single_line(self) -> str:
        """Single-line summary for badges."""
        st = self.current_state
        buffered = self.queue.pending_count()
        if st == self.STATE_ONLINE:
            return "Network: ONLINE"
        return f"NETWORK: {st} ({buffered} EVENTS BUFFERED)"

    def register_send_function(self, send_fn: Callable[[Dict[str, Any]], bool]):
        """Sets the HTTP sender callback used to transmit buffered events to Central API."""
        self._send_fn = send_fn

    def drain_queue_batch(self, send_fn: Optional[Callable[[Dict[str, Any]], bool]] = None) -> int:
        """
        Drains up to `batch_size` pending events from the SQLite queue.
        On success -> acknowledge() deletes event from queue.
        On failure -> record_failure() increments retry counter.
        """
        fn = send_fn or self._send_fn
        if not fn:
            return 0

        # Only drain if network is not strictly OFFLINE
        if self.is_offline():
            return 0

        batch = self.queue.peek_batch(batch_size=self._batch_size)
        if not batch:
            # If queue is empty and we were reconnecting, transition to ONLINE
            with self._lock:
                if self._state == self.STATE_RECONNECTING and self._simulated_mode is None:
                    self._state = self.STATE_ONLINE
                    logger.info("Local buffer fully drained; transition to ONLINE")
            return 0

        delivered_count = 0
        for item in batch:
            eid = item["event_id"]
            ev_payload = item["event"] or item
            try:
                success = fn(ev_payload)
                if success:
                    self.queue.acknowledge(eid)
                    delivered_count += 1
                else:
                    self.queue.record_failure(eid, "Central API returned non-200")
            except Exception as exc:
                self.queue.record_failure(eid, str(exc))

        logger.info(f"Drained {delivered_count}/{len(batch)} buffered events from SQLite queue")
        return delivered_count

    def start_drain_worker(self, send_fn: Callable[[Dict[str, Any]], bool]):
        """Starts background worker thread to drain buffered queue when network is available."""
        self._send_fn = send_fn
        self._stop_event.clear()
        if self._drain_thread and self._drain_thread.is_alive():
            return

        def _worker():
            logger.info("Store-and-forward queue drain worker started")
            while not self._stop_event.is_set():
                if self.is_online() or self.is_reconnecting():
                    try:
                        self.drain_queue_batch(self._send_fn)
                    except Exception as e:
                        logger.error(f"Error in drain worker: {e}")
                self._stop_event.wait(self._retry_interval_s)
            logger.info("Store-and-forward queue drain worker stopped")

        self._drain_thread = threading.Thread(target=_worker, daemon=True, name="edge-buffer-drainer")
        self._drain_thread.start()

    def get_status_dict(self) -> Dict[str, Any]:
        """Returns structured status dictionary for API and WebSocket broadcasts."""
        return {
            "state": self.current_state,
            "simulated_mode": self._simulated_mode,
            "indicator": self.get_status_text(),
            "indicator_single_line": self.get_status_single_line(),
            "pending_count": self.queue.pending_count(),
            "queue": self.queue.get_queue_status(),
        }

    def stop_drain_worker(self):
        self._stop_event.set()
        if self._drain_thread:
            self._drain_thread.join(timeout=2.0)


_default_network_manager: Optional[NetworkManager] = None


def get_network_manager() -> NetworkManager:
    """Returns the singleton NetworkManager instance."""
    global _default_network_manager
    if _default_network_manager is None:
        _default_network_manager = NetworkManager()
    return _default_network_manager


def set_network_manager(nm: NetworkManager):
    """Sets the singleton NetworkManager instance."""
    global _default_network_manager
    _default_network_manager = nm

