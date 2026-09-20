"""
NovaFlow Object & Defect Tracker
================================
IoU-based temporal consistency tracking across video frames.
Prevents repeated counting of the same pothole, road defect, or vehicle.
Enforces multi-frame persistence confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .model_engine import DetectionBox


def calculate_iou(box1: Tuple[float, float, float, float], box2: Tuple[float, float, float, float]) -> float:
    """Calculates Intersection over Union (IoU) between two bounding boxes (x1, y1, x2, y2)."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if intersection == 0.0:
        return 0.0

    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection

    return intersection / union if union > 0.0 else 0.0


@dataclass
class TrackedObject:
    """Represents a unique tracked real-world object or road defect."""
    track_id: int
    class_name: str
    severity: str
    first_frame: int
    last_frame: int
    hits: int = 1
    time_since_update: int = 0
    is_confirmed: bool = False
    best_confidence: float = 0.0
    best_bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    best_normalized_bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    best_frame_number: int = 0
    location: Dict[str, float] = field(default_factory=dict)
    evidence_image_path: Optional[str] = None
    annotated_image_path: Optional[str] = None
    original_image_path: Optional[str] = None
    thumbnail_image_path: Optional[str] = None
    created_ticket_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "class_name": self.class_name,
            "severity": self.severity,
            "hits": self.hits,
            "is_confirmed": self.is_confirmed,
            "best_confidence": round(self.best_confidence, 4),
            "best_bbox": [round(c, 1) for c in self.best_bbox],
            "best_normalized_bbox": [round(c, 4) for c in self.best_normalized_bbox],
            "best_frame_number": self.best_frame_number,
            "location": self.location,
            "evidence_image_path": self.evidence_image_path,
            "annotated_image_path": self.annotated_image_path,
            "original_image_path": self.original_image_path,
            "thumbnail_image_path": self.thumbnail_image_path,
        }


class DetectionTracker:
    """
    Tracks detections across sampled video frames using spatial IoU association.
    Objects must persist for `confirmation_frames` to be officially confirmed.
    """

    def __init__(
        self,
        iou_threshold: float = 0.30,
        confirmation_frames: int = 2,
        max_age: int = 5,
    ):
        self.iou_threshold = iou_threshold
        self.confirmation_frames = confirmation_frames
        self.max_age = max_age

        self._next_id: int = 1
        self.active_tracks: List[TrackedObject] = []
        self.confirmed_tracks: List[TrackedObject] = []

    def update(
        self,
        detections: List[DetectionBox],
        frame_number: int,
        gps: Dict[str, float],
    ) -> List[TrackedObject]:
        """
        Updates tracker with new detections for a specific frame number.
        Returns all active tracks that are currently confirmed.
        """
        # Increment time since update for all existing active tracks
        for track in self.active_tracks:
            track.time_since_update += 1

        matched_tracks = set()
        matched_detections = set()

        # Match detections to existing tracks by class and IoU
        for d_idx, det in enumerate(detections):
            best_iou = 0.0
            best_track_idx = -1

            for t_idx, track in enumerate(self.active_tracks):
                if t_idx in matched_tracks:
                    continue
                if track.class_name != det.class_name:
                    continue

                iou = calculate_iou(track.best_bbox, det.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_track_idx = t_idx

            if best_track_idx != -1 and best_iou >= self.iou_threshold:
                # Update existing track
                matched_tracks.add(best_track_idx)
                matched_detections.add(d_idx)
                track = self.active_tracks[best_track_idx]

                track.hits += 1
                track.time_since_update = 0
                track.last_frame = frame_number

                # Update best confidence and bbox
                if det.confidence > track.best_confidence:
                    track.best_confidence = det.confidence
                    track.best_bbox = det.bbox
                    track.best_normalized_bbox = det.normalized_bbox
                    track.best_frame_number = frame_number
                    track.severity = det.severity
                    track.location = gps

                # Confirm if threshold reached
                if track.hits >= self.confirmation_frames and not track.is_confirmed:
                    track.is_confirmed = True
                    if track not in self.confirmed_tracks:
                        self.confirmed_tracks.append(track)

        # Create new tracks for unmatched detections
        for d_idx, det in enumerate(detections):
            if d_idx not in matched_detections:
                new_track = TrackedObject(
                    track_id=self._next_id,
                    class_name=det.class_name,
                    severity=det.severity,
                    first_frame=frame_number,
                    last_frame=frame_number,
                    hits=1,
                    best_confidence=det.confidence,
                    is_confirmed=(
                        self.confirmation_frames <= 1
                        or (
                            det.class_name in ("pothole", "road_damage", "road_crack", "waterlogging")
                            and det.confidence >= 0.35
                        )
                    ),
                    best_bbox=det.bbox,
                    best_normalized_bbox=det.normalized_bbox,
                    best_frame_number=frame_number,
                    location=gps,
                )
                self._next_id += 1
                self.active_tracks.append(new_track)
                if new_track.is_confirmed:
                    self.confirmed_tracks.append(new_track)

        # Prune tracks that haven't been seen for max_age frames
        self.active_tracks = [
            t for t in self.active_tracks if t.time_since_update <= self.max_age
        ]

        return [t for t in self.active_tracks if t.is_confirmed]

    def get_all_confirmed(self) -> List[TrackedObject]:
        """Returns all confirmed unique tracks recorded across the video."""
        return self.confirmed_tracks
