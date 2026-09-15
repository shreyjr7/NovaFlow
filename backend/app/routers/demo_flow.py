"""
Demo Flow REST API Router (Phase 35)
====================================
Exposes execution endpoints for the canonical 17-step demonstration scenario
and the vehicle incident investigation pipeline.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Path, Query

from ..services.demo_flow_service import get_demo_flow_service

router = APIRouter()


@router.get("/state", summary="Retrieve current state of the 17-step demo scenario")
async def get_scenario_state() -> Dict[str, Any]:
    svc = get_demo_flow_service()
    return {
        "current_step": svc.current_step,
        "scenario_state": svc.scenario_state,
        "incident_state": svc.incident_state,
    }


@router.post("/reset", summary="Reset demo flow scenario to Step 0")
async def reset_demo_scenario() -> Dict[str, Any]:
    svc = get_demo_flow_service()
    svc.reset_scenario()
    return {
        "status": "RESET",
        "current_step": 0,
        "message": "Demo flow reset to initial baseline.",
    }


@router.post("/step/{step_number}", summary="Execute a specific step (1 to 17) of the demo scenario")
async def execute_demo_step(
    step_number: int = Path(..., ge=1, le=17, description="Step number 1 to 17"),
) -> Dict[str, Any]:
    svc = get_demo_flow_service()
    return svc.execute_step(step_number)


@router.post("/run-all", summary="Autonomously execute all 17 steps of the scenario sequentially")
async def run_all_demo_steps() -> Dict[str, Any]:
    svc = get_demo_flow_service()
    return svc.run_all_steps()


@router.post("/incident-run", summary="Execute the complete vehicle incident investigation flow")
async def run_incident_investigation(
    vehicle_id: str = Query("TRACK_VEH_842"),
    plate_text: str = Query("DL 01 AB 1234"),
) -> Dict[str, Any]:
    svc = get_demo_flow_service()
    return svc.run_incident_flow(vehicle_id=vehicle_id, plate_text=plate_text)
