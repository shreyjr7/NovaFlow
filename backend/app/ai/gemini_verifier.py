"""
Gemini Multimodal Secondary Verification Layer (Phase 10)
==========================================================
Provides a secondary verification layer for NovaFlow Road Intelligence.
Does NOT replace the primary YOLO detector.

Used ONLY when:
- Primary YOLO confidence is low (0.35 <= confidence < threshold)
- Detected issue class is ambiguous or unconfirmed
- Scene interpretation is needed (potential collision, pedestrian conflict)
- Unsupported or unusual road condition is detected

Features:
- Strict server-side only execution (never expose API key to browser)
- Structured JSON output validated via Pydantic
- Configurable thresholds, timeout, max frames budget, and rate limiter
- Complete graceful fallback to primary YOLO detection if unavailable or failing
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger("novaflow.gemini_verifier")


class GeminiVerificationResult(BaseModel):
    """Structured Pydantic schema for Gemini multimodal road verification."""
    is_verified: bool = Field(default=True, description="Whether the identified condition is verified present in the image")
    verified_class: str = Field(default="UNKNOWN", description="Canonical class: POTHOLE, ROAD_DAMAGE, ROAD_CRACK, WATERLOGGING, DEBRIS, CLEAR_ROAD, etc.")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Model certainty score from 0.0 to 1.0")
    severity: str = Field(default="MEDIUM", description="Severity assessment: LOW, MEDIUM, HIGH, CRITICAL, NONE")
    reasoning: Optional[str] = Field(default=None, description="Visual reasoning supporting this verification")
    hazard_present: bool = Field(default=True, description="True if an actionable roadway hazard exists")
    recommended_action: Optional[str] = Field(default="Inspect and log observation", description="Suggested immediate municipal action")

    # Dynamic alias fields for prompt variance
    is_road_hazard: Optional[bool] = None
    hazard_type: Optional[str] = None
    scene_context: Optional[str] = None
    safety_implication: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_aliases(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # is_road_hazard <-> hazard_present <-> is_verified
            if "is_road_hazard" in values and "hazard_present" not in values:
                values["hazard_present"] = values["is_road_hazard"]
            if "hazard_present" in values and "is_road_hazard" not in values:
                values["is_road_hazard"] = values["hazard_present"]
            if "is_road_hazard" in values and "is_verified" not in values:
                values["is_verified"] = values["is_road_hazard"]
            # hazard_type <-> verified_class
            if "hazard_type" in values and "verified_class" not in values:
                values["verified_class"] = values["hazard_type"]
            if "verified_class" in values and "hazard_type" not in values:
                values["hazard_type"] = values["verified_class"]
            # scene_context <-> reasoning
            if "scene_context" in values and "reasoning" not in values:
                values["reasoning"] = values["scene_context"]
            if "reasoning" in values and "scene_context" not in values:
                values["scene_context"] = values["reasoning"]
        return values


class GeminiVerifier:
    """Secondary multimodal verification service calling Google Gemini API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        enabled: Optional[bool] = None,
        confidence_threshold: Optional[float] = None,
        request_timeout: Optional[float] = None,
        max_frames_per_job: Optional[int] = None,
        rate_limit_per_min: Optional[int] = None,
        model_name: str = "gemini-2.5-flash",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        self.enabled = (
            enabled
            if enabled is not None
            else os.getenv("ENABLE_GEMINI_VERIFICATION", "true").lower() in ("true", "1")
        )
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else float(os.getenv("GEMINI_CONFIDENCE_THRESHOLD", "0.65"))
        )
        self.request_timeout = (
            request_timeout
            if request_timeout is not None
            else float(os.getenv("GEMINI_REQUEST_TIMEOUT", "8.0"))
        )
        self.max_frames_per_job = (
            max_frames_per_job
            if max_frames_per_job is not None
            else int(os.getenv("GEMINI_MAX_FRAMES_PER_JOB", "5"))
        )
        self.rate_limit_per_min = (
            rate_limit_per_min
            if rate_limit_per_min is not None
            else int(os.getenv("GEMINI_RATE_LIMIT_PER_MIN", "15"))
        )
        self.model_name = os.getenv("GEMINI_MODEL_NAME", model_name)

        # Rate limiting state
        self._request_timestamps: List[float] = []
        self._job_frame_counters: Dict[str, int] = {}

    def is_available(self) -> bool:
        """Returns True if Gemini verification is enabled and configured with an API key."""
        return bool(self.enabled and self.api_key.strip())

    def should_verify(
        self,
        confidence: float,
        issue_type: str = "ROAD_DEFECT",
        is_ambiguous: bool = False,
        scene_flag: Optional[str] = None,
        class_name: Optional[str] = None,
        ambiguity_score: Optional[float] = None,
    ) -> bool:
        """
        Determines whether a detection warrants secondary Gemini verification.
        Selective rule: only send uncertain, ambiguous, or complex scenes.
        """
        if class_name:
            issue_type = class_name
        if ambiguity_score is not None and ambiguity_score >= 0.5:
            is_ambiguous = True

        if not self.is_available():
            return False

        # 1. Low confidence range (e.g. 0.35 to threshold)
        if 0.35 <= confidence < self.confidence_threshold:
            return True

        # 2. Ambiguous or unknown classification
        ambiguous_types = {"AMBIGUOUS", "UNKNOWN", "ROAD_DAMAGE", "UNUSUAL_HAZARD", "OBSTRUCTION"}
        if is_ambiguous or issue_type.upper() in ambiguous_types:
            return True

        # 3. Complex scene needing multimodal interpretation
        if scene_flag in {"POTENTIAL_COLLISION", "POTENTIAL_INCIDENT", "PEDESTRIAN_CONFLICT"}:
            return True

        return False

    def can_process_job_frame(self, job_id: str) -> bool:
        """Checks if session/job frame budget has remaining quota."""
        count = self._job_frame_counters.get(job_id, 0)
        return count < self.max_frames_per_job

    def _check_rate_limit(self) -> bool:
        """Enforces rate limit per minute."""
        now = time.time()
        # Keep only timestamps within the last 60 seconds
        self._request_timestamps = [t for t in self._request_timestamps if now - t < 60.0]
        if len(self._request_timestamps) >= self.rate_limit_per_min:
            logger.warning("Gemini verifier rate limit reached; skipping secondary verification")
            return False
        return True

    async def verify_evidence_frame(
        self,
        frame_bytes: bytes,
        preliminary_type: str,
        preliminary_confidence: float,
        preliminary_severity: str = "MEDIUM",
        job_id: str = "default_session",
    ) -> GeminiVerificationResult:
        """
        Invokes Gemini multimodal model with the evidence frame to verify or refine
        preliminary YOLO detections. Returns a validated GeminiVerificationResult.
        Falls back gracefully to primary YOLO values if anything fails.
        """
        # Fallback template
        fallback_result = GeminiVerificationResult(
            is_verified=True,
            verified_class=preliminary_type,
            confidence=preliminary_confidence,
            severity=preliminary_severity,
            reasoning=f"Validated via primary detector ({preliminary_type}, conf {preliminary_confidence:.2f})",
            hazard_present=preliminary_confidence >= 0.50,
            recommended_action="Inspect and log observation",
        )

        if not self.is_available():
            return fallback_result

        if not self.can_process_job_frame(job_id):
            logger.info(f"Gemini budget reached for job {job_id} ({self.max_frames_per_job} max frames); using primary result")
            return fallback_result

        if not self._check_rate_limit():
            return fallback_result

        try:
            # Increment job counter & record timestamp
            self._job_frame_counters[job_id] = self._job_frame_counters.get(job_id, 0) + 1
            self._request_timestamps.append(time.time())

            # Prepare image payload
            image_b64 = base64.b64encode(frame_bytes).decode("utf-8")

            prompt = (
                f"You are an expert municipal road inspection AI for NovaFlow. "
                f"The primary vision model flagged a potential road hazard: '{preliminary_type}' "
                f"with confidence {preliminary_confidence:.2f} and severity '{preliminary_severity}'.\n\n"
                f"Analyze this roadway frame carefully. Is there an actual road defect, obstruction, or hazard? "
                f"Determine the exact condition class (POTHOLE, ROAD_DAMAGE, ROAD_CRACK, WATERLOGGING, DEBRIS, "
                f"CLEAR_ROAD, etc.), confidence (0.0 to 1.0), and severity (LOW, MEDIUM, HIGH, CRITICAL, NONE).\n"
                f"Respond ONLY with a JSON object conforming to this schema:\n"
                f"{{\n"
                f'  "is_verified": true/false,\n'
                f'  "verified_class": "CLASS_NAME",\n'
                f'  "confidence": 0.85,\n'
                f'  "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | "NONE",\n'
                f'  "reasoning": "Brief description of visual findings",\n'
                f'  "hazard_present": true/false,\n'
                f'  "recommended_action": "Recommended municipal repair or monitoring action"\n'
                f"}}"
            )

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

            request_body = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inlineData": {
                                    "mimeType": "image/jpeg",
                                    "data": image_b64,
                                }
                            },
                        ]
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.1,
                },
            }

            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                resp = await client.post(url, json=request_body)

                if resp.status_code != 200:
                    logger.warning(f"Gemini API returned HTTP {resp.status_code}: {resp.text[:200]}; falling back to primary detector")
                    return fallback_result

                data = resp.json()
                candidate_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed_json = json.loads(candidate_text)

                # Validate using Pydantic schema
                result = GeminiVerificationResult(**parsed_json)
                logger.info(f"Gemini verified: {result.verified_class} ({result.confidence:.2f}, {result.severity})")
                return result

        except Exception as err:
            logger.warning(f"Gemini verification error: {err}; continuing with primary AI detector without failure")
            return fallback_result


# Global singleton instance
_verifier_instance: Optional[GeminiVerifier] = None


def get_gemini_verifier() -> GeminiVerifier:
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = GeminiVerifier()
    return _verifier_instance
