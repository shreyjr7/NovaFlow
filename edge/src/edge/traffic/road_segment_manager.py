"""
Traffic Bottleneck Detection – Road Segment Manager
=====================================================
Defines named road segments as GPS polylines and provides fast lookup
of which segment a given GPS coordinate belongs to.

Each segment carries:
  - id, name, type (arterial / collector / expressway / local)
  - GPS polyline (ordered list of waypoints)
  - capacity (vehicles/km under free-flow conditions)
  - free_flow_speed_kmh (reference speed with no congestion)

For the hackathon three cities are pre-loaded with realistic segments.
In production these would be loaded from PostGIS road_segments table.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class GpsPoint:
    lat: float
    lon: float


@dataclass
class RoadSegment:
    segment_id:          str
    name:                str
    road_type:           str          # "arterial" | "collector" | "expressway" | "local"
    city:                str
    polyline:            List[GpsPoint]
    capacity_per_km:     int   = 80   # vehicles/km at free flow
    free_flow_speed_kmh: float = 50.0
    length_km:           float = 1.0
    tags:                Dict  = field(default_factory=dict)

    @property
    def midpoint(self) -> GpsPoint:
        """Approximate midpoint of the polyline."""
        lats = [p.lat for p in self.polyline]
        lons = [p.lon for p in self.polyline]
        return GpsPoint(lat=sum(lats)/len(lats), lon=sum(lons)/len(lons))


# ── Haversine distance helper ─────────────────────────────────────────────────

_R_EARTH_KM = 6371.0

def _haversine_km(p1: GpsPoint, p2: GpsPoint) -> float:
    """Great-circle distance between two GPS points in kilometres."""
    lat1, lat2 = math.radians(p1.lat), math.radians(p2.lat)
    dlat = math.radians(p2.lat - p1.lat)
    dlon = math.radians(p2.lon - p1.lon)
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * _R_EARTH_KM * math.asin(math.sqrt(a))


def _point_to_segment_km(p: GpsPoint, a: GpsPoint, b: GpsPoint) -> float:
    """Minimum distance from point p to line segment a→b (km)."""
    ax, ay = a.lon, a.lat
    bx, by = b.lon, b.lat
    px, py = p.lon, p.lat
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return _haversine_km(p, a)
    t = max(0, min(1, ((px-ax)*dx + (py-ay)*dy) / (dx*dx + dy*dy)))
    closest = GpsPoint(lat=ay + t*dy, lon=ax + t*dx)
    return _haversine_km(p, closest)


def _polyline_min_dist_km(p: GpsPoint, polyline: List[GpsPoint]) -> float:
    """Minimum distance from point p to any segment of the polyline (km)."""
    if len(polyline) == 1:
        return _haversine_km(p, polyline[0])
    return min(_point_to_segment_km(p, polyline[i], polyline[i+1])
               for i in range(len(polyline)-1))


# ── Pre-defined road segments for 3 sample cities ────────────────────────────

ROAD_SEGMENTS: List[RoadSegment] = [
    # ── Delhi ──────────────────────────────────────────────────────────────────
    RoadSegment(
        segment_id="DEL_01", name="Ring Road – Dhaula Kuan to Mahipalpur",
        road_type="expressway", city="Delhi",
        polyline=[GpsPoint(28.5918, 77.1675), GpsPoint(28.5842, 77.1545),
                  GpsPoint(28.5765, 77.1420)],
        capacity_per_km=120, free_flow_speed_kmh=70.0, length_km=2.1,
    ),
    RoadSegment(
        segment_id="DEL_02", name="NH-48 – Dhaula Kuan to Shankar Vihar",
        road_type="arterial", city="Delhi",
        polyline=[GpsPoint(28.5971, 77.1690), GpsPoint(28.6050, 77.1680),
                  GpsPoint(28.6130, 77.1670)],
        capacity_per_km=90, free_flow_speed_kmh=55.0, length_km=1.8,
    ),
    RoadSegment(
        segment_id="DEL_03", name="Mehrauli-Badarpur Road",
        road_type="arterial", city="Delhi",
        polyline=[GpsPoint(28.5205, 77.1855), GpsPoint(28.5145, 77.1960),
                  GpsPoint(28.5085, 77.2065)],
        capacity_per_km=75, free_flow_speed_kmh=45.0, length_km=1.5,
    ),
    RoadSegment(
        segment_id="DEL_04", name="Outer Ring Road – Dhaula Kuan",
        road_type="arterial", city="Delhi",
        polyline=[GpsPoint(28.6102, 77.1540), GpsPoint(28.6150, 77.1640),
                  GpsPoint(28.6148, 77.1740)],
        capacity_per_km=80, free_flow_speed_kmh=50.0, length_km=1.2,
    ),

    # ── Mumbai ─────────────────────────────────────────────────────────────────
    RoadSegment(
        segment_id="MUM_01", name="Eastern Express Highway – Kurla",
        road_type="expressway", city="Mumbai",
        polyline=[GpsPoint(19.0748, 72.8856), GpsPoint(19.0800, 72.8900),
                  GpsPoint(19.0855, 72.8940)],
        capacity_per_km=130, free_flow_speed_kmh=80.0, length_km=2.3,
    ),
    RoadSegment(
        segment_id="MUM_02", name="LBS Marg – Ghatkopar",
        road_type="arterial", city="Mumbai",
        polyline=[GpsPoint(19.0865, 72.9077), GpsPoint(19.0900, 72.9110),
                  GpsPoint(19.0940, 72.9145)],
        capacity_per_km=70, free_flow_speed_kmh=40.0, length_km=1.4,
    ),
    RoadSegment(
        segment_id="MUM_03", name="Sion – Panvel Highway",
        road_type="expressway", city="Mumbai",
        polyline=[GpsPoint(19.0432, 72.8697), GpsPoint(19.0388, 72.8749),
                  GpsPoint(19.0340, 72.8802)],
        capacity_per_km=110, free_flow_speed_kmh=70.0, length_km=2.0,
    ),

    # ── Bangalore ──────────────────────────────────────────────────────────────
    RoadSegment(
        segment_id="BLR_01", name="Outer Ring Road – Marathahalli",
        road_type="arterial", city="Bangalore",
        polyline=[GpsPoint(12.9591, 77.6971), GpsPoint(12.9540, 77.7020),
                  GpsPoint(12.9489, 77.7070)],
        capacity_per_km=85, free_flow_speed_kmh=45.0, length_km=1.6,
    ),
    RoadSegment(
        segment_id="BLR_02", name="Hosur Road – Silk Board",
        road_type="arterial", city="Bangalore",
        polyline=[GpsPoint(12.9170, 77.6233), GpsPoint(12.9122, 77.6270),
                  GpsPoint(12.9075, 77.6308)],
        capacity_per_km=90, free_flow_speed_kmh=40.0, length_km=1.3,
    ),
    RoadSegment(
        segment_id="BLR_03", name="Bellary Road – Hebbal Flyover",
        road_type="expressway", city="Bangalore",
        polyline=[GpsPoint(13.0359, 77.5970), GpsPoint(13.0395, 77.5985),
                  GpsPoint(13.0430, 77.6000)],
        capacity_per_km=100, free_flow_speed_kmh=60.0, length_km=1.1,
    ),
]

# ── Segment registry ──────────────────────────────────────────────────────────

_SEGMENT_BY_ID: Dict[str, RoadSegment] = {s.segment_id: s for s in ROAD_SEGMENTS}


class RoadSegmentManager:
    """
    Fast nearest-segment lookup via brute-force (suitable for ≤ 1000 segments).
    For large datasets, replace with a spatial index (R-tree / PostGIS ST_DWithin).

    Parameters
    ----------
    segments        : list of RoadSegment objects (defaults to ROAD_SEGMENTS)
    snap_radius_km  : maximum distance to associate a GPS point with a segment
    """

    def __init__(
        self,
        segments:       Optional[List[RoadSegment]] = None,
        snap_radius_km: float = 0.15,   # ~150 m
    ):
        self._segments       = segments or ROAD_SEGMENTS
        self._snap_radius_km = snap_radius_km

    def nearest(self, lat: float, lon: float) -> Optional[RoadSegment]:
        """Return the nearest segment within snap_radius_km, or None."""
        point = GpsPoint(lat=lat, lon=lon)
        best_dist = float("inf")
        best_seg: Optional[RoadSegment] = None
        for seg in self._segments:
            d = _polyline_min_dist_km(point, seg.polyline)
            if d < best_dist:
                best_dist = d
                best_seg = seg
        if best_dist <= self._snap_radius_km:
            return best_seg
        return None

    def get(self, segment_id: str) -> Optional[RoadSegment]:
        return _SEGMENT_BY_ID.get(segment_id)

    def all_segments(self) -> List[RoadSegment]:
        return list(self._segments)
