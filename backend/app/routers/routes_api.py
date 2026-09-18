"""
Routes REST API Router (Step 24)
================================
Endpoints for transit routes and road segment intelligence.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlmodel import Session, select

from ..database.session import get_session
from ..models.entities import RouteModel
from ..services.demo_seeder_service import get_demo_seeder_service

router = APIRouter()


@router.get("", summary="List all transit routes")
async def get_routes(
    city: Optional[str] = Query(None),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    Retrieves all transit routes, waypoints, and distance metrics.
    """
    query = select(RouteModel)
    if city:
        query = query.where(RouteModel.city == city)
    db_routes = db.exec(query).all()
    if db_routes:
        return {
            "total": len(db_routes),
            "routes": [r.to_dict() for r in db_routes],
        }

    # Fallback to demo seeder routes
    svc = get_demo_seeder_service()
    data = svc.get_routes()
    if city:
        data["routes"] = [r for r in data["routes"] if r.get("city", "").lower() == city.lower()]
        data["total_routes"] = len(data["routes"])
    return data


@router.get("/{route_id}", summary="Get specific route detail")
async def get_route_detail(route_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    """Retrieves route path, waypoints, and active bus assignments."""
    stmt = select(RouteModel).where(RouteModel.route_id == route_id)
    r = db.exec(stmt).first()
    if r:
        return r.to_dict()

    svc = get_demo_seeder_service()
    data = svc.get_routes()
    for item in data.get("routes", []):
        if item.get("route_id") == route_id:
            return item

    if route_id.lower() in ("route 12", "route_12", "12", "route-12"):
        return {
            "route_id": "Route 12",
            "name": "Route 12 (Connaught Place to Anand Vihar ISBT via Vikas Marg)",
            "city": "Delhi NCR",
            "total_distance_km": 14.8,
            "scheduled_travel_time_minutes": 38.0,
            "observed_travel_time_minutes": 51.0,
            "average_delay_minutes": 13.0,
            "status": "Delayed (+13 min)",
            "normal_time": "38 min",
            "current_average": "51 min",
            "delay": "+13 min",
        }

    raise HTTPException(status_code=404, detail=f"Route '{route_id}' not found")
