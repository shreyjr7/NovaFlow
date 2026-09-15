"""
Public Urban Safety Dashboard Router (Phase 30)
================================================
Public unauthenticated API endpoints delivering aggregated, non-sensitive civic information:
  - Road condition: Defect counts, surface health score, repair stats.
  - Congestion: Corridor delay tiers and average speeds.
  - Waterlogging: Flood notices and safe passage advisories.
  - Public road hazards: Standard alerts ("Road hazard reported", "Heavy congestion", "Waterlogging").
  - Traffic trends: Diurnal mobility curve.
  - Map hotspots: Anonymized GIS pins.

Guaranteed Zero-PII: No passenger data, no raw footage, no license plates, no incident evidence.
"""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from ..services.public_safety_service import (
    get_public_safety_service,
    PublicOverview,
    PublicRoadCondition,
    PublicCongestionSummary,
    PublicWaterlogNotice,
    PublicHazardAlert,
    PublicTrafficTrendPoint,
    PublicMapHotspot,
)

router = APIRouter()


@router.get("/overview", response_model=PublicOverview, summary="Get public city-wide road and mobility overview")
async def get_overview():
    service = get_public_safety_service()
    return service.get_public_overview()


@router.get("/road-condition", response_model=PublicRoadCondition, summary="Get aggregated public road condition metrics")
async def get_road_condition():
    service = get_public_safety_service()
    return service.get_public_road_condition()


@router.get("/congestion", response_model=PublicCongestionSummary, summary="Get public traffic congestion and corridor speed tiers")
async def get_congestion():
    service = get_public_safety_service()
    return service.get_public_congestion()


@router.get("/waterlogging", response_model=List[PublicWaterlogNotice], summary="Get active municipal waterlogging and flood advisories")
async def get_waterlogging():
    service = get_public_safety_service()
    return service.get_public_waterlogging()


@router.get("/hazards", response_model=List[PublicHazardAlert], summary="Get public road hazard alerts with standard labels")
async def get_hazards(
    category: Optional[str] = Query(None, description="Filter by category: 'Road Hazard', 'Traffic Congestion', 'Waterlogging', or 'All'")
):
    service = get_public_safety_service()
    return service.get_public_hazards(category=category)


@router.get("/traffic-trends", response_model=List[PublicTrafficTrendPoint], summary="Get 24-hour diurnal commuter travel trend curve")
async def get_traffic_trends():
    service = get_public_safety_service()
    return service.get_public_traffic_trends()


@router.get("/map-hotspots", response_model=List[PublicMapHotspot], summary="Get public GIS hazard markers with zero sensitive metadata")
async def get_map_hotspots():
    service = get_public_safety_service()
    return service.get_public_map_hotspots()


@router.post("/hazards/{hazard_id}/acknowledge", response_model=PublicHazardAlert, summary="Citizen acknowledgment / upvote of a public road hazard")
async def acknowledge_hazard(hazard_id: str):
    service = get_public_safety_service()
    alert = service.acknowledge_hazard(hazard_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hazard {hazard_id} not found."
        )
    return alert
