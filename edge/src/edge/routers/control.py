"""
Control Router
==============
REST endpoints for the Edge AI Simulator control panel.

POST /api/simulator/start    – start pipeline(s)
POST /api/simulator/pause    – pause all pipelines
POST /api/simulator/resume   – resume all pipelines
POST /api/simulator/stop     – stop all pipelines
GET  /api/simulator/status   – current state
GET  /api/simulator/routes   – available simulated GPS routes
GET  /api/simulator/buses    – dummy bus list for the UI
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger("routers.control")
router = APIRouter()


# ── Request / Response schemas ─────────────────────────────────────────────

class CameraSource(BaseModel):
    FRONT: Optional[str] = None   # file path or "0" for webcam
    REAR:  Optional[str] = None
    LEFT:  Optional[str] = None
    RIGHT: Optional[str] = None


class StartRequest(BaseModel):
    bus_id: str = "BUS_001"
    route_id: str = "ROUTE_1"
    cameras: CameraSource = CameraSource()
    api_base_url: str = "http://localhost:8000"
    api_token: Optional[str] = None
    frame_sample_rate: int = 5      # process every Nth frame
    speed_kmh: float = 30.0


class NetworkModeRequest(BaseModel):
    mode: str  # ONLINE, OFFLINE, RECONNECTING, or AUTO


class TestEventRequest(BaseModel):
    event_type: str = "POTHOLE_DETECTED"
    confidence: float = 0.88
    details: Dict[str, Any] = {}


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_manager(request: Request):
    mgr = request.app.state.simulator
    if mgr is None:
        raise HTTPException(status_code=500, detail="Simulator manager not initialised.")
    return mgr


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/start")
async def start(body: StartRequest, request: Request):
    mgr = _get_manager(request)

    # Build camera sources dict (skip None cameras)
    sources: Dict[str, Any] = {}
    for pos in ("FRONT", "REAR", "LEFT", "RIGHT"):
        src = getattr(body.cameras, pos)
        if src is not None:
            # "0" → integer for webcam
            sources[pos] = int(src) if src.isdigit() else src

    if not sources:
        # Default: use webcam 0 for FRONT if nothing specified
        sources["FRONT"] = 0

    mgr.start(
        bus_id=body.bus_id,
        route_id=body.route_id,
        camera_sources=sources,
        api_base_url=body.api_base_url,
        api_token=body.api_token,
        frame_sample_rate=body.frame_sample_rate,
        speed_kmh=body.speed_kmh,
    )
    return {"ok": True, "message": f"Started {len(sources)} camera pipeline(s).", "cameras": list(sources.keys())}


@router.post("/pause")
async def pause(request: Request):
    mgr = _get_manager(request)
    mgr.pause()
    return {"ok": True, "message": "Paused."}


@router.post("/resume")
async def resume(request: Request):
    mgr = _get_manager(request)
    mgr.resume()
    return {"ok": True, "message": "Resumed."}


@router.post("/stop")
async def stop(request: Request):
    mgr = _get_manager(request)
    mgr.stop()
    return {"ok": True, "message": "Stopped."}


@router.get("/status")
async def status(request: Request):
    mgr = _get_manager(request)
    return mgr.status()


@router.get("/routes")
async def list_routes():
    from ...gps_simulator import SAMPLE_ROUTES
    return {"routes": list(SAMPLE_ROUTES.keys())}


@router.get("/buses")
async def list_buses():
    """Dummy bus list for the control-panel dropdown."""
    return {
        "buses": [
            {"id": "BUS_001", "name": "Bus 001 – Route 1", "route": "ROUTE_1"},
            {"id": "BUS_002", "name": "Bus 002 – Route 2", "route": "ROUTE_2"},
            {"id": "BUS_003", "name": "Bus 003 – Route 3", "route": "ROUTE_3"},
        ]
    }


# ── Phase 15: Network Store-and-Forward Endpoints ────────────────────────────

@router.post("/network/mode")
async def set_network_mode(body: NetworkModeRequest, request: Request):
    """
    Sets simulated network mode: ONLINE, OFFLINE, RECONNECTING, or AUTO.
    """
    mgr = _get_manager(request)
    try:
        mgr.network_manager.set_mode(body.mode)
        return {
            "ok": True,
            "mode": mgr.network_manager.current_state,
            "indicator": mgr.network_manager.get_status_text(),
            "status": mgr.network_manager.get_status_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/network/status")
async def get_network_status(request: Request):
    """
    Returns current network state, queue metrics, and prompt-mandated UI indicator text.
    """
    mgr = _get_manager(request)
    return mgr.network_manager.get_status_dict()


@router.post("/network/flush")
async def flush_network_buffer(request: Request):
    """
    Manually triggers store-and-forward retransmission of pending SQLite events.
    """
    mgr = _get_manager(request)
    drained = mgr.flush_buffered_events()
    return {
        "ok": True,
        "drained_count": drained,
        "remaining": mgr.network_manager.queue.pending_count(),
        "status": mgr.network_manager.get_status_dict(),
    }


@router.post("/network/test-event")
async def inject_test_event(body: TestEventRequest, request: Request):
    """
    Injects a test event to verify online streaming vs offline buffering.
    """
    mgr = _get_manager(request)
    event = {
        "event_id": f"test_ev_{uuid.uuid4().hex[:8]}",
        "event_type": body.event_type,
        "confidence": body.confidence,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gps": {"lat": 12.9716, "lon": 77.5946, "bearing_deg": 45.0, "road_segment": "MG_ROAD_SEG_1"},
        "details": body.details,
    }

    if mgr.network_manager.is_offline():
        mgr.network_manager.queue.enqueue(event)
        buffered = True
    else:
        sent = mgr._drain_sender(event)
        buffered = not sent
        if buffered:
            mgr.network_manager.queue.enqueue(event)

    return {
        "ok": True,
        "event_id": event["event_id"],
        "buffered": buffered,
        "network_status": mgr.network_manager.get_status_dict(),
    }

