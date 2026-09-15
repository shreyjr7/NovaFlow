"""
In-Memory Message Queue Stream Provider
=======================================
Thread-safe in-memory stream queue mirroring Redis Streams semantics.
Provides reliable standalone operation and test suite isolation.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import MessageQueueProvider

logger = logging.getLogger("queue.memory")


class InMemoryStreamsProvider(MessageQueueProvider):
    """
    Simulates Redis Streams in memory with full Consumer Group support.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # stream_name -> list of (message_id, data_dict)
        self._streams: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
        # (stream, group) -> last_delivered_index
        self._consumer_offsets: Dict[Tuple[str, str], int] = {}
        # (stream, group) -> set of acknowledged message IDs
        self._acknowledged: Dict[Tuple[str, str], Set[str]] = {}
        self._seq = 0

    def publish(self, stream: str, message: Dict[str, Any]) -> str:
        with self._lock:
            if stream not in self._streams:
                self._streams[stream] = []
            self._seq += 1
            msg_id = f"{int(time.time() * 1000)}-{self._seq}"
            # Deep copy / serialize to mimic Redis network boundary
            payload = json.loads(json.dumps(message))
            self._streams[stream].append((msg_id, payload))
            return msg_id

    def create_consumer_group(self, stream: str, group: str) -> bool:
        with self._lock:
            if stream not in self._streams:
                self._streams[stream] = []
            key = (stream, group)
            if key not in self._consumer_offsets:
                self._consumer_offsets[key] = 0
                self._acknowledged[key] = set()
                return True
            return False

    def read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 10,
        block_ms: int = 1000,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        key = (stream, group)
        with self._lock:
            if stream not in self._streams:
                self._streams[stream] = []
            if key not in self._consumer_offsets:
                self._consumer_offsets[key] = 0
                self._acknowledged[key] = set()

            offset = self._consumer_offsets[key]
            all_msgs = self._streams[stream]

            if offset >= len(all_msgs):
                return []

            batch = all_msgs[offset : offset + count]
            self._consumer_offsets[key] = offset + len(batch)
            return list(batch)

    def acknowledge(self, stream: str, group: str, message_ids: List[str]) -> int:
        key = (stream, group)
        with self._lock:
            if key not in self._acknowledged:
                self._acknowledged[key] = set()
            acked = 0
            for mid in message_ids:
                if mid not in self._acknowledged[key]:
                    self._acknowledged[key].add(mid)
                    acked += 1
            return acked

    def get_queue_metrics(self, stream: str, group: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            msgs = self._streams.get(stream, [])
            total_len = len(msgs)
            if group:
                key = (stream, group)
                offset = self._consumer_offsets.get(key, 0)
                acked_set = self._acknowledged.get(key, set())
                pending = max(0, offset - len(acked_set))
                unconsumed = max(0, total_len - offset)
            else:
                pending = 0
                unconsumed = total_len

            return {
                "backend": "memory",
                "stream": stream,
                "length": total_len,
                "pending": pending,
                "unconsumed": unconsumed,
            }

    def clear_stream(self, stream: str) -> bool:
        with self._lock:
            if stream in self._streams:
                self._streams[stream].clear()
            for key in list(self._consumer_offsets.keys()):
                if key[0] == stream:
                    self._consumer_offsets[key] = 0
                    self._acknowledged[key].clear()
            return True
