"""
Urban Analytics Service (Phase 28)
==================================
Synthesizes comprehensive city-wide transportation and municipal infrastructure intelligence.
Consolidates 5 core domains:
  1. ROAD CONDITION: Potholes, Road damage, Waterlogging, Missing infrastructure, trends, severity.
  2. TRAFFIC: Vehicle count, density, average speed, congestion score, active bottlenecks, 24h diurnal curve.
  3. SAFETY: Incidents, pedestrian risks, high-risk zones, collision risk clusters.
  4. FLEET: Active vs offline buses, camera optical health, edge device compute metrics.
  5. ROUTES: Average delay, worst routes ranking (Route 12 benchmark), factor attribution, delayed corridors.

Provides dynamic parameter filtering across:
  - date_range: today, yesterday, last_7_days, last_30_days
  - time_of_day: all_day, morning_peak, afternoon, evening_peak, night
  - zone: all_zones, zone_a, zone_b, zone_c, zone_d
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field


# ── Filter Multipliers & Constants ──────────────────────────────────────────

DATE_RANGE_SCALERS = {
    "today": 1.0,
    "yesterday": 0.96,
    "last_7_days": 6.8,
    "last_30_days": 28.4,
}

TIME_OF_DAY_CONFIG = {
    "all_day": {"vol_mult": 1.0, "speed_mult": 1.0, "congestion_mult": 1.0},
    "morning_peak": {"vol_mult": 1.45, "speed_mult": 0.65, "congestion_mult": 1.40},
    "afternoon": {"vol_mult": 0.90, "speed_mult": 1.05, "congestion_mult": 0.85},
    "evening_peak": {"vol_mult": 1.55, "speed_mult": 0.58, "congestion_mult": 1.50},
    "night": {"vol_mult": 0.35, "speed_mult": 1.40, "congestion_mult": 0.25},
}

ZONE_FACTORS = {
    "all_zones": 1.0,
    "zone_a": 0.35,  # Central CBD
    "zone_b": 0.28,  # North Transit Corridor
    "zone_c": 0.22,  # Tech Park East
    "zone_d": 0.15,  # Southern Residential
}


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class FilterContext(BaseModel):
    date_range: str = "today"
    time_of_day: str = "all_day"
    zone: str = "all_zones"


class DefectHotspot(BaseModel):
    corridor_id: str
    corridor_name: str
    zone: str
    potholes_count: int
    road_damage_count: int
    waterlogging_count: int
    missing_infra_count: int
    total_defects: int
    reported_by_buses_count: int
    highest_confidence: float
    status: str
    lat: float
    lon: float


class DailyDefectTrend(BaseModel):
    date: str
    discovered: int
    repaired: int
    active_backlog: int


class RoadConditionAnalytics(BaseModel):
    total_defects: int
    potholes: int
    road_damage: int
    waterlogging: int
    missing_infrastructure: int
    severity_breakdown: Dict[str, int]
    seven_day_trend: List[DailyDefectTrend]
    top_defect_corridors: List[DefectHotspot]
    filter_context: FilterContext


class DiurnalHourlyData(BaseModel):
    hour: str
    vehicle_count: int
    average_speed_kmh: float
    congestion_index: float


class CongestedSegmentItem(BaseModel):
    rank: int
    segment_id: str
    name: str
    zone: str
    congestion_score: float
    average_speed_kmh: float
    free_flow_speed_kmh: float
    vehicle_density: float
    active_bottlenecks: int
    status: str  # severe, high, moderate, low


class TrafficAnalytics(BaseModel):
    total_vehicle_count: int
    average_vehicle_density: float
    network_average_speed_kmh: float
    overall_congestion_score: float
    active_bottlenecks_count: int
    modal_split: Dict[str, int]
    diurnal_curve: List[DiurnalHourlyData]
    top_congested_segments: List[CongestedSegmentItem]
    zone_congestion_scores: Dict[str, float]
    filter_context: FilterContext


class PedestrianRiskSpot(BaseModel):
    spot_id: str
    location_name: str
    zone: str
    risk_level: str  # CRITICAL, HIGH, MEDIUM, LOW
    vulnerability_factor: str
    conflict_events_count: int
    observed_pedestrians_per_hour: int
    lat: float
    lon: float


class SafetyAnalytics(BaseModel):
    total_incidents: int
    pedestrian_risks: int
    high_risk_zones_count: int
    incident_types_breakdown: Dict[str, int]
    vulnerable_pedestrian_spots: List[PedestrianRiskSpot]
    zone_safety_indices: Dict[str, float]  # higher is safer
    filter_context: FilterContext


class EdgeComputeHealth(BaseModel):
    average_cpu_percent: float
    average_gpu_percent: float
    average_ram_percent: float
    average_disk_percent: float
    average_temperature_celsius: float
    network_latency_ms: float
    inference_fps_average: float


class FleetAnalytics(BaseModel):
    total_buses: int
    active_buses: int
    offline_buses: int
    camera_health_summary: Dict[str, int]  # HEALTHY, WARNING, DEGRADED, OFFLINE
    edge_device_health: EdgeComputeHealth
    auto_generated_maintenance_tickets: int
    filter_context: FilterContext


class RouteDelayItem(BaseModel):
    rank: int
    route_id: str
    name: str
    zone: str
    scheduled_travel_time_minutes: float
    observed_travel_time_minutes: float
    average_delay_minutes: float
    maximum_delay_minutes: float
    congestion_events_count: int
    road_defects_count: int
    contributing_factors: Dict[str, float]  # Percentage contributions
    delayed_sections_count: int
    status: str


class RoutesAnalytics(BaseModel):
    network_average_delay_minutes: float
    worst_delayed_routes: List[RouteDelayItem]
    aggregate_contributing_factors: Dict[str, float]
    total_monitored_routes: int
    delayed_routes_percentage: float
    filter_context: FilterContext


class ExecutiveSummary(BaseModel):
    generated_at: str
    filter_context: FilterContext
    road_condition: Dict[str, Any]
    traffic: Dict[str, Any]
    safety: Dict[str, Any]
    fleet: Dict[str, Any]
    routes: Dict[str, Any]


# ── Analytics Service Implementation ────────────────────────────────────────

class UrbanAnalyticsService:
    """Consolidates cross-domain transit & municipal intelligence."""

    def __init__(self):
        # Baseline canonical data seeds
        self._baseline_road_defects = {
            "potholes": 42,
            "road_damage": 28,
            "waterlogging": 15,
            "missing_infrastructure": 9,
        }
        self._baseline_corridors = [
            {
                "corridor_id": "CORR-SEG-A",
                "corridor_name": "Road Segment A (MG Radial)",
                "zone": "zone_a",
                "potholes_count": 14,
                "road_damage_count": 8,
                "waterlogging_count": 5,
                "missing_infra_count": 2,
                "reported_by_buses_count": 11,
                "highest_confidence": 0.94,
                "status": "Confirmed (Action Priority)",
                "lat": 12.9716,
                "lon": 77.5946,
            },
            {
                "corridor_id": "CORR-ORR-NORTH",
                "corridor_name": "Outer Ring Road (Hebbal Junction)",
                "zone": "zone_b",
                "potholes_count": 11,
                "road_damage_count": 7,
                "waterlogging_count": 6,
                "missing_infra_count": 3,
                "reported_by_buses_count": 9,
                "highest_confidence": 0.91,
                "status": "Confirmed",
                "lat": 13.0358,
                "lon": 77.5970,
            },
            {
                "corridor_id": "CORR-TECH-EAST",
                "corridor_name": "Whitefield ITPL Main Road",
                "zone": "zone_c",
                "potholes_count": 9,
                "road_damage_count": 6,
                "waterlogging_count": 3,
                "missing_infra_count": 2,
                "reported_by_buses_count": 7,
                "highest_confidence": 0.88,
                "status": "Under Verification",
                "lat": 12.9863,
                "lon": 77.7375,
            },
            {
                "corridor_id": "CORR-SOUTH-RES",
                "corridor_name": "Kanakapura Radial Expressway",
                "zone": "zone_d",
                "potholes_count": 5,
                "road_damage_count": 4,
                "waterlogging_count": 1,
                "missing_infra_count": 1,
                "reported_by_buses_count": 4,
                "highest_confidence": 0.85,
                "status": "Investigating",
                "lat": 12.8950,
                "lon": 77.5680,
            },
            {
                "corridor_id": "CORR-METRO-PIER",
                "corridor_name": "Hosur Road Silk Board Flyover Entry",
                "zone": "zone_a",
                "potholes_count": 8,
                "road_damage_count": 5,
                "waterlogging_count": 4,
                "missing_infra_count": 1,
                "reported_by_buses_count": 12,
                "highest_confidence": 0.96,
                "status": "Confirmed (Severe)",
                "lat": 12.9172,
                "lon": 77.6229,
            },
        ]

    # ── 1. ROAD CONDITION ───────────────────────────────────────────────────

    def get_road_condition(
        self,
        date_range: str = "today",
        time_of_day: str = "all_day",
        zone: str = "all_zones",
    ) -> RoadConditionAnalytics:
        ctx = FilterContext(
            date_range=date_range.lower(),
            time_of_day=time_of_day.lower(),
            zone=zone.lower(),
        )

        d_scale = DATE_RANGE_SCALERS.get(ctx.date_range, 1.0)
        z_factor = 1.0 if ctx.zone == "all_zones" else (ZONE_FACTORS.get(ctx.zone, 0.25) * 3.0)

        potholes = max(1, int(round(self._baseline_road_defects["potholes"] * d_scale * z_factor)))
        road_damage = max(1, int(round(self._baseline_road_defects["road_damage"] * d_scale * z_factor)))
        waterlogging = max(1, int(round(self._baseline_road_defects["waterlogging"] * d_scale * z_factor)))
        missing_infra = max(1, int(round(self._baseline_road_defects["missing_infrastructure"] * d_scale * z_factor)))

        total = potholes + road_damage + waterlogging + missing_infra

        # Severity breakdown
        severity = {
            "CRITICAL": int(round(total * 0.22)),
            "HIGH": int(round(total * 0.38)),
            "MEDIUM": int(round(total * 0.28)),
            "LOW": max(1, total - (int(round(total * 0.22)) + int(round(total * 0.38)) + int(round(total * 0.28)))),
        }

        # 7-day trend
        today_dt = datetime.now(timezone.utc)
        trends: List[DailyDefectTrend] = []
        backlog = total
        for i in range(6, -1, -1):
            day_dt = today_dt - timedelta(days=i)
            day_str = day_dt.strftime("%Y-%m-%d")
            discovered = max(2, int(round((total / 7) * (0.8 + 0.05 * i))))
            repaired = max(1, int(round(discovered * 0.75)))
            backlog = max(5, backlog + discovered - repaired)
            trends.append(
                DailyDefectTrend(
                    date=day_str,
                    discovered=discovered,
                    repaired=repaired,
                    active_backlog=backlog,
                )
            )

        # Corridors ranking
        filtered_corridors: List[DefectHotspot] = []
        for c in self._baseline_corridors:
            if ctx.zone != "all_zones" and c["zone"] != ctx.zone:
                continue
            c_pot = max(1, int(round(c["potholes_count"] * d_scale * (1.0 if ctx.zone == "all_zones" else 1.2))))
            c_dmg = max(1, int(round(c["road_damage_count"] * d_scale)))
            c_wat = max(1, int(round(c["waterlogging_count"] * d_scale)))
            c_mis = max(0, int(round(c["missing_infra_count"] * d_scale)))
            c_tot = c_pot + c_dmg + c_wat + c_mis

            filtered_corridors.append(
                DefectHotspot(
                    corridor_id=c["corridor_id"],
                    corridor_name=c["corridor_name"],
                    zone=c["zone"],
                    potholes_count=c_pot,
                    road_damage_count=c_dmg,
                    waterlogging_count=c_wat,
                    missing_infra_count=c_mis,
                    total_defects=c_tot,
                    reported_by_buses_count=c["reported_by_buses_count"],
                    highest_confidence=c["highest_confidence"],
                    status=c["status"],
                    lat=c["lat"],
                    lon=c["lon"],
                )
            )

        filtered_corridors.sort(key=lambda x: x.total_defects, reverse=True)

        return RoadConditionAnalytics(
            total_defects=total,
            potholes=potholes,
            road_damage=road_damage,
            waterlogging=waterlogging,
            missing_infrastructure=missing_infra,
            severity_breakdown=severity,
            seven_day_trend=trends,
            top_defect_corridors=filtered_corridors,
            filter_context=ctx,
        )

    # ── 2. TRAFFIC ──────────────────────────────────────────────────────────

    def get_traffic(
        self,
        date_range: str = "today",
        time_of_day: str = "all_day",
        zone: str = "all_zones",
    ) -> TrafficAnalytics:
        ctx = FilterContext(
            date_range=date_range.lower(),
            time_of_day=time_of_day.lower(),
            zone=zone.lower(),
        )

        d_scale = DATE_RANGE_SCALERS.get(ctx.date_range, 1.0)
        t_cfg = TIME_OF_DAY_CONFIG.get(ctx.time_of_day, TIME_OF_DAY_CONFIG["all_day"])
        z_factor = 1.0 if ctx.zone == "all_zones" else (ZONE_FACTORS.get(ctx.zone, 0.25) * 3.2)

        base_vol = 142500
        vol = int(round(base_vol * d_scale * t_cfg["vol_mult"] * z_factor))

        base_density = 0.68
        density = min(0.98, max(0.15, round(base_density * t_cfg["congestion_mult"] * (0.95 if ctx.zone == "all_zones" else 1.05), 2)))

        base_speed = 24.6
        speed = max(11.2, round(base_speed * t_cfg["speed_mult"], 1))

        base_cong_score = 68.4
        cong_score = min(98.5, max(15.0, round(base_cong_score * t_cfg["congestion_mult"], 1)))

        bottlenecks = max(1, int(round(8 * t_cfg["congestion_mult"] * (1.0 if ctx.zone == "all_zones" else 0.5))))

        # Modal Split
        modal_split = {
            "Cars / Cabs": int(round(vol * 0.44)),
            "Two-Wheelers": int(round(vol * 0.32)),
            "Transit Buses": int(round(vol * 0.12)),
            "Light Commercial": int(round(vol * 0.08)),
            "Heavy Trucks": int(round(vol * 0.04)),
        }

        # 24-Hour Diurnal Curve (diurnal volume vs speed)
        diurnal: List[DiurnalHourlyData] = []
        for h in range(24):
            h_str = f"{h:02d}:00"
            # Morning peak around 08:00 - 10:00, Evening peak around 17:00 - 20:00
            if 7 <= h <= 10:
                h_mult = 1.45 + 0.1 * ((h - 7) % 2)
                h_spd = round(16.5 - (h - 7) * 1.2, 1)
                h_cong = round(78.0 + (h - 7) * 4.5, 1)
            elif 17 <= h <= 20:
                h_mult = 1.58 - 0.05 * (h - 17)
                h_spd = round(14.8 + (h - 17) * 0.8, 1)
                h_cong = round(84.0 - (h - 17) * 3.0, 1)
            elif 11 <= h <= 16:
                h_mult = 0.95
                h_spd = 26.4
                h_cong = 52.0
            else:
                h_mult = 0.30
                h_spd = 44.5
                h_cong = 18.0

            hourly_vol = int(round((base_vol / 24) * h_mult * (d_scale if d_scale <= 1.0 else 1.0)))
            diurnal.append(
                DiurnalHourlyData(
                    hour=h_str,
                    vehicle_count=hourly_vol,
                    average_speed_kmh=h_spd,
                    congestion_index=h_cong,
                )
            )

        # Top 10 Congested Segments
        raw_segments = [
            ("SEG-01", "Silk Board Junction to BTM Layout", "zone_a", 92.4, 11.2, 45.0, 0.92, 2, "severe"),
            ("SEG-02", "Tin Factory Flyover Approach (Old Madras Rd)", "zone_b", 88.6, 13.4, 50.0, 0.89, 2, "severe"),
            ("SEG-03", "ITPL Main Road to Hope Farm", "zone_c", 84.1, 14.8, 45.0, 0.86, 1, "severe"),
            ("SEG-04", "Hebbal Flyover Northbound Merge", "zone_b", 81.3, 16.5, 60.0, 0.82, 1, "high"),
            ("SEG-05", "MG Road - Brigade Road Interconnect", "zone_a", 76.5, 18.2, 40.0, 0.78, 1, "high"),
            ("SEG-06", "Outer Ring Road Bellandur EcoSpace Corridor", "zone_c", 74.8, 19.1, 55.0, 0.75, 1, "high"),
            ("SEG-07", "Kanakapura Road Metro Pier Section", "zone_d", 68.2, 22.0, 50.0, 0.69, 0, "moderate"),
            ("SEG-08", "Goraguntepalya Flyover Ascent", "zone_b", 65.4, 23.5, 55.0, 0.66, 0, "moderate"),
            ("SEG-09", "Bannerghatta National Park Radial", "zone_d", 59.1, 26.0, 50.0, 0.58, 0, "moderate"),
            ("SEG-10", "Richmond Circle Underpass", "zone_a", 54.0, 28.5, 45.0, 0.52, 0, "moderate"),
        ]

        top_segments: List[CongestedSegmentItem] = []
        rank = 1
        for sid, sname, szone, sscore, sspd, sfree, sdens, sbott, sstat in raw_segments:
            if ctx.zone != "all_zones" and szone != ctx.zone:
                continue
            adj_score = min(99.0, max(10.0, round(sscore * t_cfg["congestion_mult"], 1)))
            adj_spd = max(8.0, round(sspd * t_cfg["speed_mult"], 1))
            adj_dens = min(0.99, max(0.10, round(sdens * t_cfg["congestion_mult"], 2)))
            adj_stat = "severe" if adj_score >= 80 else ("high" if adj_score >= 70 else "moderate")

            top_segments.append(
                CongestedSegmentItem(
                    rank=rank,
                    segment_id=sid,
                    name=sname,
                    zone=szone,
                    congestion_score=adj_score,
                    average_speed_kmh=adj_spd,
                    free_flow_speed_kmh=sfree,
                    vehicle_density=adj_dens,
                    active_bottlenecks=sbott,
                    status=adj_stat,
                )
            )
            rank += 1

        top_segments.sort(key=lambda x: x.congestion_score, reverse=True)
        for idx, seg in enumerate(top_segments):
            seg.rank = idx + 1

        # Zone scores
        zone_scores = {
            "Zone A (Central CBD)": round(78.5 * t_cfg["congestion_mult"], 1),
            "Zone B (North Corridor)": round(72.1 * t_cfg["congestion_mult"], 1),
            "Zone C (Tech Park East)": round(81.4 * t_cfg["congestion_mult"], 1),
            "Zone D (South Residential)": round(51.2 * t_cfg["congestion_mult"], 1),
        }

        return TrafficAnalytics(
            total_vehicle_count=vol,
            average_vehicle_density=density,
            network_average_speed_kmh=speed,
            overall_congestion_score=cong_score,
            active_bottlenecks_count=bottlenecks,
            modal_split=modal_split,
            diurnal_curve=diurnal,
            top_congested_segments=top_segments[:10],
            zone_congestion_scores=zone_scores,
            filter_context=ctx,
        )

    # ── 3. SAFETY ───────────────────────────────────────────────────────────

    def get_safety(
        self,
        date_range: str = "today",
        time_of_day: str = "all_day",
        zone: str = "all_zones",
    ) -> SafetyAnalytics:
        ctx = FilterContext(
            date_range=date_range.lower(),
            time_of_day=time_of_day.lower(),
            zone=zone.lower(),
        )

        d_scale = DATE_RANGE_SCALERS.get(ctx.date_range, 1.0)
        t_cfg = TIME_OF_DAY_CONFIG.get(ctx.time_of_day, TIME_OF_DAY_CONFIG["all_day"])
        z_factor = 1.0 if ctx.zone == "all_zones" else (ZONE_FACTORS.get(ctx.zone, 0.25) * 3.0)

        incidents = max(1, int(round(5 * d_scale * t_cfg["vol_mult"] * z_factor)))
        ped_risks = max(2, int(round(14 * d_scale * (1.3 if ctx.time_of_day in ("morning_peak", "evening_peak") else 1.0) * z_factor)))
        high_risk_zones = max(1, int(round(3 * (1.0 if ctx.zone == "all_zones" else 0.4))))

        incident_breakdown = {
            "Collision Risk / Near-Miss": max(1, int(round(incidents * 0.45))),
            "Sudden Heavy Deceleration": max(1, int(round(incidents * 0.30))),
            "Lane Intrusion / Bus Lane Encroachment": max(0, int(round(incidents * 0.15))),
            "Hit-and-Run Suspect Flag": max(0, int(round(incidents * 0.10))),
        }

        # Pedestrian risk hotspots
        raw_ped_spots = [
            ("PED-01", "St. Joseph's School Crossing (Residency Rd)", "zone_a", "CRITICAL", "School dismissal pedestrian conflict", 18, 420, 12.9702, 77.6015),
            ("PED-02", "Silk Board Transit Interchange Underpass", "zone_a", "HIGH", "High-volume commuter jaywalking", 14, 680, 12.9175, 77.6231),
            ("PED-03", "Hebbal Bus Stop Pedestrian Skywalk Entry", "zone_b", "HIGH", "Rapid bus deceleration near boarding queue", 11, 350, 13.0360, 77.5975),
            ("PED-04", "ITPL Main Gate Crosswalk", "zone_c", "MEDIUM", "Tech commuter peak crossing vs buses", 8, 290, 12.9860, 77.7370),
            ("PED-05", "Kanakapura Metro Pillar Mid-Block Crossing", "zone_d", "LOW", "Uncontrolled mid-block pedestrian crossing", 4, 110, 12.8945, 77.5685),
        ]

        ped_spots: List[PedestrianRiskSpot] = []
        for pid, pname, pzone, prisk, pfac, pconf, pped, plat, plon in raw_ped_spots:
            if ctx.zone != "all_zones" and pzone != ctx.zone:
                continue
            ped_spots.append(
                PedestrianRiskSpot(
                    spot_id=pid,
                    location_name=pname,
                    zone=pzone,
                    risk_level=prisk,
                    vulnerability_factor=pfac,
                    conflict_events_count=max(1, int(round(pconf * d_scale * (1.2 if ctx.time_of_day in ("morning_peak", "evening_peak") else 0.8)))),
                    observed_pedestrians_per_hour=int(round(pped * t_cfg["vol_mult"])),
                    lat=plat,
                    lon=plon,
                )
            )

        # Safety indices (100 is safest)
        zone_safety = {
            "Zone A (CBD)": 74.2,
            "Zone B (North)": 81.5,
            "Zone C (Tech East)": 78.0,
            "Zone D (South)": 89.6,
        }

        return SafetyAnalytics(
            total_incidents=incidents,
            pedestrian_risks=ped_risks,
            high_risk_zones_count=high_risk_zones,
            incident_types_breakdown=incident_breakdown,
            vulnerable_pedestrian_spots=ped_spots,
            zone_safety_indices=zone_safety,
            filter_context=ctx,
        )

    # ── 4. FLEET ────────────────────────────────────────────────────────────

    def get_fleet(
        self,
        date_range: str = "today",
        time_of_day: str = "all_day",
        zone: str = "all_zones",
    ) -> FleetAnalytics:
        ctx = FilterContext(
            date_range=date_range.lower(),
            time_of_day=time_of_day.lower(),
            zone=zone.lower(),
        )

        total_buses = 124
        active_buses = 112
        offline_buses = 12

        camera_health = {
            "HEALTHY": 218,
            "WARNING": 18,
            "DEGRADED": 8,
            "OFFLINE": 4,
        }

        edge_health = EdgeComputeHealth(
            average_cpu_percent=41.5,
            average_gpu_percent=62.8,
            average_ram_percent=53.2,
            average_disk_percent=38.0,
            average_temperature_celsius=48.4,
            network_latency_ms=18.6,
            inference_fps_average=28.4,
        )

        return FleetAnalytics(
            total_buses=total_buses,
            active_buses=active_buses,
            offline_buses=offline_buses,
            camera_health_summary=camera_health,
            edge_device_health=edge_health,
            auto_generated_maintenance_tickets=6,
            filter_context=ctx,
        )

    # ── 5. ROUTES ───────────────────────────────────────────────────────────

    def get_routes(
        self,
        date_range: str = "today",
        time_of_day: str = "all_day",
        zone: str = "all_zones",
    ) -> RoutesAnalytics:
        ctx = FilterContext(
            date_range=date_range.lower(),
            time_of_day=time_of_day.lower(),
            zone=zone.lower(),
        )

        t_cfg = TIME_OF_DAY_CONFIG.get(ctx.time_of_day, TIME_OF_DAY_CONFIG["all_day"])

        # Base worst routes
        # Route 12 is the canonical benchmark: Scheduled 42m, Observed 57m, Average delay 15m
        raw_routes = [
            {
                "route_id": "ROUTE-543",
                "name": "Route 543 (Hebbal ↔ Electronic City Express)",
                "zone": "zone_b",
                "sched": 65.0,
                "obs": 92.0,
                "avg_delay": 27.0,
                "max_delay": 44.0,
                "cong_events": 14,
                "defects": 9,
                "factors": {"Congestion": 62.0, "Road damage": 22.0, "Waterlogging": 16.0},
                "delayed_sec": 4,
                "status": "Critical Delay",
            },
            {
                "route_id": "ROUTE-403",
                "name": "Route 403 (KBS Majestic ↔ ITPL Whitefield)",
                "zone": "zone_c",
                "sched": 55.0,
                "obs": 73.0,
                "avg_delay": 18.0,
                "max_delay": 32.0,
                "cong_events": 10,
                "defects": 7,
                "factors": {"Congestion": 55.0, "Road damage": 25.0, "Waterlogging": 20.0},
                "delayed_sec": 3,
                "status": "Severe Delay",
            },
            {
                "route_id": "ROUTE-12",
                "name": "Route 12 (Majestic ↔ Silk Board Terminal)",
                "zone": "zone_a",
                "sched": 42.0,
                "obs": 57.0,
                "avg_delay": 15.0,
                "max_delay": 26.0,
                "cong_events": 8,
                "defects": 6,
                "factors": {"Congestion": 54.0, "Road damage": 28.0, "Waterlogging": 18.0},
                "delayed_sec": 3,
                "status": "Severe Delay",
            },
            {
                "route_id": "ROUTE-305",
                "name": "Route 305 (Shivajinagar ↔ Kadugodi Metro)",
                "zone": "zone_c",
                "sched": 48.0,
                "obs": 64.0,
                "avg_delay": 16.0,
                "max_delay": 29.0,
                "cong_events": 7,
                "defects": 5,
                "factors": {"Congestion": 50.0, "Road damage": 30.0, "Waterlogging": 20.0},
                "delayed_sec": 2,
                "status": "Moderate Delay",
            },
            {
                "route_id": "ROUTE-813",
                "name": "Route 813 (Banashankari ↔ Jaya Nagar 4th Block)",
                "zone": "zone_d",
                "sched": 35.0,
                "obs": 43.0,
                "avg_delay": 8.0,
                "max_delay": 14.0,
                "cong_events": 3,
                "defects": 2,
                "factors": {"Congestion": 40.0, "Road damage": 35.0, "Waterlogging": 25.0},
                "delayed_sec": 1,
                "status": "Normal Delay",
            },
        ]

        route_items: List[RouteDelayItem] = []
        rank = 1
        for r in raw_routes:
            if ctx.zone != "all_zones" and r["zone"] != ctx.zone:
                continue

            delay_mult = t_cfg["congestion_mult"]
            avg_d = round(r["avg_delay"] * delay_mult, 1)
            max_d = round(r["max_delay"] * delay_mult, 1)
            obs_t = round(r["sched"] + avg_d, 1)

            route_items.append(
                RouteDelayItem(
                    rank=rank,
                    route_id=r["route_id"],
                    name=r["name"],
                    zone=r["zone"],
                    scheduled_travel_time_minutes=r["sched"],
                    observed_travel_time_minutes=obs_t,
                    average_delay_minutes=avg_d,
                    maximum_delay_minutes=max_d,
                    congestion_events_count=max(1, int(round(r["cong_events"] * delay_mult))),
                    road_defects_count=r["defects"],
                    contributing_factors=r["factors"],
                    delayed_sections_count=r["delayed_sec"],
                    status=r["status"],
                )
            )
            rank += 1

        route_items.sort(key=lambda x: x.average_delay_minutes, reverse=True)
        for idx, item in enumerate(route_items):
            item.rank = idx + 1

        avg_network_delay = (
            round(sum(r.average_delay_minutes for r in route_items) / len(route_items), 1)
            if route_items
            else 14.5
        )

        factors = {
            "Congestion": 54.0,
            "Road damage": 28.0,
            "Waterlogging": 18.0,
        }

        return RoutesAnalytics(
            network_average_delay_minutes=avg_network_delay,
            worst_delayed_routes=route_items,
            aggregate_contributing_factors=factors,
            total_monitored_routes=len(raw_routes),
            delayed_routes_percentage=80.0,
            filter_context=ctx,
        )

    # ── Executive Master Summary ────────────────────────────────────────────

    def get_summary(
        self,
        date_range: str = "today",
        time_of_day: str = "all_day",
        zone: str = "all_zones",
    ) -> ExecutiveSummary:
        ctx = FilterContext(
            date_range=date_range.lower(),
            time_of_day=time_of_day.lower(),
            zone=zone.lower(),
        )

        rc = self.get_road_condition(date_range, time_of_day, zone)
        tf = self.get_traffic(date_range, time_of_day, zone)
        sf = self.get_safety(date_range, time_of_day, zone)
        fl = self.get_fleet(date_range, time_of_day, zone)
        rt = self.get_routes(date_range, time_of_day, zone)

        return ExecutiveSummary(
            generated_at=datetime.now(timezone.utc).isoformat(),
            filter_context=ctx,
            road_condition={
                "total_defects": rc.total_defects,
                "potholes": rc.potholes,
                "road_damage": rc.road_damage,
                "waterlogging": rc.waterlogging,
                "missing_infrastructure": rc.missing_infrastructure,
            },
            traffic={
                "vehicle_count": tf.total_vehicle_count,
                "average_density": tf.average_vehicle_density,
                "average_speed_kmh": tf.network_average_speed_kmh,
                "congestion_score": tf.overall_congestion_score,
                "bottlenecks": tf.active_bottlenecks_count,
            },
            safety={
                "incidents": sf.total_incidents,
                "pedestrian_risks": sf.pedestrian_risks,
                "high_risk_zones": sf.high_risk_zones_count,
            },
            fleet={
                "active_buses": fl.active_buses,
                "offline_buses": fl.offline_buses,
                "healthy_cameras": fl.camera_health_summary.get("HEALTHY", 0),
                "degraded_cameras": fl.camera_health_summary.get("DEGRADED", 0),
            },
            routes={
                "average_delay_minutes": rt.network_average_delay_minutes,
                "worst_route_id": rt.worst_delayed_routes[0].route_id if rt.worst_delayed_routes else "ROUTE-543",
                "worst_route_delay": rt.worst_delayed_routes[0].average_delay_minutes if rt.worst_delayed_routes else 27.0,
            },
        )


# Singleton instance
_service_instance: Optional[UrbanAnalyticsService] = None

def get_urban_analytics_service() -> UrbanAnalyticsService:
    global _service_instance
    if _service_instance is None:
        _service_instance = UrbanAnalyticsService()
    return _service_instance
