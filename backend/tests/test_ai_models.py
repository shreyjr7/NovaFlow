"""
Unit tests for AI Model Management (Phase 32)
=============================================
Validates:
  1. Registry of all 6 core AI models:
       - Road Defect Detection
       - Vehicle Detection
       - Vehicle Tracking
       - Pedestrian Detection
       - Plate Detection
       - OCR
  2. Model version inspection:
       - Model Name, Version, Task, Dataset, Accuracy Metrics, Deployment Status, Last Updated
  3. Side-by-side version comparison with metric diffs.
  4. STRICT DEPLOYMENT SAFETY GUARDRAIL:
       "Do not automatically deploy an unvalidated model."
       Asserts HTTP 400 rejection when attempting to activate an unvalidated candidate.
  5. Activating and deactivating validated models.
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_list_all_six_ai_models():
    """Validates that all 6 core models are registered with required attributes."""
    res = client.get("/api/v1/ai-models")
    assert res.status_code == 200
    models = res.json()

    assert len(models) == 6
    expected_names = {
        "Road Defect Detection",
        "Vehicle Detection",
        "Vehicle Tracking",
        "Pedestrian Detection",
        "Plate Detection",
        "OCR",
    }
    actual_names = {m["name"] for m in models}
    assert expected_names == actual_names

    for m in models:
        assert m["model_id"]
        assert m["current_active_version"]
        assert m["task"]
        assert m["dataset"]
        assert m["accuracy_metrics"]
        assert m["deployment_status"] == "ACTIVE"
        assert m["last_updated"]


def test_view_model_version_history():
    """Validates detailed model inspection and version history."""
    res = client.get("/api/v1/ai-models/road-defect-detection")
    assert res.status_code == 200
    detail = res.json()

    assert detail["name"] == "Road Defect Detection"
    versions = detail["versions"]
    assert len(versions) >= 3
    v_names = [v["version"] for v in versions]
    assert "v1.2.0" in v_names
    assert "v1.3.0-rc" in v_names
    assert "v1.4.0-exp" in v_names


def test_strict_unvalidated_model_deployment_guardrail():
    """
    CRITICAL SAFETY GUARDRAIL TEST:
    "Do not automatically deploy an unvalidated model."
    Attempting to activate 'v1.4.0-exp' (is_validated = False, status = VALIDATING)
    MUST be rejected with HTTP 400 Bad Request.
    """
    res = client.post("/api/v1/ai-models/road-defect-detection/versions/v1.4.0-exp/activate")
    assert res.status_code == 400
    err = res.json()["detail"]
    assert "UNVALIDATED_MODEL_DEPLOYMENT_PROHIBITED" in err
    assert "unvalidated" in err.lower()


def test_activate_validated_model():
    """Validates that activating a validated candidate (v1.3.0-rc) succeeds."""
    res = client.post("/api/v1/ai-models/road-defect-detection/versions/v1.3.0-rc/activate")
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == "v1.3.0-rc"
    assert data["deployment_status"] == "ACTIVE"

    # Verify model active version updated
    model_res = client.get("/api/v1/ai-models/road-defect-detection")
    assert model_res.status_code == 200
    assert model_res.json()["current_active_version"] == "v1.3.0-rc"


def test_deactivate_model():
    """Validates deactivating a model version."""
    res = client.post("/api/v1/ai-models/road-defect-detection/versions/v1.2.0/deactivate")
    assert res.status_code == 200
    assert res.json()["deployment_status"] == "INACTIVE"


def test_compare_versions():
    """Validates side-by-side metric comparison between two model versions."""
    res = client.get("/api/v1/ai-models/road-defect-detection/compare?v1=v1.2.0&v2=v1.3.0-rc")
    assert res.status_code == 200
    diff = res.json()

    assert diff["model_id"] == "road-defect-detection"
    assert diff["version_a"]["version"] == "v1.2.0"
    assert diff["version_b"]["version"] == "v1.3.0-rc"
    assert "metric_differences" in diff
    assert "mAP_50" in diff["metric_differences"]
    assert diff["metric_differences"]["mAP_50"] > 0  # v1.3.0-rc has higher mAP
    assert diff["recommendation"]
