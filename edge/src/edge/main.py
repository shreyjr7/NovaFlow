"""
Edge AI Simulator – Main Entry Point
=====================================
Starts the FastAPI control-plane server and the WebSocket stats broadcaster.

Run (from project root):
    uvicorn edge.src.edge.main:app --host 0.0.0.0 --port 7000 --reload

Or simply:
    python -m uvicorn edge.src.edge.main:app --port 7000
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .routers import control, ws_stats
from .pipeline.manager import SimulatorManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("edge_simulator")

# Singleton manager shared across request handlers
manager = SimulatorManager()

app = FastAPI(
    title="NovaFlow Edge AI Simulator",
    description="Simulates an onboard bus AI pipeline for development & testing.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach manager to app state so routers can access it
app.state.simulator = manager

# Mount routers
app.include_router(control.router, prefix="/api/simulator", tags=["control"])
app.include_router(ws_stats.router, prefix="/ws", tags=["websocket"])

# Serve the control-panel UI (static HTML) if ui/ directory exists
_ui_dir = os.path.join(os.path.dirname(__file__), "ui")
if os.path.isdir(_ui_dir):
    app.mount("/ui", StaticFiles(directory=_ui_dir, html=True), name="ui")


@app.get("/health", tags=["public"])
async def health():
    return {"status": "ok", "running": manager.is_running}

