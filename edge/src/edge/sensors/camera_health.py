"""
Camera Health & Degradation Monitor (Step 40)
==============================================
Monitors physical and optical sensor health on edge buses.
Detects the 5 primary field failure modes:
  1. Camera disconnected (no video signal / USB bus drop)
  2. Camera dirty (dust, mud splatter, salt spray)
  3. Camera blocked (baggage, sticker, physical obstruction)
  4. Camera blurry (out of focus, condensation, optical vibration)
  5. Camera misaligned (pointing at road sky, bumped out of angle)

When any failure condition is triggered, displays:
  ⚠️ Camera degraded — maintenance required.
and halts unreliable downstream AI inferences to prevent false positives.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional


class CameraFaultType(str, Enum):
    DISCONNECTED = "Camera disconnected"
    DIRTY        = "Camera dirty"
    BLOCKED      = "Camera blocked"
    BLURRY       = "Camera blurry"
    MISALIGNED   = "Camera misaligned"
    HEALTHY      = "Camera healthy"


DEGRADED_ALERT_MESSAGE = "⚠️ Camera degraded — maintenance required."


class CameraHealthState:
    HEALTHY  = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE  = "OFFLINE"


class CameraHealthMonitor:
    """
    Evaluates physical connectivity and optical frame characteristics.
    """

    def __init__(
        self,
        camera_id: str = "CAM-FRONT-01",
        bus_id: str = "BUS-101",
        blur_variance_threshold: float = 45.0,
        obstruction_threshold_pct: float = 25.0,
        tilt_tolerance_deg: float = 12.0,
    ):
        self.camera_id = camera_id
        self.bus_id = bus_id
        self.blur_variance_threshold = blur_variance_threshold
        self.obstruction_threshold_pct = obstruction_threshold_pct
        self.tilt_tolerance_deg = tilt_tolerance_deg

    def evaluate_health(
        self,
        is_connected: bool = True,
        lens_dirt_pct: float = 0.0,
        is_blocked: bool = False,
        blur_variance: float = 120.0,
        misalignment_angle_deg: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Detects:
          - Camera disconnected
          - Camera dirty
          - Camera blocked
          - Camera blurry
          - Camera misaligned
        Returns structured diagnostic payload with warning banner if degraded.
        """
        faults: List[CameraFaultType] = []

        if not is_connected:
            faults.append(CameraFaultType.DISCONNECTED)

        if lens_dirt_pct >= self.obstruction_threshold_pct:
            faults.append(CameraFaultType.DIRTY)

        if is_blocked:
            faults.append(CameraFaultType.BLOCKED)

        if blur_variance < self.blur_variance_threshold:
            faults.append(CameraFaultType.BLURRY)

        if abs(misalignment_angle_deg) > self.tilt_tolerance_deg:
            faults.append(CameraFaultType.MISALIGNED)

        is_degraded = len(faults) > 0

        if not is_connected:
            status = CameraHealthState.OFFLINE
        elif is_degraded:
            status = CameraHealthState.DEGRADED
        else:
            status = CameraHealthState.HEALTHY

        return {
            "camera_id": self.camera_id,
            "bus_id": self.bus_id,
            "status": status,
            "is_degraded": is_degraded,
            "detected_faults": [f.value for f in faults],
            "alert_banner": DEGRADED_ALERT_MESSAGE if is_degraded else None,
            "maintenance_required": is_degraded,
            "reliable_ai_inferences_allowed": not is_degraded,
        }
