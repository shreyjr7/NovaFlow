"""
Redis Streams Message Queue Provider (Hackathon MVP)
====================================================
Implements MessageQueueProvider on top of Redis Streams:
  - XADD: Stream message publishing
  - XGROUP CREATE: Consumer group declaration
  - XREADGROUP: Distributed consumer pull
  - XACK: Consumer group message acknowledgment
  - XLEN / XPENDING: Real-time queue depth & lag inspection
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from .base import MessageQueueProvider

logger = logging.getLogger("queue.redis")

try:
    import redis
    _REDIS_AVAILABLE = True
except ImportError:
    redis = None
    _REDIS_AVAILABLE = False


class RedisStreamsProvider(MessageQueueProvider):
    """
    Production-ready Redis Streams implementation of MessageQueueProvider.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        if not _REDIS_AVAILABLE:
            raise RuntimeError("The 'redis' Python package is required for RedisStreamsProvider.")
        self.redis_url = redis_url
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        # Test connection
        self._client.ping()
        logger.info(f"Connected to Redis Streams at {redis_url}")

    def publish(self, stream: str, message: Dict[str, Any]) -> str:
        payload_str = json.dumps(message)
        msg_id = self._client.xadd(stream, {"payload": payload_str})
        return str(msg_id)

    def create_consumer_group(self, stream: str, group: str) -> bool:
        try:
            self._client.xgroup_create(stream, group, id="0", mkstream=True)
            return True
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                # Group already exists
                return False
            raise

    def read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 10,
        block_ms: int = 1000,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        try:
            resp = self._client.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: ">"},
                count=count,
                block=block_ms,
            )
            if not resp:
                return []

            results = []
            for stream_name, messages in resp:
                for msg_id, fields in messages:
                    payload_str = fields.get("payload", "{}")
                    try:
                        msg_dict = json.loads(payload_str)
                    except Exception:
                        msg_dict = fields
                    results.append((str(msg_id), msg_dict))
            return results
        except Exception as e:
            logger.error(f"Error reading from Redis Stream {stream}: {e}")
            return []

    def acknowledge(self, stream: str, group: str, message_ids: List[str]) -> int:
        if not message_ids:
            return 0
        return self._client.xack(stream, group, *message_ids)

    def get_queue_metrics(self, stream: str, group: Optional[str] = None) -> Dict[str, Any]:
        try:
            total_len = self._client.xlen(stream)
            pending_count = 0
            if group:
                try:
                    pending_info = self._client.xpending(stream, group)
                    if pending_info:
                        pending_count = pending_info.get("pending", 0)
                except Exception:
                    pass
            return {
                "backend": "redis",
                "stream": stream,
                "length": total_len,
                "pending": pending_count,
            }
        except Exception as e:
            logger.warning(f"Could not retrieve Redis queue metrics: {e}")
            return {"backend": "redis", "stream": stream, "error": str(e)}

    def clear_stream(self, stream: str) -> bool:
        try:
            self._client.delete(stream)
            return True
        except Exception:
            return False
