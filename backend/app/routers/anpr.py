"""
Vehicle Registration Recognition (ANPR) Intelligence Router
============================================================
Endpoints for:
  - Ingesting and executing ANPR recognition on vehicle track frames
  - Filtering plate recognition records by operational state
  - Enforcing quarantine on low-confidence entries ("Human verification required")
  - Human verification & manual transcription sign-off (PATCH)
  - ANPR command center analytics and accuracy KPIs
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from edge.anpr.pipeline import AnprPipeline, HUMAN_VERIFICATION_NOTICE
from edge.anpr.format_validator import PlateFormatValidator

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class AnprCandidateIn(BaseModel):
    bus_id: str = "BUS_101"
    camera_id: str = "FRONT"
    gps: Dict[str, Any] = Field(default_factory=lambda: {"lat": 28.6139, "lon": 77.2090, "road_segment": "DEL_01"})
    candidate_frames: List[Dict[str, Any]] = Field(default_factory=list)
    incident_vehicle_info: Optional[Dict[str, Any]] = None
    plate_text_hint: Optional[str] = None
    force_missing_plate: bool = False
    timestamp: Optional[str] = None


class HumanVerificationRequest(BaseModel):
    action: str = Field(..., description="Action: 'APPROVE' | 'EDIT' | 'REJECT'")
    verified_plate: Optional[str] = None
    officer_id: str = "safety_officer_01"
    notes: Optional[str] = ""


# ── Helper for Visual Plate SVG Badges ────────────────────────────────────────

def _make_plate_svg(plate_text: str) -> str:
    import base64
    state = plate_text.split()[0] if plate_text and plate_text != "NOT_PRESENT" else "IND"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 80" width="320" height="80">
  <rect x="2" y="2" width="316" height="76" rx="8" fill="#ffffff" stroke="#1f2937" stroke-width="4"/>
  <rect x="2" y="2" width="36" height="76" rx="6" fill="#1e3a8a"/>
  <circle cx="20" cy="30" r="10" fill="#3b82f6" opacity="0.6"/>
  <text x="20" y="55" font-family="Arial" font-size="11" font-weight="900" fill="#ffffff" text-anchor="middle">IND</text>
  <text x="175" y="52" font-family="'Consolas', monospace" font-size="32" font-weight="900" fill="#111827" letter-spacing="4" text-anchor="middle">{plate_text}</text>
  <rect x="4" y="4" width="312" height="72" rx="6" fill="none" stroke="#e5e7eb" stroke-width="1"/>
</svg>"""
    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode('utf-8')).decode('utf-8')}"


# ── In-Memory Database & Demonstration Seeds ───────────────────────────────────

_ANPR_DB: Dict[str, Dict[str, Any]] = {}


