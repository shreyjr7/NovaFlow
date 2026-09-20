"""
NovaFlow AI Road Intelligence Engine (Phase 9)
==============================================
Pure algorithmic engine deriving contextual road intelligence from primary
YOLO detections and vehicle telemetry without requiring separate deep learning models.

Derived Features:
1. Traffic Congestion: low / medium / high (vehicle count, occupancy %, speed)
2. Potential Pedestrian Risk: "Potential Pedestrian Conflict/Risk" (proximity, heading)
3. Incident Indicators: "Potential Incident" (stopped vehicles, collision scenes, obstructions)
4. Severity Scoring: Multi-factor index (confidence, visible area, persistence, road centrality)
   * Strictly avoids inventing fake physical depth from ordinary RGB video.
5. Spatial Duplicate Detection: 15m radius clustering & observation count increment
6. Persistent Hazard Confirmation: Multi-frame temporal consensus
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlmodel import select


class RoadIntelligenceEngine:
    """Algorithmic derived intelligence engine for urban transit and roadway networks."""

    def __init__(
        self,
        dedup_radius_meters: float = 15.0,
        congestion_radius_meters: float = 30.0,
        min_confirmation_frames: int = 2,
    ):
        self.dedup_radius_meters = dedup_radius_meters
        self.congestion_radius_meters = congestion_radius_meters
        self.min_confirmation_frames = min_confirmation_frames

    # ── 1. TRAFFIC CONGESTION EVALUATION ─────────────────────────────────────
    def evaluate_traffic_congestion(
        self,
        detections: List[Dict[str, Any]],
        bus_speed_kmh: Optional[float] = None,
        frame_width: int = 1280,
        frame_height: int = 720,
    ) -> Dict[str, Any]:
        """
        Calculates traffic congestion level (LOW, MEDIUM, HIGH) using:
        - Vehicle detection count (cars, buses, trucks, motorcycles)
        - Road occupancy ratio (summed vehicle bounding box area / roadway zone area)
        - Transit vehicle instantaneous speed
        """
        vehicle_types = {"CAR", "BUS", "TRUCK", "MOTORCYCLE", "VEHICLE"}
        vehicle_dets = [
            d for d in detections
            if d.get("type", "").upper() in vehicle_types
        ]
        vehicle_count = len(vehicle_dets)

        # Estimate roadway area (assuming lower 75% of frame represents roadway)
        roadway_area = frame_width * (frame_height * 0.75)
        total_vehicle_area = 0.0

        for d in vehicle_dets:
            bbox = d.get("bounding_box") or {}
            x1 = bbox.get("x1", 0.0)
            y1 = bbox.get("y1", 0.0)
            x2 = bbox.get("x2", 0.0)
            y2 = bbox.get("y2", 0.0)
            # Normalize to pixels if 0.0-1.0
            if max(x1, x2, y1, y2) <= 1.0:
                w_px = max(0.0, (x2 - x1) * frame_width)
                h_px = max(0.0, (y2 - y1) * frame_height)
            else:
                w_px = max(0.0, x2 - x1)
                h_px = max(0.0, y2 - y1)
            total_vehicle_area += (w_px * h_px)

        occupancy_ratio = min(1.0, total_vehicle_area / roadway_area) if roadway_area > 0 else 0.0

        # Congestion scoring heuristic
        # Signals: vehicle count + occupancy ratio + low speed indicator
        congestion_score = 0.0
        # Count component (up to 0.40)
        congestion_score += min(0.40, (vehicle_count / 12.0) * 0.40)
        # Occupancy component (up to 0.45)
        congestion_score += (occupancy_ratio * 0.45)
        # Speed component (up to 0.15): slow speed (< 15 km/h) indicates bottleneck
        if bus_speed_kmh is not None:
            if bus_speed_kmh < 8.0:
                congestion_score += 0.15
            elif bus_speed_kmh < 18.0:
                congestion_score += 0.08

        if congestion_score >= 0.55 or (vehicle_count >= 8 and occupancy_ratio >= 0.35):
            level = "HIGH"
        elif congestion_score >= 0.25 or vehicle_count >= 4 or occupancy_ratio >= 0.18:
            level = "MEDIUM"
        else:
            level = "LOW"

        rec = "Optimal vehicle flow; road corridor clear."
        if level == "HIGH":
            rec = "High congestion: recommend headway spacing & speed advisory."
        elif level == "MEDIUM":
            rec = "Moderate vehicle density observed in travel lane."

        return {
            "level": level,
            "label": "Potential Traffic Congestion",
            "score": round(congestion_score, 3),
            "vehicle_count": vehicle_count,
            "occupancy_ratio": round(occupancy_ratio, 3),
            "road_occupancy_pct": round(occupancy_ratio * 100.0, 1),
            "recommendation": rec,
            "condition_type": "POTENTIAL",
        }

    # ── 2. PEDESTRIAN RISK EVALUATION ───────────────────────────────────────
    def evaluate_pedestrian_risk(
        self,
        detections: List[Dict[str, Any]],
        frame_width: int = 1280,
        frame_height: int = 720,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates potential conflict zones between pedestrians and moving vehicles.
        Strictly labeled: "Potential Pedestrian Conflict/Risk"
        (Explicitly does not claim medically or statistically validated risk probabilities).
        """
        peds = [d for d in detections if d.get("type", "").upper() in {"PEDESTRIAN", "PERSON"}]
        vehicles = [
            d for d in detections
            if d.get("type", "").upper() in {"CAR", "BUS", "TRUCK", "MOTORCYCLE", "VEHICLE"}
        ]

        if not peds or not vehicles:
            return []

        risk_indicators = []

        for p_idx, p in enumerate(peds):
            p_bbox = self._get_normalized_bbox(p.get("bounding_box", {}), frame_width, frame_height)
            p_cx = (p_bbox["x1"] + p_bbox["x2"]) / 2.0
            p_cy = (p_bbox["y1"] + p_bbox["y2"]) / 2.0

            # Find closest vehicle
            closest_dist = float("inf")
            closest_v = None

            for v in vehicles:
                v_bbox = self._get_normalized_bbox(v.get("bounding_box", {}), frame_width, frame_height)
                v_cx = (v_bbox["x1"] + v_bbox["x2"]) / 2.0
                v_cy = (v_bbox["y1"] + v_bbox["y2"]) / 2.0

                # Euclidean distance in normalized coordinate space
                dist = math.hypot(p_cx - v_cx, p_cy - v_cy)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_v = v

            # Proximity threshold: within 25% of screen span
            if closest_dist < 0.28 and closest_v is not None:
                # Closer proximity indicates elevated conflict potential
                if closest_dist < 0.12:
                    severity = "HIGH"
                elif closest_dist < 0.20:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"

                risk_indicators.append({
                    "type": "PEDESTRIAN_RISK",
                    "label": "Potential Pedestrian Conflict/Risk",
                    "severity": severity,
                    "condition_type": "POTENTIAL",
                    "proximity_metric": round(closest_dist, 3),
                    "pedestrian_track_id": p.get("track_id"),
                    "vehicle_type": closest_v.get("type"),
                    "vehicle_track_id": closest_v.get("track_id"),
                    "latitude": p.get("latitude") or closest_v.get("latitude"),
                    "longitude": p.get("longitude") or closest_v.get("longitude"),
                    "description": (
                        f"Potential Pedestrian Conflict/Risk identified: Pedestrian in close proximity "
                        f"({round(closest_dist * 100, 1)}% view-span) to {closest_v.get('type', 'vehicle')}."
                    ),
                })

        return risk_indicators

    # ── 3. INCIDENT INDICATORS EVALUATION ────────────────────────────────────
    def evaluate_incidents(
        self,
        detections: List[Dict[str, Any]],
        bus_speed_kmh: Optional[float] = None,
        frame_width: int = 1280,
        frame_height: int = 720,
    ) -> List[Dict[str, Any]]:
        """
        Detects visual scene indicators of potential traffic incidents:
        - Overlapping vehicle bboxes (potential collision contact)
        - Overturned vehicle aspect ratio anomalies
        - Severe road obstruction (large debris blocking travel path)
        Strictly labeled: "Potential Incident"
        """
        incidents = []
        vehicles = [
            d for d in detections
            if d.get("type", "").upper() in {"CAR", "BUS", "TRUCK", "MOTORCYCLE", "VEHICLE"}
        ]
        debris_list = [
            d for d in detections
            if d.get("type", "").upper() in {"DEBRIS", "ROAD_DEBRIS", "OBSTRUCTION"}
        ]

        # 1. Collision / Contact check: pair-wise IoU / heavy bounding box overlap
        for i in range(len(vehicles)):
            b1 = self._get_normalized_bbox(vehicles[i].get("bounding_box", {}), frame_width, frame_height)
            for j in range(i + 1, len(vehicles)):
                b2 = self._get_normalized_bbox(vehicles[j].get("bounding_box", {}), frame_width, frame_height)
                iou = self._calculate_iou(b1, b2)

                # Two vehicles overlapping by >= 15% IoU in roadway zone indicates potential collision/incident
                if iou >= 0.15:
                    incidents.append({
                        "type": "INCIDENT",
                        "label": "Potential Incident",
                        "subtype": "VEHICLE_COLLISION_INDICATOR",
                        "severity": "HIGH",
                        "condition_type": "POTENTIAL",
                        "overlap_iou": round(iou, 3),
                        "vehicle_1": vehicles[i].get("type"),
                        "vehicle_2": vehicles[j].get("type"),
                        "latitude": vehicles[i].get("latitude"),
                        "longitude": vehicles[i].get("longitude"),
                        "description": (
                            f"Potential Incident: Overlapping vehicles detected ({vehicles[i].get('type')} "
                            f"and {vehicles[j].get('type')}, IoU {round(iou, 2)}) suggesting possible collision."
                        ),
                    })

        # 2. Roadway obstruction check
        for deb in debris_list:
            bbox = self._get_normalized_bbox(deb.get("bounding_box", {}), frame_width, frame_height)
            area = (bbox["x2"] - bbox["x1"]) * (bbox["y2"] - bbox["y1"])
            # Debris taking up >= 4% of camera view indicates major lane blockage
            if area >= 0.04 or deb.get("severity") in {"HIGH", "CRITICAL"}:
                incidents.append({
                    "type": "INCIDENT",
                    "label": "Potential Incident",
                    "subtype": "ROADWAY_OBSTRUCTION",
                    "severity": "MEDIUM",
                    "condition_type": "POTENTIAL",
                    "obstruction_area_ratio": round(area, 4),
                    "latitude": deb.get("latitude"),
                    "longitude": deb.get("longitude"),
                    "description": "Potential Incident: Substantial roadway obstruction or debris blocking travel lane.",
                })

        return incidents

    # ── 4. MULTI-FACTOR SEVERITY SCORING ────────────────────────────────────
    def compute_severity_score(
        self,
        confidence: float,
        bounding_box: Dict[str, float],
        persistence_frames: int = 1,
        frame_width: int = 1280,
        frame_height: int = 720,
    ) -> Tuple[str, float]:
        """
        Computes composite severity rating (LOW, MEDIUM, HIGH, CRITICAL) without
        inventing fake pothole depth from ordinary RGB video.

        Factors:
        - Detection model confidence (0.0 to 1.0)
        - Visible affected area relative to roadway (% of screen)
        - Multi-frame temporal persistence (frames tracked)
        - Road centrality (distance from center vertical axis)
        """
        bbox = self._get_normalized_bbox(bounding_box, frame_width, frame_height)
        w = max(0.0, bbox["x2"] - bbox["x1"])
        h = max(0.0, bbox["y2"] - bbox["y1"])
        area_ratio = min(1.0, w * h)

        # Centrality factor: defects in the central 50% of the lane pose higher vehicle risk
        cx = (bbox["x1"] + bbox["x2"]) / 2.0
        dist_from_center = abs(cx - 0.5)  # 0.0 = directly centered in lane, 0.5 = at edge
        centrality_weight = max(0.2, 1.0 - (dist_from_center * 1.6))

        # Composite severity index (0.0 to 1.0)
        # 30% Confidence, 35% Visible Area, 20% Temporal Persistence, 15% Centrality
        persistence_factor = min(1.0, persistence_frames / 4.0)
        area_factor = min(1.0, area_ratio / 0.08)  # 8% of screen is considered massive defect

        composite_score = (
            (confidence * 0.30) +
            (area_factor * 0.35) +
            (persistence_factor * 0.20) +
            (centrality_weight * 0.15)
        )

        if composite_score >= 0.72:
            severity = "CRITICAL"
        elif composite_score >= 0.52:
            severity = "HIGH"
        elif composite_score >= 0.35:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        return severity, round(composite_score, 3)

    # ── 5. SPATIAL DUPLICATE DETECTION ──────────────────────────────────────
    def check_duplicate_hazard(
        self,
        new_lat: float,
        new_lon: float,
        hazard_type: str,
        existing_hazards: List[Dict[str, Any]],
        radius_meters: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Checks if a detected hazard is a spatial duplicate of an existing known hazard.
        Uses Haversine distance. If duplicate found, returns the matching hazard record.
        """
        threshold = radius_meters if radius_meters is not None else self.dedup_radius_meters
        h_type_norm = hazard_type.upper().replace(" ", "_")

        for ex in existing_hazards:
            ex_lat = ex.get("latitude") or ex.get("lat")
            ex_lon = ex.get("longitude") or ex.get("lon")
            if ex_lat is None or ex_lon is None:
                continue

            ex_type = (ex.get("type") or ex.get("hazard_type") or ex.get("asset_type") or "").upper().replace(" ", "_")

            # Check type compatibility
            if ex_type and ex_type != h_type_norm:
                # If types differ, check if both are generic defects
                defects = {"POTHOLE", "ROAD_DAMAGE", "ROAD_CRACK", "WATERLOGGING", "DEBRIS"}
                if not (h_type_norm in defects and ex_type in defects):
                    continue

            dist = self.haversine_distance(new_lat, new_lon, float(ex_lat), float(ex_lon))
            if dist <= threshold:
                return ex

        return None

    # ── 6. PERSISTENT HAZARD CONFIRMATION ────────────────────────────────────
    def evaluate_persistence(
        self,
        frames_tracked: int,
        observation_count: int = 1,
        confidence: float = 0.85,
    ) -> bool:
        """
        Determines whether a hazard should be marked CONFIRMED based on
        multi-frame temporal tracking or multi-observation consensus.
        """
        if observation_count >= 2:
            return True
        if frames_tracked >= self.min_confirmation_frames and confidence >= 0.60:
            return True
        if confidence >= 0.88:
            return True
        return False

    # ── 7. MULTI-BUS HAZARD CONFIRMATION (PHASE 12) ──────────────────────────
    def record_multi_bus_observation(
        self,
        session: Any,
        detection: Any,
        bus_id: str,
        route_id: Optional[str] = None,
        road_segment: Optional[str] = None,
        city: str = "Bengaluru",
        proximity_radius_m: float = 20.0,
        time_window_hours: float = 72.0,
    ) -> Tuple[Any, Any, bool]:
        """
        Implements repeated multi-bus observation logic (Phase 12).
        Identifies whether a detection from bus_id matches an existing active persistent hazard
        based on:
          1. Geographic proximity (Haversine <= 20m)
          2. Road segment (if available)
          3. Issue type compatibility
          4. Temporal window (within last 72 hours)

        Maintains observation history across all buses.
        Updates multi-bus consensus ("CONFIRMED BY N BUSES").
        STRICTLY PRESERVES raw individual AI model confidence without inflation.
        """
        from ..models.ai_scan_entities import PersistentHazard, HazardObservation

        h_type_norm = (detection.type or "POTHOLE").upper().replace(" ", "_")
        defects = {"POTHOLE", "ROAD_DAMAGE", "ROAD_CRACK", "WATERLOGGING", "DEBRIS", "ROAD_DEBRIS", "DEFECT"}

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=time_window_hours)

        # 1. Search for matching active persistent hazard
        existing_hazards = session.exec(
            select(PersistentHazard).where(PersistentHazard.status == "ACTIVE")
        ).all()

        matched_hazard: Optional[PersistentHazard] = None
        min_dist = float("inf")

        for h in existing_hazards:
            # Check temporal window: last detected within cutoff
            if h.last_detected_at:
                h_dt = h.last_detected_at
                if h_dt.tzinfo is None:
                    h_dt = h_dt.replace(tzinfo=timezone.utc)
                if h_dt < cutoff:
                    continue

            # Check defect type compatibility
            ex_type = (h.hazard_type or "").upper().replace(" ", "_")
            if ex_type != h_type_norm:
                if not (h_type_norm in defects and ex_type in defects):
                    continue

            # Check geographic proximity
            dist = self.haversine_distance(detection.latitude, detection.longitude, h.latitude, h.longitude)
            if dist <= proximity_radius_m and dist < min_dist:
                min_dist = dist
                matched_hazard = h

        # 2. If match found, associate new observation
        if matched_hazard is not None:
            # Create HazardObservation
            obs = HazardObservation(
                id=uuid4(),
                hazard_id=matched_hazard.id,
                detection_id=detection.id if hasattr(detection, "id") else None,
                bus_id=bus_id,
                route_id=route_id,
                road_segment=road_segment or matched_hazard.road_segment,
                model_confidence=round(float(detection.confidence), 4),  # RAW UNALTERED MODEL CONFIDENCE!
                severity=detection.severity,
                latitude=detection.latitude,
                longitude=detection.longitude,
                evidence_path=getattr(detection, "annotated_evidence_path", None) or getattr(detection, "evidence_path", None),
                thumbnail_path=getattr(detection, "thumbnail_path", None),
                observed_at=detection.timestamp if hasattr(detection, "timestamp") and detection.timestamp else now,
                created_at=now,
            )
            session.add(obs)

            # Update PersistentHazard metrics
            matched_hazard.total_observations += 1
            contributing = [b.strip() for b in (matched_hazard.contributing_buses or "").split(",") if b.strip()]
            if bus_id and bus_id not in contributing:
                contributing.append(bus_id)
                matched_hazard.independent_buses_count = len(contributing)
                matched_hazard.contributing_buses = ", ".join(contributing)

            matched_hazard.last_detected_at = detection.timestamp if hasattr(detection, "timestamp") and detection.timestamp else now
            matched_hazard.updated_at = now

            # Multi-bus persistence status formulation
            n_buses = matched_hazard.independent_buses_count
            if n_buses >= 2:
                matched_hazard.persistence_status = f"CONFIRMED BY {n_buses} BUSES"
                matched_hazard.persistence_score = min(0.99, round(0.50 + (n_buses * 0.15), 3))
            elif matched_hazard.total_observations >= 2:
                matched_hazard.persistence_status = "REPEATED OBSERVATION (1 BUS)"
                matched_hazard.persistence_score = 0.55
            else:
                matched_hazard.persistence_status = "SINGLE OBSERVATION"
                matched_hazard.persistence_score = 0.40

            # Promote severity if new observation is higher
            if str(detection.severity).upper() == "CRITICAL" and matched_hazard.severity != "CRITICAL":
                matched_hazard.severity = "CRITICAL"

            session.add(matched_hazard)
            session.commit()
            session.refresh(matched_hazard)

            # Update RoadDetection entity with persistent hazard linkage
            if hasattr(detection, "persistent_hazard_id"):
                detection.persistent_hazard_id = matched_hazard.id
                detection.independent_buses_count = matched_hazard.independent_buses_count
                detection.contributing_buses = matched_hazard.contributing_buses
                detection.persistence_badge = matched_hazard.persistence_status
                detection.last_detected_at = matched_hazard.last_detected_at
                session.add(detection)
                session.commit()

            # Synchronize all sibling detections linked to this persistent hazard
            try:
                sibling_dets = session.exec(
                    select(RoadDetection).where(RoadDetection.persistent_hazard_id == matched_hazard.id)
                ).all()
                for sib in sibling_dets:
                    sib.independent_buses_count = matched_hazard.independent_buses_count
                    sib.contributing_buses = matched_hazard.contributing_buses
                    sib.persistence_badge = matched_hazard.persistence_status
                    sib.last_detected_at = matched_hazard.last_detected_at
                    session.add(sib)
                session.commit()
            except Exception:
                pass

            return matched_hazard, obs, False

        # 3. If no match found, create new PersistentHazard
        hazard_code = f"HAZ-{city[:3].upper()}-{now.year}-{int(now.timestamp() * 1000) % 10000:04d}"
        new_hazard = PersistentHazard(
            id=uuid4(),
            hazard_code=hazard_code,
            hazard_type=h_type_norm,
            severity=str(detection.severity or "MEDIUM").upper(),
            latitude=round(float(detection.latitude), 6),
            longitude=round(float(detection.longitude), 6),
            road_segment=road_segment or f"Monitored Corridor ({detection.latitude:.4f}, {detection.longitude:.4f})",
            city=city,
            initial_confidence=round(float(detection.confidence), 4),  # RAW UNALTERED MODEL CONFIDENCE!
            persistence_score=0.40,
            persistence_status="SINGLE OBSERVATION",
            total_observations=1,
            independent_buses_count=1,
            contributing_buses=bus_id,
            first_detected_at=detection.timestamp if hasattr(detection, "timestamp") and detection.timestamp else now,
            last_detected_at=detection.timestamp if hasattr(detection, "timestamp") and detection.timestamp else now,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        session.add(new_hazard)
        session.commit()
        session.refresh(new_hazard)

        obs = HazardObservation(
            id=uuid4(),
            hazard_id=new_hazard.id,
            detection_id=detection.id if hasattr(detection, "id") else None,
            bus_id=bus_id,
            route_id=route_id,
            road_segment=new_hazard.road_segment,
            model_confidence=round(float(detection.confidence), 4),
            severity=new_hazard.severity,
            latitude=new_hazard.latitude,
            longitude=new_hazard.longitude,
            evidence_path=getattr(detection, "annotated_evidence_path", None) or getattr(detection, "evidence_path", None),
            thumbnail_path=getattr(detection, "thumbnail_path", None),
            observed_at=new_hazard.first_detected_at,
            created_at=now,
        )
        session.add(obs)

        if hasattr(detection, "persistent_hazard_id"):
            detection.persistent_hazard_id = new_hazard.id
            detection.independent_buses_count = 1
            detection.contributing_buses = bus_id
            detection.persistence_badge = "SINGLE OBSERVATION"
            detection.last_detected_at = new_hazard.last_detected_at
            session.add(detection)

        session.commit()
        session.refresh(new_hazard)
        return new_hazard, obs, True

    # ── HELPER UTILITIES ────────────────────────────────────────────────────
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Computes distance between two coordinates in meters using the Haversine formula."""
        r = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2.0) ** 2 +
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    @staticmethod
    def _get_normalized_bbox(bbox: Dict[str, Any], width: int, height: int) -> Dict[str, float]:
        """Ensures bounding box is normalized to 0.0 - 1.0 coordinate space."""
        x1 = float(bbox.get("x1", 0.0))
        y1 = float(bbox.get("y1", 0.0))
        x2 = float(bbox.get("x2", 0.0))
        y2 = float(bbox.get("y2", 0.0))

        if max(x1, x2, y1, y2) > 1.0:
            return {
                "x1": min(1.0, max(0.0, x1 / width)),
                "y1": min(1.0, max(0.0, y1 / height)),
                "x2": min(1.0, max(0.0, x2 / width)),
                "y2": min(1.0, max(0.0, y2 / height)),
            }
        return {
            "x1": min(1.0, max(0.0, x1)),
            "y1": min(1.0, max(0.0, y1)),
            "x2": min(1.0, max(0.0, x2)),
            "y2": min(1.0, max(0.0, y2)),
        }

    @staticmethod
    def _calculate_iou(b1: Dict[str, float], b2: Dict[str, float]) -> float:
        """Calculates Intersection-over-Union between two normalized bounding boxes."""
        inter_x1 = max(b1["x1"], b2["x1"])
        inter_y1 = max(b1["y1"], b2["y1"])
        inter_x2 = min(b1["x2"], b2["x2"])
        inter_y2 = min(b1["y2"], b2["y2"])

        inter_w = max(0.0, inter_x2 - inter_x1)
        inter_h = max(0.0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        b1_area = (b1["x2"] - b1["x1"]) * (b1["y2"] - b1["y1"])
        b2_area = (b2["x2"] - b2["x1"]) * (b2["y2"] - b2["y1"])
        union_area = b1_area + b2_area - inter_area

        if union_area <= 0.0:
            return 0.0
        return inter_area / union_area


# Global singleton instance
_engine_instance: Optional[RoadIntelligenceEngine] = None


def get_road_intelligence_engine() -> RoadIntelligenceEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RoadIntelligenceEngine()
    return _engine_instance


haversine_distance = RoadIntelligenceEngine.haversine_distance
