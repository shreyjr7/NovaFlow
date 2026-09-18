"""
Vehicle Tracking – ByteTrack-style Multi-Object Tracker (Phase 5 - Step 12)
============================================================================
A robust, lightweight ByteTrack association tracker providing temporal identity
continuity across frames (e.g. Frame 1 -> Car #23, Frame 2 -> Car #23 ...).

Key features:
-------------
- Two-tier association pool (HIGH confidence primary, LOW confidence secondary).
- Preserves track_id across consecutive frames to prevent double counting.
- State machine: TENTATIVE -> CONFIRMED (after min_hits) -> LOST (after max_age).
- Pure-Python fallback when numpy/scipy are not installed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import numpy as np
except ImportError:
    np = None

logger = logging.getLogger("vehicle.tracker")

# ── Assignment algorithm (Hungarian / greedy fallback) ───────────────────────

try:
    from scipy.optimize import linear_sum_assignment as _lsa
    def _hungarian(cost) -> List[Tuple[int, int]]:
        row, col = _lsa(cost)
        return list(zip(row.tolist(), col.tolist()))
except ImportError:
    def _hungarian(cost: Any) -> List[Tuple[int, int]]:
        """Greedy fallback: always pick the globally minimum cost cell."""
        pairs: List[Tuple[int, int]] = []
        used_rows: Set[int] = set()
        used_cols: Set[int] = set()
        num_rows = len(cost)
        num_cols = len(cost[0]) if num_rows > 0 else 0
        flat = []
        for r in range(num_rows):
            for c in range(num_cols):
                val = cost[r][c] if isinstance(cost, list) else cost[r, c]
                flat.append((val, r, c))
        for val, r, c in sorted(flat):
            if r not in used_rows and c not in used_cols:
                pairs.append((r, c))
                used_rows.add(r)
                used_cols.add(c)
        return pairs


# ── IoU & Centroid helpers ────────────────────────────────────────────────────

def _iou(a: List[float], b: List[float]) -> float:
    """Intersection-over-Union for two [x1, y1, x2, y2] boxes."""
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter_w = max(0.0, ix2 - ix1)
    inter_h = max(0.0, iy2 - iy1)
    inter = inter_w * inter_h
    if inter == 0:
        return 0.0
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / (union + 1e-6)


def _iou_matrix(tracks: List["Track"], dets: List[List[float]]) -> List[List[float]]:
    m: List[List[float]] = []
    for t in tracks:
        row = [_iou(t.bbox, d) for d in dets]
        m.append(row)
    return m


def _centroid(bbox: List[float]) -> List[float]:
    cx = (bbox[0] + bbox[2]) / 2.0
    cy = (bbox[1] + bbox[3]) / 2.0
    return [cx, cy]


# ── Track State & Track Object ────────────────────────────────────────────────

class TrackState(str, Enum):
    TENTATIVE = "TENTATIVE"
    CONFIRMED = "CONFIRMED"
    LOST      = "LOST"


@dataclass
class Track:
    track_id:   int
    bbox:       List[float]          # [x1, y1, x2, y2]
    label:      str
    confidence: float
    state:      TrackState = TrackState.TENTATIVE

    hits:       int = 1
    age:        int = 0              # frames since last match
    centroids:  List[List[float]] = field(default_factory=list)

    def update(self, det: List[float], label: str, confidence: float):
        self.bbox       = [float(v) for v in det]
        self.label      = label
        self.confidence = confidence
        self.hits      += 1
        self.age        = 0
        self.centroids.append(_centroid(self.bbox))
        if len(self.centroids) > 60:
            self.centroids.pop(0)

    def mark_missed(self):
        self.age += 1

    @property
    def centroid(self) -> List[float]:
        return _centroid(self.bbox)

    @property
    def display_name(self) -> str:
        """Step 12: Canonical tracking format (e.g. 'Car #23')."""
        return f"{self.label.replace('_', ' ').title()} #{self.track_id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "label": self.label,
            "display_name": self.display_name,
            "confidence": round(self.confidence, 3),
            "state": self.state.value,
            "bbox": [round(v, 1) for v in self.bbox],
            "centroid": [round(v, 1) for v in self.centroid],
            "hits": self.hits,
            "age": self.age,
        }


# ── Frame boundary filter ─────────────────────────────────────────────────────

def _is_boundary(bbox: List[float], frame_w: int, frame_h: int, margin: int = 8) -> bool:
    x1, y1, x2, y2 = bbox
    return (x1 < margin or y1 < margin or
            x2 > frame_w - margin or y2 > frame_h - margin)


# ── ByteTracker ───────────────────────────────────────────────────────────────

class ByteTracker:
    """
    Step 12 Multi-object tracker using ByteTrack association strategy:
    High-confidence pool primary match + low-confidence pool secondary match.
    Provides temporal continuity:
      Frame 1 -> Car #23
      Frame 2 -> Car #23
      Frame 3 -> Car #23
    """

    def __init__(
        self,
        high_thresh:      float = 0.50,
        iou_thresh_h:     float = 0.25,
        iou_thresh_l:     float = 0.10,
        min_hits:         int   = 3,
        max_age:          int   = 30,
        frame_w:          int   = 1280,
        frame_h:          int   = 720,
        boundary_margin:  int   = 8,
    ):
        self._high_thresh     = high_thresh
        self._iou_thresh_h    = iou_thresh_h
        self._iou_thresh_l    = iou_thresh_l
        self._min_hits        = min_hits
        self._max_age         = max_age
        self._frame_w         = frame_w
        self._frame_h         = frame_h
        self._boundary_margin = boundary_margin

        self._tracks:   List[Track] = []
        self._next_id:  int = 1

    def update(
        self,
        detections: List[Tuple[str, float, List[float]]],
        frame_w: Optional[int] = None,
        frame_h: Optional[int] = None,
    ) -> List[Track]:
        """
        Process one frame of detections and return active CONFIRMED tracks.
        """
        fw = frame_w or self._frame_w
        fh = frame_h or self._frame_h

        # 1. Filter out frame boundaries
        valid_dets: List[Tuple[str, float, List[float]]] = []
        for item in detections:
            label = item[0]
            conf = float(item[1])
            bbox = [float(v) for v in item[2]]
            if _is_boundary(bbox, fw, fh, self._boundary_margin):
                continue
            valid_dets.append((label, conf, bbox))

        # 2. Split into high and low confidence pools
        high_dets = [(l, c, b) for l, c, b in valid_dets if c >= self._high_thresh]
        low_dets  = [(l, c, b) for l, c, b in valid_dets if c <  self._high_thresh]

        active_tracks = [t for t in self._tracks if t.state != TrackState.LOST]

        # 3. Match high-confidence detections -> active tracks
        matched_h, unmatched_tracks_h, unmatched_dets_h = self._match(
            active_tracks, high_dets, self._iou_thresh_h
        )

        # 4. Match low-confidence detections -> unmatched active tracks
        still_unmatched_tracks = [active_tracks[i] for i in unmatched_tracks_h]
        matched_l, unmatched_tracks_l, _ = self._match(
            still_unmatched_tracks, low_dets, self._iou_thresh_l
        )

        # 5. Mark remaining unmatched tracks as missed
        final_unmatched_idxs = [unmatched_tracks_h[i] for i in unmatched_tracks_l]
        for i in final_unmatched_idxs:
            active_tracks[i].mark_missed()
            if active_tracks[i].age > self._max_age:
                active_tracks[i].state = TrackState.LOST

        # 6. Apply matches from high-conf pool
        for ti, di in matched_h:
            label, conf, bbox = high_dets[di]
            active_tracks[ti].update(bbox, label, conf)
            if active_tracks[ti].hits >= self._min_hits:
                active_tracks[ti].state = TrackState.CONFIRMED

        # 7. Apply matches from low-conf pool
        for ti, di in matched_l:
            label, conf, bbox = low_dets[di]
            still_unmatched_tracks[ti].update(bbox, label, conf)

        # 8. Create new tentative tracks for unmatched high-conf detections
        for di in unmatched_dets_h:
            label, conf, bbox = high_dets[di]
            t = Track(track_id=self._next_id, bbox=bbox, label=label, confidence=conf)
            t.centroids = [_centroid(bbox)]
            # If min_hits is 1, immediately confirm
            if self._min_hits <= 1:
                t.state = TrackState.CONFIRMED
            self._next_id += 1
            self._tracks.append(t)

        # 9. Clean up tracks that have been lost for too long
        self._tracks = [t for t in self._tracks if not (t.state == TrackState.LOST and t.age > self._max_age * 2)]

        return [t for t in self._tracks if t.state == TrackState.CONFIRMED]

    def reset(self):
        self._tracks.clear()
        self._next_id = 1

    def _match(
        self,
        tracks: List[Track],
        dets:   List[Tuple[str, float, List[float]]],
        thresh: float,
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        if not tracks or not dets:
            return [], list(range(len(tracks))), list(range(len(dets)))

        bbox_dets = [d[2] for d in dets]
        iou_mat = _iou_matrix(tracks, bbox_dets)
        cost = [[1.0 - val for val in row] for row in iou_mat]
        pairs = _hungarian(cost)

        matched, unmatched_t, unmatched_d = [], set(range(len(tracks))), set(range(len(dets)))
        for ti, di in pairs:
            if cost[ti][di] <= 1.0 - thresh:
                matched.append((ti, di))
                unmatched_t.discard(ti)
                unmatched_d.discard(di)

        return matched, sorted(unmatched_t), sorted(unmatched_d)

    @property
    def confirmed_count(self) -> int:
        return sum(1 for t in self._tracks if t.state == TrackState.CONFIRMED)

    @property
    def all_tracks(self) -> List[Track]:
        return list(self._tracks)
