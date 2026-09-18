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


# =====================================================================
# PHASE 8 — ANPR SPECIFIC TESTS (Steps 21, 22, 23)
# =====================================================================

from edge.anpr.pipeline import AnprState, PlateState, PlateNumberStr, PIPELINE_STAGES


def test_step21_six_stage_anpr_pipeline():
    """
    Step 21 — Detect number plates
    Pipeline:
      Vehicle -> Plate detector -> Plate crop -> Perspective correction -> OCR -> Validation
    Recommended: YOLO + PaddleOCR/EasyOCR
    """
    pipeline = AnprPipeline(bus_id="BUS_102", camera_id="FRONT")

    # 6 stages verification
    assert PIPELINE_STAGES == [
        "vehicle",
        "plate_detector",
        "plate_crop",
        "perspective_correction",
        "ocr",
        "validation",
    ]

    candidate = {
        "frame_idx": 1,
        "sharpness": 180.0,
        "detection_confidence": 0.95,
        "ocr_text": "UP 65 AB 1234",
        "plate_present": True,
        "plate_bbox": [120, 150, 320, 210],
    }
    gps = {"lat": 25.3176, "lon": 82.9739, "road_segment": "UP_VNS_01"}
    vehicle_info = {"class": "car", "track_id": 42}

    record = pipeline.run_six_stage_pipeline(
        candidate_frames=[candidate],
        gps=gps,
        incident_vehicle_info=vehicle_info,
    )

    # Verify all 6 stages completed
    assert record.stages_completed == PIPELINE_STAGES
    assert "vehicle" in record.stage_details
    assert record.stage_details["vehicle"]["class"] == "car"
    assert record.stage_details["plate_detector"]["model"] == "YOLOv8-plate"
    assert record.stage_details["plate_detector"]["plate_detected"] is True
    assert record.stage_details["plate_crop"]["cropped"] is True
    assert record.stage_details["perspective_correction"]["rectified"] is True
    assert "PaddleOCR" in record.stage_details["ocr"]["engine"]
    assert record.stage_details["validation"]["is_valid"] is True
    assert record.registration_number == "UP 65 AB 1234"


def test_step22_confidence_score_and_human_verification_gate():
    """
    Step 22 — Add confidence score
    Example:
      UP65AB1234
      Confidence: 94% -> Automated verification passed
      If:
      Confidence: 48% -> Human verification required.
    """
    pipeline = AnprPipeline(bus_id="BUS_102", camera_id="FRONT")
    gps = {"lat": 25.3176, "lon": 82.9739, "road_segment": "UP_VNS_01"}

    # Case A: UP65AB1234 with 94% confidence (0.94)
    cand_high = {
        "sharpness": 190.0,
        "detection_confidence": 0.96,
        "ocr_text": "UP 65 AB 1234",
        "plate_present": True,
    }
    rec_high = pipeline.run_pipeline(
        candidate_frames=[cand_high],
        gps=gps,
        forced_confidence=0.94,
    )
    assert rec_high.confidence == 0.94
    assert rec_high.human_verification_required is False
    assert rec_high.verification_notice == "Automated verification passed"
    assert rec_high.auto_publish is True
    assert rec_high.quarantined is False
    assert rec_high.state == AnprState.PLATE_RECOGNIZED
    assert rec_high.display_state == "Plate recognized"
    assert rec_high.registration_number == "UP 65 AB 1234"

    # Case B: UP65AB1234 with 48% confidence (0.48)
    cand_low = {
        "sharpness": 40.0,
        "detection_confidence": 0.55,
        "ocr_text": "UP 65 AB 1234",
        "plate_present": True,
        "simulate_low_confidence": True,
    }
    rec_low = pipeline.run_pipeline(
        candidate_frames=[cand_low],
        gps=gps,
        forced_confidence=0.48,
    )
    assert rec_low.confidence == 0.48
    # Human verification required!
    assert rec_low.human_verification_required is True
    assert rec_low.verification_notice == "Human verification required"
    assert rec_low.auto_publish is False
    assert rec_low.quarantined is True
    assert rec_low.state == AnprState.LOW_CONFIDENCE
    assert rec_low.display_state == "Low confidence"


