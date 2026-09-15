"""
GIS Command Center API Router (Phase 17)
========================================
Serves GeoJSON FeatureCollections, spatial layers, route vectors, live bus telemetry,
and event operational action workflows for the full-screen GIS Command Center.

Supported Map Layers (12):
  1. bus_locations
  2. bus_routes
  3. potholes
  4. road_damage
  5. waterlogging
  6. missing_signs
  7. missing_dividers
  8. zebra_crossing_issues
  9. traffic_congestion
  10. incidents
  11. pedestrian_risk
  12. maintenance_tickets
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session, col, desc, select

from ..database.session import engine, get_session
from ..models.ingested_event import IngestedEvent
from ..services.demo_seeder_service import get_demo_seeder_service

logger = logging.getLogger("routers.gis")
router = APIRouter()

# ── Action Request Schema ────────────────────────────────────────────────────

class EventActionRequest(BaseModel):
    action: str  # CONFIRM, DISMISS, ESCALATE, CREATE_MAINTENANCE_TICKET
    officer_id: Optional[str] = "OFFICER_007"
    notes: Optional[str] = None
    priority: Optional[str] = "HIGH"
    department: Optional[str] = "Road Works & Maintenance"


# ── Sample Routes & Buses GeoJSON ────────────────────────────────────────────

SAMPLE_BUS_ROUTES = [
    {
        "route_id": "ROUTE_1",
        "name": "Route 1 — Connaught Place Circular",
        "color": "#6366f1",
        "coordinates": [
            [77.2185, 28.6328],
            [77.2215, 28.6340],
            [77.2250, 28.6320],
            [77.2270, 28.6290],
            [77.2230, 28.6260],
            [77.2170, 28.6280],
            [77.2185, 28.6328],
        ],
    },
    {
        "route_id": "ROUTE_2",
        "name": "Route 2 — MG Road Corridor",
        "color": "#10b981",
        "coordinates": [
            [77.5946, 12.9716],
            [77.5980, 12.9725],
            [77.6020, 12.9738],
            [77.6070, 12.9755],
            [77.6120, 12.9770],
            [77.6180, 12.9790],
        ],
    },
    {
        "route_id": "ROUTE_3",
        "name": "Route 3 — Marine Drive Arterial",
        "color": "#f59e0b",
        "coordinates": [
            [72.8220, 18.9430],
            [72.8235, 18.9480],
            [72.8248, 18.9540],
            [72.8260, 18.9600],
            [72.8275, 18.9660],
        ],
    },
]

LIVE_BUSES = [
    {
        "bus_id": "BUS_001",
        "route_id": "ROUTE_1",
        "name": "Bus 101 (Electric Low-Floor)",
        "lat": 28.6315,
        "lon": 77.2205,
        "bearing_deg": 65.0,
        "speed_kmh": 32.5,
        "status": "IN_SERVICE",
        "passenger_load_pct": 68,
        "cameras_active": 4,
    },
    {
        "bus_id": "BUS_002",
        "route_id": "ROUTE_2",
        "name": "Bus 204 (CNG Transit)",
        "lat": 12.9730,
        "lon": 77.6000,
        "bearing_deg": 88.0,
        "speed_kmh": 28.0,
        "status": "IN_SERVICE",
        "passenger_load_pct": 84,
        "cameras_active": 4,
    },
    {
        "bus_id": "BUS_003",
        "route_id": "ROUTE_3",
        "name": "Bus 308 (Double Decker)",
        "lat": 18.9510,
        "lon": 72.8240,
        "bearing_deg": 12.0,
        "speed_kmh": 41.0,
        "status": "IN_SERVICE",
        "passenger_load_pct": 52,
        "cameras_active": 4,
    },
]

# Load nationwide GIS events dynamically from the seeder service
def _build_default_gis_events() -> List[Dict[str, Any]]:
    """Generates DEFAULT_GIS_EVENTS from the nationwide dataset."""
    layer_map = {
        "POTHOLE": "potholes",
        "DAMAGED_ROAD": "road_damage",
        "WATERLOGGING": "waterlogging",
        "CONGESTION_EVENT": "traffic_congestion",
        "PEDESTRIAN_RISK": "pedestrian_risk",
        "MISSING_TRAFFIC_SIGN": "missing_signs",
        "POSSIBLE_INCIDENT": "incidents",
    }
    try:
        seeder = get_demo_seeder_service()
        events = []
        for h in seeder.hazards:
            ev_type = h.get("event_type", "POTHOLE")
            events.append({
                "event_id": h.get("event_id"),
                "event_type": ev_type,
                "layer": layer_map.get(ev_type, "potholes"),
                "lat": h.get("lat"),
                "lon": h.get("lon"),
                "bus_id": h.get("bus_id", "BUS_001"),
                "camera_id": "FRONT",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": h.get("confidence", 0.92),
                "severity": h.get("severity", "HIGH"),
                "status": h.get("status", "ACTIVE"),
                "district": h.get("district", "Metropolitan"),
                "road_segment": h.get("address", "Monitored Corridor"),
                "address": h.get("address", "Monitored Corridor"),
                "state_code": h.get("state_code", "IN"),
                "state_name": h.get("state_name", "India"),
                "details": {},
            })
        return events
    except Exception:
        return []

DEFAULT_GIS_EVENTS: List[Dict[str, Any]] = _build_default_gis_events()

# Track actions and generated tickets in memory
ACTION_OVERRIDES: Dict[str, Dict[str, Any]] = {}
MAINTENANCE_TICKETS: List[Dict[str, Any]] = []


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/features", summary="Retrieve GeoJSON FeatureCollection with all 12 map layers")
async def get_gis_features(
    layer: Optional[str] = Query(None, description="Comma-separated layer filter"),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    bus_id: Optional[str] = Query(None),
    route_id: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    db: Session = Depends(get_session),
):
    """
    Returns RFC 7946 GeoJSON FeatureCollection for all 12 command center map layers.
    Combines live database records with default spatial clusters.
    """
    # 1. Fetch persistent database records
    db_query = select(IngestedEvent)
    if event_type:
        db_query = db_query.where(IngestedEvent.event_type == event_type.upper())
    if severity:
        db_query = db_query.where(IngestedEvent.severity == severity.upper())
    if status_filter:
        db_query = db_query.where(IngestedEvent.status == status_filter.upper())
    if bus_id:
        db_query = db_query.where(IngestedEvent.bus_id == bus_id)
    if district:
        db_query = db_query.where(IngestedEvent.district == district)

    db_events = db.exec(db_query).all()
    features = []

    # Map layer classification helper
    def _get_layer_name(ev_type: str) -> str:
        t = ev_type.upper()
        if "POTHOLE" in t: return "potholes"
        if "DAMAGE" in t: return "road_damage"
        if "WATERLOG" in t: return "waterlogging"
        if "SIGN" in t: return "missing_signs"
        if "DIVIDER" in t: return "missing_dividers"
        if "ZEBRA" in t: return "zebra_crossing_issues"
        if "CONGESTION" in t: return "traffic_congestion"
        if "INCIDENT" in t: return "incidents"
        if "PEDESTRIAN" in t: return "pedestrian_risk"
        if "TICKET" in t: return "maintenance_tickets"
        return "potholes"

    # Add DB features
    for r in db_events:
        feat = r.to_geojson_feature()
        feat["properties"]["layer"] = _get_layer_name(r.event_type)
        # Apply action overrides if any
        if r.event_id in ACTION_OVERRIDES:
            feat["properties"].update(ACTION_OVERRIDES[r.event_id])
        features.append(feat)

    # Add sample GIS seeds if database has few records
    for s in DEFAULT_GIS_EVENTS:
        if s["event_id"] not in [f["properties"]["event_id"] for f in features]:
            props = dict(s)
            if s["event_id"] in ACTION_OVERRIDES:
                props.update(ACTION_OVERRIDES[s["event_id"]])

            feat = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [s["lon"], s["lat"]],
                },
                "properties": props,
            }
            features.append(feat)

    # 2. Filter features based on query parameters
    active_layers = set(layer.split(",")) if layer else None

    filtered_features = []
    for f in features:
        p = f["properties"]
        if active_layers and p.get("layer") not in active_layers:
            continue
        if event_type and p.get("event_type", "").upper() != event_type.upper():
            continue
        if severity and p.get("severity", "").upper() != severity.upper():
            continue
        if status_filter and p.get("status", "").upper() != status_filter.upper():
            continue
        if bus_id and p.get("bus_id") != bus_id:
            continue
        if district and p.get("district", "").upper() != district.upper():
            continue
        if date and not p.get("timestamp", "").startswith(date):
            continue
        filtered_features.append(f)

    return {
        "type": "FeatureCollection",
        "features": filtered_features,
        "metadata": {
            "total_features": len(filtered_features),
            "layers_available": [
                "bus_locations", "bus_routes", "potholes", "road_damage",
                "waterlogging", "missing_signs", "missing_dividers",
                "zebra_crossing_issues", "traffic_congestion", "incidents",
                "pedestrian_risk", "maintenance_tickets"
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


@router.get("/buses", summary="Retrieve live bus telemetry for GIS layer")
async def get_gis_buses():
    """Returns active bus coordinates, headings, routes, and passenger load."""
    seeder = get_demo_seeder_service()
    buses_list = []
    for b in seeder.get_buses():
        buses_list.append({
            "bus_id": b.get("bus_id"),
            "route_id": b.get("route_id"),
            "name": b.get("name"),
            "lat": b.get("lat"),
            "lon": b.get("lon"),
            "bearing_deg": b.get("bearing_deg"),
            "speed_kmh": b.get("speed_kmh"),
            "status": b.get("status"),
            "passenger_occupancy_pct": b.get("passenger_occupancy_pct")
        })
    return {"buses": buses_list}


@router.get("/routes", summary="Retrieve bus route polylines for GIS layer")
async def get_gis_routes():
    """Returns GeoJSON FeatureCollection representing transit routes."""
    seeder = get_demo_seeder_service()
    routes_data = seeder.get_routes().get("routes", [])
    features = []
    for r in routes_data:
        coords = [[wp[1], wp[0]] for wp in r.get("waypoints", [])]
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords,
            },
            "properties": {
                "route_id": r.get("route_id"),
                "name": r.get("name"),
                "color": r.get("color"),
                "layer": "bus_routes",
            },
        })
    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.patch("/events/{event_id}/action", summary="Perform officer action on event")
async def perform_event_action(
    event_id: str,
    body: EventActionRequest,
    db: Session = Depends(get_session),
):
    """
    Executes Confirm, Dismiss, Escalate, or Maintenance Ticket generation for an event.
    """
    action_upper = body.action.upper()
    valid_actions = {"CONFIRM", "DISMISS", "ESCALATE", "CREATE_MAINTENANCE_TICKET"}
    if action_upper not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {body.action}. Must be one of {valid_actions}",
        )

    # Determine new status
    if action_upper == "CONFIRM":
        new_status = "CONFIRMED"
        ticket_id = None
    elif action_upper == "DISMISS":
        new_status = "DISMISSED"
        ticket_id = None
    elif action_upper == "ESCALATE":
        new_status = "ESCALATED"
        ticket_id = None
    else:  # CREATE_MAINTENANCE_TICKET
        new_status = "TICKET_CREATED"
        ticket_id = f"TICK-{datetime.now().year}-{uuid.uuid4().hex[:4].upper()}"
        ticket_record = {
            "ticket_id": ticket_id,
            "event_id": event_id,
            "priority": body.priority,
            "department": body.department,
            "notes": body.notes,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "ASSIGNED",
        }
        MAINTENANCE_TICKETS.append(ticket_record)

    override = {
        "status": new_status,
        "action_taken": action_upper,
        "action_timestamp": datetime.now(timezone.utc).isoformat(),
        "officer_notes": body.notes,
    }
    if ticket_id:
        override["ticket_id"] = ticket_id

    ACTION_OVERRIDES[event_id] = override

    # Also update DB if record exists there
    stmt = select(IngestedEvent).where(IngestedEvent.event_id == event_id)
    db_evt = db.exec(stmt).first()
    if db_evt:
        db_evt.status = new_status
        db.add(db_evt)
        db.commit()
        db.refresh(db_evt)

    logger.info(f"Officer action executed on event {event_id}: {action_upper} -> {new_status}")

    return {
        "ok": True,
        "event_id": event_id,
        "action": action_upper,
        "new_status": new_status,
        "ticket_id": ticket_id,
        "updated_at": override["action_timestamp"],
    }


@router.get("/maintenance-tickets", summary="List generated maintenance work orders")
async def list_maintenance_tickets():
    return {
        "count": len(MAINTENANCE_TICKETS),
        "tickets": MAINTENANCE_TICKETS,
    }
