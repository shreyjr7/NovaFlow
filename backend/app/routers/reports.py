"""
Urban Intelligence Reports Router (Phase 29)
============================================
Exposes municipal reporting endpoints:
  - Generate adhoc or saved reports based on Date range, City, Zone, Route, and Event types.
  - Return all 10 mandatory diagnostic sections + charts + GIS data + data sources.
  - Download standard-compliant PDF binary documents.
  - Save reports to the persistent municipal archive.
  - Share reports with authorized users, role restrictions, and secure tokens.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status

from ..services.report_generator_service import (
    get_report_generator_service,
    ReportConfig,
    UrbanIntelligenceReport,
    ShareReportRequest,
    ShareRecord,
)

router = APIRouter()


@router.post("/generate", response_model=UrbanIntelligenceReport, summary="Generate an urban intelligence report based on selection criteria")
async def generate_report(
    config: ReportConfig,
    auto_save: bool = Query(False, description="Whether to automatically persist the generated report to the archive"),
):
    service = get_report_generator_service()
    report = service.generate_report(config)
    if auto_save:
        service.save_report(report)
    return report


@router.get("", response_model=List[UrbanIntelligenceReport], summary="List all saved urban intelligence reports")
async def list_reports():
    service = get_report_generator_service()
    return service.list_reports()


@router.get("/{report_id}", response_model=UrbanIntelligenceReport, summary="Get report details by report ID")
async def get_report(report_id: str):
    service = get_report_generator_service()
    report = service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found."
        )
    return report


@router.post("/{report_id}/save", response_model=UrbanIntelligenceReport, summary="Save an existing report to the municipal archive")
async def save_report(report_id: str):
    service = get_report_generator_service()
    report = service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found."
        )
    return service.save_report(report)


@router.get("/{report_id}/download-pdf", summary="Download official PDF version of the urban intelligence report")
async def download_pdf(report_id: str):
    service = get_report_generator_service()
    report = service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found."
        )

    try:
        pdf_bytes = service.generate_pdf(report_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )

    filename = f"Urban_Report_{report_id}_{report.city}_{report.config.date_range}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Id": report_id,
            "X-Report-Title": report.title,
        },
    )


@router.post("/{report_id}/share", response_model=ShareRecord, summary="Share report with authorized users with role restrictions")
async def share_report(report_id: str, share_req: ShareReportRequest):
    service = get_report_generator_service()
    try:
        record = service.share_report(report_id, share_req)
        return record
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found."
        )


@router.get("/shared/{share_token}", summary="Retrieve shared report via secure access token")
async def get_shared_report(share_token: str):
    service = get_report_generator_service()
    result = service.get_shared_report(share_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared report not found or link has expired."
        )
    return result
