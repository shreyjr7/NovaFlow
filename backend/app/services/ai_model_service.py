"""
AI Model Management Service (Phase 32)
======================================
Manages edge and centralized machine learning models:
  1. Road Defect Detection
  2. Vehicle Detection
  3. Vehicle Tracking
  4. Pedestrian Detection
  5. Plate Detection
  6. OCR

Capabilities:
  - View model metadata: Model Name, Version, Task, Dataset, Accuracy Metrics, Deployment Status, Last Updated.
  - Activate model (with strict validation safety gate).
  - Deactivate model.
  - Compare versions side-by-side.

STRICT SAFETY GUARDRAIL:
  "Do not automatically deploy an unvalidated model."
  Attempts to activate unvalidated models are rejected with UNVALIDATED_MODEL_DEPLOYMENT_PROHIBITED.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ModelVersion(BaseModel):
    version: str
    release_date: str
    task: str
    dataset: str
    dataset_size: str
    accuracy_metrics: Dict[str, Any]  # mAP, precision, recall, latency, fps, etc.
    deployment_status: str  # ACTIVE, INACTIVE, STAGING, VALIDATING, REJECTED
    is_validated: bool
    validation_notes: Optional[str] = None
    parameters_millions: float
    weights_sha256: str


class AIModelSummary(BaseModel):
    model_id: str
    name: str
    current_active_version: str
    task: str
    dataset: str
    accuracy_metrics: Dict[str, Any]
    deployment_status: str  # ACTIVE, INACTIVE, VALIDATING
    last_updated: str
    versions_count: int


class AIModelDetail(BaseModel):
    model_id: str
    name: str
    current_active_version: str
    task: str
    dataset: str
    versions: List[ModelVersion]
    last_updated: str


class VersionComparisonResult(BaseModel):
    model_id: str
    model_name: str
    version_a: ModelVersion
    version_b: ModelVersion
    metric_differences: Dict[str, Any]
    recommendation: str


class AIModelManagementService:
    """Manages versioning, validation, activation, and safety gates for AI models."""

    def __init__(self):
        self._models: Dict[str, AIModelDetail] = {
            "road-defect-detection": AIModelDetail(
                model_id="road-defect-detection",
                name="Road Defect Detection",
                current_active_version="v1.2.0",
                task="Pothole & Surface Damage Detection",
                dataset="CityRoads-v4 (85k frames)",
                last_updated="2 days ago",
                versions=[
                    ModelVersion(
                        version="v1.2.0",
                        release_date="2026-08-20",
                        task="Pothole & Surface Damage Detection",
                        dataset="CityRoads-v4",
                        dataset_size="85,000 annotated frames",
                        accuracy_metrics={"mAP_50": 0.912, "precision": 0.894, "recall": 0.881, "latency_ms": 16.2, "fps": 29.5},
                        deployment_status="ACTIVE",
                        is_validated=True,
                        validation_notes="Passed edge Jetson Orin 100-hour stress benchmark (0 crashes).",
                        parameters_millions=11.2,
                        weights_sha256="7a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b",
                    ),
                    ModelVersion(
                        version="v1.3.0-rc",
                        release_date="2026-09-10",
                        task="Pothole & Surface Damage Detection",
                        dataset="CityRoads-v5",
                        dataset_size="110,000 annotated frames",
                        accuracy_metrics={"mAP_50": 0.934, "precision": 0.918, "recall": 0.905, "latency_ms": 15.8, "fps": 30.2},
                        deployment_status="STAGING",
                        is_validated=True,
                        validation_notes="Pre-production validation complete. Recommended for deployment.",
                        parameters_millions=11.4,
                        weights_sha256="9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e",
                    ),
                    ModelVersion(
                        version="v1.4.0-exp",
                        release_date="2026-09-14",
                        task="Pothole & Surface Damage Detection",
                        dataset="CityRoads-v6-Alpha",
                        dataset_size="140,000 raw frames",
                        accuracy_metrics={"mAP_50": 0.820, "precision": 0.790, "recall": 0.760, "latency_ms": 19.5, "fps": 22.0},
                        deployment_status="VALIDATING",
                        is_validated=False,
                        validation_notes="Under active testbed validation. NOT APPROVED for production.",
                        parameters_millions=14.8,
                        weights_sha256="1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
                    ),
                ],
            ),
            "vehicle-detection": AIModelDetail(
                model_id="vehicle-detection",
                name="Vehicle Detection",
                current_active_version="v2.1.0",
                task="Multi-Class Traffic Object Detection",
                dataset="UrbanTraffic-v3 (120k annotations)",
                last_updated="1 week ago",
                versions=[
                    ModelVersion(
                        version="v2.1.0",
                        release_date="2026-08-15",
                        task="Multi-Class Traffic Object Detection",
                        dataset="UrbanTraffic-v3",
                        dataset_size="120,000 annotations",
                        accuracy_metrics={"mAP_50": 0.945, "precision": 0.932, "recall": 0.920, "latency_ms": 14.5, "fps": 31.0},
                        deployment_status="ACTIVE",
                        is_validated=True,
                        validation_notes="Fully validated against diurnal daylight and nighttime runs.",
                        parameters_millions=12.5,
                        weights_sha256="3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c",
                    ),
                    ModelVersion(
                        version="v2.2.0-beta",
                        release_date="2026-09-12",
                        task="Multi-Class Traffic Object Detection",
                        dataset="UrbanTraffic-v4-Preview",
                        dataset_size="160,000 annotations",
                        accuracy_metrics={"mAP_50": 0.910, "precision": 0.880, "recall": 0.865, "latency_ms": 17.0, "fps": 26.5},
                        deployment_status="VALIDATING",
                        is_validated=False,
                        validation_notes="Incomplete rain interference benchmarks.",
                        parameters_millions=13.0,
                        weights_sha256="4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d",
                    ),
                ],
            ),
            "vehicle-tracking": AIModelDetail(
                model_id="vehicle-tracking",
                name="Vehicle Tracking",
                current_active_version="v1.4.2",
                task="Multi-Object Kinematic Trajectory Tracking",
                dataset="ArterialMOT-v2 (40 sequences)",
                last_updated="2 weeks ago",
                versions=[
                    ModelVersion(
                        version="v1.4.2",
                        release_date="2026-08-01",
                        task="Multi-Object Kinematic Trajectory Tracking",
                        dataset="ArterialMOT-v2",
                        dataset_size="40 full sequences",
                        accuracy_metrics={"mota": 0.884, "idf1": 0.865, "latency_ms": 8.5, "fps": 28.0},
                        deployment_status="ACTIVE",
                        is_validated=True,
                        validation_notes="Zero ID switches during multi-lane occlusions.",
                        parameters_millions=4.2,
                        weights_sha256="5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e",
                    ),
                    ModelVersion(
                        version="v1.5.0",
                        release_date="2026-09-08",
                        task="Multi-Object Kinematic Trajectory Tracking",
                        dataset="ArterialMOT-v3",
                        dataset_size="60 full sequences",
                        accuracy_metrics={"mota": 0.902, "idf1": 0.880, "latency_ms": 8.2, "fps": 29.5},
                        deployment_status="STAGING",
                        is_validated=True,
                        validation_notes="Benchmark passed. Ready for fleet roll-out.",
                        parameters_millions=4.5,
                        weights_sha256="6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f",
                    ),
                ],
            ),
            "pedestrian-detection": AIModelDetail(
                model_id="pedestrian-detection",
                name="Pedestrian Detection",
                current_active_version="v2.0.1",
                task="Vulnerable Road User & Crosswalk Conflict",
                dataset="PedSafeCity-v1 (50k frames)",
                last_updated="3 days ago",
                versions=[
                    ModelVersion(
                        version="v2.0.1",
                        release_date="2026-08-10",
                        task="Vulnerable Road User & Crosswalk Conflict",
                        dataset="PedSafeCity-v1",
                        dataset_size="50,000 frames",
                        accuracy_metrics={"mAP_50": 0.928, "precision": 0.915, "recall": 0.902, "latency_ms": 15.1, "fps": 30.0},
                        deployment_status="ACTIVE",
                        is_validated=True,
                        validation_notes="Verified on crosswalks and mid-block jaywalking scenarios.",
                        parameters_millions=11.8,
                        weights_sha256="7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a",
                    ),
                    ModelVersion(
                        version="v2.1.0-rc",
                        release_date="2026-09-05",
                        task="Vulnerable Road User & Crosswalk Conflict",
                        dataset="PedSafeCity-v2",
                        dataset_size="75,000 frames",
                        accuracy_metrics={"mAP_50": 0.942, "precision": 0.930, "recall": 0.918, "latency_ms": 14.8, "fps": 31.0},
                        deployment_status="STAGING",
                        is_validated=True,
                        validation_notes="High night-time detection accuracy in low-light school zones.",
                        parameters_millions=12.0,
                        weights_sha256="8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b",
                    ),
                ],
            ),
            "plate-detection": AIModelDetail(
                model_id="plate-detection",
                name="Plate Detection",
                current_active_version="v1.8.0",
                task="License Plate Localization",
                dataset="IndiaLPR-v2 (60k vehicles)",
                last_updated="1 month ago",
                versions=[
                    ModelVersion(
                        version="v1.8.0",
                        release_date="2026-07-25",
                        task="License Plate Localization",
                        dataset="IndiaLPR-v2",
                        dataset_size="60,000 vehicles",
                        accuracy_metrics={"mAP_50": 0.958, "precision": 0.941, "recall": 0.938, "latency_ms": 12.0, "fps": 32.0},
                        deployment_status="ACTIVE",
                        is_validated=True,
                        validation_notes="Confirmed localization accuracy across high-speed bus lanes.",
                        parameters_millions=9.2,
                        weights_sha256="9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c",
                    ),
                    ModelVersion(
                        version="v1.9.0-exp",
                        release_date="2026-09-13",
                        task="License Plate Localization",
                        dataset="IndiaLPR-v3-Alpha",
                        dataset_size="80,000 vehicles",
                        accuracy_metrics={"mAP_50": 0.890, "precision": 0.870, "recall": 0.850, "latency_ms": 14.0, "fps": 27.0},
                        deployment_status="VALIDATING",
                        is_validated=False,
                        validation_notes="Fails high-glare validation threshold.",
                        parameters_millions=10.0,
                        weights_sha256="0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d",
                    ),
                ],
            ),
            "ocr": AIModelDetail(
                model_id="ocr",
                name="OCR",
                current_active_version="v2.3.0",
                task="High-Speed Plate Character Recognition",
                dataset="LPR-Text-v3 (140k plates)",
                last_updated="1 month ago",
                versions=[
                    ModelVersion(
                        version="v2.3.0",
                        release_date="2026-07-28",
                        task="High-Speed Plate Character Recognition",
                        dataset="LPR-Text-v3",
                        dataset_size="140,000 plates",
                        accuracy_metrics={"char_acc": 0.982, "word_acc": 0.954, "latency_ms": 14.5, "fps": 26.0},
                        deployment_status="ACTIVE",
                        is_validated=True,
                        validation_notes="Meets 98% character recognition criteria on standard HSRP plates.",
                        parameters_millions=15.4,
                        weights_sha256="1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e",
                    ),
                    ModelVersion(
                        version="v2.4.0",
                        release_date="2026-09-02",
                        task="High-Speed Plate Character Recognition",
                        dataset="LPR-Text-v4",
                        dataset_size="190,000 plates",
                        accuracy_metrics={"char_acc": 0.989, "word_acc": 0.968, "latency_ms": 13.8, "fps": 28.0},
                        deployment_status="STAGING",
                        is_validated=True,
                        validation_notes="High-accuracy CRNN + Transformer architecture.",
                        parameters_millions=16.0,
                        weights_sha256="2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f",
                    ),
                ],
            ),
        }

    def list_models(self) -> List[AIModelSummary]:
        summaries = []
        for m in self._models.values():
            active_ver = next((v for v in m.versions if v.version == m.current_active_version), m.versions[0])
            summaries.append(
                AIModelSummary(
                    model_id=m.model_id,
                    name=m.name,
                    current_active_version=m.current_active_version,
                    task=m.task,
                    dataset=m.dataset,
                    accuracy_metrics=active_ver.accuracy_metrics,
                    deployment_status=active_ver.deployment_status,
                    last_updated=m.last_updated,
                    versions_count=len(m.versions),
                )
            )
        return summaries

    def get_model(self, model_id: str) -> Optional[AIModelDetail]:
        return self._models.get(model_id)

    def activate_model(self, model_id: str, version_str: str) -> ModelVersion:
        """
        Activates a model version for edge deployment.
        Enforces strict validation safety guardrail:
          "Do not automatically deploy an unvalidated model."
        """
        model = self.get_model(model_id)
        if not model:
            raise KeyError(f"AI Model {model_id} not found.")

        target_ver = next((v for v in model.versions if v.version == version_str), None)
        if not target_ver:
            raise KeyError(f"Version {version_str} not found for model {model_id}.")

        # Guardrail check
        if not target_ver.is_validated or target_ver.deployment_status == "VALIDATING":
            raise ValueError(
                f"UNVALIDATED_MODEL_DEPLOYMENT_PROHIBITED: Model '{model.name}' version '{version_str}' "
                f"is unvalidated (status: {target_ver.deployment_status}). "
                "Models must pass edge hardware benchmark validation before deployment to active bus fleets."
            )

        # Deactivate current active version
        for v in model.versions:
            if v.deployment_status == "ACTIVE":
                v.deployment_status = "INACTIVE"

        # Activate target version
        target_ver.deployment_status = "ACTIVE"
        model.current_active_version = target_ver.version
        model.last_updated = "Just now"

        return target_ver

    def deactivate_model(self, model_id: str, version_str: str) -> ModelVersion:
        model = self.get_model(model_id)
        if not model:
            raise KeyError(f"AI Model {model_id} not found.")

        target_ver = next((v for v in model.versions if v.version == version_str), None)
        if not target_ver:
            raise KeyError(f"Version {version_str} not found for model {model_id}.")

        target_ver.deployment_status = "INACTIVE"
        model.last_updated = "Just now"
        return target_ver

    def compare_versions(self, model_id: str, v1: str, v2: str) -> VersionComparisonResult:
        model = self.get_model(model_id)
        if not model:
            raise KeyError(f"AI Model {model_id} not found.")

        ver_a = next((v for v in model.versions if v.version == v1), None)
        ver_b = next((v for v in model.versions if v.version == v2), None)

        if not ver_a or not ver_b:
            raise KeyError(f"One or both versions ({v1}, {v2}) not found for model {model_id}.")

        # Calculate metric differences
        diffs = {}
        all_metric_keys = set(ver_a.accuracy_metrics.keys()).union(ver_b.accuracy_metrics.keys())
        for k in all_metric_keys:
            val_a = ver_a.accuracy_metrics.get(k)
            val_b = ver_b.accuracy_metrics.get(k)
            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                diffs[k] = round(val_b - val_a, 4)

        diffs["parameters_diff_millions"] = round(ver_b.parameters_millions - ver_a.parameters_millions, 2)

        # Generate recommendation
        rec = (
            f"Version {v2} is validated and demonstrates improved accuracy metrics."
            if ver_b.is_validated
            else f"CAUTION: Version {v2} is UNVALIDATED. Not recommended for production activation."
        )

        return VersionComparisonResult(
            model_id=model.model_id,
            model_name=model.name,
            version_a=ver_a,
            version_b=ver_b,
            metric_differences=diffs,
            recommendation=rec,
        )


# Singleton provider
_ai_model_service: Optional[AIModelManagementService] = None

def get_ai_model_service() -> AIModelManagementService:
    global _ai_model_service
    if _ai_model_service is None:
        _ai_model_service = AIModelManagementService()
    return _ai_model_service
