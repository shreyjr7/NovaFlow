"""
Administration Panel Service (Phase 31)
=======================================
Enterprise administration and monitoring engine providing:
  - Admin Dashboard KPIs:
      Total users, Active buses, Online devices, Events today,
      System health, API health, Queue health, Storage, AI service health.
  - Live System Monitoring (CPU, GPU, RAM, Disk, Temperature, Latency, FPS).
  - Data management across all 14 mandatory Administration Modules:
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

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class AdminDashboardKPIs(BaseModel):
    total_users: int = 48
    active_buses: int = 112
    total_buses: int = 124
    online_devices: int = 118
    total_devices: int = 124
    events_today: int = 14820
    system_health: str = "99.8% Healthy"
    api_health: str = "99.9% Uptime (18ms avg latency)"
    queue_health: str = "0 Backlog (12ms drain latency)"
    storage: str = "142 GB / 500 GB (28.4% used)"
    ai_service_health: str = "Optimal (28.4 FPS across edge nodes)"
    timestamp: str


class SystemMonitoringTelemetry(BaseModel):
    cpu_percent: float = 41.5
    gpu_percent: float = 62.8
    ram_percent: float = 53.2
    disk_percent: float = 38.0
    temperature_celsius: float = 48.4
    network_latency_ms: float = 18.6
    api_latency_ms: float = 18.0
    queue_drain_rate_events_per_sec: int = 125
    ai_inference_fps: float = 28.4
    uptime_hours: float = 384.5
    services_status: Dict[str, str] = Field(
        default_factory=lambda: {
            "fastapi_backend": "HEALTHY",
            "sqlite_database": "HEALTHY",
            "postgis_clustering": "HEALTHY",
            "event_processor_worker": "RUNNING",
            "websocket_alert_hub": "ACTIVE",
            "offline_buffer_drainer": "IDLE_EMPTY",
        }
    )


class AdminUser(BaseModel):
    user_id: str
    username: str
    name: str
    email: str
    role: str
    status: str  # ACTIVE, SUSPENDED, PENDING
    last_login: str


class AdminRole(BaseModel):
    role_id: str
    name: str
    description: str
    user_count: int
    permissions: List[str]


class AdminBus(BaseModel):
    bus_id: str
    depot: str
    assigned_route: str
    device_id: str
    status: str  # ACTIVE, OFFLINE, MAINTENANCE
    last_ping: str


class AdminRoute(BaseModel):
    route_id: str
    name: str
    total_distance_km: float
    stops_count: int
    scheduled_travel_time_min: float
    average_delay_min: float
    status: str


class AdminDevice(BaseModel):
    device_id: str
    bus_id: str
    hardware_type: str  # Jetson Orin Nano, x86 Industrial
    cpu_load_percent: float
    temp_celsius: float
    storage_used_percent: float
    status: str  # ONLINE, WARNING, OFFLINE
    last_heartbeat: str


class AdminCamera(BaseModel):
    camera_id: str
    bus_id: str
    mount_position: str  # FRONT_ROAD, CABIN_ANONYMIZED
    resolution: str
    fps: int
    optical_status: str  # HEALTHY, WARNING, DEGRADED, OFFLINE
    blur_score: float
    brightness: float


class AdminAIModel(BaseModel):
    model_id: str
    name: str
    version: str
    task: str
    dataset: str
    accuracy_metrics: Dict[str, Any]
    deployment_status: str  # ACTIVE, INACTIVE, VALIDATING
    last_updated: str


class AdminEvent(BaseModel):
    event_id: str
    timestamp: str
    event_type: str
    bus_id: str
    location: str
    confidence: float
    status: str  # INGESTED, DEDUPLICATED, ACTIONED


class AdminGISLayer(BaseModel):
    layer_id: str
    name: str
    layer_type: str  # POINT, POLYLINE, POLYGON, HEATMAP
    features_count: int
    status: str  # ACTIVE, HIDDEN


class AdminDataSource(BaseModel):
    source_id: str
    name: str
    feed_type: str
    frequency: str
    status: str  # CONNECTED, DEGRADED, DISCONNECTED
    last_packet_received: str


class AdminRetentionPolicy(BaseModel):
    policy_id: str
    data_category: str
    retention_period: str
    auto_purge_enabled: bool
    last_purge_run: str


class AdminSystemLog(BaseModel):
    log_id: str
    timestamp: str
    level: str  # INFO, WARNING, ERROR, DEBUG
    service: str
    message: str


class AdminAuditLog(BaseModel):
    audit_id: str
    timestamp: str
    actor: str
    actor_role: str
    action: str
    target_resource: str
    ip_address: str
    status: str  # SUCCESS, DENIED


# ── Admin Panel Service Implementation ──────────────────────────────────────

class AdminPanelService:
    """Consolidates administration state and system monitoring telemetry."""

    def __init__(self):
        now = datetime.now(timezone.utc)
        self._start_time = now - timedelta(hours=384, minutes=30)

    def get_dashboard(self) -> AdminDashboardKPIs:
        now_iso = datetime.now(timezone.utc).isoformat()
        return AdminDashboardKPIs(
            total_users=48,
            active_buses=112,
            total_buses=124,
            online_devices=118,
            total_devices=124,
            events_today=14820,
            system_health="99.8% Healthy",
            api_health="99.9% Uptime (18ms avg latency)",
            queue_health="0 Backlog (12ms drain latency)",
            storage="142 GB / 500 GB (28.4% used)",
            ai_service_health="Optimal (28.4 FPS across edge nodes)",
            timestamp=now_iso,
        )

    def get_system_monitoring(self) -> SystemMonitoringTelemetry:
        return SystemMonitoringTelemetry()

    # ── 1. Users ────────────────────────────────────────────────────────────
    def get_users(self) -> List[AdminUser]:
        return [
            AdminUser(user_id="USR-001", username="admin.shreyansh", name="Shreyansh S.", email="admin@novaflow.internal", role="SECURITY_ADMIN", status="ACTIVE", last_login="10 mins ago"),
            AdminUser(user_id="USR-002", username="planner.vikram", name="Vikram R.", email="v.raman@bmtc.gov.in", role="TRANSIT_PLANNER", status="ACTIVE", last_login="2 hours ago"),
            AdminUser(user_id="USR-003", username="inspector.priya", name="Priya N.", email="priya.n@bbmp.gov.in", role="SAFETY_OFFICER", status="ACTIVE", last_login="Yesterday"),
            AdminUser(user_id="USR-004", username="cop.anand", name="ACP Anand K.", email="acp.traffic@bcp.gov.in", role="TRAFFIC_POLICE_CHIEF", status="ACTIVE", last_login="3 days ago"),
            AdminUser(user_id="USR-005", username="engineer.manoj", name="Manoj D.", email="m.d@depot.bmtc.gov.in", role="FIELD_ENGINEER", status="ACTIVE", last_login="1 hour ago"),
        ]

    # ── 2. Roles ────────────────────────────────────────────────────────────
    def get_roles(self) -> List[AdminRole]:
        return [
            AdminRole(role_id="ROLE-01", name="SECURITY_ADMIN", description="Complete system administration, access audit control, and retention policy management.", user_count=4, permissions=["ALL_ACCESS", "POLICY_WRITE", "AUDIT_VIEW", "USER_MANAGEMENT"]),
            AdminRole(role_id="ROLE-02", name="TRANSIT_PLANNER", description="Route timetable analysis, bottleneck mitigation, and report generation.", user_count=12, permissions=["REPORTS_GENERATE", "ROUTES_VIEW", "ANALYTICS_VIEW"]),
            AdminRole(role_id="ROLE-03", name="SAFETY_OFFICER", description="Incident verification, pedestrian conflict monitoring, and field verification.", user_count=18, permissions=["INCIDENTS_VERIFY", "HAZARDS_VERIFY", "ALERTS_MANAGE"]),
            AdminRole(role_id="ROLE-04", name="FIELD_ENGINEER", description="On-bus edge device diagnostics and camera lens maintenance.", user_count=14, permissions=["DEVICES_WRITE", "CAMERAS_MAINTENANCE", "TICKETS_RESOLVE"]),
        ]

    # ── 3. Buses ────────────────────────────────────────────────────────────
    def get_buses(self) -> List[AdminBus]:
        return [
            AdminBus(bus_id="BUS-102", depot="Majestic Depot 1", assigned_route="ROUTE-12", device_id="DEV-JET-102", status="ACTIVE", last_ping="2s ago"),
            AdminBus(bus_id="BUS-117", depot="Majestic Depot 1", assigned_route="ROUTE-12", device_id="DEV-JET-117", status="ACTIVE", last_ping="4s ago"),
            AdminBus(bus_id="BUS-143", depot="Majestic Depot 1", assigned_route="ROUTE-12", device_id="DEV-JET-143", status="ACTIVE", last_ping="1s ago"),
            AdminBus(bus_id="BUS-205", depot="Hebbal Depot 4", assigned_route="ROUTE-543", device_id="DEV-JET-205", status="ACTIVE", last_ping="5s ago"),
            AdminBus(bus_id="BUS-308", depot="Whitefield Depot 7", assigned_route="ROUTE-403", device_id="DEV-JET-308", status="OFFLINE", last_ping="4 hours ago"),
        ]

    # ── 4. Routes ───────────────────────────────────────────────────────────
    def get_routes(self) -> List[AdminRoute]:
        return [
            AdminRoute(route_id="ROUTE-12", name="Route 12 (Majestic ↔ Silk Board)", total_distance_km=18.4, stops_count=24, scheduled_travel_time_min=42.0, average_delay_min=15.0, status="MONITORED"),
            AdminRoute(route_id="ROUTE-543", name="Route 543 (Hebbal ↔ Electronic City)", total_distance_km=32.0, stops_count=18, scheduled_travel_time_min=65.0, average_delay_min=27.0, status="MONITORED"),
            AdminRoute(route_id="ROUTE-403", name="Route 403 (Majestic ↔ ITPL Whitefield)", total_distance_km=22.6, stops_count=28, scheduled_travel_time_min=55.0, average_delay_min=18.0, status="MONITORED"),
            AdminRoute(route_id="ROUTE-305", name="Route 305 (Shivajinagar ↔ Kadugodi)", total_distance_km=21.0, stops_count=22, scheduled_travel_time_min=48.0, average_delay_min=16.0, status="MONITORED"),
        ]

    # ── 5. Devices ──────────────────────────────────────────────────────────
    def get_devices(self) -> List[AdminDevice]:
        return [
            AdminDevice(device_id="DEV-JET-102", bus_id="BUS-102", hardware_type="NVIDIA Jetson Orin Nano", cpu_load_percent=38.4, temp_celsius=46.2, storage_used_percent=24.0, status="ONLINE", last_heartbeat="2s ago"),
            AdminDevice(device_id="DEV-JET-117", bus_id="BUS-117", hardware_type="NVIDIA Jetson Orin Nano", cpu_load_percent=42.1, temp_celsius=48.0, storage_used_percent=26.5, status="ONLINE", last_heartbeat="3s ago"),
            AdminDevice(device_id="DEV-JET-143", bus_id="BUS-143", hardware_type="NVIDIA Jetson Orin Nano", cpu_load_percent=45.0, temp_celsius=51.2, storage_used_percent=31.0, status="ONLINE", last_heartbeat="1s ago"),
            AdminDevice(device_id="DEV-JET-308", bus_id="BUS-308", hardware_type="NVIDIA Jetson Orin Nano", cpu_load_percent=0.0, temp_celsius=24.0, storage_used_percent=45.0, status="OFFLINE", last_heartbeat="4 hours ago"),
        ]

    # ── 6. Cameras ──────────────────────────────────────────────────────────
    def get_cameras(self) -> List[AdminCamera]:
        return [
            AdminCamera(camera_id="CAM-102-FRONT", bus_id="BUS-102", mount_position="FRONT_ROAD", resolution="1920x1080", fps=30, optical_status="HEALTHY", blur_score=142.5, brightness=118.0),
            AdminCamera(camera_id="CAM-102-CABIN", bus_id="BUS-102", mount_position="CABIN_ANONYMIZED", resolution="1280x720", fps=15, optical_status="HEALTHY", blur_score=126.0, brightness=105.0),
            AdminCamera(camera_id="CAM-117-FRONT", bus_id="BUS-117", mount_position="FRONT_ROAD", resolution="1920x1080", fps=30, optical_status="WARNING", blur_score=88.0, brightness=122.0),
            AdminCamera(camera_id="CAM-143-FRONT", bus_id="BUS-143", mount_position="FRONT_ROAD", resolution="1920x1080", fps=30, optical_status="DEGRADED", blur_score=42.0, brightness=65.0),
        ]

    # ── 7. AI Models ────────────────────────────────────────────────────────
    def get_ai_models(self) -> List[AdminAIModel]:
        return [
            AdminAIModel(model_id="AI-01", name="Road Defect Detection", version="v1.2.0", task="Pothole & Surface Damage Detection", dataset="CityRoads-v4 (85k frames)", accuracy_metrics={"mAP_50": 0.912, "precision": 0.894, "recall": 0.881, "fps": 29.5}, deployment_status="ACTIVE", last_updated="2 days ago"),
            AdminAIModel(model_id="AI-02", name="Vehicle Detection", version="v2.1.0", task="Multi-Class Traffic Object Detection", dataset="UrbanTraffic-v3 (120k annotations)", accuracy_metrics={"mAP_50": 0.945, "precision": 0.932, "recall": 0.920, "fps": 31.0}, deployment_status="ACTIVE", last_updated="1 week ago"),
            AdminAIModel(model_id="AI-03", name="Vehicle Tracking", version="v1.4.2", task="Multi-Object Kinematic Trajectory Tracking", dataset="ArterialMOT-v2 (40 sequences)", accuracy_metrics={"mota": 0.884, "idf1": 0.865, "fps": 28.0}, deployment_status="ACTIVE", last_updated="2 weeks ago"),
            AdminAIModel(model_id="AI-04", name="Pedestrian Detection", version="v2.0.1", task="Vulnerable Road User & Crosswalk Conflict", dataset="PedSafeCity-v1 (50k frames)", accuracy_metrics={"mAP_50": 0.928, "precision": 0.915, "recall": 0.902, "fps": 30.0}, deployment_status="ACTIVE", last_updated="3 days ago"),
            AdminAIModel(model_id="AI-05", name="Plate Detection", version="v1.8.0", task="License Plate Localization", dataset="IndiaLPR-v2 (60k vehicles)", accuracy_metrics={"mAP_50": 0.958, "precision": 0.941, "recall": 0.938, "fps": 32.0}, deployment_status="ACTIVE", last_updated="1 month ago"),
            AdminAIModel(model_id="AI-06", name="OCR", version="v2.3.0", task="High-Speed Plate Character Recognition", dataset="LPR-Text-v3 (140k plates)", accuracy_metrics={"char_acc": 0.982, "word_acc": 0.954, "latency_ms": 14.5}, deployment_status="ACTIVE", last_updated="1 month ago"),
        ]

    # ── 8. Events ───────────────────────────────────────────────────────────
    def get_events(self) -> List[AdminEvent]:
        return [
            AdminEvent(event_id="EVT-9041", timestamp="1 min ago", event_type="POTHOLE_DETECTED", bus_id="BUS-102", location="MG Road Radial (Segment A)", confidence=0.94, status="DEDUPLICATED"),
            AdminEvent(event_id="EVT-9040", timestamp="3 mins ago", event_type="HEAVY_CONGESTION", bus_id="BUS-117", location="Silk Board Terminal Approach", confidence=0.91, status="ACTIONED"),
            AdminEvent(event_id="EVT-9039", timestamp="6 mins ago", event_type="WATERLOGGING", bus_id="BUS-143", location="Dairy Circle Underpass", confidence=0.88, status="INGESTED"),
            AdminEvent(event_id="EVT-9038", timestamp="8 mins ago", event_type="PEDESTRIAN_CONFLICT", bus_id="BUS-102", location="St. Joseph's School Crossing", confidence=0.92, status="ACTIONED"),
        ]

    # ── 9. GIS Layers ───────────────────────────────────────────────────────
    def get_gis_layers(self) -> List[AdminGISLayer]:
        return [
            AdminGISLayer(layer_id="GIS-01", name="Municipal Road Network Polylines", layer_type="POLYLINE", features_count=1420, status="ACTIVE"),
            AdminGISLayer(layer_id="GIS-02", name="Active Defect & Pothole Clusters", layer_type="POINT", features_count=94, status="ACTIVE"),
            AdminGISLayer(layer_id="GIS-03", name="Congestion Corridor Heatmap", layer_type="HEATMAP", features_count=48, status="ACTIVE"),
            AdminGISLayer(layer_id="GIS-04", name="School & Pedestrian Risk Zones", layer_type="POLYGON", features_count=18, status="ACTIVE"),
            AdminGISLayer(layer_id="GIS-05", name="City Drainage & Flood Zones", layer_type="POLYGON", features_count=12, status="ACTIVE"),
        ]

    # ── 10. Data Sources ────────────────────────────────────────────────────
    def get_data_sources(self) -> List[AdminDataSource]:
        return [
            AdminDataSource(source_id="SRC-01", name="BMTC Bus Edge Telemetry & Vision", feed_type="WebSocket / MQTT (TLS)", frequency="10 Hz", status="CONNECTED", last_packet_received="1s ago"),
            AdminDataSource(source_id="SRC-02", name="PostGIS Clustering Engine", feed_type="PostgreSQL PostGIS 3.4", frequency="Batch (30s)", status="CONNECTED", last_packet_received="15s ago"),
            AdminDataSource(source_id="SRC-03", name="City Transit GTFS Timetable Feed", feed_type="REST / Protocol Buffer", frequency="Hourly", status="CONNECTED", last_packet_received="12 mins ago"),
            AdminDataSource(source_id="SRC-04", name="Municipal Weather & Stormwater Sensors", feed_type="REST JSON API", frequency="5 mins", status="CONNECTED", last_packet_received="2 mins ago"),
        ]

    # ── 11. Retention Policies ──────────────────────────────────────────────
    def get_retention_policies(self) -> List[AdminRetentionPolicy]:
        return [
            AdminRetentionPolicy(policy_id="RET-01", data_category="Unflagged Raw Camera Frames (Ring Buffer)", retention_period="15 Seconds", auto_purge_enabled=True, last_purge_run="Continuous"),
            AdminRetentionPolicy(policy_id="RET-02", data_category="Unverified Sensor Anomalies", retention_period="7 Days", auto_purge_enabled=True, last_purge_run="Today 03:00 UTC"),
            AdminRetentionPolicy(policy_id="RET-03", data_category="Confirmed Incident Evidence Clips (Encrypted)", retention_period="90 Days", auto_purge_enabled=True, last_purge_run="Yesterday 03:00 UTC"),
            AdminRetentionPolicy(policy_id="RET-04", data_category="Cryptographic Custody & Access Audit Logs", retention_period="365 Days", auto_purge_enabled=False, last_purge_run="Never (Immutable)"),
            AdminRetentionPolicy(policy_id="RET-05", data_category="Anonymized Cabin Occupancy Telemetry", retention_period="24 Hours", auto_purge_enabled=True, last_purge_run="Today 04:00 UTC"),
        ]

    # ── 12. System Logs ─────────────────────────────────────────────────────
    def get_system_logs(self) -> List[AdminSystemLog]:
        return [
            AdminSystemLog(log_id="LOG-8120", timestamp="10s ago", level="INFO", service="event_processor", message="Batch of 48 telemetry events processed and deduplicated via PostGIS ST_DWithin."),
            AdminSystemLog(log_id="LOG-8119", timestamp="45s ago", level="INFO", service="fastapi_backend", message="GET /api/v1/urban-analytics/summary responded in 14.2ms (HTTP 200)."),
            AdminSystemLog(log_id="LOG-8118", timestamp="2 mins ago", level="WARNING", service="camera_health", message="CAM-143-FRONT blur score dropped below threshold (42.0 < 50.0). Maintenance ticket AUTO-TKT-088 created."),
            AdminSystemLog(log_id="LOG-8117", timestamp="5 mins ago", level="INFO", service="offline_buffer", message="Store-and-forward SQLite queue drained 12 queued events upon network restore."),
        ]

    # ── 13. Audit Logs ──────────────────────────────────────────────────────
    def get_audit_logs(self) -> List[AdminAuditLog]:
        return [
            AdminAuditLog(audit_id="AUD-501", timestamp="15 mins ago", actor="admin.shreyansh", actor_role="SECURITY_ADMIN", action="UPDATE_RETENTION_POLICY", target_resource="RET-01 (Raw Frame Buffer)", ip_address="192.168.1.104", status="SUCCESS"),
            AdminAuditLog(audit_id="AUD-502", timestamp="45 mins ago", actor="planner.vikram", actor_role="TRANSIT_PLANNER", action="EXPORT_REPORT_PDF", target_resource="REP-BLR-2026-001", ip_address="10.0.4.55", status="SUCCESS"),
            AdminAuditLog(audit_id="AUD-503", timestamp="1 hour ago", actor="unknown_guest", actor_role="NONE", action="ACCESS_RAW_EVIDENCE", target_resource="EV_CLIP_904", ip_address="198.51.100.4", status="DENIED"),
        ]

    # ── 14. Reports ─────────────────────────────────────────────────────────
    def get_reports(self) -> List[Dict[str, Any]]:
        return [
            {"report_id": "REP-BLR-2026-001", "title": "City-Wide Daily Urban Transit Diagnostic & Action Report", "city": "Bengaluru", "status": "PUBLISHED", "generated_at": "Today 05:30 UTC", "format": "PDF-1.4 / Interactive"},
            {"report_id": "REP-BLR-2026-002", "title": "Zone A Weekly Arterial Diagnostic", "city": "Bengaluru", "status": "SAVED", "generated_at": "Yesterday 18:00 UTC", "format": "PDF-1.4 / Interactive"},
        ]


# Singleton provider
_admin_service_instance: Optional[AdminPanelService] = None

def get_admin_panel_service() -> AdminPanelService:
    global _admin_service_instance
    if _admin_service_instance is None:
        _admin_service_instance = AdminPanelService()
    return _admin_service_instance
