"""FastAPI entry point for NovaFlow Transport backend."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    _SLOWAPI_AVAILABLE = True
except ImportError:
    _SLOWAPI_AVAILABLE = False
    class Limiter:
        def __init__(self, *args, **kwargs): pass
    def get_remote_address(request): return "127.0.0.1"
    class RateLimitExceeded(Exception): pass

from starlette.requests import Request
from starlette.responses import JSONResponse

from .config.settings import Settings
from .database.session import init_db
from .routers import auth, users, buses, routes, cameras, events, incidents, analytics, alerts, maintenance, reports, admin
from .routers.road_defects import router as road_defects_router
from .routers.vehicles import router as vehicles_router
from .routers.congestion import router as congestion_router
from .routers.pedestrian_safety import router as pedestrian_router
from .routers.anpr import router as anpr_router
from .routers.gis import router as gis_router
from .routers.clustering import router as clustering_router
from .routers.od_analysis import router as od_router
from .routers.privacy import router as privacy_router
from .routers.evidence import router as evidence_router
from .routers.urban_analytics import router as urban_analytics_router
from .routers.public_dashboard import router as public_dashboard_router
from .routers.ai_models import router as ai_models_router
from .routers.testing_framework import router as testing_framework_router
from .routers.demo_environment import router as demo_environment_router
from .routers.demo_flow import router as demo_flow_router
from .services.demo_seeder_service import get_demo_seeder_service
from .services.event_processor import get_event_processor

settings = Settings()

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger("novaflow_backend")

app = FastAPI(title="NovaFlow Transport Backend", version="0.1.0")

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter
if _SLOWAPI_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MIN}/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"}))

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(buses.router, prefix="/api/v1/buses", tags=["buses"])
app.include_router(routes.router, prefix="/api/v1/routes", tags=["routes"])
app.include_router(cameras.router, prefix="/api/v1/cameras", tags=["cameras"])
app.include_router(events.router, prefix="/api/v1/events", tags=["events"])
app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["incidents"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(analytics.router, prefix="/api/v1/insights", tags=["insights"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(maintenance.router, prefix="/api/v1/maintenance", tags=["maintenance"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(road_defects_router, prefix="/api/v1/road-defects", tags=["road-defects"])
app.include_router(vehicles_router,     prefix="/api/v1/vehicles",    tags=["vehicles"])
app.include_router(congestion_router,   prefix="/api/v1/congestion",  tags=["congestion"])
app.include_router(pedestrian_router,   prefix="/api/v1/pedestrian",  tags=["pedestrian-safety"])
app.include_router(anpr_router,         prefix="/api/v1/anpr",        tags=["anpr"])
app.include_router(gis_router,          prefix="/api/v1/gis",         tags=["gis"])
app.include_router(clustering_router,   prefix="/api/v1/clustering",  tags=["clustering"])
app.include_router(od_router,           prefix="/api/v1/od",          tags=["od-analysis"])
app.include_router(privacy_router,      prefix="/api/v1/privacy",     tags=["privacy"])
app.include_router(evidence_router,     prefix="/api/v1/evidence",    tags=["evidence"])
app.include_router(urban_analytics_router, prefix="/api/v1/urban-analytics", tags=["urban-analytics"])
app.include_router(public_dashboard_router, prefix="/api/v1/public", tags=["public-safety"])
app.include_router(ai_models_router, prefix="/api/v1/ai-models", tags=["ai-models"])
app.include_router(testing_framework_router, prefix="/api/v1/testing", tags=["testing"])
app.include_router(demo_environment_router, prefix="/api/v1/demo", tags=["demo-environment"])
app.include_router(demo_flow_router, prefix="/api/v1/demo-flow", tags=["demo-flow"])

# Startup / shutdown events
@app.on_event("startup")
async def on_startup():
    init_db()
    processor = get_event_processor()
    processor.start_worker()
    demo_svc = get_demo_seeder_service()
    demo_svc.seed_historical_events(target_count=525)
    logger.info("Database initialized, Event Processor started, and Demo Environment seeded.")

@app.on_event("shutdown")
async def on_shutdown():
    processor = get_event_processor()
    processor.stop_worker()
    logger.info("Event Processor stopped; shutting down NovaFlow Transport backend.")

# Simple health endpoint
@app.get("/health", tags=["public"]) 
async def health_check():
    return {"status": "ok"}
