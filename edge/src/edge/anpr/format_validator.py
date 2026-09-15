"""
Indian Vehicle Registration Number Plate Format Validator
=========================================================
Validates vehicle registration strings against statutory Indian Motor Vehicles Act
standards, including standard State/UT formats, Commercial formats, and Bharat (BH) series.

Format Specifications:
  1. Standard RTO Format:
     [STATE (2 letters)] [RTO/DISTRICT (1-2 digits)] [SERIES (1-3 letters)] [UNIQUE NUMBER (4 digits)]
     e.g., DL 01 AB 1234, MH 12 RN 5678, KA 05 MN 9012, HR 26 BC 3456

  2. Bharat (BH) Series Format (Uniform Central Series):
     [YEAR (2 digits)] BH [NUMBER (4 digits)] [SERIES (1-2 letters)]
     e.g., 22 BH 1234 AA, 23 BH 5678 B

  3. Positional Optical Character Ambiguity Correction:
     - '0' vs 'O'
     - '8' vs 'B'
     - '1' vs 'I'
     - '5' vs 'S'
     - '2' vs 'Z'
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# All 36 official Indian State & Union Territory ISO/RTO Codes
INDIAN_STATE_CODES = {
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CG": "Chhattisgarh",
    "CH": "Chandigarh",
    "DD": "Daman and Diu",
    "DL": "Delhi",
    "DN": "Dadra and Nagar Haveli",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HP": "Himachal Pradesh",
    "HR": "Haryana",
    "JH": "Jharkhand",
    "JK": "Jammu and Kashmir",
    "KA": "Karnataka",
    "KL": "Kerala",
    "LA": "Ladakh",
    "LD": "Lakshadweep",
    "MH": "Maharashtra",
    "ML": "Meghalaya",
    "MN": "Manipur",
    "MP": "Madhya Pradesh",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OD": "Odisha",
    "PB": "Punjab",
    "PY": "Puducherry",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TN": "Tamil Nadu",
    "TR": "Tripura",
    "TS": "Telangana",
    "UK": "Uttarakhand",
    "UP": "Uttar Pradesh",
    "WB": "West Bengal",
}

# Standard RTO pattern: 2 letters, 1-2 digits, 1-3 letters, 4 digits
STANDARD_RTO_REGEX = re.compile(r"^([A-Z]{2})[ -]?([0-9]{1,2})[ -]?([A-Z]{1,3})[ -]?([0-9]{4})$")

# Bharat (BH) Series pattern: 2 digits year, BH, 4 digits, 1-2 letters
BH_SERIES_REGEX = re.compile(r"^([0-9]{2})[ -]?(BH)[ -]?([0-9]{4})[ -]?([A-Z]{1,2})$")


@dataclass
class ValidationResult:
    is_valid: bool
    format_type: str  # "STANDARD_RTO" | "BHARAT_SERIES" | "INVALID"
    formatted_plate: str
    state_code: Optional[str] = None
    state_name: Optional[str] = None
    district_code: Optional[str] = None
    series: Optional[str] = None
    unique_number: Optional[str] = None
    format_score: float = 0.0
    issues: List[str] = field(default_factory=list)
    corrected_from_ambiguity: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "format_type": self.format_type,
            "formatted_plate": self.formatted_plate,
            "state_code": self.state_code,
            "state_name": self.state_name,
            "district_code": self.district_code,
            "series": self.series,
            "unique_number": self.unique_number,
            "format_score": round(self.format_score, 2),
            "issues": self.issues,
            "corrected_from_ambiguity": self.corrected_from_ambiguity,
        }


class PlateFormatValidator:
    """
    Validates, parses, and cleans Indian vehicle registration strings.
    """

    CHAR_TO_DIGIT = {"O": "0", "D": "0", "I": "1", "Z": "2", "S": "5", "B": "8"}
    DIGIT_TO_CHAR = {"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B"}

    def clean_string(self, raw_plate: str) -> str:
        """Removes spaces, hyphens, and non-alphanumeric characters, converts to uppercase."""
        if not raw_plate:
            return ""
        return re.sub(r"[^A-Za-z0-9]", "", raw_plate).upper()

    def validate(self, plate_string: str) -> ValidationResult:
        """
        Validates raw OCR plate text against Indian standards.
        Attempts grammar-based character ambiguity correction if initial parse fails.
        """
        clean = self.clean_string(plate_string)
        if not clean:
            return ValidationResult(
                is_valid=False,
                format_type="INVALID",
                formatted_plate="",
                format_score=0.0,
                issues=["Empty plate string"],
            )

        # 1. Try direct match against Standard RTO
        res = self._check_standard_rto(clean)
        if res.is_valid:
            return res
        if res.issues:
            # Matched syntax but invalid state jurisdiction
            return res

        # 2. Try direct match against BH Series
        res_bh = self._check_bh_series(clean)
        if res_bh.is_valid:
            return res_bh

        # 3. Attempt positional OCR ambiguity recovery
        corrected_clean, was_corrected = self._attempt_ambiguity_recovery(clean)
        if was_corrected:
            res_corr = self._check_standard_rto(corrected_clean)
            if res_corr.is_valid:
                res_corr.corrected_from_ambiguity = True
                res_corr.issues.append("Optical character ambiguity corrected by positional syntax rules")
                res_corr.format_score = 0.85
                return res_corr

            res_corr_bh = self._check_bh_series(corrected_clean)
            if res_corr_bh.is_valid:
                res_corr_bh.corrected_from_ambiguity = True
                res_corr_bh.issues.append("BH series ambiguity corrected by positional syntax rules")
                res_corr_bh.format_score = 0.85
                return res_corr_bh

        # Invalid format
        issues = ["Does not conform to Indian standard RTO format or Bharat (BH) series"]
        state_candidate = clean[:2]
        if state_candidate not in INDIAN_STATE_CODES:
            issues.append(f"Prefix '{state_candidate}' is not a recognized Indian State/UT code")

        return ValidationResult(
            is_valid=False,
            format_type="INVALID",
            formatted_plate=clean,
            format_score=0.2,
            issues=issues,
        )

    def _check_standard_rto(self, clean: str) -> ValidationResult:
        match = STANDARD_RTO_REGEX.match(clean)
        if not match:
            return ValidationResult(is_valid=False, format_type="INVALID", formatted_plate=clean)

        state, district, series, num = match.groups()
        if state not in INDIAN_STATE_CODES:
            return ValidationResult(
                is_valid=False,
                format_type="INVALID",
                formatted_plate=clean,
                issues=[f"State code '{state}' is not registered in official Indian RTO database"],
            )

        # Standard formatted display: "DL 01 AB 1234"
        formatted = f"{state} {int(district):02d} {series} {num}"
        return ValidationResult(
            is_valid=True,
            format_type="STANDARD_RTO",
            formatted_plate=formatted,
            state_code=state,
            state_name=INDIAN_STATE_CODES[state],
            district_code=f"{int(district):02d}",
            series=series,
            unique_number=num,
            format_score=1.0,
        )

    def _check_bh_series(self, clean: str) -> ValidationResult:
        match = BH_SERIES_REGEX.match(clean)
        if not match:
            return ValidationResult(is_valid=False, format_type="INVALID", formatted_plate=clean)

        year, bh, num, series = match.groups()
        formatted = f"{year} BH {num} {series}"
        return ValidationResult(
            is_valid=True,
            format_type="BHARAT_SERIES",
            formatted_plate=formatted,
            state_code="BH",
            state_name="Bharat Central Series",
            district_code=year,
            series=series,
            unique_number=num,
            format_score=1.0,
        )

    def _attempt_ambiguity_recovery(self, text: str) -> Tuple[str, bool]:
        """
        Applies positional rules:
        - Positions 0-1 must be letters (State code)
        - Positions 2-3 must be digits (District code)
        - Positions -4 to end must be digits (Unique number)
        """
        if len(text) < 8 or len(text) > 11:
            return text, False

        chars = list(text)
        changed = False

        # Positions 0 and 1 must be letters
        for i in (0, 1):
            if chars[i] in self.DIGIT_TO_CHAR:
                chars[i] = self.DIGIT_TO_CHAR[chars[i]]
                changed = True

        # Last 4 characters must be digits
        for i in range(len(chars) - 4, len(chars)):
            if chars[i] in self.CHAR_TO_DIGIT:
                chars[i] = self.CHAR_TO_DIGIT[chars[i]]
                changed = True

        # Characters 2 and 3 should be digits for standard RTO
        for i in (2, 3):
            if i < len(chars) - 4:
                if chars[i] in self.CHAR_TO_DIGIT:
                    chars[i] = self.CHAR_TO_DIGIT[chars[i]]
                    changed = True

        return "".join(chars), changed
