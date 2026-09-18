"""
Tests for Phase 16 (Reliability & Field Self-Healing)
=====================================================
Verifies:
  - Step 39: Watchdog crash auto-restart (AI crash -> Watchdog detects -> Restart -> Continue)
  - Step 40: Camera Health Monitoring (Disconnected, dirty, blocked, blurry, misaligned -> Warning banner)
"""

import pytest
from edge.pipeline.watchdog import EdgePipelineWatchdog, WatchdogStatus
from edge.sensors.camera_health import CameraHealthMonitor, DEGRADED_ALERT_MESSAGE


def test_step39_watchdog_ai_crash_restart_and_recovery():
    """
    Step 39: If AI crashes:
      AI crash -> Watchdog detects -> Restart -> Continue operation
    """
    watchdog = EdgePipelineWatchdog(heartbeat_timeout_s=0.5)

    restart_called = []
    watchdog.register_restart_hook(lambda: restart_called.append(True))

    # Trigger AI crash
    crash_record = watchdog.trigger_crash("Simulated YOLOv8 Segfault / CUDA OOM")
    assert crash_record["recovered"] is True
    assert len(restart_called) == 1
    assert watchdog.get_crash_history()[0]["reason"] == "Simulated YOLOv8 Segfault / CUDA OOM"

    # Ping heartbeat after restart -> operational continuity
    watchdog.ping_heartbeat()
    status = watchdog.check_health()
    assert status["is_healthy"] is True
    assert status["restart_count"] == 1


def test_step40_camera_health_degradation_modes():
    """
    Step 40: Detect:
      - Camera disconnected
      - Camera dirty
      - Camera blocked
      - Camera blurry
      - Camera misaligned
    Then show:
      ⚠️ Camera degraded — maintenance required.
    """
    monitor = CameraHealthMonitor(camera_id="CAM-FRONT", bus_id="BUS-101")

    # 1. Healthy state
    h = monitor.evaluate_health()
    assert h["status"] == "HEALTHY"
    assert h["is_degraded"] is False
    assert h["alert_banner"] is None

    # 2. Camera disconnected
    r_disc = monitor.evaluate_health(is_connected=False)
    assert r_disc["status"] == "OFFLINE"
    assert "Camera disconnected" in r_disc["detected_faults"]
    assert r_disc["alert_banner"] == DEGRADED_ALERT_MESSAGE

    # 3. Camera dirty
    r_dirt = monitor.evaluate_health(lens_dirt_pct=30.0)
    assert r_dirt["status"] == "DEGRADED"
    assert "Camera dirty" in r_dirt["detected_faults"]
    assert r_dirt["alert_banner"] == DEGRADED_ALERT_MESSAGE

    # 4. Camera blocked
    r_block = monitor.evaluate_health(is_blocked=True)
    assert r_block["status"] == "DEGRADED"
    assert "Camera blocked" in r_block["detected_faults"]
    assert r_block["alert_banner"] == DEGRADED_ALERT_MESSAGE

    # 5. Camera blurry
    r_blur = monitor.evaluate_health(blur_variance=25.0)
    assert r_blur["status"] == "DEGRADED"
    assert "Camera blurry" in r_blur["detected_faults"]
    assert r_blur["alert_banner"] == DEGRADED_ALERT_MESSAGE

    # 6. Camera misaligned
    r_mis = monitor.evaluate_health(misalignment_angle_deg=19.0)
    assert r_mis["status"] == "DEGRADED"
    assert "Camera misaligned" in r_mis["detected_faults"]
    assert r_mis["alert_banner"] == DEGRADED_ALERT_MESSAGE
