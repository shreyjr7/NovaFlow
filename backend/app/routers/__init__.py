"""
Routers package for NovaFlow backend.
Exports modular routers for defects, vehicles, and congestion,
along with stub fallback routers for standard system endpoints.
"""

from fastapi import APIRouter

from .road_defects import router as road_defects
from .vehicles import router as vehicles
from .congestion import router as congestion
from .pedestrian_safety import router as pedestrian_safety
from . import events
from . import incidents
from .anpr import router as anpr
from .clustering import router as clustering
from .od_analysis import router as od_analysis
from .route_delay import router as route_delay_router
from .insights import router as insights_router
from .alerts import router as alerts_router
from .camera_health import router as camera_health_router
from .privacy import router as privacy_router
from .evidence import router as evidence_router
from .urban_analytics import router as urban_analytics_router
from .reports import router as reports_router
from .public_dashboard import router as public_dashboard_router
from .admin_panel import router as admin_panel_router
from .ai_models import router as ai_models_router
from .buses_api import router as buses_api_router
from .maintenance import router as maintenance_router

from ..auth import router as auth_router

class _RouterHolder:
    def __init__(self, router=None):
        self.router = router or APIRouter()

auth = _RouterHolder(auth_router)
users = _RouterHolder()
buses = _RouterHolder(buses_api_router)
routes = _RouterHolder(route_delay_router)
cameras = _RouterHolder(camera_health_router)
analytics = _RouterHolder(insights_router)
alerts = _RouterHolder(alerts_router)
maintenance = _RouterHolder(maintenance_router)
reports = _RouterHolder(reports_router)
admin = _RouterHolder(admin_panel_router)

__all__ = [
    "road_defects",
    "vehicles",
    "congestion",
    "auth",
    "users",
    "buses",
    "routes",
    "cameras",
    "events",
    "incidents",
    "analytics",
    "alerts",
    "maintenance",
    "reports",
    "admin",
    "clustering",
    "od_analysis",
    "route_delay_router",
    "insights_router",
    "alerts_router",
    "camera_health_router",
    "privacy_router",
    "evidence_router",
    "urban_analytics_router",
    "reports_router",
    "public_dashboard_router",
    "admin_panel_router",
    "ai_models_router",
]
