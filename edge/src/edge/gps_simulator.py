"""
GPS Simulator
=============
Simulates realistic GPS coordinates along a named route.
Each route is a list of (lat, lon) waypoints; the simulator interpolates
between them at a configurable speed.
"""

import math
import time
from typing import List, Tuple, Optional

# Sample routes: dict of route_id → list of (lat, lon) waypoints
SAMPLE_ROUTES: dict[str, List[Tuple[float, float]]] = {
    "ROUTE_1": [
        (28.6139, 77.2090),  # New Delhi – Connaught Place
        (28.6228, 77.2089),
        (28.6317, 77.2088),
        (28.6450, 77.2100),
        (28.6555, 77.2300),
        (28.6600, 77.2500),
    ],
    "ROUTE_2": [
        (19.0760, 72.8777),  # Mumbai
        (19.0820, 72.8830),
        (19.0900, 72.8900),
        (19.0980, 72.8960),
    ],
    "ROUTE_3": [
        (12.9716, 77.5946),  # Bangalore
        (12.9780, 77.6000),
        (12.9840, 77.6080),
        (12.9900, 77.6150),
    ],
}


def _haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Great-circle distance in km between two (lat, lon) pairs."""
    R = 6371.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(h))


def _interpolate(a: Tuple[float, float], b: Tuple[float, float], t: float) -> Tuple[float, float]:
    """Linear interpolation between two (lat, lon) pairs at ratio t ∈ [0, 1]."""
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _bearing_degrees(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Compass bearing from a to b in degrees (0 = North)."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


class GPSSimulator:
    """
    Walks along a route's waypoints at a given speed (km/h).
    Call `update(dt)` every simulation tick with elapsed seconds.
    """

    def __init__(self, route_id: str = "ROUTE_1", speed_kmh: float = 30.0):
        self._waypoints = list(SAMPLE_ROUTES.get(route_id, SAMPLE_ROUTES["ROUTE_1"]))
        self._speed_kmh = speed_kmh
        self._segment_idx = 0
        self._segment_t = 0.0  # progress within current segment [0, 1]
        self._lat, self._lon = self._waypoints[0]
        self._bearing = 0.0

    def reset(self, route_id: str = "ROUTE_1", speed_kmh: float = 30.0):
        self.__init__(route_id, speed_kmh)

    def update(self, dt: float) -> Tuple[float, float, float]:
        """
        Advance position by dt seconds.
        Returns (lat, lon, bearing_deg).
        """
        if self._segment_idx >= len(self._waypoints) - 1:
            # Loop back to start
            self._segment_idx = 0
            self._segment_t = 0.0

        a = self._waypoints[self._segment_idx]
        b = self._waypoints[self._segment_idx + 1]
        seg_km = _haversine_km(a, b)

        if seg_km < 1e-6:
            self._segment_idx += 1
            return self._lat, self._lon, self._bearing

        # Fraction of segment to advance in dt seconds
        advance = (self._speed_kmh / 3600.0 * dt) / seg_km
        self._segment_t += advance

        if self._segment_t >= 1.0:
            self._segment_t -= 1.0
            self._segment_idx += 1
            if self._segment_idx >= len(self._waypoints) - 1:
                self._segment_idx = 0
            a = self._waypoints[self._segment_idx]
            b = self._waypoints[self._segment_idx + 1]

        self._lat, self._lon = _interpolate(a, b, self._segment_t)
        self._bearing = _bearing_degrees(a, b)
        return self._lat, self._lon, self._bearing

    @property
    def position(self) -> dict:
        return {
            "lat": round(self._lat, 6),
            "lon": round(self._lon, 6),
            "bearing_deg": round(self._bearing, 1),
        }

    @property
    def available_routes(self) -> List[str]:
        return list(SAMPLE_ROUTES.keys())
