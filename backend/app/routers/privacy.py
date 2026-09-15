"""
Privacy & Security API Router (Phase 26)
========================================
Endpoints for the 5-pillar Privacy Dashboard:
  - Data Retention (configurable policies & purge scheduler)
  - Camera Processing (local edge metrics)
  - Evidence Storage (encrypted storage stats)
  - Access Logs (immutable access audit ledger)
  - User Permissions (RBAC directory)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..services.privacy_service import (
    AccessLogEntry,
    EvidenceAccessLevel,
    RetentionPolicyConfig,
    RolePermission,
    UserRole,
    get_privacy_service,
)

router = APIRouter()


class EvidenceAccessRequestIn(BaseModel):
    user_id: str
    user_role: UserRole
    action: str = Field("VIEW_EVIDENCE_CLIP", description="Action to perform on clip")
    resource_id: str = Field(..., description="Evidence clip ID")
    justification: str = Field(..., description="Operational or legal justification")


@router.get("/dashboard")
async def get_privacy_dashboard_summary():
    """
    Returns high-level Privacy Dashboard data across all 5 pillars:
      Data Retention, Camera Processing, Evidence Storage, Access Logs, User Permissions.
    """
    service = get_privacy_service()
    return service.get_dashboard_summary()


@router.get("/retention-policies", response_model=RetentionPolicyConfig)
async def get_retention_policies():
    """Retrieves current configurable data retention policies."""
    service = get_privacy_service()
    return service.get_retention_policies()


@router.put("/retention-policies", response_model=RetentionPolicyConfig)
async def update_retention_policies(new_config: RetentionPolicyConfig, request: Request):
    """
    Updates configurable retention policies (raw frame buffer seconds, incident retention days, etc.).
    Logs an audit event in the immutable access ledger.
    """
    service = get_privacy_service()
    client_ip = request.client.host if request.client else "127.0.0.1"
    return service.update_retention_policies(new_config, admin_user="admin.security", ip=client_ip)


@router.get("/access-logs", response_model=List[AccessLogEntry])
async def list_access_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    action: Optional[str] = Query(None, description="Filter by action keyword"),
    limit: int = Query(50, ge=1, le=200),
):
    """Queries the immutable evidence and plate access audit ledger."""
    service = get_privacy_service()
    return service.list_access_logs(user_id=user_id, role=role, action=action, limit=limit)


@router.post("/evidence-access")
async def request_evidence_access(body: EvidenceAccessRequestIn, request: Request):
    """
    RBAC Gatekeeper endpoint:
      - Enforces role-based permissions for raw incident clip access.
      - Blocks unauthorized users (e.g. DISPATCHER cannot access unredacted raw clips).
      - Automatically logs the attempt in the immutable audit ledger.
    """
    service = get_privacy_service()
    client_ip = request.client.host if request.client else "127.0.0.1"
    result = service.verify_evidence_access(
        user_role=body.user_role,
        action=body.action,
        resource_id=body.resource_id,
        user_id=body.user_id,
        ip_address=client_ip,
        justification=body.justification,
    )
    if not result["allowed"]:
        raise HTTPException(
            status_code=403,
            detail=f"Access Denied: Role '{body.user_role.value}' lacks clearance to access unredacted raw evidence. {result['reason']}",
        )
    return result


@router.get("/roles", response_model=List[RolePermission])
async def list_user_roles():
    """Returns the RBAC permissions directory and evidence access levels."""
    service = get_privacy_service()
    return service.get_roles()


@router.post("/purge-expired")
async def trigger_retention_purge():
    """Executes manual/scheduled purge of expired raw video frames and unverified sensor logs."""
    service = get_privacy_service()
    return service.purge_expired_evidence()
