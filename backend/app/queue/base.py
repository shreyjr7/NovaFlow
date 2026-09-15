"""
Abstract Message Queue Provider Interface
=========================================
Defines the uniform contract for stream messaging providers.
Allows seamless interchangeability between:
  - Redis Streams (Hackathon MVP)
  - In-Memory Streams (Local dev & test isolation)
  - Apache Kafka (Production enterprise migration)
  - RabbitMQ (AMQP migration)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class MessageQueueProvider(ABC):
    """
    Abstract contract for decoupled message queue backends.
    """

    @abstractmethod
    def publish(self, stream: str, message: Dict[str, Any]) -> str:
        """
        Publishes a message payload to the specified stream.
        Returns the unique stream message ID (e.g. '1694750000000-0').
        """
        pass

    @abstractmethod
    def create_consumer_group(self, stream: str, group: str) -> bool:
        """
        Creates a persistent consumer group on the stream if it does not already exist.
        """
        pass

    @abstractmethod
    def read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 10,
        block_ms: int = 1000,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Reads a batch of messages for a consumer in a consumer group.
        Returns a list of tuples: (message_id, message_dict).
        """
        pass

    @abstractmethod
    def acknowledge(self, stream: str, group: str, message_ids: List[str]) -> int:
        """
        Acknowledges that messages were successfully processed by the consumer group.
        Returns the count of successfully acknowledged messages.
        """
        pass

    @abstractmethod
    def get_queue_metrics(self, stream: str, group: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves live metrics: stream length, pending messages, consumer count.
        """
        pass

    @abstractmethod
    def clear_stream(self, stream: str) -> bool:
        """
        Clears or trims stream records (useful for test resets).
        """
        pass
