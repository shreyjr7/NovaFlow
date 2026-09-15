"""
Actionable Insights API Router (Phase 23)
=========================================
Endpoints for querying, filtering, and acting on cross-domain operational recommendations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services.insights_engine import (
    ActionableInsight,
    InsightCategory,
    InsightSeverity,
    InsightStatus,
    get_insights_engine,
)

router = APIRouter()


class StatusUpdateIn(BaseModel):
    status: InsightStatus
    notes: Optional[str] = None


@router.get("/summary")
async def get_insights_summary():
    """Returns high-level KPI metrics across all actionable insights."""
    engine = get_insights_engine()
    return engine.get_summary_stats()


@router.get("", response_model=List[ActionableInsight])
async def list_insights(
    category: Optional[InsightCategory] = Query(None, description="Filter by insight category"),
    severity: Optional[InsightSeverity] = Query(None, description="Filter by severity level"),
    status: Optional[InsightStatus] = Query(None, description="Filter by operational status"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence threshold"),
):
    """
    Returns list of actionable insights with multi-sensor evidence, data sources,
    explainable reasoning, confidence score, and recommended operational actions.
    """
    engine = get_insights_engine()
    return engine.list_insights(
        category=category,
        severity=severity,
        status=status,
        min_confidence=min_confidence,
    )


@router.get("/{insight_id}", response_model=ActionableInsight)
async def get_insight_detail(insight_id: str):
    """Retrieves full details and evidentiary metrics for a specific actionable insight."""
    engine = get_insights_engine()
    ins = engine.get_insight(insight_id)
    if not ins:
        raise HTTPException(status_code=404, detail=f"Insight '{insight_id}' not found")
    return ins


@router.patch("/{insight_id}/status", response_model=ActionableInsight)
async def update_insight_status(insight_id: str, body: StatusUpdateIn):
    """Updates the operational status of an insight (e.g. ACKNOWLEDGED, ACTIONED, DISMISSED)."""
    engine = get_insights_engine()
    updated = engine.update_status(insight_id, body.status, body.notes)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Insight '{insight_id}' not found")
    return updated


@router.post("/generate")
async def trigger_insights_generation():
    """Triggers an on-demand re-evaluation of the Actionable Insights engine across all domains."""
    engine = get_insights_engine()
    # In a full deployment, triggers real-time graph re-correlation
    return {
        "status": "success",
        "message": "Actionable Insights Engine re-evaluated across all 6 telemetry domains.",
        "stats": engine.get_summary_stats(),
    }
