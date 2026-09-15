"""
Road Defect AI – Temporal Consistency Tracker
===============================================
Prevents single-frame false positives by requiring a defect class to be
seen in at least `min_hits` of the last `window_size` sampled frames before
emitting a confirmed detection.

Each (camera_id, defect_class) pair maintains its own sliding window of
raw detection confidences. When the window fills with enough hits, the
tracker emits a *confirmed* detection with an aggregated confidence score.

After confirmation, the tracker applies a cooldown so the same defect
location is not re-confirmed repeatedly unless the bus revisits the area.
"""

from __future__ import annotations

import logging
import time
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("road_defect.temporal")


@dataclass
class _ClassWindow:
    """Sliding window for one (camera, class) pair."""
    window_size:    int
    min_hits:       int
    cooldown_secs:  float

    _confidences:   deque = field(default_factory=deque)
    _last_confirmed: float = 0.0
    _last_bbox:      Optional[List[float]] = None

    def push(self, confidence: float, bbox: List[float]) -> Optional[float]:
        """
        Add a new confidence reading.
        Returns aggregated confidence if confirmed this tick, else None.
        """
        self._confidences.append(confidence)
        self._last_bbox = bbox
        if len(self._confidences) > self.window_size:
            self._confidences.popleft()

        # Cooldown guard
        if time.time() - self._last_confirmed < self.cooldown_secs:
            return None

        hits = sum(1 for c in self._confidences if c > 0)
        if hits >= self.min_hits:
            # Aggregate: weighted average (higher confidence = more weight)
            agg = sum(self._confidences) / len(self._confidences)
            self._last_confirmed = time.time()
            self._confidences.clear()   # reset after confirmation
            return round(agg, 3)
        return None

    def miss(self):
        """Record a frame where this class was NOT detected (push 0)."""
        self._confidences.append(0.0)
        if len(self._confidences) > self.window_size:
            self._confidences.popleft()


class TemporalConsistencyTracker:
    """
    Tracks detections per (camera_id, defect_class) across frames.

    Usage
    -----
    tracker = TemporalConsistencyTracker()
    confirmed = tracker.update(
        camera_id="FRONT",
        raw_detections=[("pothole", 0.82, [x1,y1,x2,y2]), ...],
        all_classes=ROAD_DEFECT_CLASSES,
    )
    # confirmed → list of (class, aggregated_confidence, bbox) for defects
    #             that passed the temporal filter this tick.
    """

    def __init__(
        self,
        window_size:   int   = 5,   # number of sampled frames to consider
        min_hits:      int   = 3,   # must appear in ≥ this many frames
        cooldown_secs: float = 20.0,  # seconds before re-confirming same class
    ):
        self._window_size   = window_size
        self._min_hits      = min_hits
        self._cooldown_secs = cooldown_secs
        # key: (camera_id, class_name) → _ClassWindow
        self._windows: Dict[Tuple[str, str], _ClassWindow] = defaultdict(
            lambda: _ClassWindow(
                window_size=self._window_size,
                min_hits=self._min_hits,
                cooldown_secs=self._cooldown_secs,
            )
        )

    def update(
        self,
        camera_id:        str,
        raw_detections:   List[Tuple[str, float, List[float]]],
        all_classes:      List[str],
    ) -> List[Tuple[str, float, List[float]]]:
        """
        Process one frame's detections.

        Parameters
        ----------
        camera_id       : e.g. "FRONT"
        raw_detections  : [(class, confidence, bbox), ...]
        all_classes     : complete list of defect class names to track misses

        Returns
        -------
        List of (class, aggregated_confidence, bbox) that are NOW confirmed.
        """
        detected_classes = {d[0]: (d[1], d[2]) for d in raw_detections}
        confirmed: List[Tuple[str, float, List[float]]] = []

        for cls in all_classes:
            key = (camera_id, cls)
            window = self._windows[key]

            if cls in detected_classes:
                conf, bbox = detected_classes[cls]
                agg = window.push(conf, bbox)
                if agg is not None:
                    confirmed.append((cls, agg, window._last_bbox or bbox))
            else:
                window.miss()

        return confirmed

    def reset(self, camera_id: Optional[str] = None):
        """Clear windows for one camera or all cameras."""
        if camera_id is None:
            self._windows.clear()
        else:
            keys_to_del = [k for k in self._windows if k[0] == camera_id]
            for k in keys_to_del:
                del self._windows[k]
