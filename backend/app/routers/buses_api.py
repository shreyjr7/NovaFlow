"""
Buses REST API Router (Step 24)
===============================
Endpoints for querying connected transit fleet buses.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlmodel import Session, select

from ..database.session import get_session
from ..models.entities import BusModel
from ..services.demo_seeder_service import get_demo_seeder_service

router = APIRouter()


@router.get("", summary="List all connected buses")
async def get_buses(
    status: Optional[str] = Query(None, description="IN_SERVICE | MAINTENANCE | DEPOT"),
    route_id: Optional[str] = Query(None, description="Filter by assigned route"),
    db: Session = Depends(get_session),
) -> List[Dict[str, Any]]:
    """
    Retrieves all connected buses with current GPS positions, kinematics, and camera status.
    Pulls from database with fallback to live kinematics simulation.
    """
    query = select(BusModel)
    if status:
        query = query.where(BusModel.status == status.upper())
    if route_id:
        query = query.where(BusModel.route_id == route_id)

    db_buses = db.exec(query).all()
    if db_buses:
        return [b.to_dict() for b in db_buses]

    # Fallback to demo kinematics service
    svc = get_demo_seeder_service()
    buses = svc.get_buses()
    if status:
        buses = [b for b in buses if b.get("status") == status.upper()]
    if route_id:
        buses = [b for b in buses if b.get("route_id") == route_id]
    return buses


@router.get("/{bus_id}", summary="Get specific bus details")
async def get_bus_detail(bus_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    """Retrieves detailed telemetry for a single bus."""
    stmt = select(BusModel).where(BusModel.bus_id == bus_id)
    bus = db.exec(stmt).first()
    if bus:
        return bus.to_dict()

    svc = get_demo_seeder_service()
    all_b = svc.get_buses()
    for b in all_b:
        if b.get("bus_id") == bus_id:
            return b

    raise HTTPException(status_code=404, detail=f"Bus '{bus_id}' not found")
