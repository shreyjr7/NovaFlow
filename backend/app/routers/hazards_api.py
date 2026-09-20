"""
NovaFlow AI Persistent Road Hazards & Observation History API (Phase 12)
========================================================================
REST endpoints for querying persistent road hazards, multi-bus confirmation
status ('CONFIRMED BY 3 BUSES'), and complete historical observation ledgers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, col, desc, select

from ..database.session import engine
from ..models.ai_scan_entities import HazardObservation, PersistentHazard

logger = logging.getLogger("novaflow.hazards_api")

router = APIRouter(prefix="/api/v1/hazards", tags=["Multi-Bus Road Hazards"])


@router.get("/persistent", summary="Retrieve active persistent road hazards")
def list_persistent_hazards(
    city: Optional[str] = Query(None, description="Filter by city e.g. Bengaluru, Mumbai, Delhi"),
    hazard_type: Optional[str] = Query(None, description="Filter by defect type e.g. POTHOLE, ROAD_DAMAGE"),
    min_buses: int = Query(1, ge=1, description="Minimum independent buses required to filter"),
    status: Optional[str] = Query("ACTIVE", description="Status filter: ACTIVE, VERIFIED, RESOLVED, ALL"),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    """
    Returns persistent hazards with multi-bus confirmation status,
    distinct AI model confidence, observation counts, and last detected time.
    """
    with Session(engine) as session:
        query = select(PersistentHazard)

        if status and status.upper() != "ALL":
            query = query.where(PersistentHazard.status == status.upper())
        if city:
            query = query.where(PersistentHazard.city.ilike(f"%{city}%"))
        if hazard_type:
            query = query.where(PersistentHazard.hazard_type == hazard_type.upper())
        if min_buses > 1:
            query = query.where(PersistentHazard.independent_buses_count >= min_buses)

        query = query.order_by(desc(PersistentHazard.last_detected_at)).limit(limit)
        hazards = session.exec(query).all()

        return {
            "total": len(hazards),
            "hazards": [h.to_dict() for h in hazards],
        }


@router.get("/{hazard_id}", summary="Retrieve detailed persistent hazard with observation history")
def get_hazard_detail(hazard_id: str) -> Dict[str, Any]:
    """
    Retrieves a persistent hazard record alongside all chronological observations
    recorded by contributing buses.
    """
    with Session(engine) as session:
        # Match by UUID or hazard_code
        hazard = None
        try:
            h_uuid = UUID(hazard_id)
            hazard = session.exec(select(PersistentHazard).where(PersistentHazard.id == h_uuid)).first()
        except Exception:
            pass

        if not hazard:
            hazard = session.exec(
                select(PersistentHazard).where(PersistentHazard.hazard_code == hazard_id)
            ).first()

        if not hazard:
            raise HTTPException(status_code=404, detail=f"Persistent hazard '{hazard_id}' not found.")

        # Fetch observations
        observations = session.exec(
            select(HazardObservation)
            .where(HazardObservation.hazard_id == hazard.id)
            .order_by(desc(HazardObservation.observed_at))
        ).all()

        h_dict = hazard.to_dict()
        h_dict["observations"] = [o.to_dict() for o in observations]
        return h_dict


@router.get("/{hazard_id}/observations", summary="Retrieve observation history for a persistent hazard")
def list_hazard_observations(hazard_id: str) -> Dict[str, Any]:
    """Returns chronological list of observations recorded by all buses for this hazard."""
    with Session(engine) as session:
        hazard = None
        try:
            h_uuid = UUID(hazard_id)
            hazard = session.exec(select(PersistentHazard).where(PersistentHazard.id == h_uuid)).first()
        except Exception:
            pass

        if not hazard:
            hazard = session.exec(
                select(PersistentHazard).where(PersistentHazard.hazard_code == hazard_id)
            ).first()

        if not hazard:
            raise HTTPException(status_code=404, detail=f"Persistent hazard '{hazard_id}' not found.")

        observations = session.exec(
            select(HazardObservation)
            .where(HazardObservation.hazard_id == hazard.id)
            .order_by(desc(HazardObservation.observed_at))
        ).all()

        return {
            "hazard_id": str(hazard.id),
            "total": len(observations),
            "observations": [o.to_dict() for o in observations],
        }
