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
from ..models.ai_scan_entities import RoadDetection, MaintenanceTicket, PersistentHazard
from ..services.demo_seeder_service import get_demo_seeder_service
from ..services.video_analyzer_service import _ACTIVE_JOBS

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
            lat_val = h.get("lat")
            lon_val = h.get("lon")
            addr_val = h.get("address", "Monitored Corridor")
            events.append({
                "event_id": h.get("event_id"),
                "event_type": ev_type,
                "layer": layer_map.get(ev_type, "potholes"),
                "lat": lat_val,
                "lon": lon_val,
                "gps": {
                    "lat": lat_val,
                    "lon": lon_val,
                    "road_segment": addr_val,
                    "address": addr_val,
                    "bearing_deg": 0,
                },
                "bus_id": h.get("bus_id", "BUS_001"),
                "camera_id": "FRONT",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": h.get("confidence", 0.92),
                "severity": h.get("severity", "HIGH"),
                "status": h.get("status", "ACTIVE"),
                "district": h.get("district", "Metropolitan"),
                "road_segment": addr_val,
                "address": addr_val,
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
    category: Optional[str] = Query(None, description="Category filter (ROAD_DAMAGE, WATERLOGGING, TRAFFIC, PEDESTRIAN_RISK, INCIDENT, ANPR)"),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    bus_id: Optional[str] = Query(None),
    route_id: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    db: Session = Depends(get_session),
):
    """
    Returns RFC 7946 GeoJSON FeatureCollection for all 12 command center map layers.
    Combines live database records with default spatial clusters.
    """
    # 1. Build maintenance ticket lookup dictionary
    ticket_by_event_id: Dict[str, Any] = {}
    try:
        db_tickets = db.exec(select(MaintenanceTicket)).all()
        for t in db_tickets:
            if t.detection_id:
                ticket_by_event_id[str(t.detection_id)] = t.to_dict()
            ticket_by_event_id[t.ticket_code] = t.to_dict()
    except Exception as t_err:
        logger.debug(f"MaintenanceTicket query note: {t_err}")

    for mt in MAINTENANCE_TICKETS:
        if mt.get("event_id"):
            ticket_by_event_id[mt["event_id"]] = mt

    # 1b. Build persistent hazard lookup dictionary
    hazard_by_id: Dict[str, Any] = {}
    try:
        db_hazards = db.exec(select(PersistentHazard)).all()
        for h in db_hazards:
            h_data = h.to_dict()
            hazard_by_id[str(h.id)] = h_data
            if h.hazard_code:
                hazard_by_id[h.hazard_code] = h_data
    except Exception as h_err:
        logger.debug(f"PersistentHazard query note: {h_err}")

    features = []
    seen_event_ids = set()

    # Helper: Convert detection record or RoadDetection model to GeoJSON Feature
    def _map_detection_to_feature(det_dict: Dict[str, Any]) -> Dict[str, Any]:
        raw_type = str(det_dict.get("type") or det_dict.get("event_type") or "POTHOLE").upper()
        
        # Direct vs. Derived categorization
        is_derived = False
        condition_type = "DIRECT"
        condition_label = "Direct AI Computer Vision Detection"

        if "POTHOLE" in raw_type:
            layer_name = "potholes"
            cat_name = "ROAD_DAMAGE"
        elif any(k in raw_type for k in ["CRACK", "DAMAGE", "DEBRIS"]):
            layer_name = "road_damage"
            cat_name = "ROAD_DAMAGE"
        elif "WATERLOG" in raw_type:
            layer_name = "waterlogging"
            cat_name = "WATERLOGGING"
        elif "ZEBRA" in raw_type:
            layer_name = "zebra_crossing_issues"
            cat_name = "ROAD_DAMAGE"
        elif "SIGN" in raw_type:
            layer_name = "missing_signs"
            cat_name = "ROAD_DAMAGE"
            is_derived = True
            condition_type = "POTENTIAL"
            condition_label = "Potential Sign Obstruction / Displacement"
        elif "DIVIDER" in raw_type:
            layer_name = "missing_dividers"
            cat_name = "ROAD_DAMAGE"
            is_derived = True
            condition_type = "POTENTIAL"
            condition_label = "Potential Divider Breach / Discontinuity"
        elif any(k in raw_type for k in ["BUS", "CAR", "TRUCK", "MOTORCYCLE", "VEHICLE", "CONGESTION"]):
            layer_name = "traffic_congestion"
            cat_name = "TRAFFIC"
            is_derived = True
            condition_type = "POTENTIAL"
            condition_label = "Potential Vehicle Density Cluster"
        elif "PEDESTRIAN" in raw_type:
            layer_name = "pedestrian_risk"
            cat_name = "PEDESTRIAN_RISK"
            is_derived = True
            condition_type = "POTENTIAL"
            condition_label = "Potential Pedestrian in Transit Corridor"
        elif "INCIDENT" in raw_type:
            layer_name = "incidents"
            cat_name = "INCIDENT"
            is_derived = True
            condition_type = "POTENTIAL"
            condition_label = "Potential Transit Corridor Incident"
        else:
            layer_name = "road_damage"
            cat_name = "ROAD_DAMAGE"

        det_id = str(det_dict.get("id") or det_dict.get("event_id") or uuid.uuid4().hex[:8].upper())
        override = ACTION_OVERRIDES.get(det_id, {})
        ticket_info = ticket_by_event_id.get(det_id, {}) or override

        ticket_id = override.get("ticket_id") or ticket_info.get("ticket_id") or det_dict.get("ticket_id")
        ticket_status = override.get("status") or ticket_info.get("status") or ("ASSIGNED" if ticket_id else "NONE")

        lat = float(det_dict.get("latitude") or det_dict.get("lat") or 12.9348)
        lon = float(det_dict.get("longitude") or det_dict.get("lon") or 77.6101)

        evidence_original = det_dict.get("original_evidence_path") or det_dict.get("evidence_path")
        evidence_annotated = det_dict.get("annotated_evidence_path") or det_dict.get("evidence_path") or det_dict.get("evidence_image_b64")
        evidence_thumb = det_dict.get("thumbnail_path")

        props = {
            "event_id": det_id,
            "id": det_id,
            "event_type": raw_type,
            "layer": layer_name,
            "category": cat_name,
            "is_derived": is_derived,
            "condition_type": condition_type,
            "condition_label": condition_label,
            "confidence": round(float(det_dict.get("confidence") or 0.85), 3),
            "severity": str(det_dict.get("severity") or "MEDIUM").upper(),
            "status": override.get("status", det_dict.get("status", "CONFIRMED")),
            "bus_id": str(det_dict.get("bus_id") or "BUS-027"),
            "camera_id": str(det_dict.get("camera_id") or "FRONT_CAMERA"),
            "source_video": str(det_dict.get("source_video") or det_dict.get("video_file_name") or "Live Camera / Stream"),
            "frame_number": int(det_dict.get("frame_number") or 0),
            "track_id": int(det_dict.get("track_id") or 0),
            "timestamp": str(det_dict.get("timestamp") or datetime.now(timezone.utc).isoformat()),
            "lat": lat,
            "lon": lon,
            "gps": {
                "lat": lat,
                "lon": lon,
                "road_segment": str(det_dict.get("road_segment") or f"Transit Corridor ({lat:.4f}, {lon:.4f})"),
                "address": str(det_dict.get("address") or f"Monitored Transit Route ({lat:.4f}, {lon:.4f})"),
                "bearing_deg": float(det_dict.get("bearing_deg") or 0),
            },
            "evidence_image_b64": evidence_annotated or evidence_original,
            "evidence_path": evidence_original,
            "original_evidence_path": evidence_original,
            "annotated_evidence_path": evidence_annotated,
            "thumbnail_path": evidence_thumb,
            "ticket_id": ticket_id,
            "maintenance_ticket_status": ticket_status,
            "persistent_hazard_id": det_dict.get("persistent_hazard_id"),
            "independent_buses_count": int((hazard_by_id.get(str(det_dict.get("persistent_hazard_id") or "")) or {}).get("independent_buses_count") or det_dict.get("independent_buses_count") or 1),
            "contributing_buses": (hazard_by_id.get(str(det_dict.get("persistent_hazard_id") or "")) or {}).get("contributing_buses") or det_dict.get("contributing_buses") or det_dict.get("bus_id") or "BUS-027",
            "persistence_badge": (hazard_by_id.get(str(det_dict.get("persistent_hazard_id") or "")) or {}).get("persistence_status") or det_dict.get("persistence_badge") or (f"CONFIRMED BY {int(det_dict.get('independent_buses_count') or 1)} BUSES" if int(det_dict.get("independent_buses_count") or 1) >= 2 else "SINGLE OBSERVATION"),
            "last_detected_at": str((hazard_by_id.get(str(det_dict.get("persistent_hazard_id") or "")) or {}).get("last_detected_at") or det_dict.get("last_detected_at") or det_dict.get("timestamp") or datetime.now(timezone.utc).isoformat()),
            "ai_confidence": round(float(det_dict.get("confidence") or 0.85), 3),
            "observation_count": int((hazard_by_id.get(str(det_dict.get("persistent_hazard_id") or "")) or {}).get("total_observations") or det_dict.get("observation_count") or 1),
            "details": det_dict.get("details") or {},
        }
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
            "properties": props,
        }

    # 2. Fetch RoadDetection records from database
    try:
        det_query = select(RoadDetection)
        if severity:
            det_query = det_query.where(RoadDetection.severity == severity.upper())
        if status_filter:
            det_query = det_query.where(RoadDetection.status == status_filter.upper())
        if bus_id:
            det_query = det_query.where(RoadDetection.bus_id == bus_id)

        db_detections = db.exec(det_query).all()
        for rd in db_detections:
            det_dict = rd.to_dict()
            feat = _map_detection_to_feature(det_dict)
            features.append(feat)
            seen_event_ids.add(feat["properties"]["event_id"])
    except Exception as det_err:
        logger.debug(f"RoadDetection query note: {det_err}")

    # 3. Include active detections from in-flight / recent scan jobs
    for jid, job in _ACTIVE_JOBS.items():
        for det in job.get("detections", []):
            d_id = det.get("id")
            if d_id and d_id not in seen_event_ids:
                det_copy = dict(det)
                det_copy["source_video"] = job.get("video_file_name", "dashcam_video.mp4")
                feat = _map_detection_to_feature(det_copy)
                features.append(feat)
                seen_event_ids.add(d_id)

    # 4. Fetch persistent IngestedEvent database records
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
    for r in db_events:
        if r.event_id not in seen_event_ids:
            feat = r.to_geojson_feature()
            feat["properties"]["layer"] = _map_detection_to_feature({"type": r.event_type})["properties"]["layer"]
            feat["properties"]["condition_type"] = "DIRECT"
            if r.event_id in ACTION_OVERRIDES:
                feat["properties"].update(ACTION_OVERRIDES[r.event_id])
            features.append(feat)
            seen_event_ids.add(r.event_id)

    # 5. Add sample GIS seeds if dataset has few records
    for s in DEFAULT_GIS_EVENTS:
        if s["event_id"] not in seen_event_ids:
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
            seen_event_ids.add(s["event_id"])

    # 6. Filter features based on query parameters
    active_layers = set(layer.split(",")) if layer else None

    filtered_features = []
    layer_counts: Dict[str, int] = {}

    for f in features:
        p = f["properties"]
        l_name = p.get("layer", "road_damage")
        layer_counts[l_name] = layer_counts.get(l_name, 0) + 1

        if active_layers and l_name not in active_layers:
            continue
        if category and category.upper() != "ALL":
            cat = category.upper()
            ev_t = p.get("event_type", "").upper()
            if cat == "ROAD_DAMAGE" and not any(k in ev_t for k in ["POTHOLE", "DAMAGE", "CRACK", "DEBRIS", "SIGN", "DIVIDER", "ZEBRA"]):
                continue
            elif cat == "WATERLOGGING" and "WATERLOG" not in ev_t:
                continue
            elif cat == "TRAFFIC" and not any(k in ev_t for k in ["CONGESTION", "BUS", "CAR", "TRUCK", "MOTORCYCLE"]):
                continue
            elif cat == "PEDESTRIAN_RISK" and "PEDESTRIAN" not in ev_t:
                continue
            elif cat == "INCIDENT" and "INCIDENT" not in ev_t:
                continue
            elif cat == "ANPR" and not any(k in ev_t for k in ["ANPR", "PLATE", "INTRUSION"]):
                continue
        if event_type and p.get("event_type", "").upper() != event_type.upper():
            continue
        if severity and p.get("severity", "").upper() != severity.upper():
            continue
        if status_filter and p.get("status", "").upper() != status_filter.upper():
            continue
        if bus_id and p.get("bus_id") != bus_id:
            continue
        if route_id and p.get("route_id") != route_id:
            continue
        if district and p.get("district", "").upper() != district.upper():
            continue
        if date and not p.get("timestamp", "").startswith(date):
            continue
        if min_confidence is not None and (p.get("confidence") or 1.0) < min_confidence:
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
            "layer_counts": layer_counts,
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
@router.post("/events/{event_id}/action", summary="Perform officer action on event (POST alias)")
async def perform_event_action(
    event_id: str,
    body: EventActionRequest,
    db: Session = Depends(get_session),
):
    """
    Executes Confirm, Dismiss, Escalate, or Maintenance Ticket generation for an event.
    """
    action_upper = body.action.upper()
    if action_upper == "CREATE_TICKET":
        action_upper = "CREATE_MAINTENANCE_TICKET"

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

    # Check if event_id matches a RoadDetection record
    try:
        clean_uuid = None
        if event_id.startswith("DET-"):
            clean_uuid = uuid.UUID(hex=event_id.replace("DET-", "").zfill(32))
        else:
            try:
                clean_uuid = uuid.UUID(event_id)
            except Exception:
                pass

        if clean_uuid:
            det_stmt = select(RoadDetection).where(RoadDetection.id == clean_uuid)
            db_det = db.exec(det_stmt).first()
            if db_det:
                db_det.status = new_status
                db.add(db_det)
                db.commit()

        if ticket_id:
            db_t = MaintenanceTicket(
                ticket_code=ticket_id,
                detection_id=clean_uuid,
                hazard_type=db_evt.event_type if db_evt else "ROAD_HAZARD",
                title=f"Repair Work Order for {event_id}",
                location_description=body.notes or "Identified via NovaFlow Edge Vision Grid",
                latitude=float(getattr(db_evt, "latitude", 12.9348) if db_evt else 12.9348),
                longitude=float(getattr(db_evt, "longitude", 77.6101) if db_evt else 77.6101),
                severity=body.priority or "HIGH",
                priority=body.priority or "P1",
                agency=body.department or "PWD Road Infrastructure Maintenance",
                status="ASSIGNED",
                evidence=getattr(db_evt, "evidence_url", None) if db_evt else None,
                source_bus=getattr(db_evt, "bus_id", "OFFICER_DISPATCH") if db_evt else "OFFICER_DISPATCH",
                observation_count=1,
                field_notes=body.notes,
            )
            db.add(db_t)
            db.commit()
    except Exception as db_sync_err:
        logger.debug(f"Action DB sync note: {db_sync_err}")

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
