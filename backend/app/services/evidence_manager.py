"""
NovaFlow AI Evidence Storage Subsystem
======================================
Manages saving, annotating, and persisting detection evidence:
  1. Original clean frame (unadorned)
  2. Annotated frame (YOLO bounding box, track ID, severity tags)
  3. Cropped thumbnail of defect/object
  4. Supabase Storage upload with resilient local disk fallback
  5. Storage path registration in database (never base64 in PostgreSQL)
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

import httpx
from sqlmodel import Session

from ..ai.annotator import annotate_frame, crop_thumbnail, encode_image_jpeg
from ..ai.model_engine import DetectionBox
from ..database.session import engine
from ..models.ai_scan_entities import EvidenceReference

logger = logging.getLogger("novaflow.services.evidence_manager")

# Directory paths for local storage fallback
BASE_DATA_DIR = Path("data")
EVIDENCE_DIR = BASE_DATA_DIR / "evidence_frames"
ORIGINAL_DIR = EVIDENCE_DIR / "originals"
ANNOTATED_DIR = EVIDENCE_DIR / "annotated"
THUMBNAIL_DIR = EVIDENCE_DIR / "thumbnails"

for d in (EVIDENCE_DIR, ORIGINAL_DIR, ANNOTATED_DIR, THUMBNAIL_DIR):
    d.mkdir(parents=True, exist_ok=True)


@dataclass
class EvidenceBundle:
    """Paths and URLs for a confirmed detection's evidence files."""
    original_url: str
    annotated_url: str
    thumbnail_url: Optional[str]
    original_local_path: str
    annotated_local_path: str
    thumbnail_local_path: Optional[str]
    storage_provider: str  # "supabase_storage" or "local_disk"


class EvidenceManager:
    """Handles storage, uploading, and database registration of AI detection evidence."""

    def __init__(self):
        self.supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        self.supabase_key = (
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or os.environ.get("SUPABASE_KEY")
            or ""
        )
        self.has_supabase_storage = bool(self.supabase_url and self.supabase_key)
        if self.has_supabase_storage:
            logger.info(f"Supabase Storage enabled for AI evidence at: {self.supabase_url}")
        else:
            logger.info("Supabase Storage credentials not detected. Operating in local storage mode.")

    def save_detection_evidence(
        self,
        job_id: str,
        track_id: int,
        frame_number: int,
        clean_frame: Any,
        detections: list[DetectionBox],
        target_box: Tuple[float, float, float, float],
        db_detection_id: Optional[uuid.UUID] = None,
    ) -> EvidenceBundle:
        """
        Saves original frame, annotated frame, and cropped thumbnail.
        Uploads to Supabase Storage if configured, otherwise stores locally.
        """
        prefix = f"{job_id}_t{track_id}_f{frame_number}"
        orig_filename = f"{prefix}_orig.jpg"
        annot_filename = f"{prefix}_annot.jpg"
        thumb_filename = f"{prefix}_thumb.jpg"

        # 1. Save Original Clean Frame
        orig_local = EVIDENCE_DIR / orig_filename
        if cv2 is not None and clean_frame is not None:
            cv2.imwrite(str(orig_local), clean_frame)

        # 2. Generate and Save Annotated Frame
        annot_local = EVIDENCE_DIR / annot_filename
        annotated_img = annotate_frame(clean_frame, detections, [track_id])
        if cv2 is not None and annotated_img is not None:
            cv2.imwrite(str(annot_local), annotated_img)

        # 3. Generate and Save Cropped Thumbnail
        thumb_local = EVIDENCE_DIR / thumb_filename
        thumb_img = crop_thumbnail(annotated_img if annotated_img is not None else clean_frame, target_box)
        has_thumb = False
        if cv2 is not None and thumb_img is not None and thumb_img.size > 0:
            cv2.imwrite(str(thumb_local), thumb_img)
            has_thumb = True

        # Default local URLs served via FastAPI
        orig_url = f"/api/v1/evidence/file/{orig_filename}"
        annot_url = f"/api/v1/evidence/file/{annot_filename}"
        thumb_url = f"/api/v1/evidence/file/{thumb_filename}" if has_thumb else None
        storage_provider = "local_disk"

        # 4. Attempt Supabase Storage Upload if configured
        if self.has_supabase_storage:
            try:
                up_orig = self._upload_to_supabase(
                    bucket="evidence-frames",
                    filename=orig_filename,
                    file_path=orig_local,
                )
                up_annot = self._upload_to_supabase(
                    bucket="annotated-frames",
                    filename=annot_filename,
                    file_path=annot_local,
                )
                if up_orig:
                    orig_url = up_orig
                    storage_provider = "supabase_storage"
                if up_annot:
                    annot_url = up_annot

                if has_thumb:
                    up_thumb = self._upload_to_supabase(
                        bucket="thumbnails",
                        filename=thumb_filename,
                        file_path=thumb_local,
                    )
                    if up_thumb:
                        thumb_url = up_thumb
            except Exception as e:
                logger.warning(f"Supabase Storage upload warning (falling back to local): {e}")

        bundle = EvidenceBundle(
            original_url=orig_url,
            annotated_url=annot_url,
            thumbnail_url=thumb_url,
            original_local_path=str(orig_local),
            annotated_local_path=str(annot_local),
            thumbnail_local_path=str(thumb_local) if has_thumb else None,
            storage_provider=storage_provider,
        )

        # 5. Register in DB evidence_references table
        self._record_db_reference(db_detection_id, orig_filename, orig_url, "evidence-frames", storage_provider)
        self._record_db_reference(db_detection_id, annot_filename, annot_url, "annotated-frames", storage_provider)
        if has_thumb and thumb_url:
            self._record_db_reference(db_detection_id, thumb_filename, thumb_url, "thumbnails", storage_provider)

        return bundle

    def _upload_to_supabase(
        self,
        bucket: str,
        filename: str,
        file_path: Path,
    ) -> Optional[str]:
        """Uploads a file to Supabase Storage via REST API."""
        if not file_path.exists():
            return None

        url = f"{self.supabase_url}/storage/v1/object/{bucket}/{filename}"
        headers = {
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "image/jpeg",
        }

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=headers, content=content)
                if res.status_code in (200, 201):
                    public_url = f"{self.supabase_url}/storage/v1/object/public/{bucket}/{filename}"
                    return public_url
                else:
                    logger.debug(f"Supabase upload returned {res.status_code}: {res.text}")
        except Exception as err:
            logger.debug(f"Supabase storage upload error: {err}")

        return None

    def _record_db_reference(
        self,
        detection_id: Optional[uuid.UUID],
        filename: str,
        storage_url: str,
        bucket: str,
        storage_provider: str,
    ) -> None:
        """Saves file reference into evidence_references table."""
        if not detection_id:
            return
        try:
            with Session(engine) as session:
                ref = EvidenceReference(
                    detection_id=detection_id,
                    bucket_name=bucket,
                    file_path=storage_url,
                    file_name=filename,
                    storage_provider=storage_provider,
                )
                session.add(ref)
                session.commit()
        except Exception as e:
            logger.debug(f"Notice: could not record evidence DB reference ({e})")


_evidence_manager_instance: Optional[EvidenceManager] = None


def get_evidence_manager() -> EvidenceManager:
    global _evidence_manager_instance
    if _evidence_manager_instance is None:
        _evidence_manager_instance = EvidenceManager()
    return _evidence_manager_instance
