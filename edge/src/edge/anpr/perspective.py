"""
Perspective Correction and Planar Plate Rectification
=====================================================
Performs four-point perspective transformation to rectify tilted, angled, or skewed
license plates into a standardized planar rectangular projection (320x80 px).
"""

from __future__ import annotations

import base64
import math
from typing import Any, List, Optional, Tuple

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    _CV2_AVAILABLE = False


def order_points(pts: List[List[float]]) -> Any:
    """
    Orders 4 points in consistent clockwise order:
    top-left, top-right, bottom-right, bottom-left.
    """
    if _CV2_AVAILABLE and np is not None:
        pts_arr = np.array(pts, dtype="float32")
        rect = np.zeros((4, 2), dtype="float32")

        s = pts_arr.sum(axis=1)
        rect[0] = pts_arr[np.argmin(s)]  # top-left
        rect[2] = pts_arr[np.argmax(s)]  # bottom-right

        diff = np.diff(pts_arr, axis=1)
        rect[1] = pts_arr[np.argmin(diff)]  # top-right
        rect[3] = pts_arr[np.argmax(diff)]  # bottom-left
        return rect

    # Pure Python fallback
    sorted_pts = sorted(pts, key=lambda p: (p[1], p[0]))
    top_two = sorted(sorted_pts[:2], key=lambda p: p[0])
    bottom_two = sorted(sorted_pts[2:], key=lambda p: p[0], reverse=True)
    return [top_two[0], top_two[1], bottom_two[0], bottom_two[1]]


class PerspectiveCorrector:
    """
    Rectifies camera perspective skew into an orthogonal plate view.
    """

    DEFAULT_WIDTH = 320
    DEFAULT_HEIGHT = 80

    def rectify_plate(
        self,
        frame: Any,
        corners: Optional[List[List[float]]] = None,
        bbox: Optional[List[int]] = None,
        target_width: int = DEFAULT_WIDTH,
        target_height: int = DEFAULT_HEIGHT,
    ) -> Tuple[Any, str]:
        """
        Applies four-point warp perspective. Returns (rectified_img, base64_jpeg).
        """
        # If OpenCV is available and we have a valid numpy frame
        if _CV2_AVAILABLE and frame is not None and isinstance(frame, np.ndarray):
            h, w = frame.shape[:2]

            # Derive corners from bbox if not explicitly provided
            if corners is None:
                if bbox is not None and len(bbox) == 4:
                    x1, y1, x2, y2 = bbox
                    corners = [
                        [float(x1), float(y1)],
                        [float(x2), float(y1)],
                        [float(x2), float(y2)],
                        [float(x1), float(y2)],
                    ]
                else:
                    corners = [
                        [float(w * 0.2), float(h * 0.7)],
                        [float(w * 0.8), float(h * 0.7)],
                        [float(w * 0.8), float(h * 0.85)],
                        [float(w * 0.2), float(h * 0.85)],
                    ]

            rect = order_points(corners)
            dst = np.array([
                [0, 0],
                [target_width - 1, 0],
                [target_width - 1, target_height - 1],
                [0, target_height - 1],
            ], dtype="float32")

            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(frame, M, (target_width, target_height))

            # Base64 encode
            _, buf = cv2.imencode(".jpg", warped, [cv2.IMWRITE_JPEG_QUALITY, 85])
            b64 = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("utf-8")
            return warped, b64

        # Clean SVG Mock Rectification fallback
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {target_width} {target_height}" width="{target_width}" height="{target_height}">
  <rect width="{target_width}" height="{target_height}" rx="6" fill="#f8fafc" stroke="#334155" stroke-width="2"/>
  <rect x="2" y="2" width="34" height="{target_height - 4}" rx="4" fill="#1e3a8a"/>
  <circle cx="19" cy="30" r="9" fill="#3b82f6" opacity="0.8"/>
  <text x="19" y="55" font-family="Arial" font-size="10" font-weight="900" fill="#ffffff" text-anchor="middle">IND</text>
  <line x1="42" y1="8" x2="42" y2="{target_height - 8}" stroke="#e2e8f0" stroke-width="1"/>
  <text x="{target_width // 2 + 18}" y="52" font-family="monospace" font-size="30" font-weight="900" fill="#0f172a" letter-spacing="3" text-anchor="middle">RECTIFIED</text>
</svg>"""
        b64 = f"data:image/svg+xml;base64,{base64.b64encode(svg.encode('utf-8')).decode('utf-8')}"
        return None, b64
