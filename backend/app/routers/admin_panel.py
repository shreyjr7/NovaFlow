"""
Administration Panel Router (Phase 31)
======================================
Exposes endpoints for the enterprise Admin Dashboard, System Monitoring,
and all 14 Administration Modules:
  1. Users
  2. Roles
  3. Buses
  4. Routes
  5. Devices
  6. Cameras
  7. AI Models
  8. Events
  9. GIS Layers
  10. Data Sources
  11. Retention Policies
  12. System Logs
  13. Audit Logs
  14. Reports
"""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter

from ..services.admin_panel_service import (
    get_admin_panel_service,
    AdminDashboardKPIs,
    SystemMonitoringTelemetry,
    AdminUser,
    AdminRole,
    AdminBus,
    AdminRoute,
    AdminDevice,
    AdminCamera,
    AdminAIModel,
    AdminEvent,
    AdminGISLayer,
    AdminDataSource,
    AdminRetentionPolicy,
    AdminSystemLog,
    AdminAuditLog,
)

router = APIRouter()


@router.get("/dashboard", response_model=AdminDashboardKPIs, summary="Get high-level Admin Dashboard KPIs")
async def get_dashboard():
    service = get_admin_panel_service()
    return service.get_dashboard()


@router.get("/system-monitoring", response_model=SystemMonitoringTelemetry, summary="Get live real-time system monitoring telemetry")
async def get_system_monitoring():
    service = get_admin_panel_service()
    return service.get_system_monitoring()


# ── 14 Subsystem Module Endpoints ───────────────────────────────────────────

@router.get("/users", response_model=List[AdminUser], summary="Get users catalog")
async def get_users():
    return get_admin_panel_service().get_users()


@router.get("/roles", response_model=List[AdminRole], summary="Get roles & permissions directory")
async def get_roles():
    return get_admin_panel_service().get_roles()


@router.get("/buses", response_model=List[AdminBus], summary="Get fleet buses roster")
async def get_buses():
    return get_admin_panel_service().get_buses()


@router.get("/routes", response_model=List[AdminRoute], summary="Get transit routes")
async def get_routes():
    return get_admin_panel_service().get_routes()


@router.get("/devices", response_model=List[AdminDevice], summary="Get edge devices inventory")
async def get_devices():
    return get_admin_panel_service().get_devices()


@router.get("/cameras", response_model=List[AdminCamera], summary="Get optical cameras registry")
async def get_cameras():
    return get_admin_panel_service().get_cameras()


@router.get("/ai-models", response_model=List[AdminAIModel], summary="Get AI models status")
async def get_ai_models():
    return get_admin_panel_service().get_ai_models()


@router.get("/events", response_model=List[AdminEvent], summary="Get ingested events feed")
async def get_events():
    return get_admin_panel_service().get_events()


@router.get("/gis-layers", response_model=List[AdminGISLayer], summary="Get GIS map layers")
async def get_gis_layers():
    return get_admin_panel_service().get_gis_layers()


@router.get("/data-sources", response_model=List[AdminDataSource], summary="Get upstream data sources")
async def get_data_sources():
    return get_admin_panel_service().get_data_sources()


@router.get("/retention-policies", response_model=List[AdminRetentionPolicy], summary="Get retention policies")
async def get_retention_policies():
    return get_admin_panel_service().get_retention_policies()


@router.get("/system-logs", response_model=List[AdminSystemLog], summary="Get real-time system logs")
async def get_system_logs():
    return get_admin_panel_service().get_system_logs()


@router.get("/audit-logs", response_model=List[AdminAuditLog], summary="Get immutable audit logs")
async def get_audit_logs():
    return get_admin_panel_service().get_audit_logs()


@router.get("/reports", response_model=List[Dict[str, Any]], summary="Get reports archive index")
async def get_reports():
    return get_admin_panel_service().get_reports()
