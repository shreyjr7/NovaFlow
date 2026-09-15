"""Bus model definitions for FastAPI backend.
Includes fields required for fleet monitoring.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from .user import User  # example relation if needed

class Bus(SQLModel, table=True):
    __tablename__ = "bus"
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    route_id: Optional[UUID] = Field(default=None, foreign_key="route.id")
    status: str = Field(max_length=32, description="ONLINE, OFFLINE, WARNING, MAINTENANCE")
    gps_point: Optional[str] = Field(default=None, description="WKT or GeoJSON representation of current GPS point")
    edge_device_id: Optional[UUID] = Field(default=None, description="Reference to edge device")
    camera_status: Optional[str] = Field(default=None, description="Camera operational status")
    last_seen: Optional[datetime] = Field(default=None)
    network_status: Optional[str] = Field(default=None)
    temperature: Optional[float] = Field(default=None)
    cpu_usage: Optional[float] = Field(default=None)
    gpu_usage: Optional[float] = Field(default=None)
    storage_used: Optional[float] = Field(default=None)
    # Relationships (optional placeholders)
    # route: Optional["Route"] = Relationship(back_populates="buses")
    # edge_device: Optional["EdgeDevice"] = Relationship(back_populates="buses")
