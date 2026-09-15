"""
Camera & Edge Device Health Service (Phase 25)
==============================================
Monitors hardware and optical telemetry:
  - Camera status: HEALTHY, WARNING, DEGRADED, OFFLINE
  - Optical metrics: FPS, Blur score (Laplacian variance), Brightness, Lens obstruction %
  - Edge hardware metrics: Temperature, CPU, GPU, RAM, Storage, Network, Heartbeat

Critical Fail-Safe Rule:
  - If camera is dirty/obstructed (obstruction >= 25%):
    1. Do NOT silently continue producing unreliable detections (halted = True).
    2. Generate: CAMERA DEGRADED.
    3. Create maintenance ticket automatically.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DeviceHealthState(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


class MaintenanceTicket(BaseModel):
    ticket_id: str
    camera_id: str
    bus_id: str
    issue_type: str
    severity: str  # CRITICAL, HIGH, MEDIUM
    status: str  # OPEN, ASSIGNED, RESOLVED
    created_at: str
    reason: str
    halted_detections: bool = True
    assigned_technician: Optional[str] = None


class CameraTelemetry(BaseModel):
    camera_id: str
    bus_id: str
    camera_name: str
    camera_status: DeviceHealthState
    fps: float
    target_fps: float = 30.0
    blur_score: float  # Laplacian variance (higher is sharper; < 50 indicates blur)
    brightness: float  # 0 to 255
    lens_obstruction_pct: float = Field(..., ge=0.0, le=100.0)
    is_lens_obstructed: bool = False
    unreliable_detections_halted: bool = False
    temperature_celsius: float
    cpu_usage_pct: float
    gpu_usage_pct: float
    ram_usage_pct: float
    storage_usage_pct: float
    network_status: str  # ONLINE_5G, 4G_LTE, DEGRADED, OFFLINE
    network_latency_ms: float
    last_heartbeat: str
    active_maintenance_ticket_id: Optional[str] = None


class CameraHealthService:
    """Manages fleet camera optical quality and edge computing node diagnostics."""

    def __init__(self):
        self._devices: Dict[str, CameraTelemetry] = {}
        self._tickets: Dict[str, MaintenanceTicket] = {}
        self._seed_fleet_cameras()

    def _seed_fleet_cameras(self):
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Healthy Camera
        cam_102 = CameraTelemetry(
            camera_id="CAM-102-FRONT",
            bus_id="BUS-102",
            camera_name="Front Windshield Optical Sensor",
            camera_status=DeviceHealthState.HEALTHY,
            fps=29.8,
            target_fps=30.0,
            blur_score=145.2,
            brightness=132.0,
            lens_obstruction_pct=1.5,
            is_lens_obstructed=False,
            unreliable_detections_halted=False,
            temperature_celsius=48.2,
            cpu_usage_pct=41.5,
            gpu_usage_pct=64.8,
            ram_usage_pct=52.0,
            storage_usage_pct=34.1,
            network_status="ONLINE_5G",
            network_latency_ms=24.5,
            last_heartbeat=now_iso,
        )

        # 2. Warning Camera (High Temp & Slight Blur)
        cam_117 = CameraTelemetry(
            camera_id="CAM-117-FRONT",
            bus_id="BUS-117",
            camera_name="Front Wide Road-Facing Lens",
            camera_status=DeviceHealthState.WARNING,
            fps=26.4,
            target_fps=30.0,
            blur_score=68.0,
            brightness=140.0,
            lens_obstruction_pct=12.0,
            is_lens_obstructed=False,
            unreliable_detections_halted=False,
            temperature_celsius=68.5,
            cpu_usage_pct=78.2,
            gpu_usage_pct=88.4,
            ram_usage_pct=72.0,
            storage_usage_pct=61.0,
            network_status="4G_LTE",
            network_latency_ms=65.2,
            last_heartbeat=now_iso,
        )

        # 3. Degraded Camera (Lens Obstructed by Mud / Dust -> Detections Halted + Auto-Ticket)
        ticket_id = "TKT-CAM-2026-001"
        cam_143 = CameraTelemetry(
            camera_id="CAM-143-FRONT",
            bus_id="BUS-143",
            camera_name="Front Optical High-Definition Lens",
            camera_status=DeviceHealthState.DEGRADED,
            fps=18.2,
            target_fps=30.0,
            blur_score=31.5,
            brightness=78.0,
            lens_obstruction_pct=42.0,
            is_lens_obstructed=True,
            unreliable_detections_halted=True,
            temperature_celsius=52.0,
            cpu_usage_pct=48.0,
            gpu_usage_pct=55.0,
            ram_usage_pct=58.0,
            storage_usage_pct=40.0,
            network_status="ONLINE_5G",
            network_latency_ms=31.0,
            last_heartbeat=now_iso,
            active_maintenance_ticket_id=ticket_id,
        )
        self._tickets[ticket_id] = MaintenanceTicket(
            ticket_id=ticket_id,
            camera_id="CAM-143-FRONT",
            bus_id="BUS-143",
            issue_type="LENS_OBSTRUCTION_DIRT_CLEANING",
            severity="HIGH",
            status="OPEN",
            created_at=now_iso,
            reason="Lens obstruction reached 42.0% (mud splatter). Unreliable detections halted to protect data integrity.",
            halted_detections=True,
            assigned_technician="Depot 4 Maintenance Bay",
        )

        # 4. Offline Edge Node
        cam_131 = CameraTelemetry(
            camera_id="CAM-131-FRONT",
            bus_id="BUS-131",
            camera_name="Front Jetson Edge Module",
            camera_status=DeviceHealthState.OFFLINE,
            fps=0.0,
            target_fps=30.0,
            blur_score=0.0,
            brightness=0.0,
            lens_obstruction_pct=0.0,
            is_lens_obstructed=False,
            unreliable_detections_halted=True,
            temperature_celsius=0.0,
            cpu_usage_pct=0.0,
            gpu_usage_pct=0.0,
            ram_usage_pct=0.0,
            storage_usage_pct=0.0,
            network_status="OFFLINE",
            network_latency_ms=9999.0,
            last_heartbeat="2026-09-15T00:15:00Z",
        )

        # 5. Additional Fleet Camera
        cam_124 = CameraTelemetry(
            camera_id="CAM-124-FRONT",
            bus_id="BUS-124",
            camera_name="Front Telephoto Plate Lens",
            camera_status=DeviceHealthState.HEALTHY,
            fps=30.0,
            target_fps=30.0,
            blur_score=155.0,
            brightness=124.0,
            lens_obstruction_pct=3.0,
            is_lens_obstructed=False,
            unreliable_detections_halted=False,
            temperature_celsius=46.5,
            cpu_usage_pct=38.0,
            gpu_usage_pct=60.0,
            ram_usage_pct=49.0,
            storage_usage_pct=31.0,
            network_status="ONLINE_5G",
            network_latency_ms=21.0,
            last_heartbeat=now_iso,
        )

        for dev in [cam_102, cam_117, cam_143, cam_131, cam_124]:
            self._devices[dev.camera_id] = dev

    def list_cameras(self, status: Optional[DeviceHealthState] = None) -> List[CameraTelemetry]:
        results = list(self._devices.values())
        if status:
            results = [d for d in results if d.camera_status == status]
        # Sort DEGRADED & OFFLINE first
        state_order = {
            DeviceHealthState.DEGRADED: 0,
            DeviceHealthState.OFFLINE: 1,
            DeviceHealthState.WARNING: 2,
            DeviceHealthState.HEALTHY: 3,
        }
        results.sort(key=lambda x: state_order.get(x.camera_status, 4))
        return results

    def get_camera(self, camera_id: str) -> Optional[CameraTelemetry]:
        return self._devices.get(camera_id)

    def record_telemetry(self, telemetry: CameraTelemetry) -> CameraTelemetry:
        # Check fail-safe: if obstruction >= 25%, enforce CAMERA DEGRADED & auto-ticket
        if telemetry.lens_obstruction_pct >= 25.0:
            telemetry.camera_status = DeviceHealthState.DEGRADED
            telemetry.is_lens_obstructed = True
            telemetry.unreliable_detections_halted = True
            self._ensure_maintenance_ticket(telemetry, reason=f"Lens obstruction {telemetry.lens_obstruction_pct}% exceeds 25% threshold.")
        elif telemetry.camera_status == DeviceHealthState.HEALTHY:
            telemetry.unreliable_detections_halted = False
            telemetry.is_lens_obstructed = False

        self._devices[telemetry.camera_id] = telemetry
        return telemetry

    def simulate_lens_obstruction(
        self, camera_id: str, obstruction_pct: float = 65.0, reason: str = "Simulated heavy mud splatter on optical front element"
    ) -> Optional[CameraTelemetry]:
        """
        Simulates dirty or obstructed lens:
          - Automatically transitions camera to DEGRADED
          - Halts downstream unreliable detections (Do NOT silently continue producing unreliable detections)
          - Spawns automatic maintenance ticket
        """
        cam = self._devices.get(camera_id)
        if not cam:
            return None

        cam.lens_obstruction_pct = obstruction_pct
        cam.is_lens_obstructed = True
        cam.camera_status = DeviceHealthState.DEGRADED
        cam.unreliable_detections_halted = True
        cam.blur_score = max(10.0, cam.blur_score * 0.3)
        cam.last_heartbeat = datetime.now(timezone.utc).isoformat()

        ticket = self._ensure_maintenance_ticket(cam, reason=reason)
        cam.active_maintenance_ticket_id = ticket.ticket_id
        return cam

    def _ensure_maintenance_ticket(self, camera: CameraTelemetry, reason: str) -> MaintenanceTicket:
        if camera.active_maintenance_ticket_id and camera.active_maintenance_ticket_id in self._tickets:
            return self._tickets[camera.active_maintenance_ticket_id]

        import uuid
        now_iso = datetime.now(timezone.utc).isoformat()
        ticket_id = f"TKT-CAM-{uuid.uuid4().hex[:6].upper()}"
        ticket = MaintenanceTicket(
            ticket_id=ticket_id,
            camera_id=camera.camera_id,
            bus_id=camera.bus_id,
            issue_type="LENS_CLEANING_AND_OPTICAL_REALIGNMENT",
            severity="HIGH",
            status="OPEN",
            created_at=now_iso,
            reason=f"CAMERA DEGRADED: {reason}. Unreliable computer vision detections halted.",
            halted_detections=True,
            assigned_technician="Auto-Assigned Depot Dispatch",
        )
        self._tickets[ticket_id] = ticket
        camera.active_maintenance_ticket_id = ticket_id
        return ticket

    def list_maintenance_tickets(self) -> List[MaintenanceTicket]:
        return list(self._tickets.values())

    def get_summary(self) -> Dict[str, Any]:
        cams = list(self._devices.values())
        total = len(cams)
        healthy = sum(1 for c in cams if c.camera_status == DeviceHealthState.HEALTHY)
        warning = sum(1 for c in cams if c.camera_status == DeviceHealthState.WARNING)
        degraded = sum(1 for c in cams if c.camera_status == DeviceHealthState.DEGRADED)
        offline = sum(1 for c in cams if c.camera_status == DeviceHealthState.OFFLINE)
        halted = sum(1 for c in cams if c.unreliable_detections_halted)

        return {
            "total_monitored_cameras": total,
            "healthy_count": healthy,
            "warning_count": warning,
            "degraded_count": degraded,
            "offline_count": offline,
            "detections_halted_count": halted,
            "active_maintenance_tickets": len(self._tickets),
            "fleet_average_fps": round(sum(c.fps for c in cams) / total, 1) if total else 0.0,
            "fleet_average_temp_celsius": round(sum(c.temperature_celsius for c in cams if c.temperature_celsius > 0) / max(1, total - offline), 1),
        }


# Singleton
_health_service: Optional[CameraHealthService] = None


def get_camera_health_service() -> CameraHealthService:
    global _health_service
    if _health_service is None:
        _health_service = CameraHealthService()
    return _health_service