def _seed_anpr_records():
    if _ANPR_DB:
        return

    now_iso = datetime.now(timezone.utc).isoformat()

    seeds = [
        {
            "record_id": "anpr_rec_001",
            "registration_number": "DL 01 AB 1234",
            "confidence": 0.942,
            "timestamp": now_iso,
            "gps": {"lat": 28.6315, "lon": 77.2167, "road_segment": "DEL_CP_01", "address": "Connaught Place, New Delhi"},
            "bus_id": "BUS_101",
            "camera_id": "FRONT",
            "evidence_reference": "ev_sha256_8f2d4e1b9a7c3e5d0a1b2c3d",
            "state": "READABLE",
            "human_verification_required": False,
            "verification_notice": "Automated verification passed",
            "perspective_crop_b64": _make_plate_svg("DL 01 AB 1234"),
            "raw_frame_b64": "",
            "auto_publish": True,
            "quarantined": False,
            "character_confs": [
                {"char": "D", "confidence": 0.98}, {"char": "L", "confidence": 0.97},
                {"char": "0", "confidence": 0.94}, {"char": "1", "confidence": 0.95},
                {"char": "A", "confidence": 0.93}, {"char": "B", "confidence": 0.94},
                {"char": "1", "confidence": 0.96}, {"char": "2", "confidence": 0.93},
                {"char": "3", "confidence": 0.92}, {"char": "4", "confidence": 0.95},
            ],
            "format_details": {"is_valid": True, "format_type": "STANDARD_RTO", "state_code": "DL", "state_name": "Delhi"},
            "sharpness_score": 142.5,
            "detection_score": 0.95,
            "ocr_score": 0.94,
            "verified_by": None,
            "verified_at": None,
            "officer_notes": None,
        },
        {
            "record_id": "anpr_rec_002",
            "registration_number": "HR 26 BC 3456",
            "confidence": 0.778,
            "timestamp": now_iso,
            "gps": {"lat": 28.5672, "lon": 77.2100, "road_segment": "DEL_RING_04", "address": "AIIMS Ring Road, New Delhi"},
            "bus_id": "BUS_204",
            "camera_id": "REAR",
            "evidence_reference": "ev_sha256_1c3e5d7f9a2b4c6e8d0a1b2c",
            "state": "LOW_CONFIDENCE",
            "human_verification_required": True,
            "verification_notice": HUMAN_VERIFICATION_NOTICE,
            "perspective_crop_b64": _make_plate_svg("HR 26 BC 3456"),
            "raw_frame_b64": "",
            "auto_publish": False,
            "quarantined": True,
            "character_confs": [
                {"char": "H", "confidence": 0.91}, {"char": "R", "confidence": 0.90},
                {"char": "2", "confidence": 0.88}, {"char": "6", "confidence": 0.82},
                {"char": "B", "confidence": 0.64}, {"char": "C", "confidence": 0.68},  # ambiguous B vs 8
                {"char": "3", "confidence": 0.85}, {"char": "4", "confidence": 0.89},
                {"char": "5", "confidence": 0.84}, {"char": "6", "confidence": 0.87},
            ],
            "format_details": {"is_valid": True, "format_type": "STANDARD_RTO", "state_code": "HR", "state_name": "Haryana"},
            "sharpness_score": 78.4,
            "detection_score": 0.82,
            "ocr_score": 0.76,
            "verified_by": None,
            "verified_at": None,
            "officer_notes": None,
        },
        {
            "record_id": "anpr_rec_003",
            "registration_number": "NOT_READABLE",
            "confidence": 0.412,
            "timestamp": now_iso,
            "gps": {"lat": 28.6100, "lon": 77.2300, "road_segment": "DEL_MATH_02", "address": "Mathura Road, New Delhi"},
            "bus_id": "BUS_108",
            "camera_id": "FRONT",
            "evidence_reference": "ev_sha256_4a6c8e0b2d4f6a8c0e2b4d6f",
            "state": "NOT_READABLE",
            "human_verification_required": True,
            "verification_notice": HUMAN_VERIFICATION_NOTICE,
            "perspective_crop_b64": _make_plate_svg("UNREADABLE"),
            "raw_frame_b64": "",
            "auto_publish": False,
            "quarantined": True,
            "character_confs": [],
            "format_details": {"is_valid": False, "format_type": "INVALID", "issues": ["Severe motion blur and mud occlusion"]},
            "sharpness_score": 24.1,
            "detection_score": 0.55,
            "ocr_score": 0.38,
            "verified_by": None,
            "verified_at": None,
            "officer_notes": None,
        },
        {
            "record_id": "anpr_rec_004",
            "registration_number": "NOT_PRESENT",
            "confidence": 0.0,
            "timestamp": now_iso,
            "gps": {"lat": 28.6500, "lon": 77.1900, "road_segment": "DEL_KAROL_01", "address": "Karol Bagh, New Delhi"},
            "bus_id": "BUS_112",
            "camera_id": "LEFT",
            "evidence_reference": "ev_sha256_7b9d1f3a5c7e9b1d3f5a7c9e",
            "state": "NOT_PRESENT",
            "human_verification_required": False,
            "verification_notice": "No license plate identified on vehicle",
            "perspective_crop_b64": _make_plate_svg("NO PLATE"),
            "raw_frame_b64": "",
            "auto_publish": False,
            "quarantined": False,
            "character_confs": [],
            "format_details": {"is_valid": False, "format_type": "NONE", "issues": ["Plate missing or obscured"]},
            "sharpness_score": 0.0,
            "detection_score": 0.0,
            "ocr_score": 0.0,
            "verified_by": None,
            "verified_at": None,
            "officer_notes": None,
        },
        {
            "record_id": "anpr_rec_005",
            "registration_number": "KA 05 MN 9012",
            "confidence": 0.955,
            "timestamp": now_iso,
            "gps": {"lat": 12.9716, "lon": 77.5946, "road_segment": "BLR_MG_01", "address": "MG Road, Bengaluru"},
            "bus_id": "BUS_305",
            "camera_id": "FRONT",
            "evidence_reference": "ev_sha256_2e4a6c8e0b2d4f6a8c0e2b4d",
            "state": "READABLE",
            "human_verification_required": False,
            "verification_notice": "Automated verification passed",
            "perspective_crop_b64": _make_plate_svg("KA 05 MN 9012"),
            "raw_frame_b64": "",
            "auto_publish": True,
            "quarantined": False,
            "character_confs": [
                {"char": "K", "confidence": 0.98}, {"char": "A", "confidence": 0.97},
                {"char": "0", "confidence": 0.95}, {"char": "5", "confidence": 0.96},
                {"char": "M", "confidence": 0.94}, {"char": "N", "confidence": 0.95},
                {"char": "9", "confidence": 0.97}, {"char": "0", "confidence": 0.94},
                {"char": "1", "confidence": 0.96}, {"char": "2", "confidence": 0.95},
            ],
            "format_details": {"is_valid": True, "format_type": "STANDARD_RTO", "state_code": "KA", "state_name": "Karnataka"},
            "sharpness_score": 155.0,
            "detection_score": 0.96,
            "ocr_score": 0.95,
            "verified_by": None,
            "verified_at": None,
            "officer_notes": None,
        },
        {
            "record_id": "anpr_rec_006",
            "registration_number": "22 BH 1234 AA",
            "confidence": 0.925,
            "timestamp": now_iso,
            "gps": {"lat": 19.0760, "lon": 72.8777, "road_segment": "MUM_WEH_02", "address": "Bandra Kurla Complex, Mumbai"},
            "bus_id": "BUS_402",
            "camera_id": "FRONT",
            "evidence_reference": "ev_sha256_9d1f3a5c7e9b1d3f5a7c9e1b",
            "state": "READABLE",
            "human_verification_required": False,
            "verification_notice": "Automated verification passed",
            "perspective_crop_b64": _make_plate_svg("22 BH 1234 AA"),
            "raw_frame_b64": "",
            "auto_publish": True,
            "quarantined": False,
            "character_confs": [
                {"char": "2", "confidence": 0.95}, {"char": "2", "confidence": 0.94},
                {"char": "B", "confidence": 0.92}, {"char": "H", "confidence": 0.93},
                {"char": "1", "confidence": 0.94}, {"char": "2", "confidence": 0.93},
                {"char": "3", "confidence": 0.91}, {"char": "4", "confidence": 0.92},
                {"char": "A", "confidence": 0.93}, {"char": "A", "confidence": 0.92},
            ],
            "format_details": {"is_valid": True, "format_type": "BHARAT_SERIES", "state_code": "BH", "state_name": "Bharat Central Series"},
            "sharpness_score": 138.0,
            "detection_score": 0.93,
            "ocr_score": 0.92,
            "verified_by": None,
            "verified_at": None,
            "officer_notes": None,
        },
    ]

    for s in seeds:
        _ANPR_DB[s["record_id"]] = s


