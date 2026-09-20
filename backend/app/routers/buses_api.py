"""
Buses & Edge Nodes REST API Router (Phase 8)
============================================
Provides telemetry ingestion, active edge node querying, and detection association
for the connected public transit fleet.

Treats each transit bus as a mobile edge sensing node streaming kinematics,
camera health, and model inference state.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from ..database.session import get_session
from ..models.ai_scan_entities import RoadDetection
from ..models.entities import BusModel, GpsTelemetry
from ..services.demo_seeder_service import get_demo_seeder_service

logger = logging.getLogger("novaflow.buses_api")

router = APIRouter()

# Default fleet template to guarantee multi-bus architectural support
DEFAULT_FLEET = [
    {
        "bus_id": "BUS-001",
        "route_id": "R-01",
        "name": "Tata Starbus EV #1",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "speed": 38.5,
        "heading": 85.0,
        "camera_status": "ACTIVE",
        "AI_status": "ONLINE",
        "connection_status": "CONNECTED",
    },
    {
        "bus_id": "BUS-002",
        "route_id": "R-02",
        "name": "Tata Starbus EV #2",
        "latitude": 28.6250,
        "longitude": 77.2180,
        "speed": 29.0,
        "heading": 170.0,
        "camera_status": "ACTIVE",
        "AI_status": "STANDBY",
        "connection_status": "CONNECTED",
    },
    {
        "bus_id": "BUS-027",
        "route_id": "ROUTE_17",
        "name": "Ashok Leyland Electric #27",
        "latitude": 12.9352,
        "longitude": 77.6245,
        "speed": 42.0,
        "heading": 220.0,
        "camera_status": "STREAMING",
        "AI_status": "INFERENCING",
        "connection_status": "CONNECTED",
    },
    {
        "bus_id": "BUS-102",
        "route_id": "ROUTE_17",
        "name": "BYD K9 Electric #102",
        "latitude": 12.9280,
        "longitude": 77.6180,
        "speed": 34.0,
        "heading": 45.0,
        "camera_status": "ACTIVE",
        "AI_status": "INFERENCING",
        "connection_status": "CONNECTED",
    },
    {
        "bus_id": "BUS-117",
        "route_id": "R-03",
        "name": "JBM Ecolife #117",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "speed": 22.5,
        "heading": 310.0,
        "camera_status": "STREAMING",
        "AI_status": "ONLINE",
        "connection_status": "CONNECTED",
    },
    {
        "bus_id": "BUS-143",
        "route_id": "R-04",
        "name": "Olectra Greentech #143",
        "latitude": 19.0850,
        "longitude": 72.8890,
        "speed": 0.0,
        "heading": 0.0,
        "camera_status": "DEGRADED",
        "AI_status": "STANDBY",
        "connection_status": "DEGRADED",
    },
]


def ensure_default_buses_seeded(db: Session):
    """Ensures multi-bus fleet exists in the database."""
    try:
        count = db.exec(select(BusModel)).all()
        if not count:
            for item in DEFAULT_FLEET:
                b = BusModel(
                    bus_id=item["bus_id"],
                    route_id=item["route_id"],
                    name=item["name"],
                    current_lat=item["latitude"],
                    current_lon=item["longitude"],
                    latitude=item["latitude"],
                    longitude=item["longitude"],
                    speed_kmh=item["speed"],
                    speed=item["speed"],
                    bearing_deg=item["heading"],
                    heading=item["heading"],
                    camera_status=item["camera_status"],
                    AI_status=item["AI_status"],
                    connection_status=item["connection_status"],
                )
                db.add(b)
            db.commit()
    except Exception as e:
        logger.debug(f"Seeding fleet note: {e}")


class BusTelemetryPayload(BaseModel):
    """Incoming kinematic and edge intelligence heartbeat from a connected transit bus."""
    bus_id: str = Field(..., description="Unique vehicle edge ID (e.g. BUS-102)")
    route_id: Optional[str] = Field("R-01", description="Assigned transit corridor route")
    latitude: float = Field(..., description="Instantaneous GPS latitude")
    longitude: float = Field(..., description="Instantaneous GPS longitude")
    speed: float = Field(0.0, description="Instantaneous vehicle speed in km/h")
    heading: float = Field(0.0, description="Compass bearing (0-360 degrees)")
    camera_status: Optional[str] = Field("ACTIVE", description="ACTIVE | STREAMING | DEGRADED | OFFLINE")
    AI_status: Optional[str] = Field("ONLINE", description="INFERENCING | ONLINE | STANDBY | OFFLINE")
    connection_status: Optional[str] = Field("CONNECTED", description="CONNECTED | DEGRADED | DISCONNECTED")
    timestamp: Optional[datetime] = None


@router.get("", summary="List all connected buses & active edge nodes")
async def get_buses(
    status: Optional[str] = Query(None, description="Filter by operational status"),
    route_id: Optional[str] = Query(None, description="Filter by assigned route"),
    ai_status: Optional[str] = Query(None, description="Filter by AI status"),
    db: Session = Depends(get_session),
) -> List[Dict[str, Any]]:
    """
    Retrieves all connected buses with the 10 core fields:
    - bus_id, route_id, latitude, longitude, speed, heading, timestamp,
      camera_status, AI_status, connection_status
    """
    ensure_default_buses_seeded(db)

    query = select(BusModel)
    if route_id:
        query = query.where(BusModel.route_id == route_id)
    if status:
        query = query.where(BusModel.status == status.upper())

    db_buses = db.exec(query).all()
    if db_buses:
        result = [b.to_dict() for b in db_buses]
        if ai_status:
            result = [b for b in result if b.get("AI_status") == ai_status.upper()]
        return result

    # Fallback to demo service
    svc = get_demo_seeder_service()
    buses = svc.get_buses()
    return buses


@router.get("/{bus_id}", summary="Get detailed edge node telemetry and detections")
async def get_bus_detail(bus_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    """
    Returns detailed bus telemetry, hardware status, latest detections, and recent hazards.
    """
    ensure_default_buses_seeded(db)

    stmt = select(BusModel).where(BusModel.bus_id == bus_id)
    bus = db.exec(stmt).first()

    bus_dict = bus.to_dict() if bus else None

    if not bus_dict:
        # Check default fleet
        for f in DEFAULT_FLEET:
            if f["bus_id"] == bus_id:
                bus_dict = dict(f)
                bus_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
                break

    if not bus_dict:
        raise HTTPException(status_code=404, detail=f"Bus edge node '{bus_id}' not found")

    # Fetch recent detections captured by this bus
    det_stmt = (
        select(RoadDetection)
        .where(RoadDetection.bus_id == bus_id)
        .order_by(RoadDetection.timestamp.desc())
        .limit(20)
    )
    detections = db.exec(det_stmt).all()

    det_list = [d.to_dict() for d in detections]

    # Filter hazards (potholes, damage, cracks, waterlogging, debris)
    hazard_types = {"POTHOLE", "ROAD_DAMAGE", "ROAD_CRACK", "WATERLOGGING", "DEBRIS", "DAMAGED_ZEBRA_CROSSING"}
    recent_hazards = [d for d in det_list if d.get("type", "").upper() in hazard_types]

    bus_dict["latest_detections"] = det_list[:8]
    bus_dict["recent_hazards"] = recent_hazards[:8]
    bus_dict["total_detections_count"] = len(det_list)

    return bus_dict


@router.get("/{bus_id}/detections", summary="Get road detections captured by a specific bus")
async def get_bus_detections(
    bus_id: str,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_session),
) -> List[Dict[str, Any]]:
    """Returns historical road intelligence detections captured by this bus."""
    det_stmt = (
        select(RoadDetection)
        .where(RoadDetection.bus_id == bus_id)
        .order_by(RoadDetection.timestamp.desc())
        .limit(limit)
    )
    dets = db.exec(det_stmt).all()
    return [d.to_dict() for d in dets]


@router.post("/telemetry", summary="Ingest real-time kinematic & AI telemetry from a bus edge node")
async def ingest_bus_telemetry(
    payload: BusTelemetryPayload,
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    Ingests bus telemetry, updates the BusModel record, and logs a GPS breadcrumb.
    """
    now = payload.timestamp or datetime.now(timezone.utc)

    stmt = select(BusModel).where(BusModel.bus_id == payload.bus_id)
    bus = db.exec(stmt).first()

    if not bus:
        bus = BusModel(
            bus_id=payload.bus_id,
            route_id=payload.route_id or "R-01",
            name=f"Connected Transit Bus ({payload.bus_id})",
            current_lat=payload.latitude,
            current_lon=payload.longitude,
            latitude=payload.latitude,
            longitude=payload.longitude,
            speed_kmh=payload.speed,
            speed=payload.speed,
            bearing_deg=payload.heading,
            heading=payload.heading,
            camera_status=payload.camera_status or "ACTIVE",
            AI_status=payload.AI_status or "ONLINE",
            connection_status=payload.connection_status or "CONNECTED",
            last_heartbeat=now,
            timestamp=now,
        )
        db.add(bus)
    else:
        bus.sync_kinematics(
            lat=payload.latitude,
            lon=payload.longitude,
            spd=payload.speed,
            hdg=payload.heading,
            ts=now,
        )
        if payload.route_id:
            bus.route_id = payload.route_id
        if payload.camera_status:
            bus.camera_status = payload.camera_status
        if payload.AI_status:
            bus.AI_status = payload.AI_status
        if payload.connection_status:
            bus.connection_status = payload.connection_status
        db.add(bus)

    # Record GPS breadcrumb in GpsTelemetry
    try:
        ping = GpsTelemetry(
            bus_id=payload.bus_id,
            route_id=payload.route_id or bus.route_id or "R-01",
            latitude=payload.latitude,
            longitude=payload.longitude,
            speed_kmh=payload.speed,
            heading=payload.heading,
            timestamp=now,
        )
        db.add(ping)
    except Exception as ping_err:
        logger.debug(f"GpsTelemetry ping note: {ping_err}")

    db.commit()
    db.refresh(bus)

    logger.info(f"Updated telemetry for edge node {bus.bus_id} ({bus.latitude:.4f}, {bus.longitude:.4f})")
    return {"ok": True, "bus": bus.to_dict()}
