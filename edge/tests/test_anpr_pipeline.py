"""
Unit Tests for Vehicle Registration Recognition (ANPR) Edge Pipeline
=====================================================================
Tests:
  1. Indian format validator (Standard RTO, BH-series, State/UT codes)
  2. Positional OCR ambiguity correction ('0' vs 'O', '8' vs 'B', '1' vs 'I')
  3. Sharpest frame selection
  4. 4 operational states: READABLE, LOW_CONFIDENCE, NOT_READABLE, NOT_PRESENT
  5. Strict quarantine guardrail: Never auto-publish low-confidence plates
  6. Cryptographic SHA-256 evidence reference generation
"""

import pytest
from edge.anpr.format_validator import PlateFormatValidator, INDIAN_STATE_CODES
from edge.anpr.pipeline import AnprPipeline, HUMAN_VERIFICATION_NOTICE
from edge.anpr.perspective import PerspectiveCorrector


def test_format_validator_standard_rto():
    """Verify standard Indian RTO formats across various states."""
    validator = PlateFormatValidator()

    cases = [
        ("DL 01 AB 1234", "DL", "Delhi", "01", "AB", "1234"),
        ("MH12RN5678", "MH", "Maharashtra", "12", "RN", "5678"),
        ("KA-05-MN-9012", "KA", "Karnataka", "05", "MN", "9012"),
        ("HR 26 BC 3456", "HR", "Haryana", "26", "BC", "3456"),
        ("TN 07 H 1111", "TN", "Tamil Nadu", "07", "H", "1111"),
    ]

    for raw, exp_st, exp_st_name, exp_dist, exp_ser, exp_num in cases:
        res = validator.validate(raw)
        assert res.is_valid is True, f"Failed for {raw}: {res.issues}"
        assert res.format_type == "STANDARD_RTO"
        assert res.state_code == exp_st
        assert res.state_name == exp_st_name
        assert res.district_code == exp_dist
        assert res.series == exp_ser
        assert res.unique_number == exp_num


def test_format_validator_bh_series():
    """Verify Bharat (BH) series registration format."""
    validator = PlateFormatValidator()

    res = validator.validate("22 BH 1234 AA")
    assert res.is_valid is True
    assert res.format_type == "BHARAT_SERIES"
    assert res.district_code == "22"
    assert res.series == "AA"
    assert res.unique_number == "1234"

    res2 = validator.validate("23BH5678B")
    assert res2.is_valid is True
    assert res2.format_type == "BHARAT_SERIES"


def test_format_validator_ambiguity_recovery():
    """
    Verify positional syntax recovery:
      - 'O' in district number -> '0'
      - '0' in state code -> 'O'
      - 'B' in number part -> '8'
      - 'I' in number part -> '1'
    """
    validator = PlateFormatValidator()

    # 'O' instead of '0' in district
    res1 = validator.validate("DL O1 AB 1234")
    assert res1.is_valid is True
    assert res1.formatted_plate == "DL 01 AB 1234"
    assert res1.corrected_from_ambiguity is True

    # 'B' instead of '8' in last 4 digits
    res2 = validator.validate("KA 05 MN 901B")
    assert res2.is_valid is True
    assert res2.formatted_plate == "KA 05 MN 9018"
    assert res2.corrected_from_ambiguity is True


def test_format_validator_invalid_jurisdictions():
    """Unknown state prefixes and malformed strings must fail validation."""
    validator = PlateFormatValidator()

    # 'ZZ' is not an Indian state
    res1 = validator.validate("ZZ 01 AB 1234")
    assert res1.is_valid is False
    assert any("not registered in official Indian RTO database" in issue for issue in res1.issues)

    # Completely malformed
    res2 = validator.validate("HELLO_WORLD_123")
    assert res2.is_valid is False


