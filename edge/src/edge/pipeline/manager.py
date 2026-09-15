"""
Pipeline Manager
================
Orchestrates the full edge AI pipeline for a single camera channel:

  VideoCapture → Frame Sampling → Quality Check → YOLO Inference
  → Tracking → Event Detection → GPS Stamp → Local Buffer → API Send

Runs in a background thread per camera; exposes `SimulatorManager` which
coordinates up to 4 camera pipelines and broadcasts stats over a shared
asyncio queue consumed by the WebSocket router.
"""

import asyncio
import base64
import io
import logging
import queue
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

import httpx

from ..gps_simulator import GPSSimulator
from ..event_detector import EventDetector
from ..local_buffer import LocalBuffer
from ..road_defect import RoadDefectDetector, DetectorMode
from ..vehicle import VehicleProcessor, VehicleDetectorMode
from ..traffic import RoadSegmentManager, CongestionDetector
from ..pedestrian import PedestrianRiskDetector
from ..incident import IncidentAnomalyDetector, RollingFrameBuffer
from ..network_manager import NetworkManager, get_network_manager

logger = logging.getLogger("pipeline.manager")

# ── Inference backend ─────────────────────────────────────────────────────────
try:
    from ultralytics import YOLO as _YOLO
    _YOLO_AVAILABLE = True
except ImportError:
    _YOLO_AVAILABLE = False
    logger.warning("ultralytics not installed – using mock detector")


class _MockDetector:
    """Returns random plausible detections for demo/testing."""
    _LABELS = ["car", "truck", "bus", "person", "motorcycle", "bicycle",
               "stop sign", "traffic light", "pothole"]

    def detect(self, frame: np.ndarray):
        import random
        n = random.randint(0, 6)
        h, w = frame.shape[:2]
        results = []
        for _ in range(n):
            label = random.choice(self._LABELS)
            conf = round(random.uniform(0.45, 0.95), 2)
            x1 = random.randint(0, w - 60)
            y1 = random.randint(0, h - 60)
            x2 = x1 + random.randint(30, min(120, w - x1))
            y2 = y1 + random.randint(30, min(120, h - y1))
            results.append((label, conf, [x1, y1, x2, y2]))
        return results


class _YOLODetector:
    def __init__(self, model_path: str = "yolov8n.pt"):
        self._model = _YOLO(model_path)

    def detect(self, frame: np.ndarray):
        results = self._model(frame, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                label = r.names[int(box.cls)]
                conf = float(box.conf)
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                detections.append((label, conf, [x1, y1, x2, y2]))
        return detections


# ── Frame quality check ───────────────────────────────────────────────────────

def _quality_ok(frame: np.ndarray, blur_threshold: float = 80.0) -> bool:
    """Reject blurry or black frames."""
    if frame is None or frame.size == 0:
        return False
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if gray.mean() < 5:           # nearly black
        return False
    if cv2.Laplacian(gray, cv2.CV_64F).var() < blur_threshold:
        return False
    return True


def _frame_to_b64_jpeg(frame: np.ndarray, quality: int = 70) -> str:
    """Encode a frame as base-64 JPEG string."""
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf.tobytes()).decode()


# ── Single-camera pipeline ────────────────────────────────────────────────────

