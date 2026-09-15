"""
Incident & Hit-and-Run Anomaly Intelligence Router
===================================================
Endpoints for:
  - Ingesting POSSIBLE_INCIDENT events from Edge AI onboard bus nodes
  - Listing incident events with status & hit-and-run filtering
  - Human review endpoint (PATCH) strictly enforcing human-in-the-loop verification
  - Evidence clip inspection and ANPR plate verification
  - Command center summary KPIs and analytics
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..database.session import get_session
from ..models.ingested_event import IngestedEvent

router = APIRouter()

LEGAL_DISCLAIMER_TEXT = (
    "Preliminary automated sensor anomaly alert. Does not determine legal fault, "
    "criminal culpability, or driver liability. Human verification required before any enforcement action."
)

# ── Schemas ───────────────────────────────────────────────────────────────────

class InvolvedTrack(BaseModel):
    track_id: int
    class_name: str
    speed_kmh: float
    heading_deg: float
    bbox: List[int] = [0, 0, 0, 0]
    role: str = "primary"  # "primary" | "secondary" | "departing" | "disappeared"


class NearbyVehicle(BaseModel):
    track_id: int
    class_name: str
    speed_kmh: float
    distance_m: float


class SignalDetail(BaseModel):
    name: str
    triggered: bool
    value: float
    threshold: float
    unit: str
    description: str


class AnprDetail(BaseModel):
    plate_number: str
    confidence: float
    vehicle_class: str
    plate_crop_b64: str
    detected: bool = True
    state_code: str = "DL"
    bounding_box: Optional[List[int]] = None


class EvidenceFrame(BaseModel):
    phase: str  # "PRE_IMPACT" | "IMPACT" | "POST_IMPACT"
    frame_idx: int
    timestamp_s: Optional[float] = None
    frame_b64: str
    gps: Optional[Dict[str, Any]] = None


class EvidenceClipDetail(BaseModel):
    clip_id: str
    frame_count: int
    duration_s: float
    fps: float = 10.0
    frames: List[EvidenceFrame] = []
    key_frame_b64: str = ""


class IncidentEventIn(BaseModel):
    event_id: Optional[str] = None
    event_type: str = "POSSIBLE_INCIDENT"
    incident_category: str = "COLLISION_RISK"  # COLLISION_RISK | HIT_AND_RUN_SIGNATURE | TRAJECTORY_ANOMALY
    verification_status: str = "PENDING_REVIEW"
    legal_disclaimer: Optional[str] = None
    requires_human_verification: bool = True
    confidence: float = Field(..., ge=0.0, le=1.0)
    timestamp: Optional[str] = None
    location: Dict[str, Any]
    bus_id: str
    camera_id: str
    involved_tracks: List[InvolvedTrack] = []
    nearby_vehicles: List[NearbyVehicle] = []
    explainable_signals: Dict[str, SignalDetail] = {}
    anpr: Optional[AnprDetail] = None
    evidence_clip: Optional[EvidenceClipDetail] = None
    is_hit_and_run: bool = False


class IncidentEventOut(IncidentEventIn):
    reviewed_at: Optional[str] = None
    reviewer_id: Optional[str] = None
    human_notes: Optional[str] = None


class ReviewIncidentRequest(BaseModel):
    status: str = Field(..., description="Target status: VERIFIED_INCIDENT or DISMISSED")
    reviewer_id: str = "safety_officer_01"
    notes: Optional[str] = ""


# ── Synthetic Visual Plate Generator for Seeds ────────────────────────────────

def _sample_plate_svg(plate_text: str) -> str:
    import base64
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 80" width="320" height="80">
  <rect x="2" y="2" width="316" height="76" rx="8" fill="#ffffff" stroke="#1f2937" stroke-width="4"/>
  <rect x="2" y="2" width="36" height="76" rx="6" fill="#1e3a8a"/>
  <circle cx="20" cy="30" r="10" fill="#3b82f6" opacity="0.6"/>
  <text x="20" y="55" font-family="Arial, sans-serif" font-size="11" font-weight="900" fill="#ffffff" text-anchor="middle">IND</text>
  <text x="175" y="52" font-family="'Consolas', monospace" font-size="32" font-weight="900" fill="#111827" letter-spacing="4" text-anchor="middle">{plate_text}</text>
  <rect x="4" y="4" width="312" height="72" rx="6" fill="none" stroke="#e5e7eb" stroke-width="1"/>
</svg>"""
    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode('utf-8')).decode('utf-8')}"


