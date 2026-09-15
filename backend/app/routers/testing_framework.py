"""
Testing Framework REST API Router (Phase 33)
============================================
Exposes programmatic execution and telemetry endpoints for:
  - Model environmental stress tests (Day, Night, Rain, Wet roads, Glare, Motion blur, Occlusion, Dense traffic)
  - System 7-hop end-to-end trace (Video -> Edge AI -> Event -> Network -> Backend -> Database -> GIS)
  - Concurrency load testing (10, 50, 100, 500 buses)
  - Failure fault-injection suite (6 failure modes)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from starlette.testclient import TestClient

from edge.testing import ModelBenchmarkEngine
from ..testing import SystemTraceTester, LoadTestEngine, FailureInjectionSuite

logger = logging.getLogger("routers.testing_framework")
router = APIRouter()

# Keep latest benchmark reports in memory for dashboard viewing
_LATEST_REPORTS: Dict[str, Any] = {
    "model_testing": None,
    "system_trace": None,
    "load_testing": None,
    "failure_resilience": None,
}


@router.get("/status", summary="Get overall testing framework status and latest benchmark metrics")
async def get_testing_status() -> Dict[str, Any]:
    return {
        "status": "OPERATIONAL",
        "pillars": {
            "model_testing": {"conditions_count": 8, "has_run": _LATEST_REPORTS["model_testing"] is not None},
            "system_trace": {"hops_count": 7, "has_run": _LATEST_REPORTS["system_trace"] is not None},
            "load_testing": {"scales": [10, 50, 100, 500], "has_run": _LATEST_REPORTS["load_testing"] is not None},
            "failure_resilience": {"failure_modes": 6, "has_run": _LATEST_REPORTS["failure_resilience"] is not None},
        },
        "latest_reports": _LATEST_REPORTS,
    }


@router.post("/model-benchmark", summary="Run computer vision model benchmark across 8 environmental conditions")
async def run_model_benchmark(samples_per_condition: int = Query(35, ge=10, le=100)) -> Dict[str, Any]:
    engine = ModelBenchmarkEngine()
    report = engine.run_complete_model_benchmark(samples_per_condition=samples_per_condition)

    out = {
        "overall_precision": report.overall_precision,
        "overall_recall": report.overall_recall,
        "overall_f1_score": report.overall_f1_score,
        "overall_map_50": report.overall_map_50,
        "overall_map_50_95": report.overall_map_50_95,
        "conditions_tested": report.conditions_tested,
        "passed_validation": report.passed_validation,
        "summary_notes": report.summary_notes,
        "condition_reports": {
            c: {
                "condition": r.condition,
                "precision": r.precision,
                "recall": r.recall,
                "f1_score": r.f1_score,
                "map_50": r.map_50,
                "map_50_95": r.map_50_95,
                "tp": r.tp,
                "fp": r.fp,
                "fn": r.fn,
            }
            for c, r in report.condition_reports.items()
        },
        "per_class_summary": report.per_class_summary,
    }
    _LATEST_REPORTS["model_testing"] = out
    return out


@router.post("/system-trace", summary="Execute full 7-hop end-to-end pipeline validation trace")
async def run_system_trace(
    event_type: str = Query("POTHOLE"),
    bus_id: str = Query("BUS_104"),
    route_id: str = Query("ROUTE_12"),
) -> Dict[str, Any]:
    from ..main import app
    client = TestClient(app)
    tester = SystemTraceTester(client=client)
    report = tester.run_trace(event_type=event_type, bus_id=bus_id, route_id=route_id)

    out = {
        "trace_id": report.trace_id,
        "event_id": report.event_id,
        "overall_status": report.overall_status,
        "total_pipeline_latency_ms": report.total_pipeline_latency_ms,
        "verified_in_gis": report.verified_in_gis,
        "timestamp": report.timestamp,
        "summary": report.summary,
        "hops": [
            {
                "hop_number": h.hop_number,
                "name": h.name,
                "component": h.component,
                "status": h.status,
                "latency_ms": h.latency_ms,
                "details": h.details,
            }
            for h in report.hops
        ],
    }
    _LATEST_REPORTS["system_trace"] = out
    return out


@router.post("/load-test", summary="Execute multi-bus concurrency load simulation (10, 50, 100, 500 buses)")
async def run_load_test(
    num_buses: int = Query(50, ge=10, le=500),
    events_per_bus: int = Query(2, ge=1, le=10),
) -> Dict[str, Any]:
    from ..main import app
    client = TestClient(app)
    engine = LoadTestEngine(client=client)
    report = engine.run_load_test(num_buses=num_buses, events_per_bus=events_per_bus)

    out = {
        "test_id": report.test_id,
        "simulated_buses": report.simulated_buses,
        "total_events_generated": report.total_events_generated,
        "successful_ingestions": report.successful_ingestions,
        "failed_ingestions": report.failed_ingestions,
        "duration_seconds": report.duration_seconds,
        "throughput_eps": report.throughput_eps,
        "latency_min_ms": report.latency_min_ms,
        "latency_p50_ms": report.latency_p50_ms,
        "latency_p95_ms": report.latency_p95_ms,
        "latency_p99_ms": report.latency_p99_ms,
        "latency_max_ms": report.latency_max_ms,
        "error_rate_pct": report.error_rate_pct,
        "passed_slo": report.passed_slo,
        "timestamp": report.timestamp,
        "summary": report.summary,
    }
    _LATEST_REPORTS["load_testing"] = out
    return out


@router.post("/failure-scenarios", summary="Inject 6 failure modes and certify system resilience invariants")
async def run_failure_scenarios() -> Dict[str, Any]:
    from ..main import app
    client = TestClient(app)
    suite = FailureInjectionSuite(client=client)
    report = suite.run_all_failure_tests()

    out = {
        "suite_id": report.suite_id,
        "overall_resilience_status": report.overall_resilience_status,
        "scenarios_passed": report.scenarios_passed,
        "scenarios_total": report.scenarios_total,
        "invariants": {
            "events_are_not_lost": report.events_are_not_lost,
            "local_buffering_works": report.local_buffering_works,
            "system_reconnects_automatically": report.system_reconnects_automatically,
            "duplicate_events_prevented": report.duplicate_events_prevented,
        },
        "timestamp": report.timestamp,
        "summary": report.summary,
        "scenario_results": [
            {
                "scenario_name": r.scenario_name,
                "injected_failure": r.injected_failure,
                "status": r.status,
                "events_generated": r.events_generated,
                "events_buffered_locally": r.events_buffered_locally,
                "events_transmitted": r.events_transmitted,
                "zero_data_loss_verified": r.zero_data_loss_verified,
                "reconnection_verified": r.reconnection_verified,
                "duplicate_prevention_verified": r.duplicate_prevention_verified,
                "details": r.details,
            }
            for r in report.scenario_results
        ],
    }
    _LATEST_REPORTS["failure_resilience"] = out
    return out
