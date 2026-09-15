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
        from ..models.ingested_event import IngestedEvent  # noqa: F401
    except Exception:
        pass
    SQLModel.metadata.create_all(engine)

# Auto-initialize tables on load
try:
    init_db()
except Exception:
    pass
