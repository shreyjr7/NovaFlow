"""
Origin-Destination (OD) Traffic Analytics Router (Phase 21)
===========================================================
Aggregated, macro-level vehicle movement patterns between geographic zones.

Privacy & Anonymization Guarantees:
  - Strictly operates on aggregated spatial boundary crossings.
  - Zero personally identifiable tracking, license plate correlation, or individual GPS breadcrumbs.
  - Mandatory label: "Demonstration OD Analysis"
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()

DEMONSTRATION_LABEL = "Demonstration OD Analysis"
PRIVACY_STATEMENT = (
    "Demonstration OD Analysis: Aggregated, anonymized macro vehicle movement observations. "
    "Personally identifiable vehicle tracking and individual trajectory breadcrumbs are strictly prohibited and omitted."
)

# ── Geographic Zones Definition ───────────────────────────────────────────────

GEOGRAPHIC_ZONES = [
    {
        "zone_id": "Zone A",
        "name": "North Gateway & Transit Hub",
        "sub_regions": ["Kashmere Gate", "Civil Lines", "ISBT Hub", "Model Town"],
        "city": "Delhi NCR",
        "centroid": {"lat": 28.6675, "lon": 77.2285},
        "radius_meters": 3200,
        "primary_land_use": "Intermodal Transit Terminal & Residential Suburbs",
        "polygon": [
            {"lat": 28.6850, "lon": 77.2100},
            {"lat": 28.6850, "lon": 77.2450},
            {"lat": 28.6500, "lon": 77.2500},
            {"lat": 28.6500, "lon": 77.2100},
        ],
        "daily_trip_generation": 42500,
        "daily_trip_attraction": 38900,
    },
    {
        "zone_id": "Zone B",
        "name": "Central Business District & Commercial Core",
        "sub_regions": ["Connaught Place", "Barakhamba", "Janpath", "Mandi House"],
        "city": "Delhi NCR",
        "centroid": {"lat": 28.6315, "lon": 77.2167},
        "radius_meters": 2800,
        "primary_land_use": "Commercial, Government Offices & Financial District",
        "polygon": [
            {"lat": 28.6450, "lon": 77.2000},
            {"lat": 28.6450, "lon": 77.2350},
            {"lat": 28.6180, "lon": 77.2350},
            {"lat": 28.6180, "lon": 77.2000},
        ],
        "daily_trip_generation": 34200,
        "daily_trip_attraction": 64800,
    },
    {
        "zone_id": "Zone C",
        "name": "South Tech Corridor & Trade Centre",
        "sub_regions": ["Nehru Place", "Saket", "Okhla Industrial Phase", "Greater Kailash"],
        "city": "Delhi NCR",
        "centroid": {"lat": 28.5494, "lon": 77.2515},
        "radius_meters": 3600,
        "primary_land_use": "IT Parks, Electronics Market & Retail Trade",
        "polygon": [
            {"lat": 28.5700, "lon": 77.2300},
            {"lat": 28.5700, "lon": 77.2800},
            {"lat": 28.5250, "lon": 77.2800},
            {"lat": 28.5250, "lon": 77.2300},
        ],
        "daily_trip_generation": 39800,
        "daily_trip_attraction": 48200,
    },
    {
        "zone_id": "Zone D",
        "name": "East Residential & Industrial Gateway",
        "sub_regions": ["Laxmi Nagar", "Anand Vihar ISBT", "Patparganj", "Preet Vihar"],
        "city": "Delhi NCR",
        "centroid": {"lat": 28.6469, "lon": 77.3150},
        "radius_meters": 3400,
        "primary_land_use": "High-Density Residential & Logistics Corridors",
        "polygon": [
            {"lat": 28.6650, "lon": 77.2950},
            {"lat": 28.6650, "lon": 77.3350},
            {"lat": 28.6250, "lon": 77.3350},
            {"lat": 28.6250, "lon": 77.2950},
        ],
        "daily_trip_generation": 51600,
        "daily_trip_attraction": 28400,
    },
]

# ── Aggregated Zone Movement Data (Simulated for Hackathon) ───────────────────
# Movements: A -> B, A -> C, B -> D, C -> A, D -> B, etc.

OD_MOVEMENTS_SEED = [
    # A -> B (North Gateway to CBD)
    {
        "origin_id": "Zone A",
        "origin_name": "Zone A (North Gateway)",
        "destination_id": "Zone B",
        "destination_name": "Zone B (Central Commercial Core)",
        "pair_key": "A → B",
        "daily_volume": 18450,
        "morning_peak_volume": 6820,
        "evening_peak_volume": 3140,
        "distance_km": 6.8,
        "avg_duration_minutes": 26.5,
        "free_flow_duration_minutes": 14.0,
        "avg_speed_kmh": 15.4,
        "corridor_route": "Subhash Marg – Delhi Gate – Daryaganj",
        "mode_split": {"public_bus": 44, "car": 31, "two_wheeler": 20, "commercial": 5},
        "peak_movement_period": "08:15 - 10:45 (Inbound Commuter Surge)",
    },
    # A -> C (North Gateway to South Tech Hub)
    {
        "origin_id": "Zone A",
        "origin_name": "Zone A (North Gateway)",
        "destination_id": "Zone C",
        "destination_name": "Zone C (South Tech Corridor)",
        "pair_key": "A → C",
        "daily_volume": 12600,
        "morning_peak_volume": 4750,
        "evening_peak_volume": 2680,
        "distance_km": 17.2,
        "avg_duration_minutes": 52.0,
        "free_flow_duration_minutes": 28.0,
        "avg_speed_kmh": 19.8,
        "corridor_route": "Ring Road – ITO – Ashram Flyover",
        "mode_split": {"public_bus": 38, "car": 40, "two_wheeler": 18, "commercial": 4},
        "peak_movement_period": "08:30 - 10:30 (Cross-City Tech Commute)",
    },
    # B -> D (CBD to East Residential)
    {
        "origin_id": "Zone B",
        "origin_name": "Zone B (Central Commercial Core)",
        "destination_id": "Zone D",
        "destination_name": "Zone D (East Gateway)",
        "pair_key": "B → D",
        "daily_volume": 16900,
        "morning_peak_volume": 2890,
        "evening_peak_volume": 7150,
        "distance_km": 11.5,
        "avg_duration_minutes": 44.5,
        "free_flow_duration_minutes": 22.0,
        "avg_speed_kmh": 15.5,
        "corridor_route": "Vikas Marg – ITO Chungi – Laxmi Nagar Flyover",
        "mode_split": {"public_bus": 42, "car": 33, "two_wheeler": 21, "commercial": 4},
        "peak_movement_period": "17:45 - 20:45 (Evening Outbound Tidal Surge)",
    },
    # C -> A (South Tech Hub to North Gateway)
    {
        "origin_id": "Zone C",
        "origin_name": "Zone C (South Tech Corridor)",
        "destination_id": "Zone A",
        "destination_name": "Zone A (North Gateway)",
        "pair_key": "C → A",
        "daily_volume": 11800,
        "morning_peak_volume": 2420,
        "evening_peak_volume": 5890,
        "distance_km": 17.5,
        "avg_duration_minutes": 49.0,
        "free_flow_duration_minutes": 28.0,
        "avg_speed_kmh": 21.4,
        "corridor_route": "Ring Road Northbound – Moolchand – Rajghat",
        "mode_split": {"public_bus": 41, "car": 36, "two_wheeler": 19, "commercial": 4},
        "peak_movement_period": "18:00 - 20:30 (Evening Return Commute)",
    },
    # D -> B (East Residential to CBD)
    {
        "origin_id": "Zone D",
        "origin_name": "Zone D (East Gateway)",
        "destination_id": "Zone B",
        "destination_name": "Zone B (Central Commercial Core)",
        "pair_key": "D → B",
        "daily_volume": 19800,
        "morning_peak_volume": 7940,
        "evening_peak_volume": 2980,
        "distance_km": 11.2,
        "avg_duration_minutes": 42.0,
        "free_flow_duration_minutes": 21.0,
        "avg_speed_kmh": 16.0,
        "corridor_route": "Vikas Marg Inbound – Yamuna Bridge – Tilak Bridge",
        "mode_split": {"public_bus": 48, "car": 29, "two_wheeler": 21, "commercial": 2},
        "peak_movement_period": "08:15 - 10:30 (Peak Trans-Yamuna Inbound Surge)",
    },
    # B -> C (CBD to South Tech Corridor)
    {
        "origin_id": "Zone B",
        "origin_name": "Zone B (Central Commercial Core)",
        "destination_id": "Zone C",
        "destination_name": "Zone C (South Tech Corridor)",
        "pair_key": "B → C",
        "daily_volume": 14100,
        "morning_peak_volume": 4200,
        "evening_peak_volume": 4650,
        "distance_km": 12.8,
        "avg_duration_minutes": 38.0,
        "free_flow_duration_minutes": 20.0,
        "avg_speed_kmh": 20.2,
        "corridor_route": "Lala Lajpat Rai Marg – Defence Colony – Moolchand",
        "mode_split": {"public_bus": 36, "car": 45, "two_wheeler": 16, "commercial": 3},
        "peak_movement_period": "11:00 - 13:00 & 16:30 - 18:30 (Inter-Business Trips)",
    },
    # C -> B (South Tech Corridor to CBD)
    {
        "origin_id": "Zone C",
        "origin_name": "Zone C (South Tech Corridor)",
        "destination_id": "Zone B",
        "destination_name": "Zone B (Central Commercial Core)",
        "pair_key": "C → B",
        "daily_volume": 13900,
        "morning_peak_volume": 4980,
        "evening_peak_volume": 3820,
        "distance_km": 12.8,
        "avg_duration_minutes": 36.5,
        "free_flow_duration_minutes": 20.0,
        "avg_speed_kmh": 21.0,
        "corridor_route": "Barapullah Elevated – Lodhi Road – Janpath",
        "mode_split": {"public_bus": 35, "car": 47, "two_wheeler": 15, "commercial": 3},
        "peak_movement_period": "09:00 - 11:15 (Morning Inbound Executive Transit)",
    },
    # D -> C (East Residential to South Tech Corridor)
    {
        "origin_id": "Zone D",
        "origin_name": "Zone D (East Gateway)",
        "destination_id": "Zone C",
        "destination_name": "Zone C (South Tech Corridor)",
        "pair_key": "D → C",
        "daily_volume": 15200,
        "morning_peak_volume": 6120,
        "evening_peak_volume": 2450,
        "distance_km": 15.6,
        "avg_duration_minutes": 48.0,
        "free_flow_duration_minutes": 25.0,
        "avg_speed_kmh": 19.5,
        "corridor_route": "Noida Link Road – Kalindi Kunj – Modi Mill Flyover",
        "mode_split": {"public_bus": 43, "car": 33, "two_wheeler": 20, "commercial": 4},
        "peak_movement_period": "08:30 - 10:45 (Trans-Yamuna Tech Hub Commuters)",
    },
    # C -> D (South Tech Corridor to East Residential)
    {
        "origin_id": "Zone C",
        "origin_name": "Zone C (South Tech Corridor)",
        "destination_id": "Zone D",
        "destination_name": "Zone D (East Gateway)",
        "pair_key": "C → D",
        "daily_volume": 14600,
        "morning_peak_volume": 2150,
        "evening_peak_volume": 6480,
        "distance_km": 15.6,
        "avg_duration_minutes": 51.0,
        "free_flow_duration_minutes": 25.0,
        "avg_speed_kmh": 18.3,
        "corridor_route": "Outer Ring Road – Sarita Vihar – Mayur Vihar",
        "mode_split": {"public_bus": 44, "car": 31, "two_wheeler": 21, "commercial": 4},
        "peak_movement_period": "18:00 - 20:45 (Evening Outbound Return Surge)",
    },
    # A -> D (North Gateway to East Suburbs)
    {
        "origin_id": "Zone A",
        "origin_name": "Zone A (North Gateway)",
        "destination_id": "Zone D",
        "destination_name": "Zone D (East Gateway)",
        "pair_key": "A → D",
        "daily_volume": 8900,
        "morning_peak_volume": 2850,
        "evening_peak_volume": 2940,
        "distance_km": 12.1,
        "avg_duration_minutes": 35.0,
        "free_flow_duration_minutes": 20.0,
        "avg_speed_kmh": 20.7,
        "corridor_route": "ISBT Flyover – Geeta Colony – Vikas Marg",
        "mode_split": {"public_bus": 50, "car": 25, "two_wheeler": 20, "commercial": 5},
        "peak_movement_period": "09:00 - 10:30 & 18:30 - 20:00 (Inter-Suburban Transit)",
    },
    # D -> A (East Suburbs to North Gateway)
    {
        "origin_id": "Zone D",
        "origin_name": "Zone D (East Gateway)",
        "destination_id": "Zone A",
        "destination_name": "Zone A (North Gateway)",
        "pair_key": "D → A",
        "daily_volume": 8400,
        "morning_peak_volume": 2910,
        "evening_peak_volume": 2720,
        "distance_km": 12.1,
        "avg_duration_minutes": 34.0,
        "free_flow_duration_minutes": 20.0,
        "avg_speed_kmh": 21.3,
        "corridor_route": "Shastri Park – Yamuna Bund – Old Delhi",
        "mode_split": {"public_bus": 52, "car": 24, "two_wheeler": 19, "commercial": 5},
        "peak_movement_period": "08:45 - 10:15 & 18:15 - 19:45",
    },
    # B -> A (CBD to North Gateway)
    {
        "origin_id": "Zone B",
        "origin_name": "Zone B (Central Commercial Core)",
        "destination_id": "Zone A",
        "destination_name": "Zone A (North Gateway)",
        "pair_key": "B → A",
        "daily_volume": 12400,
        "morning_peak_volume": 2100,
        "evening_peak_volume": 5320,
        "distance_km": 6.8,
        "avg_duration_minutes": 24.5,
        "free_flow_duration_minutes": 14.0,
        "avg_speed_kmh": 16.6,
        "corridor_route": "Ajmeri Gate – Paharganj – Civil Lines",
        "mode_split": {"public_bus": 43, "car": 32, "two_wheeler": 22, "commercial": 3},
        "peak_movement_period": "17:30 - 20:00 (Evening Northbound Commuters)",
    },
]

# Intrazonal circulation estimates (within same zone)
INTRAZONAL_SEED = {
    "Zone A": {"volume": 9200, "avg_duration_min": 12.0, "avg_speed": 22.0},
    "Zone B": {"volume": 14500, "avg_duration_min": 14.5, "avg_speed": 16.0},
    "Zone C": {"volume": 18200, "avg_duration_min": 15.0, "avg_speed": 18.5},
    "Zone D": {"volume": 11300, "avg_duration_min": 13.5, "avg_speed": 20.0},
}


# ── Mathematical Helper for Flow Arcs ─────────────────────────────────────────

def _compute_bezier_control_point(p1: Dict[str, float], p2: Dict[str, float], curve_factor: float = 0.15) -> Dict[str, float]:
    """
    Computes a perpendicular bezier control point to render aesthetically pleasing
    curved flow vectors between zone centroids on 2D GIS canvas.
    """
    mid_lat = (p1["lat"] + p2["lat"]) / 2.0
    mid_lon = (p1["lon"] + p2["lon"]) / 2.0
    d_lat = p2["lat"] - p1["lat"]
    d_lon = p2["lon"] - p1["lon"]

    # Perpendicular vector rotated 90 degrees
    ctrl_lat = mid_lat - (d_lon * curve_factor)
    ctrl_lon = mid_lon + (d_lat * curve_factor)
    return {"lat": round(ctrl_lat, 5), "lon": round(ctrl_lon, 5)}


# ── REST Endpoints ────────────────────────────────────────────────────────────

@router.get("/summary")
async def get_od_analytics_summary():
    """
    High-level Origin-Destination KPI summary with strict anonymization statement.
    """
    total_interzonal_volume = sum(m["daily_volume"] for m in OD_MOVEMENTS_SEED)
    total_intrazonal_volume = sum(v["volume"] for v in INTRAZONAL_SEED.values())
    total_daily_movements = total_interzonal_volume + total_intrazonal_volume

    avg_trip_duration = round(
        sum(m["daily_volume"] * m["avg_duration_minutes"] for m in OD_MOVEMENTS_SEED) / total_interzonal_volume, 1
    )
    avg_trip_distance = round(
        sum(m["daily_volume"] * m["distance_km"] for m in OD_MOVEMENTS_SEED) / total_interzonal_volume, 1
    )

    # Calculate net public transport share
    bus_trips = sum(m["daily_volume"] * (m["mode_split"]["public_bus"] / 100.0) for m in OD_MOVEMENTS_SEED)
    bus_share_pct = round((bus_trips / total_interzonal_volume) * 100.0, 1)

    return {
        "demonstration_label": DEMONSTRATION_LABEL,
        "privacy_statement": PRIVACY_STATEMENT,
        "privacy_compliance": {
            "individual_tracking_disabled": True,
            "license_plate_correlation": False,
            "aggregation_level": "Macro Zone-to-Zone Boundary Crossings",
            "anonymization_verified": True,
        },
        "kpis": {
            "total_geographic_zones": len(GEOGRAPHIC_ZONES),
            "total_daily_movements": total_daily_movements,
            "interzonal_trips_volume": total_interzonal_volume,
            "intrazonal_trips_volume": total_intrazonal_volume,
            "average_transit_duration_minutes": avg_trip_duration,
            "average_transit_distance_km": avg_trip_distance,
            "transit_fleet_mode_share_pct": bus_share_pct,
            "busiest_corridor_pair": "D → B (East Residential → CBD)",
        },
    }


@router.get("/zones")
async def list_geographic_zones():
    """
    Returns configured geographic zones (Zone A, Zone B, Zone C, Zone D)
    with polygon perimeters, centroid GPS coordinates, and land-use metadata.
    """
    return {
        "demonstration_label": DEMONSTRATION_LABEL,
        "count": len(GEOGRAPHIC_ZONES),
        "zones": GEOGRAPHIC_ZONES,
    }


@router.get("/matrix")
async def get_origin_destination_matrix():
    """
    Returns the complete 4x4 Origin-Destination cross-tabular matrix.
    Rows = Origin Zones, Columns = Destination Zones.
    Cells contain daily trip volume, morning peak volume, and average duration.
    """
    zone_ids = [z["zone_id"] for z in GEOGRAPHIC_ZONES]

    # Pre-populate map
    lookup = {}
    for m in OD_MOVEMENTS_SEED:
        lookup[(m["origin_id"], m["destination_id"])] = m

    matrix_rows = []
    for origin in zone_ids:
        row_cells = []
        for dest in zone_ids:
            if origin == dest:
                intra = INTRAZONAL_SEED.get(origin, {"volume": 10000, "avg_duration_min": 15.0, "avg_speed": 20.0})
                row_cells.append({
                    "origin": origin,
                    "destination": dest,
                    "is_intrazonal": True,
                    "daily_volume": intra["volume"],
                    "avg_duration_minutes": intra["avg_duration_min"],
                    "avg_speed_kmh": intra["avg_speed"],
                    "distance_km": 3.5,
                })
            else:
                m = lookup.get((origin, dest))
                if m:
                    row_cells.append({
                        "origin": origin,
                        "destination": dest,
                        "is_intrazonal": False,
                        "daily_volume": m["daily_volume"],
                        "morning_peak_volume": m["morning_peak_volume"],
                        "evening_peak_volume": m["evening_peak_volume"],
                        "avg_duration_minutes": m["avg_duration_minutes"],
                        "free_flow_duration_minutes": m["free_flow_duration_minutes"],
                        "avg_speed_kmh": m["avg_speed_kmh"],
                        "distance_km": m["distance_km"],
                        "corridor_route": m["corridor_route"],
                    })
                else:
                    row_cells.append({
                        "origin": origin,
                        "destination": dest,
                        "is_intrazonal": False,
                        "daily_volume": 0,
                        "avg_duration_minutes": 0.0,
                        "avg_speed_kmh": 0.0,
                        "distance_km": 0.0,
                    })

        matrix_rows.append({
            "origin_zone": origin,
            "destinations": row_cells,
            "total_origin_trips": sum(c["daily_volume"] for c in row_cells),
        })

    return {
        "demonstration_label": DEMONSTRATION_LABEL,
        "zone_headers": zone_ids,
        "matrix": matrix_rows,
    }


@router.get("/flows")
async def get_od_flow_map_vectors():
    """
    Directional movement flow vectors for rendering dynamic visual flow arcs on the GIS map.
    Each vector contains origin/destination coordinates, volume intensity, and bezier control points.
    """
    zones_by_id = {z["zone_id"]: z for z in GEOGRAPHIC_ZONES}
    max_volume = max(m["daily_volume"] for m in OD_MOVEMENTS_SEED)

    flow_vectors = []
    for m in OD_MOVEMENTS_SEED:
        orig = zones_by_id[m["origin_id"]]["centroid"]
        dest = zones_by_id[m["destination_id"]]["centroid"]
        vol = m["daily_volume"]
        intensity = round(vol / max_volume, 3)

        ctrl = _compute_bezier_control_point(orig, dest, curve_factor=0.18)

        flow_vectors.append({
            "pair_key": m["pair_key"],
            "origin_id": m["origin_id"],
            "destination_id": m["destination_id"],
            "origin_centroid": orig,
            "destination_centroid": dest,
            "bezier_control_point": ctrl,
            "daily_volume": vol,
            "morning_peak_volume": m["morning_peak_volume"],
            "evening_peak_volume": m["evening_peak_volume"],
            "flow_intensity": intensity,  # 0.0 - 1.0 for visual stroke width
            "avg_duration_minutes": m["avg_duration_minutes"],
            "delay_minutes": round(m["avg_duration_minutes"] - m["free_flow_duration_minutes"], 1),
            "corridor_route": m["corridor_route"],
            "mode_split": m["mode_split"],
        })

    # Sort descending by volume for proper layer stacking
    flow_vectors.sort(key=lambda f: f["daily_volume"], reverse=True)

    return {
        "demonstration_label": DEMONSTRATION_LABEL,
        "count": len(flow_vectors),
        "flows": flow_vectors,
    }


@router.get("/top-pairs")
async def get_top_origin_destination_pairs(
    limit: int = Query(6, ge=1, le=20, description="Number of top OD pairs to return")
):
    """
    Top Origin-Destination pairs ranked by daily commuter volume,
    including delay overhead, transit duration, and primary transit corridor.
    """
    sorted_pairs = sorted(OD_MOVEMENTS_SEED, key=lambda m: m["daily_volume"], reverse=True)
    top_items = []
    for idx, item in enumerate(sorted_pairs[:limit], start=1):
        rec = dict(item)
        rec["rank"] = idx
        rec["delay_minutes"] = round(rec["avg_duration_minutes"] - rec["free_flow_duration_minutes"], 1)
        top_items.append(rec)

    return {
        "demonstration_label": DEMONSTRATION_LABEL,
        "count": len(top_items),
        "limit": limit,
        "top_pairs": top_items,
    }


@router.get("/peak-periods")
async def get_od_peak_movement_periods():
    """
    Compares directional commuter tidal shifts across distinct time periods:
      - Morning Rush (08:00 - 11:00): Strong Inbound to Zone B (CBD) and Zone C (Tech Hub)
      - Evening Rush (17:30 - 21:00): Strong Outbound to Zone A (North) and Zone D (East)
      - Midday Circulation (12:00 - 16:00): Commercial and inter-zone distribution
      - Nocturnal Freight & Logistics (22:00 - 05:30): Outer ring arterial freight
    """
    periods = [
        {
            "period_id": "MORNING_RUSH",
            "name": "Morning Commuter Peak",
            "time_window": "08:00 - 11:00",
            "primary_flow_direction": "Inbound into Central Business District (B) & South Tech Hub (C)",
            "dominant_pairs": ["D → B (7,940 trips)", "A → B (6,820 trips)", "D → C (6,120 trips)"],
            "total_period_volume": 42100,
            "avg_speed_kmh": 16.2,
            "congestion_level": "SEVERE",
            "mode_share_public_transit": 48.5,
        },
        {
            "period_id": "MIDDAY_INTERZONAL",
            "name": "Midday Commercial Circulation",
            "time_window": "11:30 - 16:00",
            "primary_flow_direction": "Balanced Inter-Business & Intra-Zonal Trade",
            "dominant_pairs": ["B → C (4,200 trips)", "C → B (3,820 trips)", "A → D (2,850 trips)"],
            "total_period_volume": 31400,
            "avg_speed_kmh": 24.8,
            "congestion_level": "MODERATE",
            "mode_share_public_transit": 36.2,
        },
        {
            "period_id": "EVENING_RUSH",
            "name": "Evening Commuter Peak (Tidal Reversal)",
            "time_window": "17:30 - 21:00",
            "primary_flow_direction": "Outbound Return into East Residential (D) & North Suburbs (A)",
            "dominant_pairs": ["B → D (7,150 trips)", "C → D (6,480 trips)", "C → A (5,890 trips)"],
            "total_period_volume": 46800,
            "avg_speed_kmh": 14.8,
            "congestion_level": "SEVERE",
            "mode_share_public_transit": 46.0,
        },
        {
            "period_id": "NIGHT_LOGISTICS",
            "name": "Nocturnal Freight & Logistics",
            "time_window": "22:00 - 05:30",
            "primary_flow_direction": "Ring Road Arterial Corridors & Inter-State Terminals",
            "dominant_pairs": ["A → D (1,420 trips)", "D → A (1,380 trips)", "A → C (980 trips)"],
            "total_period_volume": 12800,
            "avg_speed_kmh": 46.5,
            "congestion_level": "LOW",
            "mode_share_public_transit": 12.0,
        },
    ]

    return {
        "demonstration_label": DEMONSTRATION_LABEL,
        "peak_periods": periods,
    }