_seed_anpr_records()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/recognize", status_code=201, response_model=Dict[str, Any])
async def execute_anpr_pipeline(payload: AnprCandidateIn):
    """
    Executes the 9-stage ANPR pipeline on input track frames and persists the record.
    Enforces strict quarantine on low-confidence plates with "Human verification required".
    """
    _seed_anpr_records()

    pipeline = AnprPipeline(bus_id=payload.bus_id, camera_id=payload.camera_id)

    record = pipeline.run_pipeline(
        candidate_frames=payload.candidate_frames,
        gps=payload.gps,
        incident_vehicle_info=payload.incident_vehicle_info,
        plate_text_hint=payload.plate_text_hint,
        force_missing_plate=payload.force_missing_plate,
        timestamp=payload.timestamp,
    )

    rec_id = f"anpr_rec_{uuid.uuid4().hex[:8]}"
    doc = record.to_dict()
    doc["record_id"] = rec_id
    doc["verified_by"] = None
    doc["verified_at"] = None
    doc["officer_notes"] = None

    _ANPR_DB[rec_id] = doc
    return doc


@router.get("/records", response_model=Dict[str, Any])
async def list_anpr_records(
    state: Optional[str] = Query(None, description="Filter: READABLE | LOW_CONFIDENCE | NOT_READABLE | NOT_PRESENT"),
    quarantined: Optional[bool] = Query(None, description="Filter quarantined records awaiting human review"),
    state_code: Optional[str] = Query(None, description="Filter by Indian State/UT code (e.g. DL, MH, KA)"),
    bus_id: Optional[str] = Query(None, description="Filter by bus identifier"),
    plate_query: Optional[str] = Query(None, description="Search plate number substring"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Retrieves ANPR records with filtering by state, quarantine status, and plate substring.
    """
    _seed_anpr_records()

    items = list(_ANPR_DB.values())

    if state:
        items = [i for i in items if i.get("state") == state.upper()]
    if quarantined is not None:
        items = [i for i in items if i.get("quarantined") == quarantined]
    if bus_id:
        items = [i for i in items if i.get("bus_id") == bus_id]
    if state_code:
        items = [i for i in items if i.get("format_details", {}).get("state_code") == state_code.upper()]
    if plate_query:
        q = plate_query.upper()
        items = [i for i in items if q in i.get("registration_number", "").upper()]

    items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    total = len(items)
    paged = items[offset : offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": paged,
    }


@router.get("/records/{record_id}", response_model=Dict[str, Any])
async def get_anpr_record_detail(record_id: str):
    """
    Retrieves full evidentiary record including perspective crop and character confidences.
    """
    _seed_anpr_records()

    item = _ANPR_DB.get(record_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"ANPR record '{record_id}' not found")
    return item


@router.patch("/records/{record_id}/verify", response_model=Dict[str, Any])
async def human_verify_anpr_record(record_id: str, review: HumanVerificationRequest):
    """
    Human verification endpoint for low-confidence or disputed plates.
    Authorized officer can approve transcription, edit corrected plate, or reject as unreadable.
    Un-quarantines the plate upon successful confirmation.
    """
    _seed_anpr_records()

    item = _ANPR_DB.get(record_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"ANPR record '{record_id}' not found")

    action = review.action.upper()
    now_iso = datetime.now(timezone.utc).isoformat()

    validator = PlateFormatValidator()

    if action in ("APPROVE", "EDIT"):
        target_plate = review.verified_plate or item["registration_number"]
        val_res = validator.validate(target_plate)

        item["registration_number"] = val_res.formatted_plate if val_res.is_valid else target_plate
        item["state"] = "READABLE"
        item["quarantined"] = False
        item["auto_publish"] = True
        item["human_verification_required"] = False
        item["verification_notice"] = f"Human verified by {review.officer_id}"
        item["perspective_crop_b64"] = _make_plate_svg(item["registration_number"])
        item["format_details"] = val_res.to_dict()

    elif action == "REJECT":
        item["state"] = "NOT_READABLE"
        item["registration_number"] = "NOT_READABLE"
        item["quarantined"] = False
        item["auto_publish"] = False
        item["human_verification_required"] = False
        item["verification_notice"] = f"Marked as NOT_READABLE by {review.officer_id}"

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid action. Permitted actions: 'APPROVE', 'EDIT', 'REJECT'."
        )

    item["verified_by"] = review.officer_id
    item["verified_at"] = now_iso
    item["officer_notes"] = review.notes or ""

    return {
        "status": "updated",
        "record_id": record_id,
        "state": item["state"],
        "registration_number": item["registration_number"],
        "quarantined": item["quarantined"],
        "verification_notice": item["verification_notice"],
        "verified_by": item["verified_by"],
        "verified_at": item["verified_at"],
        "officer_notes": item["officer_notes"],
    }


@router.get("/stats", response_model=Dict[str, Any])
async def get_anpr_stats():
    """
    Returns aggregated KPIs, readability ratios, and quarantine backlog counts.
    """
    _seed_anpr_records()

    all_items = list(_ANPR_DB.values())
    total = len(all_items)
    readable = sum(1 for i in all_items if i.get("state") == "READABLE")
    low_conf = sum(1 for i in all_items if i.get("state") == "LOW_CONFIDENCE")
    not_readable = sum(1 for i in all_items if i.get("state") == "NOT_READABLE")
    not_present = sum(1 for i in all_items if i.get("state") == "NOT_PRESENT")
    quarantined = sum(1 for i in all_items if i.get("quarantined", False))

    confs = [i.get("confidence", 0.0) for i in all_items if i.get("state") != "NOT_PRESENT"]
    avg_conf = round(sum(confs) / len(confs), 3) if confs else 0.0
    readability_rate = round((readable / max(1, total)) * 100, 1)

    state_breakdown: Dict[str, int] = {}
    for i in all_items:
        st = i.get("format_details", {}).get("state_code") or "OTHER"
        state_breakdown[st] = state_breakdown.get(st, 0) + 1

    return {
        "total_scanned": total,
        "readable_count": readable,
        "low_confidence_count": low_conf,
        "not_readable_count": not_readable,
        "not_present_count": not_present,
        "quarantined_count": quarantined,
        "readability_rate_pct": readability_rate,
        "average_confidence": avg_conf,
        "state_breakdown": state_breakdown,
        "safety_guardrails": {
            "auto_publish_low_confidence_blocked": True,
            "human_verification_mandated": True,
            "quarantined_backlog": quarantined,
        },
    }
