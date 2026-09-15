"""
Vehicle Tracking – ByteTrack-style Multi-Object Tracker
=========================================================
A lightweight, self-contained implementation of the ByteTrack association
strategy using IoU-based matching with the Hungarian algorithm.

No external tracking library required – falls back to scipy for the
linear_sum_assignment if available, else uses a greedy fallback.

Key design decisions
--------------------
* Each detection gets a *confidence tier*:
    HIGH  (≥ high_thresh)  → primary association pool
    LOW   (< high_thresh)  → secondary pool, only matched to lost tracks
* Tracks are promoted from TENTATIVE → CONFIRMED after `min_hits` frames.
* Tracks are deleted after `max_age` unmatched frames.
* Frame-boundary detections (bbox touching ± margin of frame edges)
  are suppressed before association to prevent unstable partial detections.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

try:
    import numpy as np
except ImportError:
    np = None

from typing import Any

logger = logging.getLogger("vehicle.tracker")

# ── Try to import scipy for optimal assignment ────────────────────────────────
try:
    from scipy.optimize import linear_sum_assignment as _lsa
    def _hungarian(cost) -> List[Tuple[int, int]]:
        row, col = _lsa(cost)
        return list(zip(row.tolist(), col.tolist()))
except ImportError:
    def _hungarian(cost) -> List[Tuple[int, int]]:  # type: ignore[misc]
        """Greedy fallback: always pick the globally minimum cost cell."""
        pairs: List[Tuple[int, int]] = []
        used_rows, used_cols = set(), set()
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


# ── IoU helper ────────────────────────────────────────────────────────────────

def _iou(a, b) -> float:
    """Intersection-over-Union for two [x1,y1,x2,y2] boxes."""
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter_w = max(0, ix2 - ix1)
    inter_h = max(0, iy2 - iy1)
    inter = inter_w * inter_h
    if inter == 0:
        return 0.0
    area_a = (a[2]-a[0]) * (a[3]-a[1])
    area_b = (b[2]-b[0]) * (b[3]-b[1])
    return inter / (area_a + area_b - inter + 1e-6)


def _iou_matrix(tracks: List["Track"], dets: List[Any]):
    if np is not None:
        m = np.zeros((len(tracks), len(dets)))
        for i, t in enumerate(tracks):
            for j, d in enumerate(dets):
                m[i, j] = _iou(t.bbox, d)
        return m
    m = []
    for t in tracks:
        m.append([_iou(t.bbox, d) for d in dets])
    return m


def _centroid(bbox):
    cx = (bbox[0] + bbox[2]) / 2.0
    cy = (bbox[1] + bbox[3]) / 2.0
    if np is not None:
        return np.array([cx, cy])
    return [cx, cy]


# ── Track state ───────────────────────────────────────────────────────────────

class TrackState(str, Enum):
    TENTATIVE = "TENTATIVE"
    CONFIRMED = "CONFIRMED"
    LOST      = "LOST"


@dataclass
class Track:
    track_id:   int
    bbox:       np.ndarray           # [x1,y1,x2,y2]
    label:      str
    confidence: float
    state:      TrackState = TrackState.TENTATIVE

    hits:       int = 1
    age:        int = 0              # frames since last match
    centroids:  List[np.ndarray] = field(default_factory=list)

    def update(self, det: np.ndarray, label: str, confidence: float):
        self.bbox       = det
        self.label      = label
        self.confidence = confidence
        self.hits      += 1
        self.age        = 0
        self.centroids.append(_centroid(det))
        if len(self.centroids) > 60:
            self.centroids.pop(0)

    def mark_missed(self):
        self.age += 1

    @property
    def centroid(self) -> np.ndarray:
        return _centroid(self.bbox)


# ── Frame boundary filter ─────────────────────────────────────────────────────

def _is_boundary(bbox: np.ndarray, frame_w: int, frame_h: int, margin: int = 8) -> bool:
    """Return True if the bbox touches the frame edge within `margin` pixels."""
    x1, y1, x2, y2 = bbox
    return (x1 < margin or y1 < margin or
            x2 > frame_w - margin or y2 > frame_h - margin)


# ── ByteTracker ───────────────────────────────────────────────────────────────

class ByteTracker:
    """
    Multi-object tracker using the ByteTrack association strategy.

    Parameters
    ----------
    high_thresh  : confidence threshold separating high/low-confidence dets
    iou_thresh_h : IoU threshold for high-confidence matching
    iou_thresh_l : IoU threshold for low-confidence (secondary) matching
    min_hits     : hits before a track is CONFIRMED
    max_age      : frames a track survives without a match before deletion
    frame_w, frame_h : frame dimensions for boundary suppression
    boundary_margin  : pixel margin for boundary detection suppression
    """

    def __init__(
        self,
        high_thresh:      float = 0.5,
        iou_thresh_h:     float = 0.35,
        iou_thresh_l:     float = 0.20,
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

    # ── Public API ────────────────────────────────────────────────────────────

    def update(
        self,
        detections: List[Tuple[str, float, List[float]]],
        frame_w: Optional[int] = None,
        frame_h: Optional[int] = None,
    ) -> List[Track]:
        """
        Process one frame's detections and return active CONFIRMED tracks.

        Parameters
        ----------
        detections : [(label, confidence, [x1,y1,x2,y2]), ...]
        frame_w, frame_h : optional override for boundary suppression

        Returns
        -------
        List of CONFIRMED Track objects updated this frame.
        """
        fw = frame_w or self._frame_w
        fh = frame_h or self._frame_h

        # ── Filter boundary detections ────────────────────────────────────────
        valid_dets = []
        for (label, conf, bbox_raw) in detections:
            bbox = np.array(bbox_raw, dtype=float)
            if _is_boundary(bbox, fw, fh, self._boundary_margin):
                continue
            valid_dets.append((label, conf, bbox))

        # ── Split into high / low confidence pools ────────────────────────────
        high_dets = [(l, c, b) for l, c, b in valid_dets if c >= self._high_thresh]
        low_dets  = [(l, c, b) for l, c, b in valid_dets if c <  self._high_thresh]

        active_tracks = [t for t in self._tracks if t.state != TrackState.LOST]
        lost_tracks   = [t for t in self._tracks if t.state == TrackState.LOST]

        # ── Step 1: Match high-conf dets → active tracks ──────────────────────
        matched_h, unmatched_tracks_h, unmatched_dets_h = self._match(
            active_tracks, high_dets, self._iou_thresh_h
        )

        # ── Step 2: Match low-conf dets → unmatched active tracks ─────────────
        still_unmatched_tracks = [active_tracks[i] for i in unmatched_tracks_h]
        matched_l, unmatched_tracks_l, _ = self._match(
            still_unmatched_tracks, low_dets, self._iou_thresh_l
        )

        # ── Step 3: Mark unmatched tracks as missed ───────────────────────────
        final_unmatched_idxs = [unmatched_tracks_h[i] for i in unmatched_tracks_l]
        for i in final_unmatched_idxs:
            active_tracks[i].mark_missed()
            if active_tracks[i].age > self._max_age:
                active_tracks[i].state = TrackState.LOST

        # ── Apply high-conf matches ───────────────────────────────────────────
        for ti, di in matched_h:
            label, conf, bbox = high_dets[di]
            active_tracks[ti].update(bbox, label, conf)
            if active_tracks[ti].hits >= self._min_hits:
                active_tracks[ti].state = TrackState.CONFIRMED

        # ── Apply low-conf matches ────────────────────────────────────────────
        for ti, di in matched_l:
            label, conf, bbox = low_dets[di]
            still_unmatched_tracks[ti].update(bbox, label, conf)

        # ── Create new tracks for unmatched high-conf dets ────────────────────
        for di in unmatched_dets_h:
            label, conf, bbox = high_dets[di]
            t = Track(track_id=self._next_id, bbox=bbox, label=label, confidence=conf)
            t.centroids = [_centroid(bbox)]
            self._next_id += 1
            self._tracks.append(t)

        # Prune permanently lost tracks (age > 2× max_age)
        self._tracks = [t for t in self._tracks if not (t.state == TrackState.LOST and t.age > self._max_age * 2)]

        return [t for t in self._tracks if t.state == TrackState.CONFIRMED]

    def reset(self):
        self._tracks.clear()
        self._next_id = 1

    # ── Internal matching ─────────────────────────────────────────────────────

    def _match(
        self,
        tracks: List[Track],
        dets:   List[Tuple[str, float, np.ndarray]],
        thresh: float,
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Hungarian IoU matching. Returns (matched, unmatched_track_idxs, unmatched_det_idxs)."""
        if not tracks or not dets:
            return [], list(range(len(tracks))), list(range(len(dets)))

        bbox_dets = [np.array(d[2]) for d in dets]
        cost = 1.0 - _iou_matrix(tracks, bbox_dets)
        pairs = _hungarian(cost)

        matched, unmatched_t, unmatched_d = [], set(range(len(tracks))), set(range(len(dets)))
        for ti, di in pairs:
            if cost[ti, di] <= 1.0 - thresh:
                matched.append((ti, di))
                unmatched_t.discard(ti)
                unmatched_d.discard(di)

        return matched, sorted(unmatched_t), sorted(unmatched_d)

    @property
    def confirmed_count(self) -> int:
        return sum(1 for t in self._tracks if t.state == TrackState.CONFIRMED)
