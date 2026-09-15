"""
School Zone Geospatial & Bell Schedule Database
===============================================
Maintains geofenced school zones and active operating hours.

Fields:
  - school_id: Unique school identifier
  - name: School name
  - location: GPS coordinate (lat, lon)
  - radius_m: Circular geofence radius in meters (or polygon)
  - active_hours: Time ranges when students enter/exit (e.g. 07:30-09:30, 13:30-15:45)
  - speed_limit_kmh: Regulated school zone speed limit
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timezone
import math
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class GpsPoint:
    lat: float
    lon: float


@dataclass
class SchoolZone:
    school_id:       str
    name:            str
    city:            str
    location:        GpsPoint
    radius_m:        float = 250.0
    active_hours:    List[Tuple[str, str]] = field(default_factory=lambda: [("07:30", "09:30"), ("13:30", "16:00")])
    speed_limit_kmh: float = 25.0
    polygon:         Optional[List[GpsPoint]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "school_id":       self.school_id,
            "name":            self.name,
            "city":            self.city,
            "location":        {"lat": self.location.lat, "lon": self.location.lon},
            "radius_m":        self.radius_m,
            "active_hours":    self.active_hours,
            "speed_limit_kmh": self.speed_limit_kmh,
        }


# ── Haversine distance in meters ──────────────────────────────────────────────

_R_EARTH_METERS = 6371000.0

def _haversine_distance_m(p1: GpsPoint, p2: GpsPoint) -> float:
    """Distance between two GPS points in meters."""
    lat1, lat2 = math.radians(p1.lat), math.radians(p2.lat)
    dlat = math.radians(p2.lat - p1.lat)
    dlon = math.radians(p2.lon - p1.lon)
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    return 2 * _R_EARTH_METERS * math.asin(math.sqrt(a))


def is_time_in_ranges(t: time, ranges: List[Tuple[str, str]]) -> bool:
    """Check if a time falls within any [start_str, end_str] interval."""
    cur_mins = t.hour * 60 + t.minute
    for start_str, end_str in ranges:
        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))
        if (sh * 60 + sm) <= cur_mins <= (eh * 60 + em):
            return True
    return False


# ── Seed School Zones ────────────────────────────────────────────────────────

DEFAULT_SCHOOL_ZONES: List[SchoolZone] = [
    # Delhi
    SchoolZone(
        school_id="SCH_DEL_01",
        name="Delhi Public School, R.K. Puram",
        city="Delhi",
        location=GpsPoint(28.5672, 77.1720),
        radius_m=300.0,
        active_hours=[("07:30", "09:30"), ("13:30", "15:45")],
        speed_limit_kmh=25.0,
    ),
    SchoolZone(
        school_id="SCH_DEL_02",
        name="Army Public School, Dhaula Kuan",
        city="Delhi",
        location=GpsPoint(28.5910, 77.1650),
        radius_m=350.0,
        active_hours=[("07:15", "09:15"), ("13:15", "15:30")],
        speed_limit_kmh=25.0,
    ),
    SchoolZone(
        school_id="SCH_DEL_03",
        name="Modern School, Barakhamba",
        city="Delhi",
        location=GpsPoint(28.6295, 77.2285),
        radius_m=250.0,
        active_hours=[("07:45", "09:45"), ("13:45", "16:00")],
        speed_limit_kmh=25.0,
    ),

    # Mumbai
    SchoolZone(
        school_id="SCH_MUM_01",
        name="Dhirubhai Ambani International School, BKC",
        city="Mumbai",
        location=GpsPoint(19.0655, 72.8680),
        radius_m=300.0,
        active_hours=[("07:30", "09:30"), ("14:00", "16:15")],
        speed_limit_kmh=25.0,
    ),
    SchoolZone(
        school_id="SCH_MUM_02",
        name="St. Xavier's High School, Fort",
        city="Mumbai",
        location=GpsPoint(18.9430, 72.8315),
        radius_m=250.0,
        active_hours=[("07:15", "09:30"), ("13:30", "15:45")],
        speed_limit_kmh=25.0,
    ),

    # Bangalore
    SchoolZone(
        school_id="SCH_BLR_01",
        name="National Public School, Indiranagar",
        city="Bangalore",
        location=GpsPoint(12.9780, 77.6430),
        radius_m=250.0,
        active_hours=[("07:45", "09:45"), ("14:15", "16:00")],
        speed_limit_kmh=25.0,
    ),
    SchoolZone(
        school_id="SCH_BLR_02",
        name="Bishop Cotton Boys' School, Residency Road",
        city="Bangalore",
        location=GpsPoint(12.9690, 77.6010),
        radius_m=300.0,
        active_hours=[("07:30", "09:30"), ("13:30", "15:45")],
        speed_limit_kmh=25.0,
    ),
]


class SchoolZoneDatabase:
    """
    Registry and geofencing engine for urban school zones.
    """

    def __init__(self, zones: Optional[List[SchoolZone]] = None):
        self._zones: List[SchoolZone] = list(zones or DEFAULT_SCHOOL_ZONES)
        self._by_id: Dict[str, SchoolZone] = {z.school_id: z for z in self._zones}

    def add_zone(self, zone: SchoolZone):
        self._zones.append(zone)
        self._by_id[zone.school_id] = zone

    def get_zone(self, school_id: str) -> Optional[SchoolZone]:
        return self._by_id.get(school_id)

    def all_zones(self) -> List[SchoolZone]:
        return list(self._zones)

    def check_location(
        self,
        lat: float,
        lon: float,
        dt: Optional[datetime] = None,
    ) -> Optional[Tuple[SchoolZone, float, bool]]:
        """
        Check if (lat, lon) is within any school zone geofence.

        Returns:
          (SchoolZone, distance_m, is_active_hours) or None
        """
        target = GpsPoint(lat=lat, lon=lon)
        now_dt = dt or datetime.now(timezone.utc)
        cur_time = now_dt.time()

        # Is it a weekend? (Saturday=5, Sunday=6)
        is_weekend = now_dt.weekday() >= 5

        closest_zone: Optional[SchoolZone] = None
        min_dist = float("inf")

        for zone in self._zones:
            dist = _haversine_distance_m(target, zone.location)
            if dist <= zone.radius_m:
                if dist < min_dist:
                    min_dist = dist
                    closest_zone = zone

        if closest_zone is not None:
            # Active hours check (inactive on weekends)
            active_now = not is_weekend and is_time_in_ranges(cur_time, closest_zone.active_hours)
            return (closest_zone, round(min_dist, 1), active_now)

        return None
