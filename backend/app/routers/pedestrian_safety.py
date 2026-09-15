"""
Pedestrian Safety & School Zone Intelligence Router
===================================================
Endpoints for:
  - Ingesting vulnerable PEDESTRIAN_RISK events
  - Querying school zone registries and bell schedules
  - Inspecting zone-level pedestrian crowd densities
  - Retrieving summary KPIs and evidence frames
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class TrajectoryInfo(BaseModel):
    speed_px_s:         float
    heading_deg:        float
    moving_toward_road: bool
    vector:             List[float] = [0.0, 0.0]


class SchoolZoneInfo(BaseModel):
    school_id:       str
    name:            str
    distance_m:      float
    active_now:      bool
    speed_limit_kmh: Optional[float] = 25.0


class RoadBoundaryInfo(BaseModel):
    distance_px:      float
    is_near_boundary: bool


class ZoneDensityInfo(BaseModel):
    level:            str  # "LOW" | "MEDIUM" | "HIGH"
    pedestrian_count: int
    is_crowded:       bool
    density_score:    Optional[float] = 0.0


class PedestrianRiskEventIn(BaseModel):
    event_id:         Optional[str] = None
    event_type:       str = "PEDESTRIAN_RISK"
    location:         Dict[str, float]  # {"lat": float, "lon": float}
    timestamp:        Optional[str] = None
    bus_id:           str
    camera_id:        str
    confidence:       float = Field(..., ge=0.0, le=1.0)
    trajectory:       TrajectoryInfo
    school_zone:      SchoolZoneInfo
    road_boundary:    RoadBoundaryInfo
    zone_density:     ZoneDensityInfo
    crowded_area:     Optional[bool] = False
    frame_b64:        Optional[str] = None


# ── School Zones Seed Data ────────────────────────────────────────────────────

SCHOOLS_SEED = [
    {
        "school_id":       "SCH_DEL_01",
        "name":            "Delhi Public School, R.K. Puram",
        "city":            "Delhi",
        "location":        {"lat": 28.5672, "lon": 77.1720},
        "radius_m":        300.0,
        "active_hours":    [["07:30", "09:30"], ["13:30", "15:45"]],
        "speed_limit_kmh": 25.0,
        "current_density": "HIGH",
        "pedestrian_count": 9,
        "alerts_today":    7,
    },
    {
        "school_id":       "SCH_DEL_02",
        "name":            "Army Public School, Dhaula Kuan",
        "city":            "Delhi",
        "location":        {"lat": 28.5910, "lon": 77.1650},
        "radius_m":        350.0,
        "active_hours":    [["07:15", "09:15"], ["13:15", "15:30"]],
        "speed_limit_kmh": 25.0,
        "current_density": "MEDIUM",
        "pedestrian_count": 5,
        "alerts_today":    4,
    },
    {
        "school_id":       "SCH_DEL_03",
        "name":            "Modern School, Barakhamba Road",
        "city":            "Delhi",
        "location":        {"lat": 28.6295, "lon": 77.2285},
        "radius_m":        250.0,
        "active_hours":    [["07:45", "09:45"], ["13:45", "16:00"]],
        "speed_limit_kmh": 25.0,
        "current_density": "LOW",
        "pedestrian_count": 2,
        "alerts_today":    1,
    },
    {
        "school_id":       "SCH_MUM_01",
        "name":            "Dhirubhai Ambani International School, BKC",
        "city":            "Mumbai",
        "location":        {"lat": 19.0655, "lon": 72.8680},
        "radius_m":        300.0,
        "active_hours":    [["07:30", "09:30"], ["14:00", "16:15"]],
        "speed_limit_kmh": 25.0,
        "current_density": "HIGH",
        "pedestrian_count": 11,
        "alerts_today":    6,
    },
    {
        "school_id":       "SCH_MUM_02",
        "name":            "St. Xavier's High School, Fort",
        "city":            "Mumbai",
        "location":        {"lat": 18.9430, "lon": 72.8315},
        "radius_m":        250.0,
        "active_hours":    [["07:15", "09:30"], ["13:30", "15:45"]],
        "speed_limit_kmh": 25.0,
        "current_density": "MEDIUM",
        "pedestrian_count": 6,
        "alerts_today":    3,
    },
    {
        "school_id":       "SCH_BLR_01",
        "name":            "National Public School, Indiranagar",
        "city":            "Bangalore",
        "location":        {"lat": 12.9780, "lon": 77.6430},
        "radius_m":        250.0,
        "active_hours":    [["07:45", "09:45"], ["14:15", "16:00"]],
        "speed_limit_kmh": 25.0,
        "current_density": "MEDIUM",
        "pedestrian_count": 6,
        "alerts_today":    5,
    },
    {
        "school_id":       "SCH_BLR_02",
        "name":            "Bishop Cotton Boys' School, Residency Road",
        "city":            "Bangalore",
        "location":        {"lat": 12.9690, "lon": 77.6010},
        "radius_m":        300.0,
        "active_hours":    [["07:30", "09:30"], ["13:30", "15:45"]],
        "speed_limit_kmh": 25.0,
        "current_density": "HIGH",
        "pedestrian_count": 12,
        "alerts_today":    8,
    },
]

# ── In-Memory Store & Pre-seeded Events ────────────────────────────────────────

_events: List[Dict[str, Any]] = []
_schools_store: Dict[str, Dict[str, Any]] = {s["school_id"]: dict(s) for s in SCHOOLS_SEED}
_MAX_EVENTS = 5000


def _init_seed_events():
    now_iso = datetime.now(timezone.utc).isoformat()
    # Sample realistic seed events
    seed_data = [
        {
            "school_id": "SCH_DEL_01",
            "name": "Delhi Public School, R.K. Puram",
            "city": "Delhi",
            "lat": 28.5672,
            "lon": 77.1720,
            "dist_m": 42.0,
            "dx": 18.5,
            "dy": 12.0,
            "heading": 33.0,
            "speed": 45.2,
            "dist_px": 24.5,
            "bus": "BUS_DEL_101",
            "count": 9,
            "level": "HIGH",
            "crowded": True,
        },
        {
            "school_id": "SCH_BLR_02",
            "name": "Bishop Cotton Boys' School, Residency Road",
            "city": "Bangalore",
            "lat": 12.9690,
            "lon": 77.6010,
            "dist_m": 65.0,
            "dx": -22.0,
            "dy": 15.0,
            "heading": 145.0,
            "speed": 52.0,
            "dist_px": 18.0,
            "bus": "BUS_BLR_204",
            "count": 12,
            "level": "HIGH",
            "crowded": True,
        },
        {
            "school_id": "SCH_DEL_02",
            "name": "Army Public School, Dhaula Kuan",
            "city": "Delhi",
            "lat": 28.5910,
            "lon": 77.1650,
            "dist_m": 88.0,
            "dx": 14.0,
            "dy": 8.0,
            "heading": 29.0,
            "speed": 34.0,
            "dist_px": 35.0,
            "bus": "BUS_DEL_104",
            "count": 5,
            "level": "MEDIUM",
            "crowded": True,
        },
        {
            "school_id": "SCH_MUM_01",
            "name": "Dhirubhai Ambani International School, BKC",
            "city": "Mumbai",
            "lat": 19.0655,
            "lon": 72.8680,
            "dist_m": 50.0,
            "dx": -16.0,
            "dy": 10.0,
            "heading": 148.0,
            "speed": 40.5,
            "dist_px": 22.0,
            "bus": "BUS_MUM_305",
            "count": 11,
            "level": "HIGH",
            "crowded": True,
        },
    ]

    for item in seed_data:
        _events.append({
            "event_id":         str(uuid.uuid4()),
            "event_type":       "PEDESTRIAN_RISK",
            "location":         {"lat": item["lat"], "lon": item["lon"]},
            "timestamp":        now_iso,
            "bus_id":           item["bus"],
            "camera_id":        "FRONT",
            "confidence":       0.91,
            "trajectory": {
                "speed_px_s":         item["speed"],
                "heading_deg":        item["heading"],
                "moving_toward_road": True,
                "vector":             [item["dx"], item["dy"]],
            },
            "school_zone": {
                "school_id":       item["school_id"],
                "name":            item["name"],
                "distance_m":      item["dist_m"],
                "active_now":      True,
                "speed_limit_kmh": 25.0,
            },
            "road_boundary": {
                "distance_px":      item["dist_px"],
                "is_near_boundary": True,
            },
            "zone_density": {
                "level":            item["level"],
                "pedestrian_count": item["count"],
                "is_crowded":       item["crowded"],
                "density_score":    round(item["count"] / 12.0, 2),
            },
            "crowded_area":     item["crowded"],
            "frame_b64":        None,
            "methodology_note": (
                "Proxy detection: Person + road boundary proximity + trajectory towards road "
                "+ school zone + active hours. No unscientific child age estimation is used."
            ),
        })

_init_seed_events()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/events", status_code=201)
async def ingest_pedestrian_risk_event(event: PedestrianRiskEventIn):
    """
    Ingest a real-time PEDESTRIAN_RISK event from a bus edge camera.
    """
    rec = event.model_dump()
    rec["event_id"] = rec.get("event_id") or str(uuid.uuid4())
    rec["timestamp"] = rec.get("timestamp") or datetime.now(timezone.utc).isoformat()
    rec["event_type"] = "PEDESTRIAN_RISK"
    rec["methodology_note"] = (
        "Proxy detection: Person + road boundary proximity + trajectory towards road "
        "+ school zone + active hours. No unscientific child age estimation is used."
    )

    # Update school zone alert counter
    sch_id = rec.get("school_zone", {}).get("school_id")
    if sch_id and sch_id in _schools_store:
        _schools_store[sch_id]["alerts_today"] = _schools_store[sch_id].get("alerts_today", 0) + 1
        zd = rec.get("zone_density", {})
        if zd.get("level"):
            _schools_store[sch_id]["current_density"] = zd["level"]
        if zd.get("pedestrian_count"):
            _schools_store[sch_id]["pedestrian_count"] = zd["pedestrian_count"]

    _events.append(rec)
    if len(_events) > _MAX_EVENTS:
        _events.pop(0)

    return {"ok": True, "event_id": rec["event_id"]}


@router.get("/events")
async def list_pedestrian_risk_events(
    school_id:  Optional[str] = Query(None),
    bus_id:     Optional[str] = Query(None),
    is_crowded: Optional[bool] = Query(None),
    city:       Optional[str] = Query(None),
    limit:      int           = Query(50, ge=1, le=200),
    offset:     int           = Query(0, ge=0),
):
    """
    Query list of PEDESTRIAN_RISK events.
    """
    results = list(reversed(_events))
    if school_id:
        results = [e for e in results if e.get("school_zone", {}).get("school_id") == school_id]
    if bus_id:
        results = [e for e in results if e.get("bus_id") == bus_id]
    if is_crowded is not None:
        results = [e for e in results if e.get("crowded_area") == is_crowded]
    if city:
        city_lower = city.lower()
        results = [
            e for e in results
            if city_lower in (e.get("school_zone", {}).get("name", "")).lower()
            or city_lower in (e.get("school_zone", {}).get("school_id", "")).lower()
        ]

    total = len(results)
    return {
        "total": total,
        "items": results[offset: offset + limit],
    }


@router.get("/schools")
async def list_school_zones(
    city: Optional[str] = Query(None)
):
    """
    Return all registered school zones with geofence geometry, active bell hours,
    and current pedestrian density.
    """
    schools = list(_schools_store.values())
    if city:
        schools = [s for s in schools if s.get("city", "").lower() == city.lower()]
    return {
        "count": len(schools),
        "schools": schools,
    }


@router.get("/density")
async def get_zone_densities(
    city: Optional[str] = Query(None)
):
    """
    Return zone-level pedestrian crowd densities for school zones and transit gates.
    """
    schools = list(_schools_store.values())
    if city:
        schools = [s for s in schools if s.get("city", "").lower() == city.lower()]

    densities = [
        {
            "school_id":        s["school_id"],
            "name":             s["name"],
            "city":             s["city"],
            "density_level":    s.get("current_density", "LOW"),
            "pedestrian_count": s.get("pedestrian_count", 0),
            "is_crowded":       s.get("current_density") == "HIGH",
            "location":         s["location"],
        }
        for s in schools
    ]
    return {
        "count": len(densities),
        "zones": densities,
    }


@router.get("/stats")
async def pedestrian_safety_stats(
    city: Optional[str] = Query(None)
):
    """
    Returns high-level summary KPIs and hourly distribution of risk alerts.
    """
    schools = list(_schools_store.values())
    if city:
        schools = [s for s in schools if s.get("city", "").lower() == city.lower()]

    total_alerts = sum(s.get("alerts_today", 0) for s in schools)
    crowded_zones = sum(1 for s in schools if s.get("current_density") == "HIGH")

    # Worst/Peak risk school
    peak_school = None
    if schools:
        peak_school = max(schools, key=lambda s: s.get("alerts_today", 0))

    # Diurnal hourly breakdown of alerts (peaks during morning bell 8-9 AM and afternoon 2-3 PM)
    hourly_distribution = [
        {"hour": "07:00", "count": 2},
        {"hour": "08:00", "count": 14},  # Morning drop-off peak
        {"hour": "09:00", "count": 8},
        {"hour": "10:00", "count": 1},
        {"hour": "11:00", "count": 0},
        {"hour": "12:00", "count": 2},
        {"hour": "13:00", "count": 3},
        {"hour": "14:00", "count": 16},  # Afternoon dismissal peak
        {"hour": "15:00", "count": 9},
        {"hour": "16:00", "count": 3},
        {"hour": "17:00", "count": 1},
    ]

    return {
        "total_risk_alerts_today": total_alerts,
        "monitored_school_zones":  len(schools),
        "active_bell_zones":       len([s for s in schools if s.get("current_density") in ("MEDIUM", "HIGH")]),
        "crowded_zones_count":     crowded_zones,
        "peak_risk_school":        peak_school,
        "hourly_distribution":     hourly_distribution,
        "methodology": {
            "disclaimer": (
                "AI strictly refrains from child age classification. Risk is computed via "
                "road boundary proximity, trajectory vectors towards road, school geofences, "
                "and active operating bell schedules."
            )
        },
    }
