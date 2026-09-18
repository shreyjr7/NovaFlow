"""
Event Processor Background Consumer Worker
===========================================
Asynchronously consumes raw ingested events from the Message Queue (Redis Streams),
executes deduplication validation against PostGIS/database, persists canonical entities,
and triggers downstream analytics / domain notifications.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from ..database.session import engine
from ..models.ingested_event import IngestedEvent
from ..queue.base import MessageQueueProvider
from ..queue.factory import get_message_queue_provider
from .deduplication import get_deduplication_service

logger = logging.getLogger("services.event_processor")

STREAM_NAME = "novaflow-events"
CONSUMER_GROUP = "novaflow-event-processors"
CONSUMER_NAME = "worker-1"


class EventProcessor:
    """
    Background worker that drains message queue streams, enforces database
    idempotency, and stores spatial event records.
    """

    def __init__(self, queue_provider: Optional[MessageQueueProvider] = None):
        self.queue = queue_provider or get_message_queue_provider()
        self.dedup = get_deduplication_service()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._total_processed = 0
        self._init_group()

    def _init_group(self):
        try:
            self.queue.create_consumer_group(STREAM_NAME, CONSUMER_GROUP)
        except Exception as e:
            logger.debug(f"Consumer group init note: {e}")

    def process_message(self, message_id: str, msg: Dict[str, Any]) -> bool:
        """
        Processes a single message: validates deduplication in DB, persists to IngestedEvent,
        and returns True on success.
        """
        idemp_key = msg.get("idempotency_key") or f"idemp_{msg.get('event_id')}"
        event_id = msg.get("event_id") or f"ev_{int(time.time()*1000)}"

        # 1. Deduplication check against persistent database
        with Session(engine) as session:
            stmt = select(IngestedEvent).where(IngestedEvent.idempotency_key == idemp_key)
            existing = session.exec(stmt).first()
            if existing:
                logger.info(f"Processor: duplicate event {idemp_key} detected in database; skipping persistence.")
                self.dedup.check_and_mark(idemp_key, event_id)
                return True

            # Parse timestamp
            ts_val = msg.get("timestamp")
            if isinstance(ts_val, str):
                try:
                    dt = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
                except Exception:
                    dt = datetime.now(timezone.utc)
            elif isinstance(ts_val, datetime):
                dt = ts_val
            else:
                dt = datetime.now(timezone.utc)

            gps_data = msg.get("gps") or {}
            lat = float(gps_data.get("lat", 0.0))
            lon = float(gps_data.get("lon", 0.0))
            bearing = gps_data.get("bearing_deg")
            seg = gps_data.get("road_segment") or "UNKNOWN_SEGMENT"
            address = gps_data.get("address") or ""

            # Classify district from segment or coords
            district = "Central"
            if "MG_ROAD" in seg or "CONNAUGHT" in seg:
                district = "Central"
            elif "OUTER" in seg or "AIRPORT" in seg:
                district = "North"
            elif "SUBURB" in seg or "RING" in seg:
                district = "South"

            # Create canonical database record
            route_id_val = str(msg.get("route_id") or msg.get("routeId") or "R-01")
            raw_status = str(msg.get("status") or "unverified").lower()
            if raw_status in ("active", "ai_detected"):
                raw_status = "unverified"

            db_event = IngestedEvent(
                idempotency_key=idemp_key,
                event_id=event_id,
                event_type=str(msg.get("event_type", "GENERIC")).upper(),
                bus_id=str(msg.get("bus_id", "BUS_001")),
                route_id=route_id_val,
                camera_id=str(msg.get("camera_id", "FRONT")),
                timestamp=dt,
                gps_lat=lat,
                gps_lon=lon,
                bearing_deg=bearing,
                road_segment=seg,
                address=address,
                district=district,
                confidence=float(msg.get("confidence", 1.0)),
                evidence_reference=str(msg.get("evidence_reference") or ""),
                evidence_image_b64=msg.get("evidence_image_b64"),
                evidence_clip_url=msg.get("evidence_clip_url"),
                severity=str(msg.get("severity", "medium")).lower(),
                status=raw_status,
                metadata_json=json.dumps(msg.get("details", {})),
                processed_at=datetime.now(timezone.utc),
            )
            session.add(db_event)
            session.commit()
            session.refresh(db_event)

            self._total_processed += 1
            logger.debug(f"Persisted event {event_id} ({db_event.event_type}) with PostGIS coordinates.")

            # Hook into Spatial-Temporal Deduplication & Clustering (Phase 19)
            try:
                from .spatial_clustering_service import get_spatial_clustering_service
                from ..schemas.spatial_clustering import RawObservationIn
                cluster_svc = get_spatial_clustering_service()
                cluster_svc.ingest_observation(
                    RawObservationIn(
                        event_id=event_id,
                        bus_id=str(msg.get("bus_id", "BUS_001")),
                        camera_id=str(msg.get("camera_id", "FRONT")),
                        lat=lat,
                        lon=lon,
                        timestamp=dt.isoformat(),
                        confidence=float(msg.get("confidence", 1.0)),
                        defect_type=str(msg.get("event_type", "POTHOLE")).upper(),
                        severity=str(msg.get("severity", "MEDIUM")).upper(),
                        road_segment=seg,
                    )
                )
            except Exception as ce:
                logger.debug(f"Spatial clustering hook notice: {ce}")

            return True

    def process_batch(self, count: int = 10) -> int:
        """
        Pulls and processes up to `count` messages from the stream consumer group.
        Acknowledges messages upon successful processing.
        """
        messages = self.queue.read_group(
            stream=STREAM_NAME,
            group=CONSUMER_GROUP,
            consumer=CONSUMER_NAME,
            count=count,
            block_ms=500,
        )
        if not messages:
            return 0

        acked_ids = []
        for msg_id, payload in messages:
            try:
                success = self.process_message(msg_id, payload)
                if success:
                    acked_ids.append(msg_id)
            except Exception as e:
                logger.error(f"Error processing message {msg_id}: {e}")

        if acked_ids:
            self.queue.acknowledge(STREAM_NAME, CONSUMER_GROUP, acked_ids)

        return len(acked_ids)

    def start_worker(self):
        """Starts background worker polling thread."""
        self._stop_event.clear()
        if self._thread and self._thread.is_alive():
            return

        def _run():
            logger.info("Event processor background consumer started.")
            while not self._stop_event.is_set():
                try:
                    self.process_batch(count=15)
                except Exception as e:
                    logger.error(f"Processor worker error: {e}")
                self._stop_event.wait(0.5)
            logger.info("Event processor background consumer stopped.")

        self._thread = threading.Thread(target=_run, daemon=True, name="novaflow-event-worker")
        self._thread.start()

    def stop_worker(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    @property
    def total_processed(self) -> int:
        return self._total_processed


_default_event_processor: Optional[EventProcessor] = None


def get_event_processor() -> EventProcessor:
    global _default_event_processor
    if _default_event_processor is None:
        _default_event_processor = EventProcessor()
    return _default_event_processor
