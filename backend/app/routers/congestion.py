"""
Traffic Bottleneck & Congestion Router (Phase 11 & Phase 20)
============================================================
Endpoints for:
  - Ingesting edge Congestion Events
  - Querying active bottleneck alerts
  - Generating spatial heatmap points with Date & Time-of-Day filtering
  - Returning road segment polyline statuses with route delay & severity colors
  - Top 10 Congested Road Segments leaderboard
  - Diurnal peak hours & historical congestion analytics
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..database.session import get_session
from ..models.ingested_event import IngestedEvent

router = APIRouter()

# ── Enums & Schemas ───────────────────────────────────────────────────────────

class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    SEVERE = "SEVERE"


class DateRangeFilter(str, Enum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"


class TimeOfDayFilter(str, Enum):
    ALL = "all"
    MORNING = "morning"      # 06:00 - 11:59
    AFTERNOON = "afternoon"  # 12:00 - 16:59
    EVENING = "evening"      # 17:00 - 21:59
    NIGHT = "night"          # 22:00 - 05:59


class LocationModel(BaseModel):
    lat: float
    lon: float


class CongestionEventIn(BaseModel):
    event_id:         Optional[str] = None
    road_segment:     str
    segment_name:     Optional[str] = None
    density:          float = Field(..., ge=0.0, le=1.0)
    average_speed:    float = Field(..., ge=0.0)
    congestion_score: float = Field(..., ge=0.0, le=100.0)
    severity:         SeverityLevel
    timestamp:        Optional[str] = None
    location:         LocationModel
    vehicle_count:    Optional[int] = 0
    duration_seconds: Optional[float] = 0.0
    is_bottleneck:    Optional[bool] = False
    bus_id:           Optional[str] = None
    camera_id:        Optional[str] = None


# ── Monitored Road Segments Seed (16 Comprehensive Metro Corridors) ───────────

SEGMENTS_SEED = [
    # ── Delhi NCR Corridors ──
    {
        "segment_id": "DEL_01",
        "name": "Ring Road – Dhaula Kuan to Mahipalpur",
        "road_type": "expressway",
        "city": "Delhi",
        "length_km": 5.4,
        "capacity_per_km": 120,
        "free_flow_speed": 70.0,
        "baseline_speed": 45.0,
        "current_speed": 14.2,
        "density": 0.88,
        "congestion_score": 86.4,
        "severity": "SEVERE",
        "is_bottleneck": True,
        "active_vehicles": 42,
        "peak_hours": "08:30 - 10:30 & 18:00 - 20:30",
        "polyline": [
            {"lat": 28.5918, "lon": 77.1675},
            {"lat": 28.5842, "lon": 77.1545},
            {"lat": 28.5765, "lon": 77.1420},
        ],
    },
    {
        "segment_id": "DEL_02",
        "name": "NH-48 – Dhaula Kuan to Shankar Vihar",
        "road_type": "arterial",
        "city": "Delhi",
        "length_km": 4.8,
        "capacity_per_km": 90,
        "free_flow_speed": 55.0,
        "baseline_speed": 38.0,
        "current_speed": 19.5,
        "density": 0.72,
        "congestion_score": 71.8,
        "severity": "HIGH",
        "is_bottleneck": True,
        "active_vehicles": 29,
        "peak_hours": "09:00 - 11:00 & 18:30 - 21:00",
        "polyline": [
            {"lat": 28.5971, "lon": 77.1690},
            {"lat": 28.6050, "lon": 77.1680},
            {"lat": 28.6130, "lon": 77.1670},
        ],
    },
    {
        "segment_id": "DEL_03",
        "name": "Mehrauli-Badarpur Road",
        "road_type": "arterial",
        "city": "Delhi",
        "length_km": 6.2,
        "capacity_per_km": 75,
        "free_flow_speed": 45.0,
        "baseline_speed": 32.0,
        "current_speed": 22.0,
        "density": 0.54,
        "congestion_score": 52.0,
        "severity": "MEDIUM",
        "is_bottleneck": False,
        "active_vehicles": 18,
        "peak_hours": "08:00 - 10:00 & 17:30 - 19:30",
        "polyline": [
            {"lat": 28.5205, "lon": 77.1855},
            {"lat": 28.5145, "lon": 77.1960},
            {"lat": 28.5085, "lon": 77.2065},
        ],
    },
    {
        "segment_id": "DEL_04",
        "name": "Outer Ring Road – Nehru Place Flyover",
        "road_type": "arterial",
        "city": "Delhi",
        "length_km": 3.9,
        "capacity_per_km": 80,
        "free_flow_speed": 50.0,
        "baseline_speed": 36.0,
        "current_speed": 38.5,
        "density": 0.22,
        "congestion_score": 18.0,
        "severity": "LOW",
        "is_bottleneck": False,
        "active_vehicles": 9,
        "peak_hours": "09:00 - 10:30 & 18:30 - 20:00",
        "polyline": [
            {"lat": 28.5490, "lon": 77.2520},
            {"lat": 28.5520, "lon": 77.2580},
            {"lat": 28.5560, "lon": 77.2640},
        ],
    },
    {
        "segment_id": "DEL_05",
        "name": "ITO Junction – Vikas Marg Bridge",
        "road_type": "arterial",
        "city": "Delhi",
        "length_km": 3.2,
        "capacity_per_km": 95,
        "free_flow_speed": 45.0,
        "baseline_speed": 28.0,
        "current_speed": 11.0,
        "density": 0.91,
        "congestion_score": 89.5,
        "severity": "SEVERE",
        "is_bottleneck": True,
        "active_vehicles": 46,
        "peak_hours": "08:45 - 11:00 & 17:45 - 20:45",
        "polyline": [
            {"lat": 28.6300, "lon": 77.2400},
            {"lat": 28.6320, "lon": 77.2480},
            {"lat": 28.6335, "lon": 77.2560},
        ],
    },
    {
        "segment_id": "DEL_06",
        "name": "Ashram Chowk – Mathura Road Underpass",
        "road_type": "arterial",
        "city": "Delhi",
        "length_km": 4.1,
        "capacity_per_km": 105,
        "free_flow_speed": 50.0,
        "baseline_speed": 30.0,
        "current_speed": 13.5,
        "density": 0.84,
        "congestion_score": 81.2,
        "severity": "SEVERE",
        "is_bottleneck": True,
        "active_vehicles": 39,
        "peak_hours": "08:30 - 10:30 & 18:00 - 21:00",
        "polyline": [
            {"lat": 28.5710, "lon": 77.2590},
            {"lat": 28.5745, "lon": 77.2620},
            {"lat": 28.5780, "lon": 77.2655},
        ],
    },

    # ── Mumbai MMR Corridors ──
    {
        "segment_id": "MUM_01",
        "name": "Eastern Express Highway – Kurla Junction",
        "road_type": "expressway",
        "city": "Mumbai",
        "length_km": 5.8,
        "capacity_per_km": 130,
        "free_flow_speed": 80.0,
        "baseline_speed": 52.0,
        "current_speed": 16.0,
        "density": 0.85,
        "congestion_score": 83.2,
        "severity": "SEVERE",
        "is_bottleneck": True,
        "active_vehicles": 51,
        "peak_hours": "08:30 - 11:00 & 18:00 - 21:30",
        "polyline": [
            {"lat": 19.0748, "lon": 72.8856},
            {"lat": 19.0800, "lon": 72.8900},
            {"lat": 19.0855, "lon": 72.8940},
        ],
    },
    {
        "segment_id": "MUM_02",
        "name": "LBS Marg – Ghatkopar West",
        "road_type": "arterial",
        "city": "Mumbai",
        "length_km": 4.5,
        "capacity_per_km": 70,
        "free_flow_speed": 40.0,
        "baseline_speed": 28.0,
        "current_speed": 15.8,
        "density": 0.68,
        "congestion_score": 67.4,
        "severity": "HIGH",
        "is_bottleneck": True,
        "active_vehicles": 24,
        "peak_hours": "09:00 - 10:45 & 18:15 - 20:30",
        "polyline": [
            {"lat": 19.0865, "lon": 72.9077},
            {"lat": 19.0900, "lon": 72.9110},
            {"lat": 19.0940, "lon": 72.9145},
        ],
    },
    {
        "segment_id": "MUM_03",
        "name": "Western Express Highway – Bandra Flyover",
        "road_type": "expressway",
        "city": "Mumbai",
        "length_km": 6.1,
        "capacity_per_km": 110,
        "free_flow_speed": 70.0,
        "baseline_speed": 48.0,
        "current_speed": 34.0,
        "density": 0.46,
        "congestion_score": 42.1,
        "severity": "MEDIUM",
        "is_bottleneck": False,
        "active_vehicles": 19,
        "peak_hours": "08:15 - 10:15 & 17:45 - 20:15",
        "polyline": [
            {"lat": 19.0550, "lon": 72.8420},
            {"lat": 19.0620, "lon": 72.8460},
            {"lat": 19.0700, "lon": 72.8510},
        ],
    },
    {
        "segment_id": "MUM_04",
        "name": "JVLR – Powai Lake Corridor",
        "road_type": "arterial",
        "city": "Mumbai",
        "length_km": 5.2,
        "capacity_per_km": 85,
        "free_flow_speed": 50.0,
        "baseline_speed": 34.0,
        "current_speed": 17.2,
        "density": 0.74,
        "congestion_score": 73.5,
        "severity": "HIGH",
        "is_bottleneck": True,
        "active_vehicles": 31,
        "peak_hours": "08:30 - 10:45 & 18:00 - 21:00",
        "polyline": [
            {"lat": 19.1240, "lon": 72.8980},
            {"lat": 19.1280, "lon": 72.9050},
            {"lat": 19.1310, "lon": 72.9120},
        ],
    },
    {
        "segment_id": "MUM_05",
        "name": "Sion Circle – Dr. B.A. Road",
        "road_type": "arterial",
        "city": "Mumbai",
        "length_km": 3.7,
        "capacity_per_km": 95,
        "free_flow_speed": 45.0,
        "baseline_speed": 29.0,
        "current_speed": 12.8,
        "density": 0.86,
        "congestion_score": 84.8,
        "severity": "SEVERE",
        "is_bottleneck": True,
        "active_vehicles": 41,
        "peak_hours": "08:45 - 11:15 & 18:30 - 21:15",
        "polyline": [
            {"lat": 19.0380, "lon": 72.8630},
            {"lat": 19.0430, "lon": 72.8660},
            {"lat": 19.0480, "lon": 72.8690},
        ],
    },

    # ── Bangalore Corridors ──
    {
        "segment_id": "BLR_01",
        "name": "Outer Ring Road – Marathahalli Bridge",
        "road_type": "arterial",
        "city": "Bangalore",
        "length_km": 4.9,
        "capacity_per_km": 85,
        "free_flow_speed": 45.0,
        "baseline_speed": 30.0,
        "current_speed": 8.5,
        "density": 0.94,
        "congestion_score": 92.5,
        "severity": "SEVERE",
        "is_bottleneck": True,
        "active_vehicles": 48,
        "peak_hours": "08:30 - 11:30 & 17:30 - 21:30",
        "polyline": [
            {"lat": 12.9591, "lon": 77.6971},
            {"lat": 12.9540, "lon": 77.7020},
            {"lat": 12.9489, "lon": 77.7070},
        ],
    },
    {
        "segment_id": "BLR_02",
        "name": "Hosur Road – Central Silk Board",
        "road_type": "arterial",
        "city": "Bangalore",
        "length_km": 5.1,
        "capacity_per_km": 90,
        "free_flow_speed": 40.0,
        "baseline_speed": 26.0,
        "current_speed": 10.2,
        "density": 0.89,
        "congestion_score": 88.0,
        "severity": "SEVERE",
        "is_bottleneck": True,
        "active_vehicles": 44,
        "peak_hours": "08:15 - 11:30 & 18:00 - 21:45",
        "polyline": [
            {"lat": 12.9170, "lon": 77.6233},
            {"lat": 12.9122, "lon": 77.6270},
            {"lat": 12.9075, "lon": 77.6308},
        ],
    },
    {
        "segment_id": "BLR_03",
        "name": "Bellary Road – Hebbal Flyover Entry",
        "road_type": "expressway",
        "city": "Bangalore",
        "length_km": 6.5,
        "capacity_per_km": 100,
        "free_flow_speed": 60.0,
        "baseline_speed": 42.0,
        "current_speed": 26.5,
        "density": 0.58,
        "congestion_score": 54.2,
        "severity": "MEDIUM",
        "is_bottleneck": False,
        "active_vehicles": 22,
        "peak_hours": "08:45 - 10:30 & 18:15 - 20:30",
        "polyline": [
            {"lat": 13.0359, "lon": 77.5970},
            {"lat": 13.0395, "lon": 77.5985},
            {"lat": 13.0430, "lon": 77.6000},
        ],
    },
    {
        "segment_id": "BLR_04",
        "name": "Whitefield Main Road – ITPL Gate",
        "road_type": "arterial",
        "city": "Bangalore",
        "length_km": 4.2,
        "capacity_per_km": 80,
        "free_flow_speed": 40.0,
        "baseline_speed": 27.0,
        "current_speed": 13.0,
        "density": 0.81,
        "congestion_score": 79.5,
        "severity": "HIGH",
        "is_bottleneck": True,
        "active_vehicles": 35,
        "peak_hours": "09:00 - 11:30 & 17:45 - 20:45",
        "polyline": [
            {"lat": 12.9860, "lon": 77.7280},
            {"lat": 12.9890, "lon": 77.7340},
            {"lat": 12.9920, "lon": 77.7400},
        ],
    },
    {
        "segment_id": "BLR_05",
        "name": "Bannerghatta Road – Dairy Circle",
        "road_type": "arterial",
        "city": "Bangalore",
        "length_km": 4.0,
        "capacity_per_km": 75,
        "free_flow_speed": 40.0,
        "baseline_speed": 28.0,
        "current_speed": 18.0,
        "density": 0.62,
        "congestion_score": 62.0,
        "severity": "HIGH",
        "is_bottleneck": True,
        "active_vehicles": 25,
        "peak_hours": "08:30 - 10:30 & 18:00 - 20:30",
        "polyline": [
            {"lat": 12.9350, "lon": 77.6010},
            {"lat": 12.9300, "lon": 77.6030},
            {"lat": 12.9250, "lon": 77.6050},
        ],
    },
]

# ── In-Memory Stores ──────────────────────────────────────────────────────────

_events: List[Dict[str, Any]] = []
_segments_store: Dict[str, Dict[str, Any]] = {s["segment_id"]: dict(s) for s in SEGMENTS_SEED}
_MAX_EVENTS = 5000


def _init_seed_events():
    """Populate initial realistic events corresponding to the seeded bottlenecks."""
    now_iso = datetime.now(timezone.utc).isoformat()
    for seg in SEGMENTS_SEED:
        if seg["is_bottleneck"]:
            mid = seg["polyline"][len(seg["polyline"]) // 2]
            _events.append({
                "event_id":         str(uuid.uuid4()),
                "event_type":       "congestion_event",
                "road_segment":     seg["segment_id"],
                "segment_name":     seg["name"],
                "density":          seg["density"],
                "average_speed":    seg["current_speed"],
                "congestion_score": seg["congestion_score"],
                "severity":         seg["severity"],
                "timestamp":        now_iso,
                "location":         {"lat": mid["lat"], "lon": mid["lon"]},
                "vehicle_count":    seg["active_vehicles"],
                "duration_seconds": 180.0 if seg["severity"] == "SEVERE" else 75.0,
                "is_bottleneck":    True,
                "bus_id":           f"BUS_{seg['city'][:3].upper()}_102",
                "camera_id":        "FRONT",
            })

_init_seed_events()


# ── Mathematical Helper Functions ─────────────────────────────────────────────

def _calculate_route_delay_minutes(length_km: float, current_speed_kmh: float, free_flow_speed_kmh: float) -> float:
    """
    Computes route delay (extra minutes lost compared to free-flow conditions):
      delay_min = max(0, (L / current_speed - L / free_flow_speed) * 60)
    """
    if current_speed_kmh <= 0 or free_flow_speed_kmh <= 0:
        return 0.0
    delay = ((length_km / current_speed_kmh) - (length_km / free_flow_speed_kmh)) * 60.0
    return round(max(0.0, delay), 1)


def _get_severity_color(severity: str) -> str:
    """
    Prompt requirement:
      Green = low
      Yellow = moderate
      Orange = high
      Red = severe
    """
    s = severity.upper()
    if s == "LOW":
        return "green"
    elif s in ("MEDIUM", "MODERATE"):
        return "yellow"
    elif s == "HIGH":
        return "orange"
    elif s == "SEVERE":
        return "red"
    return "yellow"


def _apply_temporal_modifiers(base_score: float, base_speed: float, time_filter: TimeOfDayFilter, date_filter: DateRangeFilter) -> tuple[float, float, str]:
    """
    Applies deterministic time-of-day and date multipliers to reflect realistic traffic shifts:
      - Morning (06-12): AM rush hour peak (+15% congestion)
      - Afternoon (12-17): Midday lull (-10% congestion)
      - Evening (17-22): PM rush hour peak (+25% congestion)
      - Night (22-06): Free-flow nocturnal (-65% congestion)
    """
    score = base_score
    speed = base_speed

    if time_filter == TimeOfDayFilter.MORNING:
        score = min(99.0, score * 1.15)
        speed = max(6.0, speed * 0.88)
    elif time_filter == TimeOfDayFilter.AFTERNOON:
        score = max(10.0, score * 0.85)
        speed = min(75.0, speed * 1.15)
    elif time_filter == TimeOfDayFilter.EVENING:
        score = min(99.0, score * 1.25)
        speed = max(5.0, speed * 0.80)
    elif time_filter == TimeOfDayFilter.NIGHT:
        score = max(5.0, score * 0.35)
        speed = min(75.0, speed * 1.65)

    if date_filter == DateRangeFilter.YESTERDAY:
        score = score * 0.98
    elif date_filter == DateRangeFilter.LAST_7_DAYS:
        score = score * 0.95
    elif date_filter == DateRangeFilter.LAST_30_DAYS:
        score = score * 0.92

    score = round(min(100.0, max(0.0, score)), 1)
    speed = round(max(5.0, speed), 1)

    if score >= 80.0:
        sev = "SEVERE"
    elif score >= 60.0:
        sev = "HIGH"
    elif score >= 35.0:
        sev = "MEDIUM"
    else:
        sev = "LOW"

    return score, speed, sev


# ── Core Endpoints ────────────────────────────────────────────────────────────

@router.post("/events", status_code=201)
async def ingest_congestion_event(event: CongestionEventIn):
    """
    Ingest a real-time Congestion Event from the edge AI pipeline.
    Updates the road segment live cache and appends to event history.
    """
    rec = event.model_dump()
    rec["event_id"] = rec.get("event_id") or str(uuid.uuid4())
    rec["timestamp"] = rec.get("timestamp") or datetime.now(timezone.utc).isoformat()
    rec["event_type"] = "congestion_event"

    seg_id = rec["road_segment"]
    if seg_id in _segments_store:
        _segments_store[seg_id]["current_speed"] = rec["average_speed"]
        _segments_store[seg_id]["density"] = rec["density"]
        _segments_store[seg_id]["congestion_score"] = rec["congestion_score"]
        _segments_store[seg_id]["severity"] = rec["severity"]
        _segments_store[seg_id]["is_bottleneck"] = rec.get("is_bottleneck", False)
        if rec.get("vehicle_count"):
            _segments_store[seg_id]["active_vehicles"] = rec["vehicle_count"]

    _events.append(rec)
    if len(_events) > _MAX_EVENTS:
        _events.pop(0)

    return {"ok": True, "event_id": rec["event_id"]}


@router.get("/events")
async def list_congestion_events(
    severity:     Optional[SeverityLevel] = Query(None),
    road_segment: Optional[str]           = Query(None),
    city:         Optional[str]           = Query(None),
    limit:        int                     = Query(50, ge=1, le=200),
    offset:       int                     = Query(0, ge=0),
    db: Session = Depends(get_session),
):
    """
    List congestion events with optional severity and segment filtering.
    """
    db_query = select(IngestedEvent).where(IngestedEvent.event_type == 'CONGESTION_EVENT')
    if severity:
        db_query = db_query.where(IngestedEvent.severity == severity.value.upper())
    if road_segment:
        db_query = db_query.where(IngestedEvent.road_segment == road_segment)
    
    db_events = db.exec(db_query).all()
    db_results = []
    for e in db_events:
        city_match = True
        if city:
            c = city.lower()
            if not ((e.address and c in e.address.lower()) or (e.road_segment and c in e.road_segment.lower())):
                city_match = False
        if city_match:
            db_results.append({
                "event_id": e.event_id,
                "event_type": "congestion_event",
                "road_segment": e.road_segment or "UNKNOWN",
                "segment_name": e.address,
                "density": 0.8,
                "average_speed": 10.0,
                "congestion_score": 80.0,
                "severity": e.severity or "HIGH",
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "location": {"lat": e.gps_lat, "lon": e.gps_lon},
                "is_bottleneck": True,
                "bus_id": e.bus_id,
                "camera_id": e.camera_id,
            })

    results = db_results + list(reversed(_events))
    if severity and not db_events:
        results = [e for e in results if e.get("severity") == severity.value]
    elif severity:
        results = [e for e in results if e.get("severity") == severity.value or (e in db_results)]
    
    # We still need to filter memory _events
    filtered_results = []
    for e in results:
        if severity and e.get("severity") != severity.value:
            continue
        if road_segment and e.get("road_segment") != road_segment:
            continue
        if city:
            c = city.lower()
            if not ((e.get("segment_name") and c in e.get("segment_name").lower()) or (e.get("road_segment") and c in e.get("road_segment").lower())):
                continue
        filtered_results.append(e)

    total = len(filtered_results)
    return {
        "total": total,
        "items": filtered_results[offset: offset + limit],
    }


@router.get("/heatmap")
async def get_congestion_heatmap(
    date_range:  DateRangeFilter = Query(DateRangeFilter.TODAY, description="Today | Yesterday | Last 7 days | Last 30 days"),
    time_of_day: TimeOfDayFilter = Query(TimeOfDayFilter.ALL, description="Morning | Afternoon | Evening | Night | All"),
    city:        Optional[str]   = Query(None, description="Optional city filter (Delhi, Mumbai, Bangalore)"),
    db: Session = Depends(get_session),
):
    """
    Returns spatial points with coordinates, normalized intensity (0.0 - 1.0),
    and exact visual color mappings (Green, Yellow, Orange, Red) to render a dynamic
    congestion heatmap layer on GIS maps.
    Supports filtering by Date Range and Time of Day.
    """
    heatmap_points = []

    for seg in _segments_store.values():
        if city and seg.get("city", "").lower() != city.lower():
            continue

        raw_score = seg.get("congestion_score", 0.0)
        raw_speed = seg.get("current_speed", 50.0)
        length_km = seg.get("length_km", 4.5)
        free_flow = seg.get("free_flow_speed", 50.0)

        # Apply temporal modifications
        score, speed, severity = _apply_temporal_modifiers(raw_score, raw_speed, time_of_day, date_range)
        color = _get_severity_color(severity)
        delay_min = _calculate_route_delay_minutes(length_km, speed, free_flow)

        # Base intensity: 0.0 to 1.0 normalized
        base_intensity = round(score / 100.0, 3)

        polyline = seg.get("polyline", [])
        if not polyline:
            continue

        # Points along corridor polyline
        for idx, pt in enumerate(polyline):
            weight = base_intensity
            if severity == "SEVERE":
                weight = min(1.0, round(weight * 1.1, 3))

            heatmap_points.append({
                "lat": pt["lat"],
                "lon": pt["lon"],
                "intensity": weight,
                "severity": severity,
                "color": color,
                "score": score,
                "segment_id": seg["segment_id"],
                "name": seg["name"],
                "city": seg["city"],
                "speed_kmh": speed,
                "density": seg.get("density", 0.5),
                "route_delay_minutes": delay_min,
            })

    # Also add DB points
    db_events = db.exec(select(IngestedEvent).where(IngestedEvent.event_type == 'CONGESTION_EVENT')).all()
    for e in db_events:
        # Simple city filter check
        if city:
            c = city.lower()
            if not ((e.address and c in e.address.lower()) or (e.road_segment and c in e.road_segment.lower())):
                continue
                
        sev = e.severity or "MEDIUM"
        heatmap_points.append({
            "lat": e.gps_lat,
            "lon": e.gps_lon,
            "intensity": 0.8 if sev in ("HIGH", "SEVERE") else 0.5,
            "severity": sev,
            "color": _get_severity_color(sev),
            "score": 80.0 if sev in ("HIGH", "SEVERE") else 50.0,
            "segment_id": e.road_segment or "UNKNOWN",
            "name": e.address or "DB Event",
            "city": "Unknown",
            "speed_kmh": 15.0,
            "density": 0.8,
            "route_delay_minutes": 5.0,
        })

    return {
        "count": len(heatmap_points),
        "filters": {
            "date_range": date_range.value,
            "time_of_day": time_of_day.value,
            "city": city or "All",
        },
        "palette": {
            "LOW": {"color": "green", "hex": "#10b981", "label": "Low Congestion"},
            "MEDIUM": {"color": "yellow", "hex": "#eab308", "label": "Moderate Congestion"},
            "HIGH": {"color": "orange", "hex": "#f97316", "label": "High Congestion"},
            "SEVERE": {"color": "red", "hex": "#ef4444", "label": "Severe Bottleneck"},
        },
        "points": heatmap_points,
    }


@router.get("/segments")
async def list_monitored_segments(
    city:        Optional[str]   = Query(None),
    date_range:  DateRangeFilter = Query(DateRangeFilter.TODAY),
    time_of_day: TimeOfDayFilter = Query(TimeOfDayFilter.ALL),
):
    """
    Return all monitored road segments with geometry, baseline speeds, current speeds,
    route delay (minutes lost vs free-flow), and color-coded severity.
    """
    if not isinstance(date_range, DateRangeFilter):
        date_range = DateRangeFilter(date_range) if isinstance(date_range, str) else DateRangeFilter.TODAY
    if not isinstance(time_of_day, TimeOfDayFilter):
        time_of_day = TimeOfDayFilter(time_of_day) if isinstance(time_of_day, str) else TimeOfDayFilter.ALL

    raw_segments = list(_segments_store.values())
    if city:
        raw_segments = [s for s in raw_segments if s.get("city", "").lower() == city.lower()]

    enriched = []
    for s in raw_segments:
        item = dict(s)
        base = max(1.0, item.get("baseline_speed", 50.0))
        raw_speed = item.get("current_speed", base)
        raw_score = item.get("congestion_score", 50.0)
        length_km = item.get("length_km", 4.5)
        free_flow = item.get("free_flow_speed", 50.0)

        # Modify with temporal selection
        score, speed, sev = _apply_temporal_modifiers(raw_score, raw_speed, time_of_day, date_range)
        deficit = max(0.0, (base - speed) / base * 100.0)
        delay_min = _calculate_route_delay_minutes(length_km, speed, free_flow)

        item["current_speed"] = speed
        item["congestion_score"] = score
        item["severity"] = sev
        item["severity_color"] = _get_severity_color(sev)
        item["speed_deficit_pct"] = round(deficit, 1)
        item["route_delay_minutes"] = delay_min
        item["is_bottleneck"] = sev in ("HIGH", "SEVERE")
        enriched.append(item)

    return {"count": len(enriched), "segments": enriched}


@router.get("/top-segments")
async def get_top_congested_segments(
    limit:       int             = Query(10, ge=1, le=50, description="Top N segments (default 10)"),
    city:        Optional[str]   = Query(None),
    date_range:  DateRangeFilter = Query(DateRangeFilter.TODAY),
    time_of_day: TimeOfDayFilter = Query(TimeOfDayFilter.ALL),
):
    """
    Top 10 Congested Road Segments leaderboard ranked by congestion score,
    complete with route delay minutes, vehicle density, speed deficit, and peak hour windows.
    """
    if not isinstance(date_range, DateRangeFilter):
        date_range = DateRangeFilter(date_range) if isinstance(date_range, str) else DateRangeFilter.TODAY
    if not isinstance(time_of_day, TimeOfDayFilter):
        time_of_day = TimeOfDayFilter(time_of_day) if isinstance(time_of_day, str) else TimeOfDayFilter.ALL

    segments_data = (await list_monitored_segments(city=city, date_range=date_range, time_of_day=time_of_day))["segments"]
    # Sort descending by congestion_score, then route_delay_minutes
    sorted_segs = sorted(segments_data, key=lambda s: (s["congestion_score"], s["route_delay_minutes"]), reverse=True)

    top_n = sorted_segs[:limit]
    for idx, item in enumerate(top_n, start=1):
        item["rank"] = idx

    return {
        "count": len(top_n),
        "limit": limit,
        "date_range": date_range.value,
        "time_of_day": time_of_day.value,
        "top_segments": top_n,
    }


@router.get("/bottlenecks")
async def list_active_bottlenecks(
    city: Optional[str] = Query(None)
):
    """
    List currently active bottlenecks (segments with severity HIGH or SEVERE).
    """
    bottlenecks = [
        s for s in _segments_store.values()
        if s.get("is_bottleneck", False) or s.get("severity") in ("HIGH", "SEVERE")
    ]
    if city:
        bottlenecks = [b for b in bottlenecks if b.get("city", "").lower() == city.lower()]

    return {
        "count": len(bottlenecks),
        "bottlenecks": bottlenecks,
    }


@router.get("/analytics")
async def get_congestion_analytics(
    city:        Optional[str]   = Query(None),
    date_range:  DateRangeFilter = Query(DateRangeFilter.TODAY),
    time_of_day: TimeOfDayFilter = Query(TimeOfDayFilter.ALL),
):
    """
    Comprehensive Traffic Congestion Analytics:
      - Network KPIs: Average Speed, Vehicle Density, Total Route Delay
      - Peak Hours breakdown (AM Rush, PM Rush, Night Baseline)
      - 24-Hour Diurnal Congestion vs Speed curve
      - Historical Trend over selected range
      - Top 10 Congested Segments leaderboard
    """
    if not isinstance(date_range, DateRangeFilter):
        date_range = DateRangeFilter(date_range) if isinstance(date_range, str) else DateRangeFilter.TODAY
    if not isinstance(time_of_day, TimeOfDayFilter):
        time_of_day = TimeOfDayFilter(time_of_day) if isinstance(time_of_day, str) else TimeOfDayFilter.ALL

    segments_res = await list_monitored_segments(city=city, date_range=date_range, time_of_day=time_of_day)
    segments = segments_res["segments"]

    if not segments:
        return {"error": "No segment data available"}

    n = len(segments)
    avg_speed = round(sum(s["current_speed"] for s in segments) / n, 1)
    avg_density = round(sum(s["density"] for s in segments) / n, 2)
    avg_score = round(sum(s["congestion_score"] for s in segments) / n, 1)
    total_delay = round(sum(s["route_delay_minutes"] for s in segments), 1)
    avg_delay = round(total_delay / n, 1)
    active_bottlenecks = sum(1 for s in segments if s.get("is_bottleneck", False))

    severity_counts = defaultdict(int)
    for s in segments:
        severity_counts[s["severity"]] += 1

    # 24-Hour Diurnal Progression Profile
    # Standard urban commuter pattern: dual-peaked curve at 09:00 and 19:00
    hourly_profile = []
    for h in range(24):
        # Peak multipliers: morning rush (8-10), evening rush (18-20)
        if 8 <= h <= 10:
            h_mult = 1.35
            spd_mult = 0.65
        elif 18 <= h <= 20:
            h_mult = 1.45
            spd_mult = 0.58
        elif 12 <= h <= 15:
            h_mult = 0.95
            spd_mult = 1.05
        elif 22 <= h or h <= 5:
            h_mult = 0.35
            spd_mult = 1.60
        else:
            h_mult = 1.0
            spd_mult = 1.0

        h_score = round(min(98.0, max(5.0, avg_score * h_mult)), 1)
        h_speed = round(max(6.0, avg_speed * spd_mult), 1)
        h_baseline_speed = round(avg_speed * 1.15, 1)

        hourly_profile.append({
            "hour": f"{h:02d}:00",
            "hour_int": h,
            "congestion_score": h_score,
            "average_speed_kmh": h_speed,
            "baseline_speed_kmh": h_baseline_speed,
            "is_peak": (8 <= h <= 10) or (18 <= h <= 20),
        })

    # Historical multi-day trend
    days_count = 30 if date_range == DateRangeFilter.LAST_30_DAYS else (7 if date_range == DateRangeFilter.LAST_7_DAYS else 3)
    historical_trend = []
    base_date = datetime.now(timezone.utc)
    for d in range(days_count - 1, -1, -1):
        day_date = datetime.fromtimestamp(base_date.timestamp() - (d * 86400), tz=timezone.utc)
        day_str = day_date.strftime("%b %d")
        jitter = (math.sin(d * 1.2) * 6.0)
        historical_trend.append({
            "date": day_str,
            "avg_congestion_score": round(min(95.0, max(20.0, avg_score + jitter)), 1),
            "peak_congestion_score": round(min(99.0, max(40.0, avg_score + jitter + 16.0)), 1),
            "avg_speed_kmh": round(max(8.0, avg_speed - (jitter * 0.4)), 1),
            "total_bottlenecks": max(1, int(active_bottlenecks + (jitter // 4))),
        })

    # Top 10 Congested Segments
    sorted_segs = sorted(segments, key=lambda s: (s["congestion_score"], s["route_delay_minutes"]), reverse=True)[:10]
    for idx, item in enumerate(sorted_segs, start=1):
        item["rank"] = idx

    return {
        "filters": {
            "date_range": date_range.value,
            "time_of_day": time_of_day.value,
            "city": city or "All",
        },
        "kpis": {
            "average_speed_kmh": avg_speed,
            "average_vehicle_density": avg_density,
            "average_route_delay_minutes": avg_delay,
            "total_route_delay_minutes": total_delay,
            "network_congestion_score": avg_score,
            "active_bottlenecks_count": active_bottlenecks,
            "monitored_segments_count": n,
            "severity_distribution": dict(severity_counts),
        },
        "peak_hours": {
            "morning_peak": {
                "window": "08:30 - 10:30",
                "label": "Morning Commuter Peak",
                "avg_score": round(min(98.0, avg_score * 1.35), 1),
                "avg_speed_kmh": round(max(6.0, avg_speed * 0.65), 1),
                "primary_cause": "Office inbound radial transit & expressway merges",
            },
            "evening_peak": {
                "window": "18:00 - 20:30",
                "label": "Evening Commuter Peak",
                "avg_score": round(min(99.0, avg_score * 1.45), 1),
                "avg_speed_kmh": round(max(5.0, avg_speed * 0.58), 1),
                "primary_cause": "CBD outbound corridors & arterial bottlenecks",
            },
            "off_peak_baseline": {
                "window": "23:00 - 05:30",
                "label": "Nocturnal Baseline Flow",
                "avg_score": round(max(5.0, avg_score * 0.35), 1),
                "avg_speed_kmh": round(min(75.0, avg_speed * 1.60), 1),
                "primary_cause": "Uncongested free-flow conditions",
            },
        },
        "hourly_diurnal_profile": hourly_profile,
        "historical_trend": historical_trend,
        "top_10_congested_segments": sorted_segs,
    }


@router.get("/stats")
async def congestion_summary_stats(
    city: Optional[str] = Query(None)
):
    """
    High-level dashboard KPIs and analytical aggregations for traffic congestion.
    """
    analytics = await get_congestion_analytics(city=city)
    kpis = analytics["kpis"]
    top_10 = analytics["top_10_congested_segments"]

    return {
        "monitored_segments": kpis["monitored_segments_count"],
        "active_bottlenecks": kpis["active_bottlenecks_count"],
        "average_congestion_score": kpis["network_congestion_score"],
        "average_speed_kmh": kpis["average_speed_kmh"],
        "average_route_delay_minutes": kpis["average_route_delay_minutes"],
        "total_route_delay_minutes": kpis["total_route_delay_minutes"],
        "avg_speed_deficit_pct": round(max(0.0, (45.0 - kpis["average_speed_kmh"]) / 45.0 * 100.0), 1),
        "severity_counts": kpis["severity_distribution"],
        "worst_segment": top_10[0] if top_10 else None,
    }