def test_step23_five_plate_states_and_no_hallucination():
    """
    Step 23 — Handle unreadable plates
    Support 5 explicit states:
      1. Plate detected
      2. Plate recognized
      3. Low confidence
      4. Unreadable
      5. No plate visible
    Rule: Don't force the OCR system to produce a number when it can't (No hallucination).
    """
    pipeline = AnprPipeline(bus_id="BUS_202", camera_id="FRONT")
    gps = {"lat": 28.6139, "lon": 77.2090, "road_segment": "DEL_01"}

    # 1. Plate recognized (high confidence, valid syntax)
    rec_recognized = pipeline.run_pipeline(
        candidate_frames=[{"sharpness": 175.0, "detection_confidence": 0.95, "ocr_text": "DL 01 AB 1234"}],
        gps=gps,
        forced_confidence=0.92,
    )
    assert rec_recognized.state == AnprState.PLATE_RECOGNIZED
    assert rec_recognized.display_state == "Plate recognized"
    assert rec_recognized.registration_number == "DL 01 AB 1234"

    # 2. Low confidence (readable format but degraded confidence e.g. 48%)
    rec_low = pipeline.run_pipeline(
        candidate_frames=[{"sharpness": 50.0, "detection_confidence": 0.60, "ocr_text": "MH 12 RN 5678"}],
        gps=gps,
        forced_confidence=0.48,
    )
    assert rec_low.state == AnprState.LOW_CONFIDENCE
    assert rec_low.display_state == "Low confidence"
    assert rec_low.human_verification_required is True

    # 3. Unreadable (OCR cannot decipher garbled characters, severely damaged/occluded)
    # Don't force/hallucinate a plate number!
    rec_unreadable = pipeline.run_pipeline(
        candidate_frames=[{"sharpness": 20.0, "detection_confidence": 0.45, "ocr_text": "?? #$ 99", "unreadable": True}],
        gps=gps,
        forced_confidence=0.25,
    )
    assert rec_unreadable.state == AnprState.UNREADABLE
    assert rec_unreadable.display_state == "Unreadable"
    assert rec_unreadable.registration_number == "UNREADABLE", "Must NOT hallucinate a number for unreadable plates!"
    assert rec_unreadable.human_verification_required is True
    assert rec_unreadable.auto_publish is False

    # 4. No plate visible (missing or completely hidden plate)
    # Don't force/hallucinate a plate number!
    rec_no_plate = pipeline.run_pipeline(
        candidate_frames=[],
        gps=gps,
        force_missing_plate=True,
    )
    assert rec_no_plate.state == AnprState.NO_PLATE_VISIBLE
    assert rec_no_plate.display_state == "No plate visible"
    assert rec_no_plate.registration_number == "NO_PLATE_VISIBLE", "Must NOT invent a number when no plate is visible!"
    assert rec_no_plate.confidence == 0.0

    # 5. Plate detected state definition & polymorphic comparison
    detected_state = PlateState("PLATE_DETECTED")
    assert detected_state == "Plate detected"
    assert detected_state == "PLATE_DETECTED"
    assert detected_state.display_name == "Plate detected"


def test_phase3_standard_event_format_anpr():
    """Verify ANPR record generates canonical Phase 3 10-key standard event dictionary."""
    pipeline = AnprPipeline(bus_id="BUS-102", camera_id="FRONT")
    gps = {"lat": 28.6139, "lon": 77.2090, "road_segment": "R-12"}

    rec = pipeline.run_pipeline(
        candidate_frames=[{"sharpness": 180.0, "detection_confidence": 0.95, "ocr_text": "UP 65 AB 1234"}],
        gps=gps,
        forced_confidence=0.94,
    )

    evt = rec.to_standard_dict()
    assert set(evt.keys()) == {
        "eventId", "type", "confidence", "latitude", "longitude",
        "timestamp", "busId", "routeId", "severity", "status",
    }
    assert evt["type"] == "anpr"
    assert evt["confidence"] == 0.94
    assert evt["latitude"] == 28.6139
    assert evt["longitude"] == 77.2090
    assert evt["busId"] == "BUS-102"
    assert evt["routeId"] == "R-12"
    assert evt["status"] == "confirmed"
