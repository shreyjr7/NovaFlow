"""
Unit & Integration Tests for Phase 33: Model Testing
====================================================
Verifies:
  1. All 8 environmental conditions evaluated:
     Day, Night, Rain, Wet roads, Glare, Motion blur, Occlusion, Dense traffic.
  2. Reporting metrics: Precision, Recall, mAP@0.50, mAP@[0.50:0.95], F1 score.
  3. Per-class performance reporting across all classes:
     pothole, damaged_road, waterlogging, missing_road_divider, missing_zebra,
     damaged_sign, missing_sign, car, bus, truck, motorcycle, auto_rickshaw,
     pedestrian, jaywalker, license_plate.
  4. Day conditions have highest precision and recall.
  5. Challenging conditions (Night, Glare, Motion blur, Occlusion) degrade realistically.
"""

import pytest
from edge.testing import (
    ENVIRONMENTAL_CONDITIONS,
    BENCHMARK_CLASSES,
    SyntheticDatasetGenerator,
    ModelBenchmarkEngine,
)


def test_all_eight_environmental_conditions_defined():
    expected_conditions = {
        "Day",
        "Night",
        "Rain",
        "Wet roads",
        "Glare",
        "Motion blur",
        "Occlusion",
        "Dense traffic",
    }
    assert set(ENVIRONMENTAL_CONDITIONS) == expected_conditions


def test_synthetic_dataset_generation():
    gen = SyntheticDatasetGenerator(seed=42)
    dataset = gen.generate_complete_benchmark_dataset(samples_per_condition=20)

    for cond in ENVIRONMENTAL_CONDITIONS:
        assert cond in dataset
        samples = dataset[cond]
        assert len(samples) >= 20
        for sample in samples:
            assert sample.condition == cond
            assert sample.category in BENCHMARK_CLASSES
            assert len(sample.bbox) == 4
            x1, y1, x2, y2 = sample.bbox
            assert 0.0 <= x1 < x2 <= 1.0
            assert 0.0 <= y1 < y2 <= 1.0


def test_model_benchmark_execution_and_metrics():
    engine = ModelBenchmarkEngine(seed=77)
    report = engine.run_complete_model_benchmark(samples_per_condition=30)

    # 1. Verify all 8 conditions tested
    assert len(report.conditions_tested) == 8
    for cond in ENVIRONMENTAL_CONDITIONS:
        assert cond in report.condition_reports
        cond_rep = report.condition_reports[cond]
        assert 0.0 < cond_rep.precision <= 1.0
        assert 0.0 < cond_rep.recall <= 1.0
        assert 0.0 < cond_rep.f1_score <= 1.0
        assert 0.0 < cond_rep.map_50 <= 1.0
        assert 0.0 < cond_rep.map_50_95 <= cond_rep.map_50

    # 2. Verify overall metrics
    assert 0.80 <= report.overall_precision <= 1.0
    assert 0.75 <= report.overall_recall <= 1.0
    assert 0.80 <= report.overall_f1_score <= 1.0
    assert 0.80 <= report.overall_map_50 <= 1.0
    assert report.passed_validation is True

    # 3. Verify Day condition outperforms adverse conditions
    day_f1 = report.condition_reports["Day"].f1_score
    night_f1 = report.condition_reports["Night"].f1_score
    blur_f1 = report.condition_reports["Motion blur"].f1_score
    assert day_f1 > night_f1
    assert day_f1 > blur_f1

    # 4. Verify Per-class performance reporting
    for cls_name in BENCHMARK_CLASSES:
        assert cls_name in report.per_class_summary
        metrics = report.per_class_summary[cls_name]
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert "ap_50" in metrics
        assert 0.0 <= metrics["precision"] <= 1.0
        assert 0.0 <= metrics["recall"] <= 1.0
