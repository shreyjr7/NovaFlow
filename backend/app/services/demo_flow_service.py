"""
Demo Flow Service (Phase 35)
============================
Orchestrates the canonical 17-step end-to-end demonstration scenario:
  Scenario: Bus 104 is travelling on Route 12.

  Step 1:  Bus camera begins processing video.
  Step 2:  Vehicle detection identifies: Cars, Motorcycles, Buses, Trucks.
  Step 3:  Tracking estimates: Vehicle count, Density, Average speed.
  Step 4:  System detects: High density + low speed -> TRAFFIC BOTTLENECK.
  Step 5:  Road-facing camera detects a pothole. Require temporal confirmation. Generate: ROAD DEFECT.
  Step 6:  GPS attaches location.
  Step 7:  Bus temporarily loses network connectivity. Store event locally.
  Step 8:  Network reconnects. Event is transmitted.
  Step 9:  Central backend receives event.
  Step 10: Duplicate detection checks nearby existing events.
  Step 11: Event appears on GIS map.
  Step 12: Maintenance authority receives alert.
  Step 13: Authority verifies the pothole.
  Step 14: Maintenance ticket is created.
  Step 15: Another bus detects the same pothole. System increases confidence rather than creating a duplicate.
  Step 16: Analytics dashboard updates.
  Step 17: After repair, buses stop confirming the pothole. Authority marks: RESOLVED.

Also orchestrates the Vehicle Incident Investigation flow:
  Vehicle anomaly → Track vehicle → Retrieve buffered clip → Plate detection → OCR
  → Confidence → Human verification → Incident report.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from ..database.session import engine
from ..models.ingested_event import IngestedEvent
from ..services.spatial_clustering_service import get_spatial_clustering_service
from ..schemas.spatial_clustering import RawObservationIn

logger = logging.getLogger("services.demo_flow")


class DemoFlowService:
    """
    Coordinates and persists the 17-step demonstration scenario and incident pipeline.
    """

    _instance: Optional[DemoFlowService] = None

    def __init__(self):
        self._lock = threading.Lock()
        self.current_step = 0
        self.scenario_state: Dict[str, Any] = {}
        self.incident_state: Dict[str, Any] = {}
        self.reset_scenario()

    @classmethod
    def get_instance(cls) -> DemoFlowService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reset_scenario(self):
        with self._lock:
            self.current_step = 0
            self.scenario_state = {
                "scenario_name": "Bus 104 on Route 12 — Autonomous Defect & Bottleneck Lifecycle",
                "bus_id": "BUS_104",
                "bus_name": "Bus 104 (Ashok Leyland JanBus CNG)",
                "route_id": "ROUTE_12",
                "route_name": "Route 12 — Connaught Outer Arterial",
                "road_segment": "ROUTE_12_SEG_4",
                "gps": {"lat": 28.6322, "lon": 77.2198, "bearing_deg": 74.0},
                "network_state": "ONLINE",
                "local_buffer_events_count": 0,
                "current_event_id": "ev_demo_flow_pothole_104",
                "traffic_telemetry": {
                    "cars": 22,
                    "motorcycles": 11,
                    "buses": 3,
                    "trucks": 2,
                    "vehicle_count": 38,
                    "density_per_km": 152.0,
                    "average_speed_kmh": 8.5,
                    "congestion_level": "SEVERE_BOTTLENECK",
                },
                "pothole_detection": {
                    "temporal_confirmed": False,
                    "frames_observed": 0,
                    "confidence": 0.84,
                    "depth_cm": 7.4,
                    "diameter_cm": 45.0,
                },
                "cluster_confidence": 0.84,
                "observation_count": 1,
                "maintenance_ticket_id": None,
                "defect_status": "PENDING",
                "analytics_updated": False,
                "history_log": [],
            }
            self.reset_incident_flow()

    def reset_incident_flow(self):
        self.incident_state = {
            "incident_id": "INC-2026-0915-01",
            "bus_id": "BUS_104",
            "anomaly_type": "NEAR_MISS_COLLISION_AND_SUDDEN_BRAKING",
            "tracked_vehicle_id": "TRACK_VEH_842",
            "buffered_clip": {
                "clip_id": "clip_2026_0915_01.mp4",
                "duration_sec": 30.0,
                "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "pre_roll_sec": 15.0,
                "post_roll_sec": 15.0,
            },
            "plate_detection": {
                "detected": True,
                "roi_box": [0.42, 0.65, 0.58, 0.73],
                "perspective_corrected": True,
            },
            "ocr_result": {
                "raw_text": "DL 01 AB 1234",
                "standard": "Standard Indian RTO (Delhi Central)",
                "character_confidences": [0.99, 0.98, 0.96, 0.97, 0.98, 0.95, 0.94, 0.96, 0.97, 0.98],
            },
            "compound_confidence": 0.92,
            "human_verification": {
                "status": "QUARANTINED_PENDING_REVIEW",
                "tag": "Human verification required",
                "verified_by": None,
                "verified_at": None,
            },
            "incident_report": None,
        }

    def execute_step(self, step_number: int) -> Dict[str, Any]:
        """Executes a specific step of the 17-step scenario."""
        with self._lock:
            self.current_step = step_number
            ts = datetime.now(timezone.utc).isoformat()
            log_entry = {"step": step_number, "timestamp": ts, "title": "", "details": {}}

            if step_number == 1:
                log_entry["title"] = "Step 1: Bus camera begins processing video"
                log_entry["details"] = {
                    "bus_id": self.scenario_state["bus_id"],
                    "camera": "FRONT_ROAD_WINDSHIELD",
                    "fps": 30.0,
                    "resolution": "1920x1080",
                    "lux_level": 520.0,
                    "optical_clarity": "HEALTHY",
                }

            elif step_number == 2:
                log_entry["title"] = "Step 2: Vehicle detection identifies Cars, Motorcycles, Buses, Trucks"
                log_entry["details"] = {
                    "detected_entities": {
                        "Cars": self.scenario_state["traffic_telemetry"]["cars"],
                        "Motorcycles": self.scenario_state["traffic_telemetry"]["motorcycles"],
                        "Buses": self.scenario_state["traffic_telemetry"]["buses"],
                        "Trucks": self.scenario_state["traffic_telemetry"]["trucks"],
                    },
                    "detector": "YOLOv8-Vehicle-v3.1.0",
                    "inference_time_ms": 16.4,
                }

            elif step_number == 3:
                log_entry["title"] = "Step 3: Tracking estimates Vehicle count, Density, Average speed"
                log_entry["details"] = {
                    "vehicle_count": self.scenario_state["traffic_telemetry"]["vehicle_count"],
                    "density_per_km": self.scenario_state["traffic_telemetry"]["density_per_km"],
                    "average_speed_kmh": self.scenario_state["traffic_telemetry"]["average_speed_kmh"],
                    "tracker": "ByteTrack-v1.8.2 (Spatial-Temporal Association)",
                }

            elif step_number == 4:
                log_entry["title"] = "Step 4: System detects High density + low speed -> TRAFFIC BOTTLENECK"
                log_entry["details"] = {
                    "event_type": "TRAFFIC BOTTLENECK",
                    "trigger_condition": "Density > 120 veh/km AND Speed < 15 km/h",
                    "measured_density": "152.0 veh/km",
                    "measured_speed": "8.5 km/h",
                    "severity": "SEVERE",
                    "recommended_action": "Signal timing optimization and dynamic arterial diversion.",
                }

            elif step_number == 5:
                log_entry["title"] = "Step 5: Road-facing camera detects a pothole (temporal confirmation required)"
                self.scenario_state["pothole_detection"]["temporal_confirmed"] = True
                self.scenario_state["pothole_detection"]["frames_observed"] = 3
                log_entry["details"] = {
                    "event_type": "ROAD DEFECT",
                    "defect_class": "POTHOLE",
                    "temporal_confirmation": "PASSED (Confirmed across 3 consecutive frames)",
                    "initial_confidence": self.scenario_state["pothole_detection"]["confidence"],
                    "estimated_depth": "7.4 cm",
                    "estimated_diameter": "45.0 cm",
                }

            elif step_number == 6:
                log_entry["title"] = "Step 6: GPS attaches location"
                log_entry["details"] = {
                    "road_segment": self.scenario_state["road_segment"],
                    "lat": self.scenario_state["gps"]["lat"],
                    "lon": self.scenario_state["gps"]["lon"],
                    "bearing_deg": self.scenario_state["gps"]["bearing_deg"],
                    "address": "Route 12, Connaught Outer Arterial, Section 4",
                }

            elif step_number == 7:
                log_entry["title"] = "Step 7: Bus temporarily loses network connectivity -> Stored locally"
                self.scenario_state["network_state"] = "OFFLINE"
                self.scenario_state["local_buffer_events_count"] = 1
                log_entry["details"] = {
                    "network_state": "OFFLINE",
                    "onboard_buffer": "SqliteEventQueue (edge_store/event_buffer.db)",
                    "buffered_events_count": 1,
                    "zero_data_loss_guaranteed": True,
                    "ui_status": "NETWORK:\nOFFLINE\n1 EVENTS BUFFERED",
                }

            elif step_number == 8:
                log_entry["title"] = "Step 8: Network reconnects -> Event is transmitted"
                self.scenario_state["network_state"] = "ONLINE"
                self.scenario_state["local_buffer_events_count"] = 0
                log_entry["details"] = {
                    "network_state": "ONLINE",
                    "drained_from_buffer": 1,
                    "ui_status": "Network:\nONLINE",
                    "transmission_status": "HTTP POST /api/v1/events/ingest (202 ACCEPTED)",
                }

            elif step_number == 9:
                log_entry["title"] = "Step 9: Central backend receives event"
                ev_id = self.scenario_state["current_event_id"]
                log_entry["details"] = {
                    "event_id": ev_id,
                    "idempotency_key": f"idemp_{ev_id}",
                    "queue_stream": "novaflow-events",
                    "auth_verified": "Bearer novaflow-edge-dev-token",
                    "schema_validation": "PASSED (EventIngestIn)",
                }

            elif step_number == 10:
                log_entry["title"] = "Step 10: Duplicate detection checks nearby existing events"
                # Register with spatial clustering engine
                cluster_svc = get_spatial_clustering_service()
                cluster, is_new = cluster_svc.ingest_observation(
                    RawObservationIn(
                        event_id=self.scenario_state["current_event_id"],
                        bus_id=self.scenario_state["bus_id"],
                        camera_id="FRONT_ROAD",
                        lat=self.scenario_state["gps"]["lat"],
                        lon=self.scenario_state["gps"]["lon"],
                        timestamp=ts,
                        confidence=self.scenario_state["pothole_detection"]["confidence"],
                        defect_type="POTHOLE",
                        severity="HIGH",
                        road_segment=self.scenario_state["road_segment"],
                    )
                )
                self.scenario_state["cluster_id"] = cluster.canonical_id
                self.scenario_state["cluster_confidence"] = cluster.confidence
                self.scenario_state["observation_count"] = cluster.number_of_observations
                log_entry["details"] = {
                    "cluster_id": cluster.canonical_id,
                    "spatial_radius_m": 15.0,
                    "status": "NEW_CLUSTER_INITIALIZED" if is_new else "EXISTING_CLUSTER_REINFORCED",
                    "initial_confidence": cluster.confidence,
                    "observation_count": cluster.number_of_observations,
                }

            elif step_number == 11:
                log_entry["title"] = "Step 11: Event appears on GIS map"
                # Persist to database so it shows on GIS layers
                with Session(engine) as session:
                    existing = session.exec(
                        select(IngestedEvent).where(IngestedEvent.event_id == self.scenario_state["current_event_id"])
                    ).first()
                    if not existing:
                        db_ev = IngestedEvent(
                            idempotency_key=f"idemp_{self.scenario_state['current_event_id']}",
                            event_id=self.scenario_state["current_event_id"],
                            event_type="POTHOLE",
                            bus_id=self.scenario_state["bus_id"],
                            camera_id="FRONT_ROAD",
                            timestamp=datetime.now(timezone.utc),
                            gps_lat=self.scenario_state["gps"]["lat"],
                            gps_lon=self.scenario_state["gps"]["lon"],
                            bearing_deg=self.scenario_state["gps"]["bearing_deg"],
                            road_segment=self.scenario_state["road_segment"],
                            address="Route 12 Section 4, New Delhi",
                            district="Central",
                            confidence=self.scenario_state["cluster_confidence"],
                            evidence_reference="sha256:r12_pothole_ev104",
                            severity="HIGH",
                            status="ACTIVE",
                        )
                        session.add(db_ev)
                        session.commit()

                log_entry["details"] = {
                    "layer": "potholes",
                    "pin_style": "Pulsating Orange Alert Pin",
                    "geojson_query": "GET /api/v1/gis/features?layer=potholes",
                    "coordinates": [self.scenario_state["gps"]["lon"], self.scenario_state["gps"]["lat"]],
                }

            elif step_number == 12:
                log_entry["title"] = "Step 12: Maintenance authority receives alert"
                log_entry["details"] = {
                    "alert_center": "CRITICAL / HIGH INBOX",
                    "alert_id": "ALT-2026-R12-04",
                    "recipient": "Municipal Works & Road Safety Division",
                    "summary": "Severe Pothole detected on Route 12 Corridor (depth 7.4cm).",
                }

            elif step_number == 13:
                log_entry["title"] = "Step 13: Authority verifies the pothole"
                self.scenario_state["defect_status"] = "VERIFIED"
                log_entry["details"] = {
                    "action": "VERIFIED_BY_OFFICER",
                    "officer_id": "OFFICER_VERMA_MUNICIPAL",
                    "optical_evidence_reviewed": True,
                    "depth_verified_cm": 7.4,
                    "action_taken": "Escalated for immediate patch crew dispatch",
                }

            elif step_number == 14:
                log_entry["title"] = "Step 14: Maintenance ticket is created"
                ticket_id = "TICK-2026-R12-01"
                self.scenario_state["maintenance_ticket_id"] = ticket_id
                self.scenario_state["defect_status"] = "TICKET_CREATED"
                log_entry["details"] = {
                    "ticket_id": ticket_id,
                    "assignee": "Zone 1 Central Asphalt Patch Crew #4",
                    "sla_hours": 24,
                    "priority": "HIGH",
                    "estimated_repair_time": "3.5 hours",
                }

            elif step_number == 15:
                log_entry["title"] = "Step 15: Another bus detects the same pothole -> Increases confidence, no duplicate"
                # Bus 109 observes the same location
                cluster_svc = get_spatial_clustering_service()
                cluster, is_new = cluster_svc.ingest_observation(
                    RawObservationIn(
                        event_id="ev_demo_flow_pothole_109",
                        bus_id="BUS_109",
                        camera_id="FRONT_ROAD",
                        lat=self.scenario_state["gps"]["lat"] + 0.00005,
                        lon=self.scenario_state["gps"]["lon"] - 0.00004,
                        timestamp=ts,
                        confidence=0.91,
                        defect_type="POTHOLE",
                        severity="HIGH",
                        road_segment=self.scenario_state["road_segment"],
                    )
                )
                self.scenario_state["cluster_confidence"] = cluster.confidence
                self.scenario_state["observation_count"] = cluster.number_of_observations
                log_entry["details"] = {
                    "second_bus": "BUS_109",
                    "result": "SPATIAL DEDUPLICATION & REINFORCEMENT",
                    "confidence_boost": f"0.84 -> {cluster.confidence:.2f}",
                    "total_observations": cluster.number_of_observations,
                    "duplicate_created": False,
                }

            elif step_number == 16:
                log_entry["title"] = "Step 16: Analytics dashboard updates"
                self.scenario_state["analytics_updated"] = True
                log_entry["details"] = {
                    "updated_charts": [
                        "Road Condition Index (Corridor A)",
                        "Active Road Defects (Potholes +1)",
                        "Bottleneck Congestion Duration (Route 12)",
                    ],
                    "city_road_health_score": "78.4 / 100",
                }

            elif step_number == 17:
                log_entry["title"] = "Step 17: After repair, buses stop confirming pothole -> Authority marks RESOLVED"
                self.scenario_state["defect_status"] = "RESOLVED"
                # Update database event status to RESOLVED
                with Session(engine) as session:
                    db_ev = session.exec(
                        select(IngestedEvent).where(IngestedEvent.event_id == self.scenario_state["current_event_id"])
                    ).first()
                    if db_ev:
                        db_ev.status = "RESOLVED"
                        session.add(db_ev)
                        session.commit()

                log_entry["details"] = {
                    "repair_status": "PHYSICAL ROAD RESURFACING COMPLETED",
                    "authority_action": "RESOLVED",
                    "resolution_verified_by": "OFFICER_VERMA_MUNICIPAL",
                    "buses_confirming": 0,
                    "closed_at": ts,
                }

            self.scenario_state["history_log"].append(log_entry)
            return {
                "step": step_number,
                "current_step": self.current_step,
                "scenario_state": self.scenario_state,
                "latest_log": log_entry,
            }

    def run_all_steps(self) -> Dict[str, Any]:
        """Executes all 17 steps in sequential automated order."""
        self.reset_scenario()
        timeline = []
        for s in range(1, 18):
            res = self.execute_step(s)
            timeline.append(res["latest_log"])

        return {
            "status": "ALL_17_STEPS_COMPLETED",
            "total_steps": 17,
            "timeline": timeline,
            "final_scenario_state": self.scenario_state,
        }

    def run_incident_flow(
        self,
        vehicle_id: str = "TRACK_VEH_842",
        plate_text: str = "DL 01 AB 1234",
    ) -> Dict[str, Any]:
        """
        Executes the incident investigation pipeline:
        Vehicle anomaly → Track vehicle → Retrieve buffered clip → Plate detection → OCR
        → Confidence → Human verification → Incident report.
        """
        with self._lock:
            ts = datetime.now(timezone.utc).isoformat()
            # 1. Vehicle Anomaly
            # 2. Track Vehicle
            # 3. Retrieve Buffered Clip
            clip_meta = self.incident_state["buffered_clip"]
            # 4. Plate Detection
            # 5. OCR
            # 6. Compound Confidence
            conf = 0.94
            # 7. Human Verification
            self.incident_state["human_verification"] = {
                "status": "VERIFIED_BY_OFFICER",
                "tag": "Human verification completed",
                "verified_by": "SAFETY_SUPERVISOR_KUMAR",
                "verified_at": ts,
                "confirmed_plate": plate_text,
            }

            # 8. Incident Report
            report = {
                "report_id": f"INC-REP-{int(time.time())}",
                "incident_type": self.incident_state["anomaly_type"],
                "bus_id": self.incident_state["bus_id"],
                "vehicle_track_id": vehicle_id,
                "license_plate": plate_text,
                "confidence": conf,
                "evidence_clip": clip_meta["clip_id"],
                "clip_sha256": clip_meta["sha256_hash"],
                "chain_of_custody_status": "VERIFIED_IMMUTABLE",
                "dispatched_to": "Traffic Police Enforcement & Municipal Claims Board",
                "generated_at": ts,
            }
            self.incident_state["incident_report"] = report

            return {
                "status": "INCIDENT_FLOW_COMPLETED",
                "incident_id": self.incident_state["incident_id"],
                "stages": [
                    {"stage": 1, "name": "Vehicle Anomaly", "status": "DETECTED"},
                    {"stage": 2, "name": "Track Vehicle", "tracker_id": vehicle_id, "status": "TRACKED"},
                    {"stage": 3, "name": "Retrieve Buffered Clip", "clip": clip_meta["clip_id"], "status": "RETRIEVED"},
                    {"stage": 4, "name": "Plate Detection", "status": "ROI_EXTRACTED"},
                    {"stage": 5, "name": "OCR", "text": plate_text, "status": "RECOGNIZED"},
                    {"stage": 6, "name": "Confidence", "score": conf, "status": "HIGH_CONFIDENCE"},
                    {"stage": 7, "name": "Human Verification", "status": "CONFIRMED_BY_OFFICER"},
                    {"stage": 8, "name": "Incident Report", "report_id": report["report_id"], "status": "DISPATCHED"},
                ],
                "report": report,
            }


def get_demo_flow_service() -> DemoFlowService:
    return DemoFlowService.get_instance()
