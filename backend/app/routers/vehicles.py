"""
Vehicle Detection API Router – FastAPI
=======================================
Endpoints for vehicle detection snapshots and crossing events.

Routes
------
  POST /api/v1/vehicles/snapshot   – ingest a vehicle_snapshot event
  POST /api/v1/vehicles/crossing   – ingest a vehicle_crossing event
  GET  /api/v1/vehicles/snapshots  – list recent snapshots (paginated)
  GET  /api/v1/vehicles/crossings  – list crossing events (filterable)
  GET  /api/v1/vehicles/stats      – aggregated traffic statistics
  GET  /api/v1/vehicles/density    – current density by region
"""

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()

# ── In-memory stores ──────────────────────────────────────────────────────────

_snapshots: List[Dict[str, Any]] = []
_crossings: List[Dict[str, Any]] = []
_MAX_RECORDS = 5000


# ── Schemas ───────────────────────────────────────────────────────────────────

class VehicleSnapshotIn(BaseModel):
    event_id:       Optional[str]  = None
    event_type:     str            = "vehicle_snapshot"
    camera_id:      str
    bus_id:         str
    route_id:       Optional[str]  = None
    timestamp:      Optional[str]  = None
    gps:            Dict[str, Any]
    active_tracks:  int            = 0
    counts:         Dict[str, int] = {}
    avg_speed_kmh:  Dict[str, float] = {}
    density:        List[Dict]     = []
    lines:          List[Dict]     = []


class VehicleCrossingIn(BaseModel):
    event_id:   Optional[str]  = None
    event_type: str            = "vehicle_crossing"
    camera_id:  str
    bus_id:     str
    route_id:   Optional[str]  = None
    timestamp:  Optional[str]  = None
    gps:        Dict[str, Any]
    track_id:   int
    label:      str
    group:      str
    line:       str
    direction:  str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/snapshot", status_code=201)
async def ingest_snapshot(body: VehicleSnapshotIn):
    record = body.model_dump()
    record["event_id"]   = record.get("event_id") or str(uuid.uuid4())
    record["received_at"] = datetime.now(timezone.utc).isoformat()
    _snapshots.append(record)
    if len(_snapshots) > _MAX_RECORDS:
        _snapshots.pop(0)
    return {"ok": True, "event_id": record["event_id"]}


@router.post("/crossing", status_code=201)
async def ingest_crossing(body: VehicleCrossingIn):
    record = body.model_dump()
    record["event_id"]    = record.get("event_id") or str(uuid.uuid4())
    record["received_at"] = datetime.now(timezone.utc).isoformat()
    _crossings.append(record)
    if len(_crossings) > _MAX_RECORDS:
        _crossings.pop(0)
    return {"ok": True, "event_id": record["event_id"]}


@router.get("/snapshots")
async def list_snapshots(
    bus_id:   Optional[str] = Query(None),
    camera_id: Optional[str] = Query(None),
    limit:    int           = Query(50, le=200),
    offset:   int           = Query(0, ge=0),
):
    results = _snapshots
    if bus_id:
        results = [r for r in results if r.get("bus_id") == bus_id]
    if camera_id:
        results = [r for r in results if r.get("camera_id") == camera_id]
    total = len(results)
    return {"total": total, "items": results[offset: offset + limit]}


@router.get("/crossings")
async def list_crossings(
    bus_id:   Optional[str] = Query(None),
    line:     Optional[str] = Query(None),
    group:    Optional[str] = Query(None),
    limit:    int           = Query(100, le=500),
    offset:   int           = Query(0, ge=0),
):
    results = _crossings
    if bus_id:
        results = [r for r in results if r.get("bus_id") == bus_id]
    if line:
        results = [r for r in results if r.get("line") == line]
    if group:
        results = [r for r in results if r.get("group") == group]
    total = len(results)
    return {"total": total, "items": results[offset: offset + limit]}


@router.get("/stats")
async def aggregated_stats():
    """Aggregate all crossing events into per-class totals and speed averages."""
    totals: Dict[str, int] = defaultdict(int)
    speeds: Dict[str, List[float]] = defaultdict(list)

    for snap in _snapshots:
        for cls, cnt in snap.get("counts", {}).items():
            totals[cls] += cnt
        for cls, spd in snap.get("avg_speed_kmh", {}).items():
            if spd > 0:
                speeds[cls].append(spd)

    avg_speeds = {cls: round(sum(v)/len(v), 1) for cls, v in speeds.items() if v}

    latest_density = []
    if _snapshots:
        latest_density = _snapshots[-1].get("density", [])

    return {
        "total_snapshots":  len(_snapshots),
        "total_crossings":  len(_crossings),
        "cumulative_counts": dict(totals),
        "avg_speed_kmh":     avg_speeds,
        "latest_density":    latest_density,
    }


@router.get("/density")
async def current_density():
    """Return density from the most recent snapshot."""
    if not _snapshots:
        return {"density": [], "timestamp": None}
    last = _snapshots[-1]
    return {"density": last.get("density", []), "timestamp": last.get("timestamp")}
