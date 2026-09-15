"""
Incident & Hit-and-Run Anomaly Detection Engine
================================================
Implements the 10-step incident workflow triggered exclusively by compound
physical trajectory conditions.

Strict Legal & Ethical Constraints:
  1. System NEVER asserts legal fault or criminal liability.
  2. Event type is strictly labeled 'POSSIBLE_INCIDENT' (never 'CONFIRMED CRIME' or 'DRIVER AT FAULT').
  3. Every alert enforces 'PENDING_REVIEW' verification status.
  4. Solitary hard-braking is rejected as normal vehicle operation.
"""

from __future__ import annotations

import logging
import math
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .signals import (
    SignalResult,
    TrajectorySignalEvaluator,
    VehicleTrackState,
)
from .rolling_buffer import RollingFrameBuffer
from .anpr import NumberPlateRecognizer, AnprResult

logger = logging.getLogger("edge.incident.detector")

LEGAL_DISCLAIMER = (
    "Preliminary automated sensor anomaly alert. Does not determine legal fault, "
    "criminal culpability, or driver liability. Human verification required before any enforcement action."
)


class IncidentAnomalyDetector:
    """
    Edge AI engine for detecting possible traffic incidents and hit-and-run signatures.
    """

    def __init__(
        self,
        camera_id: str = "FRONT",
        bus_id: str = "BUS_01",
        rolling_buffer: Optional[RollingFrameBuffer] = None,
        cooldown_seconds: float = 8.0,
    ):
        self.camera_id = camera_id
        self.bus_id = bus_id
        self.buffer = rolling_buffer or RollingFrameBuffer(capacity=30)
        self.signal_evaluator = TrajectorySignalEvaluator()
        self.anpr_engine = NumberPlateRecognizer()
        self.cooldown_seconds = cooldown_seconds

        # Track historical states across frames: track_id -> VehicleTrackState
        self._previous_states: Dict[int, VehicleTrackState] = {}
        self._last_alert_time: float = 0.0
        self._disappeared_tracker: Dict[int, float] = {}  # track_id -> timestamp

    def process_frame(
        self,
        frame: Any,
        tracks: List[Dict[str, Any]],
        gps: Dict[str, Any],
        timestamp: Optional[str] = None,
        frame_idx: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Processes a frame with tracked vehicle inputs.
        If compound anomaly condition is met, executes the 10-step incident workflow.
        """
        now_ts = time.time()
        iso_timestamp = timestamp or datetime.now(timezone.utc).isoformat()

        # Update rolling buffer
        self.buffer.push(
            frame=frame,
            timestamp_s=now_ts,
            frame_idx=frame_idx,
            gps=gps,
        )

        current_track_states: List[VehicleTrackState] = []
        active_ids = set()

        for t in tracks:
            tid = int(t.get("track_id", 0))
            active_ids.add(tid)
            cls_name = str(t.get("class", "car")).lower()
            speed = float(t.get("speed_kmh", 30.0))
            bbox = t.get("bbox", [0, 0, 50, 50])
            heading = float(t.get("heading_deg", 0.0))

            # Correlate with historical state
            prev = self._previous_states.get(tid)
            prev_speed = prev.speed_kmh if prev else None
            prev_heading = prev.heading_deg if prev else None
            prev_bbox = prev.bbox if prev else None
            had_interaction = prev.had_recent_interaction if prev else False
            interaction_tid = prev.interaction_track_id if prev else None

            # Acceleration estimation
            accel = 0.0
            if prev_speed is not None:
                accel = ((speed - prev_speed) / 3.6) / 0.2  # assuming ~5Hz

            state = VehicleTrackState(
                track_id=tid,
                class_name=cls_name,
                speed_kmh=speed,
                bbox=bbox,
                heading_deg=heading,
                prev_speed_kmh=prev_speed,
                prev_heading_deg=prev_heading,
                prev_bbox=prev_bbox,
                acceleration_m_s2=accel,
                had_recent_interaction=had_interaction,
                interaction_track_id=interaction_tid,
            )
            current_track_states.append(state)

        # Detect disappeared tracks (tracks seen recently that vanished)
        for prev_tid, prev_state in self._previous_states.items():
            if prev_tid not in active_ids:
                if prev_tid not in self._disappeared_tracker:
                    self._disappeared_tracker[prev_tid] = now_ts
                elapsed = now_ts - self._disappeared_tracker[prev_tid]
                if elapsed <= 2.5:  # within recent window
                    ghost_state = VehicleTrackState(
                        track_id=prev_tid,
                        class_name=prev_state.class_name,
                        speed_kmh=0.0,
                        bbox=prev_state.bbox,
                        heading_deg=prev_state.heading_deg,
                        disappeared=True,
                        disappeared_at_s=self._disappeared_tracker[prev_tid],
                        had_recent_interaction=prev_state.had_recent_interaction,
                        interaction_track_id=prev_state.interaction_track_id,
                    )
                    current_track_states.append(ghost_state)

        # Update state cache
        self._previous_states = {s.track_id: s for s in current_track_states if not s.disappeared}

        # Check for incident anomalies
        events: List[Dict[str, Any]] = []

        # Enforce cooldown between incident bursts
        if (now_ts - self._last_alert_time) < self.cooldown_seconds:
            return events

        for primary in current_track_states:
            if primary.disappeared:
                continue

            signals = self.signal_evaluator.evaluate_signals(
                primary_track=primary,
                nearby_tracks=current_track_states,
                dt=0.2,
            )

            is_incident, category, conf = self.signal_evaluator.evaluate_compound_condition(signals)

            if is_incident:
                # ── 10-STEP INCIDENT WORKFLOW ─────────────────────────────────
                # Step 1: Retrieve involved vehicle tracks
                involved = [
                    {
                        "track_id": primary.track_id,
                        "class_name": primary.class_name,
                        "speed_kmh": round(primary.speed_kmh, 1),
                        "heading_deg": round(primary.heading_deg, 1),
                        "bbox": primary.bbox,
                        "role": "departing" if category == "HIT_AND_RUN_SIGNATURE" else "primary",
                    }
                ]
                if primary.interaction_track_id is not None:
                    inter_state = next((s for s in current_track_states if s.track_id == primary.interaction_track_id), None)
                    if inter_state:
                        involved.append({
                            "track_id": inter_state.track_id,
                            "class_name": inter_state.class_name,
                            "speed_kmh": round(inter_state.speed_kmh, 1),
                            "heading_deg": round(inter_state.heading_deg, 1),
                            "bbox": inter_state.bbox,
                            "role": "disappeared" if inter_state.disappeared else "secondary",
                        })

                # Step 2: Identify nearby vehicles
                involved_ids = {item["track_id"] for item in involved}
                nearby = []
                for other in current_track_states:
                    if other.track_id not in involved_ids and not other.disappeared:
                        dist_px = math.hypot(primary.center[0] - other.center[0], primary.center[1] - other.center[1])
                        nearby.append({
                            "track_id": other.track_id,
                            "class_name": other.class_name,
                            "speed_kmh": round(other.speed_kmh, 1),
                            "distance_m": round(dist_px * 0.05, 1),  # estimate
                        })

                # Step 3: Save event timestamp (ISO UTC)
                event_ts = iso_timestamp

                # Step 4: Save GPS
                event_gps = {
                    "lat": gps.get("lat", 28.6139),
                    "lon": gps.get("lon", 77.2090),
                    "bearing_deg": gps.get("bearing_deg", 0.0),
                    "road_segment": gps.get("road_segment", "DEL_01"),
                }

                # Step 5: Select relevant camera
                rel_camera = self.camera_id

                # Step 6 & 7: Retrieve rolling buffer and create evidence clip
                clip = self.buffer.create_evidence_clip(
                    anomaly_timestamp_s=now_ts,
                    pre_frames=4,
                    post_frames=4,
                )

                # Step 8: Run ANPR on best available frame of primary/departing vehicle
                anpr_res = self.anpr_engine.process_vehicle(
                    frame=frame,
                    bbox=primary.bbox,
                    track_id=primary.track_id,
                    vehicle_class=primary.class_name,
                )

                # Step 9: Generate confidence score
                final_confidence = round(conf, 3)

                # Step 10: Send secure alert (Strictly POSSIBLE_INCIDENT)
                event_payload = {
                    "event_id": f"inc_{uuid.uuid4().hex[:10]}",
                    "event_type": "POSSIBLE_INCIDENT",
                    "incident_category": category,
                    "verification_status": "PENDING_REVIEW",
                    "legal_disclaimer": LEGAL_DISCLAIMER,
                    "requires_human_verification": True,
                    "confidence": final_confidence,
                    "timestamp": event_ts,
                    "location": event_gps,
                    "bus_id": self.bus_id,
                    "camera_id": rel_camera,
                    "involved_tracks": involved,
                    "nearby_vehicles": nearby,
                    "explainable_signals": {
                        k: v.to_dict() for k, v in signals.items()
                    },
                    "anpr": anpr_res.to_dict(),
                    "evidence_clip": clip,
                    "is_hit_and_run": (category == "HIT_AND_RUN_SIGNATURE"),
                }

                events.append(event_payload)
                self._last_alert_time = now_ts
                logger.warning(
                    f"[{self.camera_id}] Flagged POSSIBLE_INCIDENT ({category}) "
                    f"with confidence {final_confidence}. Pending human review."
                )
                break  # one incident event per frame window

        return events
