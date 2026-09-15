"""
Message Queue Provider Factory
==============================
Instantiates and provides the active MessageQueueProvider.
Defaults to Redis Streams; falls back gracefully to InMemoryStreamsProvider.
Allows future swapping to KafkaProvider or RabbitMQProvider.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from .base import MessageQueueProvider
from .memory_streams import InMemoryStreamsProvider

logger = logging.getLogger("queue.factory")

_active_provider: Optional[MessageQueueProvider] = None


def get_message_queue_provider() -> MessageQueueProvider:
    """
    Returns the active singleton MessageQueueProvider.
    Tries Redis Streams first if requested/available; falls back to InMemoryStreamsProvider.
    """
    global _active_provider
    if _active_provider is not None:
        return _active_provider

    backend_type = os.getenv("MESSAGE_QUEUE_BACKEND", "redis").lower()
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    if backend_type == "redis":
        try:
            from .redis_streams import RedisStreamsProvider
            provider = RedisStreamsProvider(redis_url=redis_url)
            _active_provider = provider
            logger.info("Using Redis Streams as message queue provider.")
            return provider
        except Exception as e:
            logger.warning(f"Redis Streams unavailable ({e}). Falling back to InMemoryStreamsProvider.")

    # Fallback to in-memory streams
    provider = InMemoryStreamsProvider()
    _active_provider = provider
    logger.info("Using InMemoryStreamsProvider for standalone execution.")
    return provider


def set_message_queue_provider(provider: MessageQueueProvider):
    """Overrides the active message queue provider (e.g. for testing)."""
    global _active_provider
    _active_provider = provider
