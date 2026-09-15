"""
Demo Seeder Service (Phase 34)
==============================
Generates and maintains a realistic demonstration environment:
  - 20 connected buses (BUS_001 through BUS_020)
  - 5 major metropolitan transit routes
  - 115 distinct road segments (exceeds 100+ requirement)
  - 500+ realistic historical events across 7 types:
      * Potholes
      * Waterlogging
      * Congestion
      * Road damage
      * Missing signs
      * Pedestrian risk
      * Possible incidents
  - Realistic waypoint-interpolated movement along routes
  - Live simulation ticker & DEMO MODE state indicator
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import random
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select

from ..database.session import engine
from ..models.ingested_event import IngestedEvent

logger = logging.getLogger("services.demo_seeder")


# ── 5 Routes & 115 Road Segments ──────────────────────────────────────────────

ROUTE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "ROUTE_1": {
        "name": "Route 1 — Connaught Place Circular Ring (Delhi)",
        "city": "New Delhi",
        "color": "#6366f1",
        "waypoints": [
            (28.6328, 77.2185), (28.6340, 77.2215), (28.6320, 77.2250),
            (28.6290, 77.2270), (28.6265, 77.2240), (28.6250, 77.2200),
            (28.6270, 77.2160), (28.6300, 77.2150), (28.6328, 77.2185),
        ],
        "segment_count": 25,
        "prefix": "CP_RING",
    },
    "ROUTE_2": {
        "name": "Route 2 — Mumbai Western Express Arterial (Mumbai)",
        "city": "Mumbai",
        "color": "#06b6d4",
        "waypoints": [
            (19.0550, 72.8350), (19.0680, 72.8420), (19.0820, 72.8510),
            (19.0960, 72.8600), (19.1120, 72.8680), (19.1300, 72.8720),
            (19.1550, 72.8750), (19.1780, 72.8690), (19.2050, 72.8620),
        ],
        "segment_count": 25,
        "prefix": "WEH_MUM",
    },
    "ROUTE_3": {
        "name": "Route 3 — Bengaluru Outer Ring Road Tech Trunk (Bengaluru)",
        "city": "Bengaluru",
        "color": "#10b981",
        "waypoints": [
            (12.9250, 77.6850), (12.9350, 77.6920), (12.9520, 77.7010),
            (12.9730, 77.7120), (12.9900, 77.7050), (13.0100, 77.6900),
            (13.0250, 77.6650), (13.0380, 77.6400), (13.0450, 77.6150),
        ],
        "segment_count": 25,
        "prefix": "ORR_BLR",
    },
    "ROUTE_4": {
        "name": "Route 4 — Old Delhi Heritage Loop (Chandni Chowk - Red Fort)",
        "city": "New Delhi",
        "color": "#f59e0b",
        "waypoints": [
            (28.6505, 77.2300), (28.6530, 77.2350), (28.6560, 77.2410),
            (28.6580, 77.2450), (28.6550, 77.2490), (28.6500, 77.2440),
            (28.6470, 77.2380), (28.6485, 77.2320), (28.6505, 77.2300),
        ],
        "segment_count": 20,
        "prefix": "HERITAGE_DEL",
    },
    "ROUTE_5": {
        "name": "Route 5 — Indira Gandhi Airport Express Corridor",
        "city": "New Delhi",
        "color": "#ec4899",
        "waypoints": [
            (28.5800, 77.1600), (28.5680, 77.1450), (28.5550, 77.1300),
            (28.5480, 77.1120), (28.5520, 77.0950), (28.5580, 77.0850),
            (28.5650, 77.0900), (28.5720, 77.1100), (28.5800, 77.1600),
        ],
        "segment_count": 20,
        "prefix": "AERO_DEL",
    },
}


# ── Road Segments Generator ───────────────────────────────────────────────────

def _generate_road_segments() -> List[Dict[str, Any]]:
    segments = []
    for r_id, cfg in ROUTE_CONFIGS.items():
        prefix = cfg["prefix"]
        count = cfg["segment_count"]
        wps = cfg["waypoints"]
        for i in range(1, count + 1):
            t_ratio = (i - 1) / max(1, count - 1)
            # Find approximate coordinates along waypoints
            idx = int(t_ratio * (len(wps) - 1))
            lat, lon = wps[min(idx, len(wps) - 1)]
            seg_id = f"{prefix}_SEG_{i:02d}"
            seg_name = f"{cfg['city']} {prefix} Corridor - Section {i}"
            speed_limit = 50 if "RING" in prefix or "MUM" in prefix else 40
            segments.append({
                "segment_id": seg_id,
                "route_id": r_id,
                "name": seg_name,
                "speed_limit_kmh": speed_limit,
                "lanes": 3 if "WEH" in prefix or "ORR" in prefix else 2,
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "surface_condition": random.choice(["EXCELLENT", "GOOD", "FAIR", "NEEDS_MAINTENANCE"]),
            })
    return segments


ALL_ROAD_SEGMENTS: List[Dict[str, Any]] = _generate_road_segments()


# ── 20 Buses Specification ────────────────────────────────────────────────────

def _generate_twenty_buses() -> List[Dict[str, Any]]:
    buses = []
    routes = list(ROUTE_CONFIGS.keys())
    models = [
        ("Tata Ultra Electric EV", "ELECTRIC"),
        ("Ashok Leyland JanBus CNG", "CNG"),
        ("Olectra K9 Electric", "ELECTRIC"),
        ("Volvo 8400 Low Floor", "DIESEL_HYBRID"),
        ("Switch EiV 12 Electric", "ELECTRIC"),
    ]

    for b in range(1, 21):
        bus_id = f"BUS_{b:03d}"
        route_id = routes[(b - 1) % len(routes)]
        cfg = ROUTE_CONFIGS[route_id]
        model_name, p_type = models[(b - 1) % len(models)]

        # Initial offset along route waypoints
        wps = cfg["waypoints"]
        offset_idx = (b * 2) % len(wps)
        lat, lon = wps[offset_idx]

        buses.append({
            "bus_id": bus_id,
            "route_id": route_id,
            "route_name": cfg["name"],
            "name": f"Bus {100 + b} ({model_name})",
            "model": model_name,
            "propulsion": p_type,
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "bearing_deg": round((b * 35.0) % 360.0, 1),
            "speed_kmh": round(random.uniform(22.0, 42.0), 1),
            "status": "IN_SERVICE",
            "passenger_occupancy_pct": random.randint(35, 88),
            "active_cameras": 4,
            "camera_status": "HEALTHY" if b != 4 else "WARNING",
            "edge_device": "NVIDIA Jetson AGX Orin 64GB",
            "driver_name": f"Driver {b:02d} (Emp #{4000 + b})",
            "segment_idx": offset_idx,
            "segment_progress": random.uniform(0.1, 0.9),
        })
    return buses


# ── Demo Seeder & Kinematics Engine ───────────────────────────────────────────

class DemoSeederService:
    """
    Coordinates seeding and real-time kinematic simulation of 20 buses across 5 routes.
    """

    _instance: Optional[DemoSeederService] = None

    def __init__(self):
        self.routes = ROUTE_CONFIGS
        self.segments = ALL_ROAD_SEGMENTS
        self.buses = _generate_twenty_buses()
        self._lock = threading.Lock()
        self._is_seeded = False
        self._is_demo_mode = True
        self._last_tick_time = time.time()

    @classmethod
    def get_instance(cls) -> DemoSeederService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_demo_mode(self) -> bool:
        return self._is_demo_mode

    def get_status(self) -> Dict[str, Any]:
        with Session(engine) as session:
            ev_count = session.exec(select(IngestedEvent)).all()
            total_events = len(ev_count)

        return {
            "demo_mode": True,
            "indicator": "DEMO MODE",
            "banner_text": "⚡ DEMO MODE | 20 Active Buses • 5 Routes • 115 Road Segments • Simulated Fleet Telemetry",
            "buses_count": len(self.buses),
            "routes_count": len(self.routes),
            "road_segments_count": len(self.segments),
            "historical_events_in_database": total_events,
            "is_seeded": self._is_seeded,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def get_buses(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(b) for b in self.buses]

    def get_routes(self) -> Dict[str, Any]:
        return {
            "routes": [
                {
                    "route_id": r_id,
                    "name": cfg["name"],
                    "city": cfg["city"],
                    "color": cfg["color"],
                    "segment_count": cfg["segment_count"],
                    "waypoints": cfg["waypoints"],
                }
                for r_id, cfg in self.routes.items()
            ],
            "total_segments": len(self.segments),
            "segments_sample": self.segments[:15],
        }

    def advance_kinematics(self, dt_seconds: float = 2.0) -> List[Dict[str, Any]]:
        """
        Advances all 20 buses along their respective route waypoints realistically.
        """
        with self._lock:
            for b in self.buses:
                route_id = b["route_id"]
                wps = self.routes[route_id]["waypoints"]
                curr_idx = b.get("segment_idx", 0)
                next_idx = (curr_idx + 1) % len(wps)

                p1 = wps[curr_idx]
                p2 = wps[next_idx]

                # Speed in m/s
                speed_mps = (b.get("speed_kmh", 30.0) * 1000.0) / 3600.0
                dist_traveled = speed_mps * dt_seconds

                # Approximate distance between waypoints (~500m)
                seg_length = 500.0
                prog = b.get("segment_progress", 0.0) + (dist_traveled / seg_length)

                if prog >= 1.0:
                    b["segment_idx"] = next_idx
                    b["segment_progress"] = 0.0
                    prog = 0.0
                    p1 = wps[next_idx]
                    p2 = wps[(next_idx + 1) % len(wps)]
                else:
                    b["segment_progress"] = prog

                # Linear interpolation
                lat = p1[0] + (p2[0] - p1[0]) * prog
                lon = p1[1] + (p2[1] - p1[1]) * prog

                # Compass bearing from p1 to p2
                dlon = math.radians(p2[1] - p1[1])
                lat1 = math.radians(p1[0])
                lat2 = math.radians(p2[0])
                x = math.sin(dlon) * math.cos(lat2)
                y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
                bearing = (math.degrees(math.atan2(x, y)) + 360.0) % 360.0

                b["lat"] = round(lat, 5)
                b["lon"] = round(lon, 5)
                b["bearing_deg"] = round(bearing, 1)
                b["speed_kmh"] = round(max(15.0, min(50.0, b["speed_kmh"] + random.uniform(-2.0, 2.0))), 1)

            self._last_tick_time = time.time()
            return [dict(b) for b in self.buses]

    def seed_historical_events(self, target_count: int = 525) -> int:
        """
        Seeds 500+ historical events into the SQLite/SQLModel database.
        Includes all 7 event types:
          - Potholes
          - Waterlogging
          - Congestion
          - Road damage
          - Missing signs
          - Pedestrian risk
          - Possible incidents
        """
        with self._lock:
            with Session(engine) as session:
                existing = session.exec(select(IngestedEvent)).all()
                if len(existing) >= target_count:
                    self._is_seeded = True
                    return len(existing)

                event_types_weights = [
                    ("POTHOLE", 125, "HIGH"),
                    ("WATERLOGGING", 65, "HIGH"),
                    ("CONGESTION_EVENT", 115, "MEDIUM"),
                    ("DAMAGED_ROAD", 90, "MEDIUM"),
                    ("MISSING_TRAFFIC_SIGN", 45, "LOW"),
                    ("PEDESTRIAN_RISK", 55, "HIGH"),
                    ("POSSIBLE_INCIDENT", 30, "SEVERE"),
                ]

                now = datetime.now(timezone.utc)
                seeded_events = []
                counter = 1

                for ev_type, count_for_type, default_sev in event_types_weights:
                    for i in range(count_for_type):
                        # Distribute randomly over the past 7 days
                        hours_ago = random.uniform(0.5, 168.0)
                        ev_time = now - timedelta(hours=hours_ago)

                        # Pick a random bus and route
                        bus_obj = random.choice(self.buses)
                        bus_id = bus_obj["bus_id"]
                        route_id = bus_obj["route_id"]

                        # Pick matching segment or coordinate
                        cfg = self.routes[route_id]
                        wps = cfg["waypoints"]
                        wp = random.choice(wps)
                        lat = wp[0] + (random.random() - 0.5) * 0.008
                        lon = wp[1] + (random.random() - 0.5) * 0.008

                        seg_id = f"{cfg['prefix']}_SEG_{random.randint(1, cfg['segment_count']):02d}"
                        ev_id = f"ev_demo_{ev_type.lower()}_{counter:04d}"
                        idemp_key = f"idemp_{ev_id}"
                        conf = round(random.uniform(0.82, 0.98), 2)
                        sha256_hash = hashlib.sha256(f"{ev_id}|{bus_id}|{conf}".encode()).hexdigest()

                        status_val = "ACTIVE"
                        if hours_ago > 48 and random.random() > 0.4:
                            status_val = "RESOLVED"
                        elif hours_ago > 12 and random.random() > 0.3:
                            status_val = "CONFIRMED"

                        db_event = IngestedEvent(
                            idempotency_key=idemp_key,
                            event_id=ev_id,
                            event_type=ev_type,
                            bus_id=bus_id,
                            camera_id="FRONT",
                            timestamp=ev_time,
                            gps_lat=round(lat, 5),
                            gps_lon=round(lon, 5),
                            bearing_deg=round(random.random() * 360.0, 1),
                            road_segment=seg_id,
                            address=f"{cfg['name']} ({seg_id})",
                            district="Central" if "CP" in seg_id or "HERITAGE" in seg_id else "North",
                            confidence=conf,
                            evidence_reference=f"sha256:{sha256_hash}",
                            severity=default_sev,
                            status=status_val,
                            metadata_json=json.dumps({
                                "route_id": route_id,
                                "bus_name": bus_obj["name"],
                                "simulated": True,
                            }),
                            processed_at=ev_time + timedelta(seconds=random.uniform(0.5, 2.0)),
                        )
                        session.add(db_event)
                        counter += 1

                session.commit()
                self._is_seeded = True
                logger.info(f"Successfully seeded {counter - 1} demo historical events into database.")
                return counter - 1


def get_demo_seeder_service() -> DemoSeederService:
    return DemoSeederService.get_instance()
