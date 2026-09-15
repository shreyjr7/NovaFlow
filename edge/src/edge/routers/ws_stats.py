"""
WebSocket Stats Router
======================
WS /ws/stats  – streams real-time pipeline stats to the control-panel UI.

The pipeline threads push stats dicts into `manager.stats_queue`.
This router drains that queue and broadcasts JSON to all connected clients.
"""

import asyncio
import json
import logging
import queue
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request

logger = logging.getLogger("routers.ws_stats")
router = APIRouter()

_clients: Set[WebSocket] = set()


async def _broadcast(payload: dict):
    dead = set()
    for ws in _clients:
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


async def _drain_queue(mgr_queue: queue.Queue):
    """Drain the manager stats queue and broadcast each item."""
    while True:
        try:
            stats = mgr_queue.get_nowait()
            await _broadcast(stats)
        except queue.Empty:
            break


@router.websocket("/stats")
async def stats_ws(websocket: WebSocket, request: Request):
    await websocket.accept()
    _clients.add(websocket)
    mgr = request.app.state.simulator
    logger.info(f"WS client connected. Total: {len(_clients)}")
    try:
        while True:
            await _drain_queue(mgr.stats_queue)
            # Also keep the connection alive by waiting briefly
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(websocket)
        logger.info(f"WS client disconnected. Remaining: {len(_clients)}")
