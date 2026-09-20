"""
NovaFlow Transport Database Domain Models (Step 25)
===================================================
PostgreSQL + PostGIS compatible entity models for:
  1. Events          (IngestedEvent)
  2. GPS             (GpsTelemetry)
  3. Routes          (RouteModel)
  4. Buses           (BusModel)
  5. Infrastructure  (InfrastructureDefect)
  6. Status          (StatusAuditLog)
  7. Verification    (EventVerification)
  8. Users           (UserModel)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

# Re-export canonical IngestedEvent
from .ingested_event import IngestedEvent
# Re-export AI Road Scan entities
from .ai_scan_entities import ScanJob, RoadDetection, MaintenanceTicket, EvidenceReference


class GpsTelemetry(SQLModel, table=True):
    """Time-series GPS pings recorded from fleet buses."""
    __tablename__ = "gps_telemetry"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    bus_id: str = Field(index=True, max_length=64)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    lat: float = Field(index=True)
    lon: float = Field(index=True)
    speed_kmh: float = Field(default=0.0)
    bearing_deg: Optional[float] = Field(default=0.0)
    altitude_m: Optional[float] = Field(default=0.0)
    hdop: Optional[float] = Field(default=1.0)
    road_segment: Optional[str] = Field(default="UNKNOWN", max_length=128)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "bus_id": self.bus_id,
            "timestamp": self.timestamp.isoformat(),
            "lat": self.lat,
            "lon": self.lon,
            "speed_kmh": self.speed_kmh,
            "bearing_deg": self.bearing_deg,
            "road_segment": self.road_segment,
        }


class RouteModel(SQLModel, table=True):
    """Transit routes with spatial waypoints and coverage."""
    __tablename__ = "transit_routes"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    route_id: str = Field(unique=True, index=True, max_length=64)
    name: str = Field(max_length=255)
    city: str = Field(default="Delhi NCR", max_length=128)
    state: str = Field(default="Delhi", max_length=128)
    distance_km: float = Field(default=15.0)
    scheduled_travel_time_minutes: float = Field(default=40.0)
    waypoints_json: str = Field(default="[]")
    road_segments_json: str = Field(default="[]")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_waypoints(self) -> List[Dict[str, float]]:
        try:
            return json.loads(self.waypoints_json)
        except Exception:
            return []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route_id": self.route_id,
            "name": self.name,
            "city": self.city,
            "state": self.state,
            "distance_km": self.distance_km,
            "scheduled_travel_time_minutes": self.scheduled_travel_time_minutes,
            "waypoints": self.get_waypoints(),
        }


class BusModel(SQLModel, table=True):
    """Connected transit buses with current kinematic position and AI edge status."""
    __tablename__ = "transit_buses"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    bus_id: str = Field(unique=True, index=True, max_length=64)
    name: str = Field(default="Connected Transit Bus", max_length=128)
    model: str = Field(default="Tata Starbus EV", max_length=128)
    route_id: Optional[str] = Field(default="R-01", index=True, max_length=64)
    status: str = Field(default="IN_SERVICE", max_length=32)  # IN_SERVICE, MAINTENANCE, DEPOT

    # Kinematics & Spatial (Core Phase 8: latitude, longitude, speed, heading, timestamp)
    current_lat: float = Field(default=28.6139)
    current_lon: float = Field(default=77.2090)
    latitude: Optional[float] = Field(default=28.6139)
    longitude: Optional[float] = Field(default=77.2090)
    speed_kmh: float = Field(default=35.0)
    speed: Optional[float] = Field(default=35.0)
    bearing_deg: float = Field(default=0.0)
    heading: Optional[float] = Field(default=0.0)
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Edge Hardware & Intelligence (camera_status, AI_status, connection_status)
    camera_status: str = Field(default="ACTIVE", max_length=32)  # ACTIVE, STREAMING, DEGRADED, OFFLINE
    AI_status: str = Field(default="ONLINE", max_length=32)       # INFERENCING, ONLINE, STANDBY, OFFLINE
    connection_status: str = Field(default="CONNECTED", max_length=32)  # CONNECTED, DEGRADED, DISCONNECTED
    edge_device_id: str = Field(default="NVIDIA Jetson Orin Nano", max_length=128)

    def sync_kinematics(self, lat: float, lon: float, spd: float = 0.0, hdg: float = 0.0, ts: Optional[datetime] = None):
        """Helper to synchronize dual kinematic fields."""
        now = ts or datetime.now(timezone.utc)
        self.current_lat = lat
        self.latitude = lat
        self.current_lon = lon
        self.longitude = lon
        self.speed_kmh = spd
        self.speed = spd
        self.bearing_deg = hdg
        self.heading = hdg
        self.last_heartbeat = now
        self.timestamp = now

    def to_dict(self) -> Dict[str, Any]:
        lat = self.latitude if self.latitude is not None else self.current_lat
        lon = self.longitude if self.longitude is not None else self.current_lon
        spd = self.speed if self.speed is not None else self.speed_kmh
        hdg = self.heading if self.heading is not None else self.bearing_deg
        ts = (self.timestamp or self.last_heartbeat or datetime.now(timezone.utc)).isoformat()

        return {
            # 10 Core Phase 8 fields
            "bus_id": self.bus_id,
            "route_id": self.route_id or "R-01",
            "latitude": lat,
            "longitude": lon,
            "speed": spd,
            "heading": hdg,
            "timestamp": ts,
            "camera_status": self.camera_status,
            "AI_status": self.AI_status,
            "connection_status": self.connection_status,

            # Legacy & UI compatibility fields
            "name": self.name,
            "model": self.model,
            "status": self.status,
            "current_lat": lat,
            "current_lon": lon,
            "speed_kmh": spd,
            "bearing_deg": hdg,
            "edge_device": self.edge_device_id,
            "last_heartbeat": ts,
        }


class InfrastructureDefect(SQLModel, table=True):
    """Road infrastructure defects and assets."""
    __tablename__ = "infrastructure_defects"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    asset_id: str = Field(unique=True, index=True, max_length=64)
    asset_type: str = Field(index=True, max_length=64)  # POTHOLE, WATERLOGGING, MISSING_SIGN, DAMAGED_ROAD
    lat: float = Field(index=True)
    lon: float = Field(index=True)
    road_name: str = Field(default="Arterial Road", max_length=255)
    severity: str = Field(default="medium", index=True, max_length=32)
    condition_score: float = Field(default=0.85)
    status: str = Field(default="unverified", max_length=32)
    observation_count: int = Field(default=1)
    first_detected: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_detected: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "lat": self.lat,
            "lon": self.lon,
            "road_name": self.road_name,
            "severity": self.severity,
            "condition_score": self.condition_score,
            "status": self.status,
            "observation_count": self.observation_count,
            "first_detected": self.first_detected.isoformat(),
            "last_detected": self.last_detected.isoformat(),
            "verified_by": self.verified_by,
        }


class StatusAuditLog(SQLModel, table=True):
    """Lifecycle state machine audit records."""
    __tablename__ = "status_audit_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    event_id: str = Field(index=True, max_length=128)
    previous_status: str = Field(max_length=32)
    new_status: str = Field(max_length=32)
    actor: str = Field(default="OPERATOR", max_length=128)
    reason: Optional[str] = None
    work_order_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "event_id": self.event_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "actor": self.actor,
            "reason": self.reason,
            "work_order_id": self.work_order_id,
            "timestamp": self.timestamp.isoformat(),
        }


class EventVerification(SQLModel, table=True):
    """Human and supervisor verification records for detections."""
    __tablename__ = "event_verifications"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    event_id: str = Field(unique=True, index=True, max_length=128)
    verified_by: str = Field(max_length=128)
    verification_status: str = Field(default="CONFIRMED", max_length=32)  # CONFIRMED, DISMISSED, ESCALATED
    notes: Optional[str] = None
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "event_id": self.event_id,
            "verified_by": self.verified_by,
            "verification_status": self.verification_status,
            "notes": self.notes,
            "verified_at": self.verified_at.isoformat(),
        }


class UserModel(SQLModel, table=True):
    """Platform users and RBAC credentials."""
    __tablename__ = "system_users"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    username: str = Field(unique=True, index=True, max_length=64)
    email: str = Field(unique=True, index=True, max_length=128)
    hashed_password: str = Field(max_length=255)
    role: str = Field(default="ANALYST", index=True, max_length=64)  # ADMIN, TRAFFIC POLICE, ROAD ENGINEER, ANALYST
    department: str = Field(default="Transport Authority", max_length=128)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "department": self.department,
            "is_active": self.is_active,
        }
