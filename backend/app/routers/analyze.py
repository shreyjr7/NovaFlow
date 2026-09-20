"""
NovaFlow AI Road Intelligence API Router
========================================
Endpoints:
  POST /api/v1/analyze/video          - Upload and trigger asynchronous video analysis
  GET  /api/v1/jobs/{job_id}          - Poll job progress and canonical detection records
  POST /api/v1/analyze/frame          - Ingest and analyze a single live camera/dashcam frame
  GET  /api/v1/analyze/supported-classes - Inspect model classes and weights status
  GET  /api/v1/evidence/file/{filename} - Fetch generated evidence frames
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..database.session import engine
from ..models.ai_scan_entities import RoadDetection, MaintenanceTicket
from ..models.entities import BusModel, GpsTelemetry
from ..ai.annotator import annotate_frame, encode_image_jpeg
from ..ai.road_intelligence_engine import get_road_intelligence_engine
from ..ai.gemini_verifier import get_gemini_verifier
from .maintenance import create_or_associate_ticket
from ..services.evidence_manager import get_evidence_manager
from ..services.video_analyzer_service import (
    EVIDENCE_DIR,
    get_video_analyzer_service,
)

logger = logging.getLogger("routers.analyze")
router = APIRouter()

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
MAX_VIDEO_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB


# ── Schemas ───────────────────────────────────────────────────────────────────

class SingleFrameRequest(BaseModel):
    frame_b64: str = Field(..., description="Base64 encoded JPEG or PNG image frame")
    bus_id: str = Field("BUS-027", description="Vehicle ID")
    route_id: str = Field("ROUTE-17", description="Route corridor")
    latitude: float = Field(12.9348, description="Current GPS latitude")
    longitude: float = Field(77.6101, description="Current GPS longitude")
    speed_kmh: Optional[float] = Field(None, description="Vehicle speed in km/h")
    heading_deg: Optional[float] = Field(None, description="Compass heading in degrees")
    timestamp: Optional[str] = Field(None, description="ISO capture timestamp")
    confidence_threshold: Optional[float] = 0.50
    persist_detections: Optional[bool] = True
    camera_status: Optional[str] = Field("ACTIVE", description="ACTIVE | STREAMING | DEGRADED | OFFLINE")
    ai_status: Optional[str] = Field("INFERENCING", description="INFERENCING | ONLINE | STANDBY | OFFLINE")
    connection_status: Optional[str] = Field("CONNECTED", description="CONNECTED | DEGRADED | DISCONNECTED")


class FrameBatchItem(BaseModel):
    frame_b64: str = Field(..., description="Base64 encoded frame")
    frame_idx: Optional[int] = 0
    timestamp: Optional[str] = None


class FrameBatchRequest(BaseModel):
    frames: List[FrameBatchItem] = Field(..., description="List of frame items")
    bus_id: str = Field("BUS-027", description="Vehicle ID")
    route_id: str = Field("ROUTE-17", description="Route corridor")
    latitude: float = Field(12.9348, description="Current GPS latitude")
    longitude: float = Field(77.6101, description="Current GPS longitude")
    speed_kmh: Optional[float] = None
    heading_deg: Optional[float] = None
    confidence_threshold: Optional[float] = 0.50
    persist_detections: Optional[bool] = True
    camera_status: Optional[str] = "ACTIVE"
    ai_status: Optional[str] = "INFERENCING"
    connection_status: Optional[str] = "CONNECTED"


def update_bus_edge_telemetry(
    bus_id: str,
    route_id: str,
    lat: float,
    lon: float,
    spd: Optional[float] = None,
    hdg: Optional[float] = None,
    camera_status: str = "ACTIVE",
    ai_status: str = "INFERENCING",
    connection_status: str = "CONNECTED",
):
    """Upserts BusModel and logs GPS breadcrumb for edge node tracking."""
    try:
        with Session(engine) as session:
            stmt = select(BusModel).where(BusModel.bus_id == bus_id)
            bus = session.exec(stmt).first()
            now = datetime.now(timezone.utc)
            if not bus:
                bus = BusModel(
                    bus_id=bus_id,
                    route_id=route_id or "R-01",
                    name=f"Connected Transit Bus ({bus_id})",
                    current_lat=lat,
                    current_lon=lon,
                    latitude=lat,
                    longitude=lon,
                    speed_kmh=spd or 0.0,
                    speed=spd or 0.0,
                    bearing_deg=hdg or 0.0,
                    heading=hdg or 0.0,
                    camera_status=camera_status,
                    AI_status=ai_status,
                    connection_status=connection_status,
                    last_heartbeat=now,
                    timestamp=now,
                )
                session.add(bus)
            else:
                bus.sync_kinematics(lat=lat, lon=lon, spd=spd or 0.0, hdg=hdg or 0.0, ts=now)
                bus.camera_status = camera_status
                bus.AI_status = ai_status
                bus.connection_status = connection_status
                if route_id:
                    bus.route_id = route_id
                session.add(bus)

            # Record telemetry ping
            ping = GpsTelemetry(
                bus_id=bus_id,
                route_id=route_id or "R-01",
                latitude=lat,
                longitude=lon,
                speed_kmh=spd or 0.0,
                heading=hdg or 0.0,
                timestamp=now,
            )
            session.add(ping)
            session.commit()
    except Exception as b_err:
        logger.debug(f"Telemetry update note: {b_err}")


class VideoAnalysisInitResponse(BaseModel):
    job_id: str
    status: str
    message: str
    video_file_name: str
    sample_fps: float
    confidence_threshold: float


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/analyze/supported-classes", tags=["AI Vision Engine"])
def get_supported_classes():
    """Returns the list of classes supported by the loaded YOLO model and custom weight configurations."""
    service = get_video_analyzer_service()
    return service.get_supported_classes()


@router.get("/scan/sample-video", tags=["AI Vision Engine"], summary="Pre-recorded Indian road video for judge demo")
@router.get("/analyze/sample-video", tags=["AI Vision Engine"], summary="Pre-recorded Indian road video for judge demo")
async def get_sample_road_video():
    """
    Serves the pre-recorded Indian road inspection video (Phase 13 Judge Demo Mode)
    for 1-click loading and testing.
    """
    candidates = [
        Path("test_road_sample.mp4").resolve(),
        Path(__file__).resolve().parent.parent.parent.parent / "test_road_sample.mp4",
        Path(__file__).resolve().parent.parent / "data" / "test_road_sample.mp4",
        Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "public" / "sample_indian_road.mp4",
    ]
    for p in candidates:
        if p.exists():
            return FileResponse(
                path=str(p),
                media_type="video/mp4",
                filename="sample_indian_road.mp4",
            )
    raise HTTPException(status_code=404, detail="Sample road video not found.")


@router.post(
    "/analyze/video",
    response_model=VideoAnalysisInitResponse,
    tags=["AI Vision Engine"],
)
async def analyze_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(..., description="Road video file (MP4, MOV, AVI, WebM)"),
    sample_fps: float = Form(1.0, description="Frames sampled per second of video"),
    confidence_threshold: float = Form(0.50, description="Minimum detection confidence"),
    iou_threshold: float = Form(0.35, description="IoU association threshold for tracking"),
    confirmation_frames: int = Form(2, description="Consecutive frames required to confirm detection"),
    bus_id: str = Form("BUS-027"),
    route_id: str = Form("ROUTE-17"),
    city: str = Form("Bengaluru"),
):
    """
    Uploads a road video file and starts an asynchronous sampling and AI detection worker.
    """
    filename = video.filename or "uploaded_road_video.mp4"
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}",
        )

    service = get_video_analyzer_service()

    # Save video to temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(temp_fd, "wb") as f_out:
            bytes_written = 0
            while chunk := await video.read(1024 * 1024):  # 1MB chunks
                bytes_written += len(chunk)
                if bytes_written > MAX_VIDEO_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Video file exceeds maximum allowed limit of 500 MB.",
                    )
                f_out.write(chunk)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to receive video: {e}")

    # Register Job
    job_id = service.create_job(
        file_name=filename,
        bus_id=bus_id,
        route_id=route_id,
        city=city,
        sample_fps=max(0.5, min(10.0, sample_fps)),
        confidence_threshold=max(0.1, min(0.99, confidence_threshold)),
        iou_threshold=max(0.1, min(0.9, iou_threshold)),
        confirmation_frames=max(1, confirmation_frames),
    )

    # Launch background processing task
    background_tasks.add_task(service.process_video_async, job_id, temp_path)

    return VideoAnalysisInitResponse(
        job_id=job_id,
        status="QUEUED",
        message="Video successfully queued for AI frame sampling and detection.",
        video_file_name=filename,
        sample_fps=sample_fps,
        confidence_threshold=confidence_threshold,
    )


@router.get("/analyze/health", tags=["AI Vision Engine"])
def get_ai_health():
    """Health check for AI Vision Engine and model availability."""
    service = get_video_analyzer_service()
    return {
        "status": "HEALTHY",
        "service": "NovaFlow AI Vision Engine",
        "model_weights": service.model_engine.weights_path,
        "ultralytics_available": service.model_engine._ultralytics_available,
        "is_custom_model": service.model_engine.is_custom_model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/jobs/{job_id}/cancel", tags=["AI Vision Engine"])
def cancel_analysis_job(job_id: str):
    """Cancels an ongoing video analysis job."""
    service = get_video_analyzer_service()
    job = service.get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    if job.get("status") in ("COMPLETED", "FAILED"):
        return {
            "job_id": job_id,
            "status": job["status"],
            "message": f"Job is already {job['status'].lower()}.",
        }
    service.cancel_job(job_id)
    return {
        "job_id": job_id,
        "status": "CANCELLED",
        "message": "Video analysis job successfully cancelled.",
    }


@router.get("/jobs/{job_id}", tags=["AI Vision Engine"])
def get_job_status(job_id: str):
    """
    Polls the progress and results of a video analysis job.
    """
    service = get_video_analyzer_service()
    status_data = service.get_job_status(job_id)

    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    return status_data


@router.post("/analyze/frame", tags=["AI Vision Engine"])
async def analyze_single_frame(req: SingleFrameRequest):
    """
    Analyzes a single live dashcam or mobile camera frame with the YOLO vision engine,
    reporting inference latency, saving evidence for confirmed hazards, and syncing with GIS.
    Integrates Phase 8 bus telemetry, Phase 9 road intelligence, Phase 10 Gemini verification,
    and Phase 11 municipal ticket pipeline.
    """
    if cv2 is None or np is None:
        raise HTTPException(status_code=500, detail="OpenCV/NumPy unavailable.")

    t_start = time.perf_counter()

    # Update Edge Bus Telemetry (Phase 8)
    update_bus_edge_telemetry(
        bus_id=req.bus_id,
        route_id=req.route_id,
        lat=req.latitude,
        lon=req.longitude,
        spd=req.speed_kmh,
        hdg=req.heading_deg,
        camera_status=req.camera_status or "ACTIVE",
        ai_status=req.ai_status or "INFERENCING",
        connection_status=req.connection_status or "CONNECTED",
    )

    # Decode base64 frame
    try:
        raw_b64 = req.frame_b64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(raw_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("cv2.imdecode returned None")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {e}")

    h, w = frame.shape[:2]
    service = get_video_analyzer_service()
    detections = service.model_engine.detect(
        frame,
        custom_conf=req.confidence_threshold,
    )

    latency_ms = round((time.perf_counter() - t_start) * 1000, 1)

    # Annotated image
    annotated = annotate_frame(frame, detections)
    annotated_b64 = base64.b64encode(encode_image_jpeg(annotated)).decode("ascii")

    capture_time = req.timestamp or datetime.now(timezone.utc).isoformat()
    det_dicts = [d.to_dict() for d in detections]

    # Road Intelligence Engine (Phase 9)
    intel_engine = get_road_intelligence_engine()
    congestion = intel_engine.evaluate_traffic_congestion(
        det_dicts,
        bus_speed_kmh=req.speed_kmh,
        frame_width=w,
        frame_height=h,
    )
    ped_risk = intel_engine.evaluate_pedestrian_risk(
        det_dicts,
        frame_width=w,
        frame_height=h,
    )
    incidents = intel_engine.evaluate_incidents(
        det_dicts,
        bus_speed_kmh=req.speed_kmh,
        frame_width=w,
        frame_height=h,
    )

    gemini_verifier = get_gemini_verifier()
    tickets_spawned = []

    # If detections were found and persistence is enabled, save evidence and persist to RoadDetection
    if req.persist_detections and detections:
        evidence_mgr = get_evidence_manager()

        for i, (det_obj, d_dict) in enumerate(zip(detections, det_dicts)):
            det_uuid = uuid.uuid4()
            d_dict["id"] = f"DET-{det_uuid.hex[:8].upper()}"
            d_dict["bus_id"] = req.bus_id
            d_dict["route_id"] = req.route_id
            d_dict["latitude"] = req.latitude
            d_dict["longitude"] = req.longitude
            d_dict["lat"] = req.latitude
            d_dict["lng"] = req.longitude
            d_dict["timestamp"] = capture_time
            d_dict["speed_kmh"] = req.speed_kmh
            d_dict["heading_deg"] = req.heading_deg
            d_dict["status"] = "CONFIRMED"
            d_dict["condition_type"] = "DIRECT"

            # Multi-factor Severity Scoring (Phase 9)
            norm_bbox = {
                "x1": det_obj.bbox[0] / max(1, w),
                "y1": det_obj.bbox[1] / max(1, h),
                "x2": det_obj.bbox[2] / max(1, w),
                "y2": det_obj.bbox[3] / max(1, h),
            }
            computed_sev, sev_score = intel_engine.compute_severity_score(
                confidence=det_obj.confidence,
                bounding_box=norm_bbox,
                persistence_frames=1,
                frame_width=w,
                frame_height=h,
            )
            d_dict["severity"] = computed_sev
            d_dict["severity_score"] = sev_score

            # Secondary Multimodal Verification (Phase 10)
            is_gemini_verified = False
            ver_notes = None
            if gemini_verifier.should_verify(det_obj.confidence, det_obj.class_name):
                try:
                    g_res = await gemini_verifier.verify_evidence_frame(
                        frame_bytes=img_bytes,
                        preliminary_type=det_obj.class_name,
                        preliminary_confidence=det_obj.confidence,
                        preliminary_severity=computed_sev,
                        job_id=f"LIVE-{req.bus_id}",
                    )
                    if g_res.is_verified:
                        is_gemini_verified = True
                        d_dict["severity"] = g_res.severity
                        computed_sev = g_res.severity
                        ver_notes = f"Gemini: {g_res.reasoning}"
                        d_dict["verification_notes"] = ver_notes
                except Exception as g_err:
                    logger.debug(f"Gemini verification call note: {g_err}")

            d_dict["is_multimodal_verified"] = is_gemini_verified

            try:
                bundle = evidence_mgr.save_detection_evidence(
                    job_id="LIVE-CAM",
                    track_id=i + 1,
                    frame_number=1,
                    clean_frame=frame,
                    detections=detections,
                    target_box=det_obj.bbox,
                    db_detection_id=det_uuid,
                )
                d_dict["evidence_path"] = bundle.original_url
                d_dict["original_evidence_path"] = bundle.original_url
                d_dict["annotated_evidence_path"] = bundle.annotated_url
                d_dict["thumbnail_path"] = bundle.thumbnail_url

                with Session(engine) as session:
                    db_det = RoadDetection(
                        id=det_uuid,
                        bus_id=req.bus_id,
                        type=det_obj.class_name.upper(),
                        confidence=round(det_obj.confidence, 4),
                        severity=computed_sev,
                        latitude=req.latitude,
                        longitude=req.longitude,
                        location_accuracy=2.5,
                        frame_number=1,
                        track_id=i + 1,
                        bounding_box_json=json.dumps(norm_bbox),
                        evidence_path=bundle.original_url,
                        annotated_evidence_path=bundle.annotated_url,
                        thumbnail_path=bundle.thumbnail_url,
                        source_model=service.model_engine.weights_path,
                        status="CONFIRMED",
                        condition_type="DIRECT",
                        is_multimodal_verified=is_gemini_verified,
                        verification_notes=ver_notes,
                    )
                    session.add(db_det)
                    session.commit()
                    session.refresh(db_det)

                    # Maintenance Tickets Integration (Phase 11)
                    ticket = create_or_associate_ticket(
                        db=session,
                        detection=db_det,
                        source_bus=req.bus_id,
                    )
                    if ticket:
                        d_dict["ticket_id"] = ticket.ticket_code
                        d_dict["ticket_status"] = ticket.status
                        tickets_spawned.append(ticket.to_dict())

                    # Multi-Bus Hazard Confirmation (Phase 12)
                    try:
                        hazard, obs, is_new_h = intel_engine.record_multi_bus_observation(
                            session=session,
                            detection=db_det,
                            bus_id=req.bus_id,
                            route_id=req.route_id,
                            city="Bengaluru",
                        )
                        if hazard:
                            d_dict["persistent_hazard_id"] = str(hazard.id)
                            d_dict["independent_buses_count"] = hazard.independent_buses_count
                            d_dict["contributing_buses"] = hazard.contributing_buses
                            d_dict["persistence_badge"] = hazard.persistence_status
                            d_dict["last_detected_at"] = hazard.last_detected_at.isoformat() if hazard.last_detected_at else None
                    except Exception as haz_err:
                        logger.debug(f"Live camera persistent hazard note: {haz_err}")
            except Exception as e_err:
                logger.debug(f"Live camera persistence note: {e_err}")
    else:
        for d in det_dicts:
            d["latitude"] = req.latitude
            d["longitude"] = req.longitude
            d["bus_id"] = req.bus_id
            d["timestamp"] = capture_time
            d["speed_kmh"] = req.speed_kmh
            d["heading_deg"] = req.heading_deg

    return {
        "bus_id": req.bus_id,
        "route_id": req.route_id,
        "timestamp": capture_time,
        "latency_ms": latency_ms,
        "detections_count": len(detections),
        "detections": det_dicts,
        "derived_intelligence": {
            "traffic_congestion": congestion,
            "pedestrian_risk": ped_risk,
            "incidents": incidents,
        },
        "tickets_spawned": tickets_spawned,
        "gemini_verification_enabled": gemini_verifier.is_available(),
        "speed_kmh": req.speed_kmh,
        "heading_deg": req.heading_deg,
        "annotated_frame_b64": f"data:image/jpeg;base64,{annotated_b64}",
    }


@router.post("/analyze/batch", tags=["AI Vision Engine"])
async def analyze_frame_batch(req: FrameBatchRequest):
    """
    Analyzes a small batch of frames captured by a connected bus camera.
    Returns aggregated detections, annotated frames, and aggregate processing latency.
    """
    if cv2 is None or np is None:
        raise HTTPException(status_code=500, detail="OpenCV/NumPy unavailable.")

    t_start = time.perf_counter()

    # Update Edge Bus Telemetry (Phase 8)
    update_bus_edge_telemetry(
        bus_id=req.bus_id,
        route_id=req.route_id,
        lat=req.latitude,
        lon=req.longitude,
        spd=req.speed_kmh,
        hdg=req.heading_deg,
        camera_status=req.camera_status or "ACTIVE",
        ai_status=req.ai_status or "INFERENCING",
        connection_status=req.connection_status or "CONNECTED",
    )

    service = get_video_analyzer_service()
    evidence_mgr = get_evidence_manager()
    intel_engine = get_road_intelligence_engine()
    gemini_verifier = get_gemini_verifier()

    batch_results = []
    all_detections = []
    tickets_spawned = []
    total_dets_count = 0

    for item in req.frames:
        try:
            raw_b64 = item.frame_b64
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(raw_b64)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            h, w = frame.shape[:2]
            frame_t = item.timestamp or datetime.now(timezone.utc).isoformat()
            detections = service.model_engine.detect(frame, custom_conf=req.confidence_threshold)
            total_dets_count += len(detections)

            annotated = annotate_frame(frame, detections)
            annotated_b64 = base64.b64encode(encode_image_jpeg(annotated)).decode("ascii")

            frame_det_dicts = [d.to_dict() for d in detections]

            for i, (det_obj, d_dict) in enumerate(zip(detections, frame_det_dicts)):
                det_uuid = uuid.uuid4()
                d_dict["id"] = f"DET-{det_uuid.hex[:8].upper()}"
                d_dict["bus_id"] = req.bus_id
                d_dict["route_id"] = req.route_id
                d_dict["latitude"] = req.latitude
                d_dict["longitude"] = req.longitude
                d_dict["timestamp"] = frame_t
                d_dict["speed_kmh"] = req.speed_kmh
                d_dict["heading_deg"] = req.heading_deg
                d_dict["status"] = "CONFIRMED"
                d_dict["condition_type"] = "DIRECT"

                norm_bbox = {
                    "x1": det_obj.bbox[0] / max(1, w),
                    "y1": det_obj.bbox[1] / max(1, h),
                    "x2": det_obj.bbox[2] / max(1, w),
                    "y2": det_obj.bbox[3] / max(1, h),
                }
                computed_sev, sev_score = intel_engine.compute_severity_score(
                    confidence=det_obj.confidence,
                    bounding_box=norm_bbox,
                    persistence_frames=1,
                    frame_width=w,
                    frame_height=h,
                )
                d_dict["severity"] = computed_sev
                d_dict["severity_score"] = sev_score

                is_gemini_verified = False
                ver_notes = None
                if gemini_verifier.should_verify(det_obj.confidence, det_obj.class_name):
                    try:
                        g_res = await gemini_verifier.verify_evidence_frame(
                            frame_bytes=img_bytes,
                            preliminary_type=det_obj.class_name,
                            preliminary_confidence=det_obj.confidence,
                            preliminary_severity=computed_sev,
                            job_id=f"LIVE-{req.bus_id}",
                        )
                        if g_res.is_verified:
                            is_gemini_verified = True
                            d_dict["severity"] = g_res.severity
                            computed_sev = g_res.severity
                            ver_notes = f"Gemini: {g_res.reasoning}"
                            d_dict["verification_notes"] = ver_notes
                    except Exception as g_err:
                        logger.debug(f"Gemini batch verification note: {g_err}")

                d_dict["is_multimodal_verified"] = is_gemini_verified

                if req.persist_detections:
                    try:
                        bundle = evidence_mgr.save_detection_evidence(
                            job_id="LIVE-BATCH",
                            track_id=item.frame_idx or (i + 1),
                            frame_number=item.frame_idx or 1,
                            clean_frame=frame,
                            detections=detections,
                            target_box=det_obj.bbox,
                            db_detection_id=det_uuid,
                        )
                        d_dict["evidence_path"] = bundle.original_url
                        d_dict["original_evidence_path"] = bundle.original_url
                        d_dict["annotated_evidence_path"] = bundle.annotated_url
                        d_dict["thumbnail_path"] = bundle.thumbnail_url

                        with Session(engine) as session:
                            db_det = RoadDetection(
                                id=det_uuid,
                                bus_id=req.bus_id,
                                type=det_obj.class_name.upper(),
                                confidence=round(det_obj.confidence, 4),
                                severity=computed_sev,
                                latitude=req.latitude,
                                longitude=req.longitude,
                                location_accuracy=2.5,
                                frame_number=item.frame_idx or 1,
                                track_id=i + 1,
                                bounding_box_json=json.dumps(norm_bbox),
                                evidence_path=bundle.original_url,
                                annotated_evidence_path=bundle.annotated_url,
                                thumbnail_path=bundle.thumbnail_url,
                                source_model=service.model_engine.weights_path,
                                status="CONFIRMED",
                                condition_type="DIRECT",
                                is_multimodal_verified=is_gemini_verified,
                                verification_notes=ver_notes,
                            )
                            session.add(db_det)
                            session.commit()
                            session.refresh(db_det)

                            # Maintenance Ticket creation (Phase 11)
                            ticket = create_or_associate_ticket(
                                db=session,
                                detection=db_det,
                                source_bus=req.bus_id,
                            )
                            if ticket:
                                d_dict["ticket_id"] = ticket.ticket_code
                                d_dict["ticket_status"] = ticket.status
                                tickets_spawned.append(ticket.to_dict())
                    except Exception as db_err:
                        logger.debug(f"Batch detection persistence note: {db_err}")

                all_detections.append(d_dict)

            batch_results.append({
                "frame_idx": item.frame_idx,
                "timestamp": frame_t,
                "detections_count": len(detections),
                "detections": frame_det_dicts,
                "annotated_frame_b64": f"data:image/jpeg;base64,{annotated_b64}",
            })
        except Exception as f_err:
            logger.debug(f"Batch frame processing exception: {f_err}")

    # Derived Intelligence over entire batch
    congestion = intel_engine.evaluate_traffic_congestion(
        all_detections,
        bus_speed_kmh=req.speed_kmh,
    )
    ped_risk = intel_engine.evaluate_pedestrian_risk(all_detections)
    incidents = intel_engine.evaluate_incidents(all_detections, bus_speed_kmh=req.speed_kmh)

    latency_ms = round((time.perf_counter() - t_start) * 1000, 1)

    return {
        "bus_id": req.bus_id,
        "route_id": req.route_id,
        "frames_processed": len(batch_results),
        "total_detections_count": total_dets_count,
        "latency_ms": latency_ms,
        "detections": all_detections,
        "frame_results": batch_results,
        "derived_intelligence": {
            "traffic_congestion": congestion,
            "pedestrian_risk": ped_risk,
            "incidents": incidents,
        },
        "tickets_spawned": tickets_spawned,
        "gemini_verification_enabled": gemini_verifier.is_available(),
    }


@router.get("/evidence/file/{filename}", tags=["Evidence Storage"])
def get_evidence_file(filename: str):
    """Serves generated evidence, annotated frames, clean originals, and thumbnails."""
    safe_name = Path(filename).name
    # Search in EVIDENCE_DIR and its subdirectories
    possible_paths = [
        EVIDENCE_DIR / safe_name,
        EVIDENCE_DIR / "originals" / safe_name,
        EVIDENCE_DIR / "annotated" / safe_name,
        EVIDENCE_DIR / "thumbnails" / safe_name,
    ]
    for p in possible_paths:
        if p.exists():
            return FileResponse(
                p,
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=86400"},
            )
    raise HTTPException(status_code=404, detail=f"Evidence frame '{filename}' not found.")


# ── Frontend Scan Aliases (Connecting UI Directly) ───────────────────────────

@router.get("/scan/health", tags=["AI Road Scan (Frontend Alias)"])
def scan_health_alias():
    """Direct alias for frontend health check."""
    return get_ai_health()


@router.post("/scan/jobs/{job_id}/cancel", tags=["AI Road Scan (Frontend Alias)"])
def scan_cancel_alias(job_id: str):
    """Direct alias for frontend job cancellation."""
    return cancel_analysis_job(job_id)


@router.post("/scan/upload-video", tags=["AI Road Scan (Frontend Alias)"])
async def scan_upload_video_alias(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    sample_fps: float = Form(1.0),
    bus_id: str = Form("BUS-027"),
    route_id: str = Form("ROUTE-17"),
    city: str = Form("Bengaluru"),
    confidence_threshold: float = Form(0.70),
):
    """Direct alias for frontend roadScanApi.uploadRoadVideo()."""
    return await analyze_video(
        background_tasks=background_tasks,
        video=video,
        sample_fps=sample_fps,
        confidence_threshold=confidence_threshold,
        bus_id=bus_id,
        route_id=route_id,
        city=city,
    )


@router.get("/scan/jobs/{job_id}", tags=["AI Road Scan (Frontend Alias)"])
def scan_job_status_alias(job_id: str):
    """Direct alias for frontend roadScanApi.getJobStatus()."""
    return get_job_status(job_id)


@router.post("/scan/analyze/frame", tags=["AI Road Scan (Frontend Alias)"])
async def scan_analyze_frame_alias(req: SingleFrameRequest):
    """Direct alias for frontend live camera frame analysis."""
    return await analyze_single_frame(req)


@router.post("/scan/analyze/batch", tags=["AI Road Scan (Frontend Alias)"])
async def scan_analyze_batch_alias(req: FrameBatchRequest):
    """Direct alias for frontend live camera batch analysis."""
    return await analyze_frame_batch(req)

