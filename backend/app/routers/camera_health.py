"""
Camera & Edge Device Health API Router (Phase 25)
=================================================
Endpoints for monitoring fleet camera optical and compute node metrics:
  - Statuses: HEALTHY, WARNING, DEGRADED, OFFLINE
  - Metrics: FPS, Blur score, Brightness, Lens obstruction, Temperature, CPU, GPU, RAM, Storage, Network, Heartbeat
  - Fail-safe trigger: Automatically flags CAMERA DEGRADED and creates maintenance tickets when lens is dirty/obstructed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..services.camera_health_service import (
    CameraTelemetry,
    DeviceHealthState,
    MaintenanceTicket,
    get_camera_health_service,
)

router = APIRouter()


class SimulateObstructionIn(BaseModel):
    obstruction_pct: float = Field(75.0, ge=0.0, le=100.0, description="Percentage of lens obstructed (mud/dirt)")
    reason: str = Field("Mud splatter & grime on external optical dome", description="Cause of optical obstruction")


@router.get("/health")
async def get_camera_fleet_health_summary():
    """Returns aggregated camera and edge compute fleet diagnostic summary."""
    service = get_camera_health_service()
    return service.get_summary()


@router.get("/maintenance-tickets", response_model=List[MaintenanceTicket])
async def list_camera_maintenance_tickets():
    """Returns all automatically and manually generated camera maintenance tickets."""
    service = get_camera_health_service()
    return service.list_maintenance_tickets()


@router.get("", response_model=List[CameraTelemetry])
async def list_fleet_cameras(
    status: Optional[DeviceHealthState] = Query(None, description="Filter by state (HEALTHY, WARNING, DEGRADED, OFFLINE)"),
):
    """
    Lists all edge camera devices with full optical and hardware telemetry.
    """
    service = get_camera_health_service()
    return service.list_cameras(status=status)


@router.get("/{camera_id}", response_model=CameraTelemetry)
async def get_camera_telemetry(camera_id: str):
    """Retrieves full telemetry for a specific camera optical and edge node."""
    service = get_camera_health_service()
    cam = service.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    return cam


@router.post("/{camera_id}/telemetry", response_model=CameraTelemetry)
async def record_camera_telemetry(camera_id: str, telemetry: CameraTelemetry):
    """Ingests edge optical and system telemetry heartbeat."""
    if telemetry.camera_id != camera_id:
        telemetry.camera_id = camera_id
    service = get_camera_health_service()
    return service.record_telemetry(telemetry)


@router.post("/{camera_id}/simulate-obstruction", response_model=CameraTelemetry)
async def simulate_lens_obstruction(camera_id: str, body: SimulateObstructionIn):
    """
    Simulates dirty or obstructed lens on camera:
      - Validates critical rule: Do NOT silently continue producing unreliable detections.
      - Sets state to CAMERA DEGRADED.
      - Halts unreliable downstream computer vision detections.
      - Automatically creates an optical maintenance ticket.
    """
    service = get_camera_health_service()
    updated = service.simulate_lens_obstruction(
        camera_id=camera_id,
        obstruction_pct=body.obstruction_pct,
        reason=body.reason,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    return updated