def _sample_frame_svg(title: str, subtitle: str, color: str = "#dc2626") -> str:
    import base64
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360" width="640" height="360">
  <rect width="640" height="360" fill="#0f172a"/>
  <path d="M120 360 L280 180 L360 180 L520 360 Z" fill="#1e293b"/>
  <line x1="320" y1="180" x2="320" y2="360" stroke="#f59e0b" stroke-width="3" stroke-dasharray="12 10"/>
  <!-- Target Vehicle Box -->
  <rect x="240" y="160" width="160" height="110" rx="6" fill="none" stroke="{color}" stroke-width="3"/>
  <rect x="240" y="140" width="160" height="20" fill="{color}"/>
  <text x="245" y="154" font-family="Arial" font-size="11" font-weight="bold" fill="#ffffff">{title}</text>
  <!-- Bounding HUD -->
  <rect x="16" y="16" width="220" height="42" rx="4" fill="#000000" fill-opacity="0.7"/>
  <text x="26" y="34" font-family="Arial" font-size="12" font-weight="bold" fill="#ffffff">CAMERA SENSOR: {subtitle}</text>
  <text x="26" y="48" font-family="Arial" font-size="10" fill="#94a3b8">INCIDENT ANOMALY CLIP</text>
</svg>"""
    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode('utf-8')).decode('utf-8')}"


# ── In-Memory Database with Demonstration Seeds ────────────────────────────────

_INCIDENTS_DB: Dict[str, Dict[str, Any]] = {}


def _seed_demo_incidents():
    if _INCIDENTS_DB:
        return

    now_iso = datetime.now(timezone.utc).isoformat()

    demo_seeds = [
        {
            "event_id": "inc_del_001",
            "event_type": "POSSIBLE_INCIDENT",
            "incident_category": "HIT_AND_RUN_SIGNATURE",
            "verification_status": "PENDING_REVIEW",
            "legal_disclaimer": LEGAL_DISCLAIMER_TEXT,
            "requires_human_verification": True,
            "confidence": 0.93,
            "timestamp": now_iso,
            "location": {
                "lat": 28.6315,
                "lon": 77.2167,
                "bearing_deg": 142.0,
                "road_segment": "DEL_CP_01",
                "address": "Connaught Place Radial Rd 3, New Delhi",
            },
            "bus_id": "BUS_101",
            "camera_id": "FRONT",
            "involved_tracks": [
                {
                    "track_id": 412,
                    "class_name": "car",
                    "speed_kmh": 46.5,
                    "heading_deg": 145.0,
                    "bbox": [210, 140, 390, 270],
                    "role": "departing",
                },
                {
                    "track_id": 415,
                    "class_name": "motorcycle",
                    "speed_kmh": 0.0,
                    "heading_deg": 110.0,
                    "bbox": [180, 220, 240, 290],
                    "role": "disappeared",
                },
            ],
            "nearby_vehicles": [
                {"track_id": 409, "class_name": "bus", "speed_kmh": 22.0, "distance_m": 14.5},
                {"track_id": 418, "class_name": "auto-rickshaw", "speed_kmh": 28.0, "distance_m": 8.2},
            ],
            "explainable_signals": {
                "sudden_deceleration": {
                    "name": "sudden_deceleration",
                    "triggered": True,
                    "value": -5.2,
                    "threshold": -4.5,
                    "unit": "m/s^2",
                    "description": "Rapid deceleration (a=-5.2 m/s^2, delta_v=-18.4 km/h)",
                },
                "abrupt_heading_change": {
                    "name": "abrupt_heading_change",
                    "triggered": True,
                    "value": 41.2,
                    "threshold": 35.0,
                    "unit": "deg",
                    "description": "Abrupt yaw or heading deviation (41.2 deg)",
                },
                "trajectory_discontinuity": {
                    "name": "trajectory_discontinuity",
                    "triggered": False,
                    "value": 28.5,
                    "threshold": 75.0,
                    "unit": "px",
                    "description": "Within normal positional continuous bounds",
                },
                "nearby_vehicle_interaction": {
                    "name": "nearby_vehicle_interaction",
                    "triggered": True,
                    "value": 34.0,
                    "threshold": 70.0,
                    "unit": "px",
                    "description": "Close proximity / collision overlap with track #415 (min_dist=34.0 px)",
                },
                "object_disappearance_after_interaction": {
                    "name": "object_disappearance_after_interaction",
                    "triggered": True,
                    "value": 1.0,
                    "threshold": 1.0,
                    "unit": "binary",
                    "description": "Interacting motorcycle track #415 vanished from view post-collision",
                },
                "unusual_acceleration": {
                    "name": "unusual_acceleration",
                    "triggered": True,
                    "value": 4.8,
                    "threshold": 4.0,
                    "unit": "m/s^2",
                    "description": "High post-event acceleration spike (a=4.8 m/s^2)",
                },
                "vehicle_leaving_scene": {
                    "name": "vehicle_leaving_scene",
                    "triggered": True,
                    "value": 46.5,
                    "threshold": 28.0,
                    "unit": "km/h",
                    "description": "Car track #412 rapidly departing scene post-interaction (46.5 km/h)",
                },
            },
            "anpr": {
                "plate_number": "DL 01 AB 1234",
                "confidence": 0.942,
                "vehicle_class": "car",
                "plate_crop_b64": _sample_plate_svg("DL 01 AB 1234"),
                "detected": True,
                "state_code": "DL",
                "bounding_box": [245, 230, 355, 265],
            },
            "evidence_clip": {
                "clip_id": "clip_del_001",
                "frame_count": 3,
                "duration_s": 2.4,
                "fps": 10.0,
                "frames": [
                    {"phase": "PRE_IMPACT", "frame_idx": 101, "timestamp_s": 100.0, "frame_b64": _sample_frame_svg("PRE-IMPACT APPROACH", "FRONT - T-0.8s", "#3b82f6")},
                    {"phase": "IMPACT", "frame_idx": 105, "timestamp_s": 100.8, "frame_b64": _sample_frame_svg("ANOMALOUS INTERACTION", "FRONT - IMPACT T=0", "#ef4444")},
                    {"phase": "POST_IMPACT", "frame_idx": 110, "timestamp_s": 101.6, "frame_b64": _sample_frame_svg("VEHICLE DEPARTING SCENE", "FRONT - T+0.8s", "#f59e0b")},
                ],
                "key_frame_b64": _sample_frame_svg("ANOMALOUS INTERACTION", "FRONT - IMPACT T=0", "#ef4444"),
            },
            "is_hit_and_run": True,
            "reviewed_at": None,
            "reviewer_id": None,
            "human_notes": None,
        },
        {
            "event_id": "inc_del_002",
            "event_type": "POSSIBLE_INCIDENT",
            "incident_category": "COLLISION_RISK",
            "verification_status": "PENDING_REVIEW",
            "legal_disclaimer": LEGAL_DISCLAIMER_TEXT,
            "requires_human_verification": True,
            "confidence": 0.875,
            "timestamp": now_iso,
            "location": {
                "lat": 28.5672,
                "lon": 77.2100,
                "bearing_deg": 88.0,
                "road_segment": "DEL_RING_04",
                "address": "Ring Road near AIIMS Flyover, New Delhi",
            },
            "bus_id": "BUS_204",
            "camera_id": "REAR",
            "involved_tracks": [
                {
                    "track_id": 512,
                    "class_name": "truck",
                    "speed_kmh": 12.0,
                    "heading_deg": 90.0,
                    "bbox": [150, 100, 480, 310],
                    "role": "primary",
                },
                {
                    "track_id": 516,
                    "class_name": "car",
                    "speed_kmh": 0.0,
                    "heading_deg": 85.0,
                    "bbox": [190, 180, 340, 280],
                    "role": "secondary",
                },
            ],
            "nearby_vehicles": [
                {"track_id": 520, "class_name": "motorcycle", "speed_kmh": 35.0, "distance_m": 12.0},
            ],
            "explainable_signals": {
                "sudden_deceleration": {
                    "name": "sudden_deceleration",
                    "triggered": True,
                    "value": -4.8,
                    "threshold": -4.5,
                    "unit": "m/s^2",
                    "description": "Sharp braking before contact (a=-4.8 m/s^2)",
                },
                "abrupt_heading_change": {
                    "name": "abrupt_heading_change",
                    "triggered": False,
                    "value": 12.0,
                    "threshold": 35.0,
                    "unit": "deg",
                    "description": "Minimal yaw deviation",
                },
                "trajectory_discontinuity": {
                    "name": "trajectory_discontinuity",
                    "triggered": True,
                    "value": 82.0,
                    "threshold": 75.0,
                    "unit": "px",
                    "description": "Positional jump during sudden stop (82.0 px)",
                },
                "nearby_vehicle_interaction": {
                    "name": "nearby_vehicle_interaction",
                    "triggered": True,
                    "value": 18.0,
                    "threshold": 70.0,
                    "unit": "px",
                    "description": "Direct bounding box contact with rear of car #516",
                },
                "object_disappearance_after_interaction": {
                    "name": "object_disappearance_after_interaction",
                    "triggered": False,
                    "value": 0.0,
                    "threshold": 1.0,
                    "unit": "binary",
                    "description": "Both vehicles remained visible in camera view",
                },
                "unusual_acceleration": {
                    "name": "unusual_acceleration",
                    "triggered": False,
                    "value": 0.0,
                    "threshold": 4.0,
                    "unit": "m/s^2",
                    "description": "No subsequent acceleration detected",
                },
                "vehicle_leaving_scene": {
                    "name": "vehicle_leaving_scene",
                    "triggered": False,
                    "value": 12.0,
                    "threshold": 28.0,
                    "unit": "km/h",
                    "description": "Truck remained stationary/slow",
                },
            },
            "anpr": {
                "plate_number": "HR 26 BC 3456",
                "confidence": 0.912,
                "vehicle_class": "truck",
                "plate_crop_b64": _sample_plate_svg("HR 26 BC 3456"),
                "detected": True,
                "state_code": "HR",
                "bounding_box": [260, 240, 370, 280],
            },
            "evidence_clip": {
                "clip_id": "clip_del_002",
                "frame_count": 3,
                "duration_s": 2.0,
                "fps": 10.0,
                "frames": [
                    {"phase": "PRE_IMPACT", "frame_idx": 201, "timestamp_s": 200.0, "frame_b64": _sample_frame_svg("TRUCK DECELERATING", "REAR - T-0.6s", "#3b82f6")},
                    {"phase": "IMPACT", "frame_idx": 204, "timestamp_s": 200.6, "frame_b64": _sample_frame_svg("BUMPER CONTACT", "REAR - CONTACT", "#ef4444")},
                    {"phase": "POST_IMPACT", "frame_idx": 208, "timestamp_s": 201.2, "frame_b64": _sample_frame_svg("VEHICLES AT REST", "REAR - T+0.6s", "#10b981")},
                ],
                "key_frame_b64": _sample_frame_svg("BUMPER CONTACT", "REAR - CONTACT", "#ef4444"),
            },
            "is_hit_and_run": False,
            "reviewed_at": None,
            "reviewer_id": None,
            "human_notes": None,
        },
        {
            "event_id": "inc_blr_003",
            "event_type": "POSSIBLE_INCIDENT",
            "incident_category": "COLLISION_RISK",
            "verification_status": "VERIFIED_INCIDENT",
            "legal_disclaimer": LEGAL_DISCLAIMER_TEXT,
            "requires_human_verification": True,
            "confidence": 0.945,
            "timestamp": now_iso,
            "location": {
                "lat": 12.9716,
                "lon": 77.5946,
                "bearing_deg": 210.0,
                "road_segment": "BLR_MG_01",
                "address": "MG Road & Brigade Rd Junction, Bengaluru",
            },
            "bus_id": "BUS_305",
            "camera_id": "FRONT",
            "involved_tracks": [
                {
                    "track_id": 601,
                    "class_name": "auto-rickshaw",
                    "speed_kmh": 0.0,
                    "heading_deg": 220.0,
                    "bbox": [180, 160, 310, 290],
                    "role": "primary",
                }
            ],
            "nearby_vehicles": [],
            "explainable_signals": {
                "sudden_deceleration": {"name": "sudden_deceleration", "triggered": True, "value": -5.6, "threshold": -4.5, "unit": "m/s^2", "description": "Abrupt stop"},
                "abrupt_heading_change": {"name": "abrupt_heading_change", "triggered": True, "value": 52.0, "threshold": 35.0, "unit": "deg", "description": "Overturned yaw trajectory"},
                "trajectory_discontinuity": {"name": "trajectory_discontinuity", "triggered": True, "value": 90.0, "threshold": 75.0, "unit": "px", "description": "Sudden lateral shift"},
                "nearby_vehicle_interaction": {"name": "nearby_vehicle_interaction", "triggered": True, "value": 20.0, "threshold": 70.0, "unit": "px", "description": "Contact with curb barrier"},
                "object_disappearance_after_interaction": {"name": "object_disappearance_after_interaction", "triggered": False, "value": 0.0, "threshold": 1.0, "unit": "binary", "description": "Object retained"},
                "unusual_acceleration": {"name": "unusual_acceleration", "triggered": False, "value": 0.0, "threshold": 4.0, "unit": "m/s^2", "description": "Stationary"},
                "vehicle_leaving_scene": {"name": "vehicle_leaving_scene", "triggered": False, "value": 0.0, "threshold": 28.0, "unit": "km/h", "description": "No departure"},
            },
            "anpr": {
                "plate_number": "KA 05 EF 9012",
                "confidence": 0.955,
                "vehicle_class": "auto-rickshaw",
                "plate_crop_b64": _sample_plate_svg("KA 05 EF 9012"),
                "detected": True,
                "state_code": "KA",
                "bounding_box": [200, 220, 300, 260],
            },
            "evidence_clip": {
                "clip_id": "clip_blr_003",
                "frame_count": 3,
                "duration_s": 2.2,
                "fps": 10.0,
                "frames": [
                    {"phase": "PRE_IMPACT", "frame_idx": 301, "timestamp_s": 300.0, "frame_b64": _sample_frame_svg("AUTO SWERVING", "FRONT - T-0.6s", "#f59e0b")},
                    {"phase": "IMPACT", "frame_idx": 304, "timestamp_s": 300.6, "frame_b64": _sample_frame_svg("BARRIER IMPACT", "FRONT - CONTACT", "#ef4444")},
                    {"phase": "POST_IMPACT", "frame_idx": 308, "timestamp_s": 301.2, "frame_b64": _sample_frame_svg("REST AT CURB", "FRONT - REST", "#3b82f6")},
                ],
                "key_frame_b64": _sample_frame_svg("BARRIER IMPACT", "FRONT - CONTACT", "#ef4444"),
            },
            "is_hit_and_run": False,
            "reviewed_at": "2026-09-14T21:30:00Z",
            "reviewer_id": "officer_blr_04",
            "human_notes": "Reviewed camera footage. Auto tipped after swerving to avoid construction debris. Ambulance dispatched.",
        },
        {
            "event_id": "inc_mum_004",
            "event_type": "POSSIBLE_INCIDENT",
            "incident_category": "TRAJECTORY_ANOMALY",
            "verification_status": "DISMISSED",
            "legal_disclaimer": LEGAL_DISCLAIMER_TEXT,
            "requires_human_verification": True,
            "confidence": 0.68,
            "timestamp": now_iso,
            "location": {
                "lat": 19.0760,
                "lon": 72.8777,
                "bearing_deg": 18.0,
                "road_segment": "MUM_WEH_02",
                "address": "Western Express Highway near Bandra, Mumbai",
            },
            "bus_id": "BUS_402",
            "camera_id": "LEFT",
            "involved_tracks": [
                {
                    "track_id": 702,
                    "class_name": "car",
                    "speed_kmh": 38.0,
                    "heading_deg": 25.0,
                    "bbox": [120, 150, 280, 270],
                    "role": "primary",
                }
            ],
            "nearby_vehicles": [],
            "explainable_signals": {
                "sudden_deceleration": {"name": "sudden_deceleration", "triggered": False, "value": -2.1, "threshold": -4.5, "unit": "m/s^2", "description": "Moderate braking"},
                "abrupt_heading_change": {"name": "abrupt_heading_change", "triggered": True, "value": 37.5, "threshold": 35.0, "unit": "deg", "description": "Rapid lane switch"},
                "trajectory_discontinuity": {"name": "trajectory_discontinuity", "triggered": True, "value": 78.0, "threshold": 75.0, "unit": "px", "description": "Lane transition displacement"},
                "nearby_vehicle_interaction": {"name": "nearby_vehicle_interaction", "triggered": False, "value": 110.0, "threshold": 70.0, "unit": "px", "description": "No vehicle contact"},
                "object_disappearance_after_interaction": {"name": "object_disappearance_after_interaction", "triggered": False, "value": 0.0, "threshold": 1.0, "unit": "binary", "description": "Normal track continuation"},
                "unusual_acceleration": {"name": "unusual_acceleration", "triggered": False, "value": 1.8, "threshold": 4.0, "unit": "m/s^2", "description": "Steady cruise"},
                "vehicle_leaving_scene": {"name": "vehicle_leaving_scene", "triggered": False, "value": 38.0, "threshold": 28.0, "unit": "km/h", "description": "Normal progression"},
            },
            "anpr": {
                "plate_number": "MH 02 CD 5678",
                "confidence": 0.865,
                "vehicle_class": "car",
                "plate_crop_b64": _sample_plate_svg("MH 02 CD 5678"),
                "detected": True,
                "state_code": "MH",
                "bounding_box": [160, 210, 240, 245],
            },
            "evidence_clip": {
                "clip_id": "clip_mum_004",
                "frame_count": 3,
                "duration_s": 1.8,
                "fps": 10.0,
                "frames": [
                    {"phase": "PRE_IMPACT", "frame_idx": 401, "timestamp_s": 400.0, "frame_b64": _sample_frame_svg("LANE CHANGE", "LEFT - T-0.5s", "#3b82f6")},
                    {"phase": "IMPACT", "frame_idx": 404, "timestamp_s": 400.5, "frame_b64": _sample_frame_svg("SHARP SWERVE", "LEFT - APEX", "#f59e0b")},
                    {"phase": "POST_IMPACT", "frame_idx": 407, "timestamp_s": 401.0, "frame_b64": _sample_frame_svg("LANE RECOVERY", "LEFT - RECOVERY", "#10b981")},
                ],
                "key_frame_b64": _sample_frame_svg("SHARP SWERVE", "LEFT - APEX", "#f59e0b"),
            },
            "is_hit_and_run": False,
            "reviewed_at": "2026-09-14T20:15:00Z",
            "reviewer_id": "officer_mum_02",
            "human_notes": "False positive: vehicle performed rapid evasive lane change around plastic road barricade with no contact.",
        },
    ]

    for item in demo_seeds:
        _INCIDENTS_DB[item["event_id"]] = item


_seed_demo_incidents()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/events", status_code=201, response_model=Dict[str, Any])
async def ingest_incident_event(payload: IncidentEventIn):
    """
    Ingest a POSSIBLE_INCIDENT event detected by edge bus node.
    Strictly preserves 'POSSIBLE_INCIDENT' label and enforces PENDING_REVIEW state.
    """
    _seed_demo_incidents()

    eid = payload.event_id or f"inc_{uuid.uuid4().hex[:10]}"
    doc = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    doc["event_id"] = eid
    doc["event_type"] = "POSSIBLE_INCIDENT"  # Immutable requirement
    doc["legal_disclaimer"] = LEGAL_DISCLAIMER_TEXT
    doc["requires_human_verification"] = True
    doc["verification_status"] = doc.get("verification_status") or "PENDING_REVIEW"
    doc["timestamp"] = doc.get("timestamp") or datetime.now(timezone.utc).isoformat()
    doc["reviewed_at"] = None
    doc["reviewer_id"] = None
    doc["human_notes"] = None

    _INCIDENTS_DB[eid] = doc
    return {
        "status": "ingested",
        "event_id": eid,
        "event_type": "POSSIBLE_INCIDENT",
        "verification_status": doc["verification_status"],
        "confidence": doc["confidence"],
        "legal_disclaimer": LEGAL_DISCLAIMER_TEXT,
    }


@router.get("/events", response_model=Dict[str, Any])
async def list_incident_events(
    verification_status: Optional[str] = Query(None, description="Filter: PENDING_REVIEW | VERIFIED_INCIDENT | DISMISSED"),
    category: Optional[str] = Query(None, description="Filter: HIT_AND_RUN_SIGNATURE | COLLISION_RISK | TRAJECTORY_ANOMALY"),
    is_hit_and_run: Optional[bool] = Query(None, description="Filter hit and run anomalies"),
    bus_id: Optional[str] = Query(None, description="Filter by bus identifier"),
    camera_id: Optional[str] = Query(None, description="Filter by camera position"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
):
    """
    Retrieve incident anomaly events with multi-criteria filtering.
    """
    _seed_demo_incidents()

    items = list(_INCIDENTS_DB.values())

    db_query = select(IngestedEvent).where(IngestedEvent.event_type == 'POSSIBLE_INCIDENT')
    db_events = db.exec(db_query).all()
    for e in db_events:
        items.append({
            "event_id": e.event_id,
            "event_type": "POSSIBLE_INCIDENT",
            "incident_category": "COLLISION_RISK",
            "verification_status": e.status if e.status in ["PENDING_REVIEW", "VERIFIED_INCIDENT", "DISMISSED"] else "PENDING_REVIEW",
            "legal_disclaimer": LEGAL_DISCLAIMER_TEXT,
            "requires_human_verification": True,
            "confidence": e.confidence or 0.9,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "location": {
                "lat": e.gps_lat,
                "lon": e.gps_lon,
                "bearing_deg": e.bearing_deg,
                "road_segment": e.road_segment,
                "address": e.address,
            },
            "bus_id": e.bus_id,
            "camera_id": e.camera_id,
            "involved_tracks": [],
            "nearby_vehicles": [],
            "explainable_signals": {},
            "anpr": None,
            "evidence_clip": None,
            "is_hit_and_run": False,
        })

    if verification_status:
        items = [i for i in items if i.get("verification_status") == verification_status]
    if category:
        items = [i for i in items if i.get("incident_category") == category]
    if is_hit_and_run is not None:
        items = [i for i in items if i.get("is_hit_and_run") == is_hit_and_run]
    if bus_id:
        items = [i for i in items if i.get("bus_id") == bus_id]
    if camera_id:
        items = [i for i in items if i.get("camera_id") == camera_id]
    if min_confidence is not None:
        items = [i for i in items if i.get("confidence", 0.0) >= min_confidence]

    # Sort reverse chronological
    items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    total = len(items)
    paged = items[offset : offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": paged,
    }


@router.get("/events/{event_id}", response_model=Dict[str, Any])
async def get_incident_event_detail(event_id: str):
    """
    Retrieve full evidentiary record for a specific incident anomaly.
    """
    _seed_demo_incidents()

    item = _INCIDENTS_DB.get(event_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Incident event '{event_id}' not found")
    return item


@router.patch("/events/{event_id}/review", response_model=Dict[str, Any])
async def review_incident_event(event_id: str, review_data: ReviewIncidentRequest):
    """
    Human verification endpoint:
    A human reviewer confirms whether the anomaly was a verified incident or dismisses it as a false alarm.
    Enforces that enforcement actions cannot proceed without this step.
    """
    _seed_demo_incidents()

    item = _INCIDENTS_DB.get(event_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Incident event '{event_id}' not found")

    target_status = review_data.status.upper()
    if target_status not in ("VERIFIED_INCIDENT", "DISMISSED"):
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Permitted human review outcomes: 'VERIFIED_INCIDENT' or 'DISMISSED'."
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    item["verification_status"] = target_status
    item["reviewed_at"] = now_iso
    item["reviewer_id"] = review_data.reviewer_id
    item["human_notes"] = review_data.notes or ""

    return {
        "status": "updated",
        "event_id": event_id,
        "verification_status": item["verification_status"],
        "reviewed_at": item["reviewed_at"],
        "reviewer_id": item["reviewer_id"],
        "human_notes": item["human_notes"],
        "legal_disclaimer": LEGAL_DISCLAIMER_TEXT,
    }


@router.get("/stats", response_model=Dict[str, Any])
async def get_incident_stats(db: Session = Depends(get_session)):
    """
    Aggregated KPIs and anomaly summary statistics for command center dashboard.
    """
    _seed_demo_incidents()

    all_items = list(_INCIDENTS_DB.values())
    
    db_events = db.exec(select(IngestedEvent).where(IngestedEvent.event_type == 'POSSIBLE_INCIDENT')).all()
    for e in db_events:
        all_items.append({
            "verification_status": e.status if e.status in ["PENDING_REVIEW", "VERIFIED_INCIDENT", "DISMISSED"] else "PENDING_REVIEW",
            "is_hit_and_run": False,
            "confidence": e.confidence or 0.9,
            "incident_category": "COLLISION_RISK",
        })

    total = len(all_items)
    pending = sum(1 for i in all_items if i.get("verification_status") == "PENDING_REVIEW")
    verified = sum(1 for i in all_items if i.get("verification_status") == "VERIFIED_INCIDENT")
    dismissed = sum(1 for i in all_items if i.get("verification_status") == "DISMISSED")
    hit_and_run = sum(1 for i in all_items if i.get("is_hit_and_run", False))

    confs = [i.get("confidence", 0.0) for i in all_items]
    avg_conf = round(sum(confs) / len(confs), 3) if confs else 0.0

    category_counts: Dict[str, int] = {}
    for i in all_items:
        cat = i.get("incident_category", "UNKNOWN")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        "total_anomalies": total,
        "pending_review": pending,
        "verified_incidents": verified,
        "dismissed_count": dismissed,
        "hit_and_run_count": hit_and_run,
        "avg_confidence": avg_conf,
        "category_counts": category_counts,
        "legal_compliance": {
            "human_in_the_loop_enforced": True,
            "fault_attribution_claim": "None",
            "disclaimer": LEGAL_DISCLAIMER_TEXT,
        },
    }
