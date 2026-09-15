"""
AI Model Management Router (Phase 32)
=====================================
API endpoints for managing machine learning models:
  - Road Defect Detection
  - Vehicle Detection
  - Vehicle Tracking
  - Pedestrian Detection
  - Plate Detection
  - OCR

Enforces strict deployment safety guardrail:
  "Do not automatically deploy an unvalidated model."
"""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, HTTPException, Query, status

from ..services.ai_model_service import (
    get_ai_model_service,
    AIModelSummary,
    AIModelDetail,
    ModelVersion,
    VersionComparisonResult,
)

router = APIRouter()


@router.get("", response_model=List[AIModelSummary], summary="List all 6 core AI models with current active version")
async def list_models():
    service = get_ai_model_service()
    return service.list_models()


@router.get("/{model_id}", response_model=AIModelDetail, summary="Get model details and complete version history")
async def get_model(model_id: str):
    service = get_ai_model_service()
    model = service.get_model(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI Model '{model_id}' not found."
        )
    return model


@router.post("/{model_id}/versions/{version}/activate", response_model=ModelVersion, summary="Activate a model version (with validation safety guardrail)")
async def activate_model(model_id: str, version: str):
    service = get_ai_model_service()
    try:
        updated_ver = service.activate_model(model_id, version)
        return updated_ver
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        # Strict validation rejection
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{model_id}/versions/{version}/deactivate", response_model=ModelVersion, summary="Deactivate a model version")
async def deactivate_model(model_id: str, version: str):
    service = get_ai_model_service()
    try:
        updated_ver = service.deactivate_model(model_id, version)
        return updated_ver
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{model_id}/compare", response_model=VersionComparisonResult, summary="Compare two model versions side-by-side")
async def compare_versions(
    model_id: str,
    v1: str = Query(..., description="First version identifier (e.g. 'v1.2.0')"),
    v2: str = Query(..., description="Second version identifier (e.g. 'v1.3.0-rc')"),
):
    service = get_ai_model_service()
    try:
        comparison = service.compare_versions(model_id, v1, v2)
        return comparison
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
