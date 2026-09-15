"""
Demo Environment REST API Router (Phase 34)
===========================================
Serves live demonstration data:
  - 20 connected buses
  - 5 metropolitan routes with 115 road segments
  - 500+ historical events
  - Live kinematic movement advancement
  - DEMO MODE indicator metadata for UI
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from sqlmodel import Session, select

from ..database.session import engine
from ..models.ingested_event import IngestedEvent
from ..services.demo_seeder_service import get_demo_seeder_service

router = APIRouter()


@router.get("/status", summary="Get demonstration environment status and DEMO MODE indicator")
async def get_demo_status() -> Dict[str, Any]:
    svc = get_demo_seeder_service()
    return svc.get_status()


@router.get("/buses", summary="Retrieve all 20 simulated buses with live kinematics")
async def get_demo_buses() -> List[Dict[str, Any]]:
    svc = get_demo_seeder_service()
    return svc.get_buses()


@router.get("/routes", summary="Retrieve all 5 routes and 115 road segments")
async def get_demo_routes() -> Dict[str, Any]:
    svc = get_demo_seeder_service()
    return svc.get_routes()


@router.get("/events", summary="Filterable query of 500+ demo historical events")
async def get_demo_events(
    event_type: Optional[str] = Query(None),
    bus_id: Optional[str] = Query(None),
    route_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> Dict[str, Any]:
    with Session(engine) as session:
        query = select(IngestedEvent)
        if event_type:
            query = query.where(IngestedEvent.event_type == event_type.upper())
        if bus_id:
            query = query.where(IngestedEvent.bus_id == bus_id)
        if severity:
            query = query.where(IngestedEvent.severity == severity.upper())

        events = session.exec(query.limit(limit)).all()
        return {
            "total_returned": len(events),
            "demo_mode": True,
            "events": [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "bus_id": e.bus_id,
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                    "gps": {
                        "lat": e.gps_lat,
                        "lon": e.gps_lon,
                        "bearing_deg": e.bearing_deg,
                        "road_segment": e.road_segment,
                        "address": e.address,
                    },
                    "confidence": e.confidence,
                    "severity": e.severity,
                    "status": e.status,
                    "evidence_reference": e.evidence_reference,
                }
                for e in events
            ],
        }


@router.post("/tick", summary="Advance bus kinematics along routes by dt seconds")
async def advance_demo_kinematics(dt_seconds: float = Query(2.0, ge=0.5, le=30.0)) -> Dict[str, Any]:
    svc = get_demo_seeder_service()
    updated = svc.advance_kinematics(dt_seconds=dt_seconds)
    return {
        "status": "TICK_COMPLETED",
        "dt_seconds": dt_seconds,
        "buses_updated": len(updated),
        "buses": updated,
    }


@router.post("/seed", summary="Seed 500+ historical events into database")
async def seed_demo_environment() -> Dict[str, Any]:
    svc = get_demo_seeder_service()
    count = svc.seed_historical_events(target_count=525)
    return {
        "status": "SEEDED",
        "total_historical_events": count,
        "demo_mode": True,
    }