class CameraPipeline(threading.Thread):
    """
    Background thread that reads frames from a video source and runs the AI
    pipeline. Results (stats + events) are pushed to `stats_queue`.
    """

    CAMERAS = ["FRONT", "REAR", "LEFT", "RIGHT"]

    def __init__(
        self,
        bus_id: str,
        route_id: str,
        camera_position: str,         # FRONT / REAR / LEFT / RIGHT
        video_source,                  # path string or int (webcam)
        stats_queue: queue.Queue,
        api_base_url: str,
        api_token: Optional[str],
        frame_sample_rate: int = 5,   # process every Nth frame
        speed_kmh: float = 30.0,
        defect_mode: DetectorMode = DetectorMode.MODE_B,
        road_defect_model_path: str = "road_defect_yolov8.pt",
        network_manager: Optional[NetworkManager] = None,
    ):
        super().__init__(daemon=True)
        self.name = f"pipeline-{camera_position}"
        self._bus_id = bus_id
        self._camera_position = camera_position
        self._source = video_source
        self._stats_queue = stats_queue
        self._api_base = api_base_url.rstrip("/")
        self._api_token = api_token
        self._sample_rate = frame_sample_rate

        self._gps = GPSSimulator(route_id=route_id, speed_kmh=speed_kmh)
        self._detector = _YOLODetector() if _YOLO_AVAILABLE else _MockDetector()
        self._event_detector = EventDetector(bus_id=bus_id, camera_position=camera_position)
        self._road_defect_detector = RoadDefectDetector(
            camera_id=camera_position,
            bus_id=bus_id,
            mode=defect_mode,
            model_path=road_defect_model_path,
        )
        self._vehicle_processor = VehicleProcessor(
            camera_id=camera_position,
            bus_id=bus_id,
            route_id=route_id,
            mode=VehicleDetectorMode.MODE_B,
        )
        self._road_segments = RoadSegmentManager()
        self._congestion_detector = CongestionDetector()
        self._pedestrian_detector = PedestrianRiskDetector(camera_id=camera_position, bus_id=bus_id)
        self._rolling_frame_buffer = RollingFrameBuffer(capacity=30)
        self._incident_detector = IncidentAnomalyDetector(
            camera_id=camera_position,
            bus_id=bus_id,
            rolling_buffer=self._rolling_frame_buffer,
        )
        self._network_manager = network_manager or get_network_manager()
        self._buffer = LocalBuffer(sqlite_queue=self._network_manager.queue)

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused by default

        # Metrics (updated each processed frame)
        self._fps_window: deque = deque(maxlen=30)
        self._events_generated = 0
        self._objects_detected = 0

    # ── Control ───────────────────────────────────────────────────────────────

    def stop(self):
        self._stop_event.set()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    @property
    def is_running(self) -> bool:
        return self.is_alive() and not self._stop_event.is_set()

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        cap = cv2.VideoCapture(self._source)
        if not cap.isOpened():
            logger.error(f"[{self._camera_position}] Cannot open source: {self._source}")
            return

        logger.info(f"[{self._camera_position}] Pipeline started.")
        frame_idx = 0
        prev_t = time.time()

        try:
            while not self._stop_event.is_set():
                self._pause_event.wait()  # blocks while paused

                ret, frame = cap.read()
                if not ret:
                    # Loop video file back to start
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                frame_idx += 1
                now = time.time()
                dt = now - prev_t
                prev_t = now

                # Update GPS
                lat, lon, bearing = self._gps.update(dt)
                gps = {"lat": round(lat, 6), "lon": round(lon, 6), "bearing_deg": round(bearing, 1)}

                # FPS calculation
                self._fps_window.append(dt)
                fps = len(self._fps_window) / max(sum(self._fps_window), 1e-6)

                # ── Sample every Nth frame ────────────────────────────────────
                if frame_idx % self._sample_rate != 0:
                    continue

                # ── Quality check + road defect pipeline ─────────────────────
                # Road defect detector handles quality internally and emits
                # CAMERA_DEGRADED events when the frame is unusable.
                road_defect_events = self._road_defect_detector.process_frame(frame, gps)

                # Separate CAMERA_DEGRADED from regular defect events
                degraded_events = [e for e in road_defect_events if e["event_type"] == "CAMERA_DEGRADED"]
                defect_events   = [e for e in road_defect_events if e["event_type"] != "CAMERA_DEGRADED"]

                # If camera is degraded, skip general inference for this frame
                if degraded_events:
                    for evt in degraded_events:
                        self._buffer.push(evt)
                        self._send_event(evt)
                    continue

                # ── Inference (general object detection) ──────────────────────
                t_inf_start = time.time()
                detections = self._detector.detect(frame)
                inference_ms = round((time.time() - t_inf_start) * 1000, 1)
                self._objects_detected = len(detections)

                # ── General event detection ───────────────────────────────────
                frame_b64 = _frame_to_b64_jpeg(frame) if detections else None
                general_events = self._event_detector.process(detections, gps, frame_b64=frame_b64)

                # ── Vehicle detection + tracking ──────────────────────────────
                vehicle_events = self._vehicle_processor.process_frame(
                    frame=frame, gps=gps, timestamp=datetime.now(timezone.utc).isoformat()
                )

                # ── Traffic bottleneck & congestion detection ──────────────────
                congestion_events = []
                vehicle_snap = self._vehicle_processor.current_snapshot()
                nearest_seg = self._road_segments.nearest(gps.get("lat", 0.0), gps.get("lon", 0.0))
                seg_id = nearest_seg.segment_id if nearest_seg else "DEL_01"

                densities = [d.get("density_score", 0.0) for d in vehicle_snap.get("density", [])]
                avg_density = sum(densities) / len(densities) if densities else 0.2
                active_v_count = vehicle_snap.get("active_tracks", 0)
                avg_speed = vehicle_snap.get("avg_speed_kmh", {}).get("all", 35.0)

                c_event = self._congestion_detector.evaluate(
                    vehicle_count=active_v_count,
                    density=avg_density,
                    average_speed=avg_speed,
                    road_segment=seg_id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    gps=gps,
                    bus_id=self._bus_id,
                    camera_id=self._camera_position,
                )
                if c_event:
                    congestion_events.append(c_event.to_dict())

                # ── Pedestrian safety & vulnerable risk detection ─────────────
                ped_events, zone_density = self._pedestrian_detector.process_frame(
                    frame=frame,
                    detections=detections,
                    gps=gps,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                ped_event_dicts = [e.to_dict() for e in ped_events]

                # ── Incident & hit-and-run anomaly detection ──────────────────
                # Extract tracked vehicle representations
                active_tracks_list = vehicle_snap.get("tracks", []) if "tracks" in vehicle_snap else []
                if not active_tracks_list:
                    active_tracks_list = [
                        {
                            "track_id": i + 1,
                            "class": det[0],
                            "speed_kmh": 32.0,
                            "bbox": det[2],
                            "heading_deg": gps.get("bearing_deg", 0.0),
                        }
                        for i, det in enumerate(detections)
                        if det[0] in ("car", "bus", "truck", "motorcycle", "van")
                    ]

                incident_events = self._incident_detector.process_frame(
                    frame=frame,
                    tracks=active_tracks_list,
                    gps=gps,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    frame_idx=frame_idx,
                )

                # ── Merge all events ──────────────────────────────────────────
                all_events = defect_events + general_events + vehicle_events + congestion_events + ped_event_dicts + incident_events
                self._events_generated += len(all_events)

                # ── Send or buffer ───────────────────────────────────────────
                for evt in all_events:
                    self._send_event(evt)

                # ── Publish stats ─────────────────────────────────────────────
                vehicle_snap = self._vehicle_processor.current_snapshot()
                stats = {
                    "bus_id":           self._bus_id,
                    "camera":           self._camera_position,
                    "fps":              round(fps, 1),
                    "inference_ms":     inference_ms,
                    "objects_detected": self._objects_detected,
                    "events_generated": self._events_generated,
                    "gps":              gps,
                    "timestamp":        datetime.now(timezone.utc).isoformat(),
                    "vehicle_counts":   vehicle_snap.get("counts", {}),
                    "avg_speed_kmh":    vehicle_snap.get("avg_speed_kmh", {}),
                    "vehicle_density":  vehicle_snap.get("density", []),
                    "active_tracks":    vehicle_snap.get("active_tracks", 0),
                    "road_segment":     seg_id,
                    "zone_density":     zone_density,
                    "incident_alerts":  len([e for e in incident_events if e.get("event_type") == "POSSIBLE_INCIDENT"]),
                    "network_state":    self._network_manager.current_state,
                    "buffered_events":  self._network_manager.queue.pending_count(),
                    "network_indicator": self._network_manager.get_status_text(),
                    "network_indicator_single": self._network_manager.get_status_single_line(),
                }
                try:
                    self._stats_queue.put_nowait(stats)
                except queue.Full:
                    pass

        finally:
            cap.release()
            logger.info(f"[{self._camera_position}] Pipeline stopped.")

    def _send_event(self, event: Dict[str, Any]):
        """POST event JSON to the central API. Diverts to local SQLite queue when offline or if send fails."""
        if self._network_manager.is_offline():
            logger.debug(f"[{self._camera_position}] Edge offline: buffering event {event.get('event_id')} locally.")
            self._buffer.push(event)
            return

        headers = {"Content-Type": "application/json"}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"

        if event.get("event_type") == "congestion_event":
            url = f"{self._api_base}/api/v1/congestion/events"
        elif event.get("event_type") == "PEDESTRIAN_RISK":
            url = f"{self._api_base}/api/v1/pedestrian/events"
        elif event.get("event_type") == "POSSIBLE_INCIDENT":
            url = f"{self._api_base}/api/v1/incidents/events"
        else:
            url = f"{self._api_base}/api/v1/events"

        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.post(url, json=event, headers=headers)
                if r.status_code not in (200, 201):
                    logger.warning(f"Event send failed ({r.status_code}), buffering to SQLite queue.")
                    self._buffer.push(event)
        except Exception as exc:
            logger.warning(f"Event send error: {exc}, buffering to SQLite queue.")
            self._buffer.push(event)


# ── Simulator Manager ─────────────────────────────────────────────────────────

class SimulatorManager:
    """
    Coordinates up to 4 CameraPipelines (one per camera position).
    Exposes start / pause / stop controls, shared stats queue, and store-and-forward retransmission.
    """

    def __init__(self, network_manager: Optional[NetworkManager] = None):
        self._pipelines: Dict[str, CameraPipeline] = {}
        self.stats_queue: queue.Queue = queue.Queue(maxsize=200)
        self.is_running = False
        self.network_manager = network_manager or get_network_manager()
        self._api_base_url: str = ""
        self._api_token: Optional[str] = None

    def _drain_sender(self, event: Dict[str, Any]) -> bool:
        """Transmits an offline-buffered event to the Central API."""
        if not self._api_base_url:
            return False
        headers = {"Content-Type": "application/json"}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"

        ev_type = event.get("event_type")
        if ev_type == "congestion_event":
            url = f"{self._api_base_url}/api/v1/congestion/events"
        elif ev_type == "PEDESTRIAN_RISK":
            url = f"{self._api_base_url}/api/v1/pedestrian/events"
        elif ev_type == "POSSIBLE_INCIDENT":
            url = f"{self._api_base_url}/api/v1/incidents/events"
        else:
            url = f"{self._api_base_url}/api/v1/events"

        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.post(url, json=event, headers=headers)
                return r.status_code in (200, 201)
        except Exception:
            return False

    # ── Control methods ───────────────────────────────────────────────────────

    def start(
        self,
        bus_id: str,
        route_id: str,
        camera_sources: Dict[str, Any],   # {"FRONT": "/path/or/0", ...}
        api_base_url: str,
        api_token: Optional[str] = None,
        frame_sample_rate: int = 5,
        speed_kmh: float = 30.0,
    ):
        """Start pipelines for each provided camera source and initiate queue drain worker."""
        self.stop()  # clean up any existing pipelines
        self._pipelines.clear()
        self._api_base_url = api_base_url.rstrip("/")
        self._api_token = api_token

        for position, source in camera_sources.items():
            pipeline = CameraPipeline(
                bus_id=bus_id,
                route_id=route_id,
                camera_position=position.upper(),
                video_source=source,
                stats_queue=self.stats_queue,
                api_base_url=api_base_url,
                api_token=api_token,
                frame_sample_rate=frame_sample_rate,
                speed_kmh=speed_kmh,
                network_manager=self.network_manager,
            )
            self._pipelines[position.upper()] = pipeline
            pipeline.start()

        self.network_manager.start_drain_worker(self._drain_sender)
        self.is_running = True
        logger.info(f"SimulatorManager: started {len(self._pipelines)} pipelines with store-and-forward.")

    def pause(self):
        for p in self._pipelines.values():
            p.pause()
        logger.info("SimulatorManager: paused.")

    def resume(self):
        for p in self._pipelines.values():
            p.resume()
        logger.info("SimulatorManager: resumed.")

    def stop(self):
        self.network_manager.stop_drain_worker()
        for p in self._pipelines.values():
            p.stop()
        for p in self._pipelines.values():
            p.join(timeout=3)
        self._pipelines.clear()
        self.is_running = False
        logger.info("SimulatorManager: stopped.")

    def flush_buffered_events(self) -> int:
        """Manually trigger draining of the SQLite buffer."""
        return self.network_manager.drain_queue_batch(self._drain_sender)

    def status(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "active_cameras": list(self._pipelines.keys()),
            "pipeline_alive": {k: v.is_alive() for k, v in self._pipelines.items()},
            "network": self.network_manager.get_status_dict(),
        }

