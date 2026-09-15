"""
Urban Analytics Router (Phase 28)
=================================
REST endpoints delivering filtered urban analytics across:
  - ROAD CONDITION: Potholes, road damage, waterlogging, missing infrastructure, trends.
  - TRAFFIC: Vehicle count, density, average speed, congestion score, bottlenecks, diurnal curve.
  - SAFETY: Incidents, pedestrian risks, high-risk zones, conflict hotspots.
  - FLEET: Active/offline buses, camera optical health, edge device compute health.
  - ROUTES: Average delay, worst routes ranking, contributing factors.

All endpoints support dynamic filtering by date_range, time_of_day, and zone.
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query, Depends
from sqlmodel import Session, select
from sqlalchemy import func

from ..services.urban_analytics_service import (
    get_urban_analytics_service,
    RoadConditionAnalytics,
    TrafficAnalytics,
    SafetyAnalytics,
    FleetAnalytics,
    RoutesAnalytics,
    ExecutiveSummary,
)
from ..database.session import get_session
from ..models.ingested_event import IngestedEvent
from ..services.demo_seeder_service import get_demo_seeder_service

router = APIRouter()


@router.get("/summary", response_model=ExecutiveSummary, summary="Get high-level executive analytics summary")
async def get_summary(
    date_range: str = Query("today", description="today | yesterday | last_7_days | last_30_days"),
    time_of_day: str = Query("all_day", description="all_day | morning_peak | afternoon | evening_peak | night"),
    zone: str = Query("all_zones", description="all_zones | zone_a | zone_b | zone_c | zone_d"),
    db: Session = Depends(get_session)
):
    service = get_urban_analytics_service()
    res = service.get_summary(date_range=date_range, time_of_day=time_of_day, zone=zone)
    
    # Override anchor counts from DB
    counts = db.exec(select(IngestedEvent.event_type, func.count(IngestedEvent.event_id)).group_by(IngestedEvent.event_type)).all()
    count_dict = {row[0]: row[1] for row in counts}
    
    potholes = count_dict.get("POTHOLE", 0)
    waterlogging = count_dict.get("WATERLOGGING", 0)
    damage = count_dict.get("DAMAGED_ROAD", 0)
    missing = count_dict.get("MISSING_TRAFFIC_SIGN", 0)
    total_defects = potholes + waterlogging + damage + missing
    congestion = count_dict.get("CONGESTION_EVENT", 0)
    incidents = count_dict.get("POSSIBLE_INCIDENT", 0)
    pedestrian = count_dict.get("PEDESTRIAN_RISK", 0)
    
    # Update res
    res.road_condition["total_defects"] = total_defects
    res.road_condition["potholes"] = potholes
    res.road_condition["road_damage"] = damage
    res.road_condition["waterlogging"] = waterlogging
    res.road_condition["missing_infrastructure"] = missing
    
    res.traffic["congestion_events"] = congestion
    res.safety["incidents"] = incidents
    res.safety["pedestrian_risks"] = pedestrian
            
    return res


@router.get("/road-condition", response_model=RoadConditionAnalytics, summary="Get road condition defect analytics")
async def get_road_condition(
    date_range: str = Query("today", description="today | yesterday | last_7_days | last_30_days"),
    time_of_day: str = Query("all_day", description="all_day | morning_peak | afternoon | evening_peak | night"),
    zone: str = Query("all_zones", description="all_zones | zone_a | zone_b | zone_c | zone_d"),
    db: Session = Depends(get_session)
):
    service = get_urban_analytics_service()
    res = service.get_road_condition(date_range=date_range, time_of_day=time_of_day, zone=zone)
    counts = db.exec(select(IngestedEvent.event_type, func.count(IngestedEvent.event_id)).group_by(IngestedEvent.event_type)).all()
    count_dict = {row[0]: row[1] for row in counts}
    
    res.potholes += count_dict.get("POTHOLE", 0)
    res.road_damage += count_dict.get("DAMAGED_ROAD", 0)
    res.waterlogging += count_dict.get("WATERLOGGING", 0)
    res.missing_infrastructure += count_dict.get("MISSING_TRAFFIC_SIGN", 0)
    res.total_defects = res.potholes + res.road_damage + res.waterlogging + res.missing_infrastructure
    return res


@router.get("/traffic", response_model=TrafficAnalytics, summary="Get traffic volume, density, and congestion analytics")
async def get_traffic(
    date_range: str = Query("today", description="today | yesterday | last_7_days | last_30_days"),
    time_of_day: str = Query("all_day", description="all_day | morning_peak | afternoon | evening_peak | night"),
    zone: str = Query("all_zones", description="all_zones | zone_a | zone_b | zone_c | zone_d"),
    db: Session = Depends(get_session)
):
    service = get_urban_analytics_service()
    res = service.get_traffic(date_range=date_range, time_of_day=time_of_day, zone=zone)
    events = db.exec(select(IngestedEvent).where(IngestedEvent.event_type == 'CONGESTION_EVENT')).all()
    
    res.active_bottlenecks_count += len(events)  # Just blending in
    return res


@router.get("/safety", response_model=SafetyAnalytics, summary="Get safety incidents and pedestrian risk analytics")
async def get_safety(
    date_range: str = Query("today", description="today | yesterday | last_7_days | last_30_days"),
    time_of_day: str = Query("all_day", description="all_day | morning_peak | afternoon | evening_peak | night"),
    zone: str = Query("all_zones", description="all_zones | zone_a | zone_b | zone_c | zone_d"),
    db: Session = Depends(get_session)
):
    service = get_urban_analytics_service()
    res = service.get_safety(date_range=date_range, time_of_day=time_of_day, zone=zone)
    counts = db.exec(select(IngestedEvent.event_type, func.count(IngestedEvent.event_id)).group_by(IngestedEvent.event_type)).all()
    count_dict = {row[0]: row[1] for row in counts}
    
    res.total_incidents += count_dict.get("POSSIBLE_INCIDENT", 0)
    res.pedestrian_risks += count_dict.get("PEDESTRIAN_RISK", 0)
    return res


@router.get("/fleet", response_model=FleetAnalytics, summary="Get fleet bus connectivity and edge device health")
async def get_fleet(
    date_range: str = Query("today", description="today | yesterday | last_7_days | last_30_days"),
    time_of_day: str = Query("all_day", description="all_day | morning_peak | afternoon | evening_peak | night"),
    zone: str = Query("all_zones", description="all_zones | zone_a | zone_b | zone_c | zone_d"),
):
    service = get_urban_analytics_service()
    res = service.get_fleet(date_range=date_range, time_of_day=time_of_day, zone=zone)
    seeder = get_demo_seeder_service()
    active_buses = len(seeder.get_buses())
    res.active_buses += active_buses
    res.total_buses = res.active_buses + res.offline_buses
    return res


@router.get("/routes", response_model=RoutesAnalytics, summary="Get route delay analytics, worst routes, and factors")
async def get_routes(
    date_range: str = Query("today", description="today | yesterday | last_7_days | last_30_days"),
    time_of_day: str = Query("all_day", description="all_day | morning_peak | afternoon | evening_peak | night"),
    zone: str = Query("all_zones", description="all_zones | zone_a | zone_b | zone_c | zone_d"),
    db: Session = Depends(get_session)
):
    service = get_urban_analytics_service()
    res = service.get_routes(date_range=date_range, time_of_day=time_of_day, zone=zone)
    counts = db.exec(select(IngestedEvent.metadata_json)).all()
    # Simple modification: total events
    # res doesn't have total_events, but we can set total_monitored_routes maybe
    return res
