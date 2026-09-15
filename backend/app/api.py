from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from uuid import UUID

app = FastAPI(title="Urban Intelligence Backend")

# Pydantic models (mirroring edge Event)
class DetectionModel(BaseModel):
    label: str
    confidence: float
    bbox: List[float]

class EventModel(BaseModel):
    id: UUID
    gps: Dict[str, float]
    timestamp: str
    detections: List[DetectionModel]
    clip_path: str | None = None
    extra: Dict[str, Any] = {}

# In‑memory store for demo purposes (replace with DB)
EVENT_STORE: Dict[UUID, EventModel] = {}

@app.post("/events", response_model=EventModel)
def ingest_event(event: EventModel):
    EVENT_STORE[event.id] = event
    return event

@app.get("/events", response_model=List[EventModel])
def list_events():
    return list(EVENT_STORE.values())

@app.get("/events/{event_id}", response_model=EventModel)
def get_event(event_id: UUID):
    event = EVENT_STORE.get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

# Placeholder analytics endpoint
@app.get("/analytics/heatmap")
def heatmap():
    # Return dummy GeoJSON heatmap data
    return JSONResponse(content={"type": "FeatureCollection", "features": []})
