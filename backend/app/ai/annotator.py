"""
NovaFlow Visual Annotator & Evidence Generator
==============================================
Draws high-contrast bounding boxes, track IDs, and severity tags.
Extracts cropped thumbnails and encodes evidence frames.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Tuple

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

from PIL import Image

from .model_engine import DetectionBox

# Color palette in BGR for OpenCV
SEVERITY_COLORS_BGR = {
    "CRITICAL": (38, 38, 220),    # Red
    "HIGH":     (12, 88, 234),    # Orange
    "MEDIUM":   (6, 119, 217),    # Amber
    "LOW":      (220, 100, 37),   # Blue
}

DEFAULT_COLOR_BGR = (220, 100, 37)


def annotate_frame(
    frame_bgr: Any,
    detections: List[DetectionBox],
    track_ids: Optional[List[int]] = None,
) -> Any:
    """
    Draws styled bounding boxes, class labels, and confidence tags on a BGR frame.
    Returns a copy of the annotated frame.
    """
    if cv2 is None or frame_bgr is None:
        return frame_bgr

    annotated = frame_bgr.copy()
    h, w = annotated.shape[:2]

    for idx, det in enumerate(detections):
        color = SEVERITY_COLORS_BGR.get(det.severity, DEFAULT_COLOR_BGR)
        x1, y1, x2, y2 = [int(c) for c in det.bbox]

        # Ensure inside image bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)

        # Draw main box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        # Build label text
        track_tag = f"#{track_ids[idx]} " if track_ids and idx < len(track_ids) else ""
        label = f"{track_tag}{det.class_name.upper()} {int(det.confidence * 100)}%"

        # Draw label background banner
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.45
        thickness = 1
        (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        banner_y1 = max(0, y1 - text_h - 6)
        banner_y2 = y1
        cv2.rectangle(
            annotated,
            (x1, banner_y1),
            (x1 + text_w + 8, banner_y2),
            color,
            -1,
        )

        # Draw text
        cv2.putText(
            annotated,
            label,
            (x1 + 4, y1 - 4),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )

    return annotated


def crop_thumbnail(
    frame_bgr: Any,
    bbox: Tuple[float, float, float, float],
    margin_pct: float = 0.20,
) -> Optional[Any]:
    """Crops a localized thumbnail around the detected object with safety margin."""
    if cv2 is None or frame_bgr is None:
        return None

    h, w = frame_bgr.shape[:2]
    x1, y1, x2, y2 = bbox
    box_w = x2 - x1
    box_h = y2 - y1

    pad_x = int(box_w * margin_pct)
    pad_y = int(box_h * margin_pct)

    crop_x1 = max(0, int(x1 - pad_x))
    crop_y1 = max(0, int(y1 - pad_y))
    crop_x2 = min(w, int(x2 + pad_x))
    crop_y2 = min(h, int(y2 + pad_y))

    if crop_x2 <= crop_x1 or crop_y2 <= crop_y1:
        return None

    return frame_bgr[crop_y1:crop_y2, crop_x1:crop_x2]


def encode_image_jpeg(frame_bgr: Any, quality: int = 85) -> bytes:
    """Encodes a BGR image frame into JPEG bytes."""
    if cv2 is not None and frame_bgr is not None:
        success, encoded = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if success:
            return encoded.tobytes()

    # Fallback using PIL
    try:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB) if cv2 is not None else frame_bgr
        pil_img = Image.fromarray(rgb)
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()
    except Exception:
        return b""