def test_sharpest_frame_selection():
    """Verify pipeline selects the frame with highest sharpness score."""
    pipeline = AnprPipeline(bus_id="BUS_101", camera_id="FRONT")

    candidates = [
        {"frame_idx": 1, "sharpness": 42.0, "bbox": [100, 100, 200, 200]},
        {"frame_idx": 2, "sharpness": 185.4, "bbox": [100, 100, 200, 200]},  # Sharpest
        {"frame_idx": 3, "sharpness": 95.0, "bbox": [100, 100, 200, 200]},
    ]

    best, score = pipeline.select_sharpest_frame(candidates)
    assert best["frame_idx"] == 2
    assert score == 185.4


def test_anpr_pipeline_readable_state():
    """High quality candidate leads to READABLE state and auto-publish allowed."""
    pipeline = AnprPipeline(bus_id="BUS_101", camera_id="FRONT")

    candidate = {
        "frame_idx": 10,
        "sharpness": 170.0,
        "detection_confidence": 0.96,
        "ocr_text": "DL 01 AB 1234",
        "plate_present": True,
    }

    gps = {"lat": 28.6315, "lon": 77.2167, "road_segment": "DEL_CP_01"}
    record = pipeline.run_pipeline(candidate_frames=[candidate], gps=gps)

    assert record.state == "READABLE"
    assert record.confidence >= 0.85
    assert record.human_verification_required is False
    assert record.auto_publish is True
    assert record.quarantined is False
    assert record.registration_number == "DL 01 AB 1234"
    assert record.evidence_reference.startswith("ev_sha256_")


def test_anpr_pipeline_low_confidence_quarantine_guardrail():
    """
    CRITICAL USER REQUIREMENT:
      - Never automatically publish a low-confidence plate.
      - Show: 'Human verification required'.
    """
    pipeline = AnprPipeline(bus_id="BUS_204", camera_id="REAR")

    # Degraded sharpness & simulated OCR ambiguity
    candidate = {
        "frame_idx": 20,
        "sharpness": 55.0,
        "detection_confidence": 0.72,
        "ocr_text": "HR 26 BC 3456",
        "simulate_low_confidence": True,
        "plate_present": True,
    }

    gps = {"lat": 28.5672, "lon": 77.2100}
    record = pipeline.run_pipeline(candidate_frames=[candidate], gps=gps)

    assert record.state == "LOW_CONFIDENCE"
    assert 0.50 <= record.confidence < 0.85
    assert record.human_verification_required is True
    assert record.verification_notice == HUMAN_VERIFICATION_NOTICE
    assert record.auto_publish is False, "Low-confidence plate must NEVER be automatically published"
    assert record.quarantined is True, "Low-confidence plate must be quarantined"


def test_anpr_pipeline_not_readable_state():
    """Severely occluded or blurred plate leads to NOT_READABLE state."""
    pipeline = AnprPipeline(bus_id="BUS_108", camera_id="FRONT")

    candidate = {
        "frame_idx": 30,
        "sharpness": 15.0,
        "detection_confidence": 0.40,
        "ocr_text": "XX ?# 99",
        "simulate_low_confidence": True,
        "plate_present": True,
    }

    gps = {"lat": 28.6100, "lon": 77.2300}
    record = pipeline.run_pipeline(candidate_frames=[candidate], gps=gps)

    assert record.state == "NOT_READABLE"
    assert record.confidence < 0.50
    assert record.human_verification_required is True
    assert record.verification_notice == HUMAN_VERIFICATION_NOTICE
    assert record.auto_publish is False


def test_anpr_pipeline_not_present_state():
    """Vehicle with missing plate leads to NOT_PRESENT state."""
    pipeline = AnprPipeline(bus_id="BUS_112", camera_id="LEFT")

    gps = {"lat": 28.6500, "lon": 77.1900}
    record = pipeline.run_pipeline(
        candidate_frames=[],
        gps=gps,
        force_missing_plate=True,
    )

    assert record.state == "NOT_PRESENT"
    assert record.confidence == 0.0
    assert record.registration_number == "NOT_PRESENT"
    assert record.human_verification_required is False
    assert record.auto_publish is False
