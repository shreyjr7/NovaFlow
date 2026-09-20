"Database session utilities for FastAPI backend."

try:
    from sqlmodel import SQLModel, create_engine, Session
except ImportError:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import declarative_base, Session
    SQLModel = declarative_base()
from ..config.settings import Settings

settings = Settings()

# Normalize postgresql URL scheme for SQLAlchemy if Supabase gives postgres://
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Check for placeholder password
if "[YOUR" in db_url:
    db_url = "sqlite:///./novaflow.db"

# Configure connection arguments (pool_pre_ping for resilient cloud connection to Supabase)
engine_kwargs = {"echo": False, "future": True}
if "sqlite" in db_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

try:
    engine = create_engine(db_url, **engine_kwargs)
except Exception:
    db_url = "sqlite:///./novaflow.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False}, echo=False, future=True)

def get_session() -> Session:
    with Session(engine) as session:
        yield session

def init_db() -> None:
    try:
        from ..models.entities import (
            IngestedEvent,
            GpsTelemetry,
            RouteModel,
            BusModel,
            InfrastructureDefect,
            StatusAuditLog,
            EventVerification,
            UserModel,
            ScanJob,
            RoadDetection,
            MaintenanceTicket,
            EvidenceReference,
            PersistentHazard,
            HazardObservation,
        )  # noqa: F401
    except Exception:
        pass
    SQLModel.metadata.create_all(engine)
    # Safe SQLite column migrations for Phase 8-12 fields
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            # ingested_events
            ev_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(ingested_events)")).fetchall()]
            if "route_id" not in ev_cols and len(ev_cols) > 0:
                conn.execute(text("ALTER TABLE ingested_events ADD COLUMN route_id VARCHAR(64) DEFAULT 'R-01'"))
                conn.commit()

            # transit_buses migrations
            bus_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(transit_buses)")).fetchall()]
            if bus_cols:
                if "latitude" not in bus_cols:
                    conn.execute(text("ALTER TABLE transit_buses ADD COLUMN latitude FLOAT DEFAULT 12.9348"))
                if "longitude" not in bus_cols:
                    conn.execute(text("ALTER TABLE transit_buses ADD COLUMN longitude FLOAT DEFAULT 77.6101"))
                if "speed" not in bus_cols:
                    conn.execute(text("ALTER TABLE transit_buses ADD COLUMN speed FLOAT DEFAULT 0.0"))
                if "heading" not in bus_cols:
                    conn.execute(text("ALTER TABLE transit_buses ADD COLUMN heading FLOAT DEFAULT 0.0"))
                if "timestamp" not in bus_cols:
                    conn.execute(text("ALTER TABLE transit_buses ADD COLUMN timestamp VARCHAR(64)"))
                if "camera_status" not in bus_cols:
                    conn.execute(text("ALTER TABLE transit_buses ADD COLUMN camera_status VARCHAR(32) DEFAULT 'ACTIVE'"))
                if "AI_status" not in bus_cols:
                    conn.execute(text("ALTER TABLE transit_buses ADD COLUMN \"AI_status\" VARCHAR(32) DEFAULT 'ONLINE'"))
                if "connection_status" not in bus_cols:
                    conn.execute(text("ALTER TABLE transit_buses ADD COLUMN connection_status VARCHAR(32) DEFAULT 'CONNECTED'"))
                conn.commit()

            # road_detections migrations
            det_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(road_detections)")).fetchall()]
            if det_cols:
                if "condition_type" not in det_cols:
                    conn.execute(text("ALTER TABLE road_detections ADD COLUMN condition_type VARCHAR(32) DEFAULT 'DIRECT'"))
                if "is_multimodal_verified" not in det_cols:
                    conn.execute(text("ALTER TABLE road_detections ADD COLUMN is_multimodal_verified BOOLEAN DEFAULT 0"))
                if "verification_notes" not in det_cols:
                    conn.execute(text("ALTER TABLE road_detections ADD COLUMN verification_notes TEXT"))
                if "observation_count" not in det_cols:
                    conn.execute(text("ALTER TABLE road_detections ADD COLUMN observation_count INTEGER DEFAULT 1"))
                if "ticket_id" not in det_cols:
                    conn.execute(text("ALTER TABLE road_detections ADD COLUMN ticket_id VARCHAR(64)"))
                if "persistent_hazard_id" not in det_cols:
                    conn.execute(text("ALTER TABLE road_detections ADD COLUMN persistent_hazard_id VARCHAR(64)"))
                if "independent_buses_count" not in det_cols:
                    conn.execute(text("ALTER TABLE road_detections ADD COLUMN independent_buses_count INTEGER DEFAULT 1"))
                if "contributing_buses" not in det_cols:
                    conn.execute(text("ALTER TABLE road_detections ADD COLUMN contributing_buses VARCHAR(512)"))
                if "persistence_badge" not in det_cols:
                    conn.execute(text("ALTER TABLE road_detections ADD COLUMN persistence_badge VARCHAR(64)"))
                if "last_detected_at" not in det_cols:
                    conn.execute(text("ALTER TABLE road_detections ADD COLUMN last_detected_at VARCHAR(64)"))
                if "location_status" not in det_cols:
                    conn.execute(text("ALTER TABLE road_detections ADD COLUMN location_status VARCHAR(32) DEFAULT 'available'"))
                conn.commit()

            # maintenance_tickets migrations
            tick_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(maintenance_tickets)")).fetchall()]
            if tick_cols:
                if "detection_id" not in tick_cols:
                    conn.execute(text("ALTER TABLE maintenance_tickets ADD COLUMN detection_id VARCHAR(64)"))
                if "evidence" not in tick_cols:
                    conn.execute(text("ALTER TABLE maintenance_tickets ADD COLUMN evidence VARCHAR(512)"))
                if "source_bus" not in tick_cols:
                    conn.execute(text("ALTER TABLE maintenance_tickets ADD COLUMN source_bus VARCHAR(64) DEFAULT 'FLEET-SYSTEM'"))
                if "observation_count" not in tick_cols:
                    conn.execute(text("ALTER TABLE maintenance_tickets ADD COLUMN observation_count INTEGER DEFAULT 1"))
                conn.commit()
    except Exception:
        pass

# Auto-initialize tables on load
try:
    init_db()
except Exception:
    pass
