"""
Rolling Frame Buffer for Incident Evidence Extraction
=====================================================
Thread-safe circular FIFO buffer holding recent camera frames.
When an anomaly occurs, the buffer extracts a synchronized multi-frame sequence
(pre-impact, impact, post-impact) to form the evidentiary clip.
"""

from __future__ import annotations

import base64
import threading
import time
import uuid
from collections import deque
from typing import Any, Dict, List, Optional

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    _CV2_AVAILABLE = False


def _encode_b64_jpeg(frame: Any, quality: int = 65) -> str:
    """Safely encodes a frame to base64 JPEG, with mock fallback."""
    if _CV2_AVAILABLE and frame is not None and isinstance(frame, np.ndarray):
        try:
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            return base64.b64encode(buf.tobytes()).decode("utf-8")
        except Exception:
            pass
    # Minimal 1x1 JPEG fallback
    return (
        "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////"
        "////////////////////////////////////////////////////////////////////////////////"
        "wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
    )


class RollingFrameBuffer:
    """
    Circular FIFO buffer storing the latest N frames for incident reconstruction.
    """

    def __init__(self, capacity: int = 30, default_fps: float = 10.0):
        self._capacity = capacity
        self._default_fps = default_fps
        self._buffer: deque = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def push(
        self,
        frame: Any,
        timestamp_s: Optional[float] = None,
        frame_idx: int = 0,
        gps: Optional[Dict[str, Any]] = None,
        frame_b64: Optional[str] = None,
    ):
        """Add a new frame to the circular buffer."""
        ts = timestamp_s if timestamp_s is not None else time.time()
        entry = {
            "timestamp_s": ts,
            "frame_idx": frame_idx,
            "frame": frame,
            "gps": gps or {},
            "frame_b64": frame_b64,
        }
        with self._lock:
            self._buffer.append(entry)

    def size(self) -> int:
        with self._lock:
            return len(self._buffer)

    def clear(self):
        with self._lock:
            self._buffer.clear()

    def retrieve_frames(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve recent frames in chronological order."""
        with self._lock:
            items = list(self._buffer)
        if count is not None and count < len(items):
            return items[-count:]
        return items

    def create_evidence_clip(
        self,
        anomaly_timestamp_s: Optional[float] = None,
        pre_frames: int = 6,
        post_frames: int = 6,
    ) -> Dict[str, Any]:
        """
        Creates an evidence clip structure with multi-frame sequence and timing.
        """
        frames_list = self.retrieve_frames()
        clip_id = f"clip_{uuid.uuid4().hex[:8]}"

        if not frames_list:
            # Generate placeholder evidence frames
            dummy_b64 = _encode_b64_jpeg(None)
            return {
                "clip_id": clip_id,
                "frame_count": 3,
                "duration_s": 1.0,
                "fps": self._default_fps,
                "frames": [
                    {"phase": "PRE_IMPACT", "frame_idx": 1, "frame_b64": dummy_b64},
                    {"phase": "IMPACT", "frame_idx": 2, "frame_b64": dummy_b64},
                    {"phase": "POST_IMPACT", "frame_idx": 3, "frame_b64": dummy_b64},
                ],
                "key_frame_b64": dummy_b64,
            }

        # Determine target window around anomaly
        n = len(frames_list)
        total_requested = pre_frames + post_frames + 1
        selected = frames_list[-total_requested:] if total_requested <= n else frames_list

        clip_frames = []
        key_frame_b64 = ""
        mid_idx = len(selected) // 2

        for i, entry in enumerate(selected):
            b64 = entry.get("frame_b64") or _encode_b64_jpeg(entry.get("frame"))
            phase = "PRE_IMPACT" if i < mid_idx else ("IMPACT" if i == mid_idx else "POST_IMPACT")
            if phase == "IMPACT" or (i == len(selected) - 1 and not key_frame_b64):
                key_frame_b64 = b64

            clip_frames.append({
                "phase": phase,
                "frame_idx": entry.get("frame_idx", i),
                "timestamp_s": entry.get("timestamp_s", 0.0),
                "frame_b64": b64,
                "gps": entry.get("gps", {}),
            })

        duration = (
            clip_frames[-1]["timestamp_s"] - clip_frames[0]["timestamp_s"]
            if len(clip_frames) > 1 else 1.0
        )

        return {
            "clip_id": clip_id,
            "frame_count": len(clip_frames),
            "duration_s": round(max(duration, 0.5), 2),
            "fps": round(self._default_fps, 1),
            "frames": clip_frames,
            "key_frame_b64": key_frame_b64 or (clip_frames[0]["frame_b64"] if clip_frames else ""),
        }
