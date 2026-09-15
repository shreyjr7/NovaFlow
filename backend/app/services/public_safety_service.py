"""
Public Urban Safety Service (Phase 30)
======================================
Provides citizen-facing, privacy-first municipal transportation and safety intelligence.
Strictly limits exposure to aggregated, non-sensitive information:
  - Road condition: Aggregated defect counts, repair progress, road quality score.
  - Congestion: Corridor delay tiers, average speeds, peak hour advisories.
  - Waterlogging: Active flood notices, water depth categories, safe passage advice.
  - Public road hazards: Standard citizen alerts formatted with:
      - "Road hazard reported"
      - "Heavy congestion"
      - "Waterlogging"
  - Aggregated traffic trends: 24-hour diurnal commuter mobility index.
  - Interactive GIS hotspots: Coordinate markers with zero internal/sensitive telemetry.

Strict Zero-PII Sanitization Guardrail:
  - NO private passenger information or cabin telemetry.
  - NO raw passenger footage or camera video streams.
  - NO sensitive incident evidence or collision recordings.
  - NO unverified license plates or ANPR data.
  - NO personally identifiable information (driver IDs, staff codes, IP/MAC addresses).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Pydantic Public Schemas ──────────────────────────────────────────────────

class PublicOverview(BaseModel):
    city: str = "Bengaluru"
    updated_at: str
    overall_road_condition_score: float  # 0-100 (higher is better)
    active_public_hazards_count: int
    congested_corridors_count: int
    waterlogged_locations_count: int
    civic_advisory: str
    privacy_guarantee: str = "Zero-PII / Privacy Protected: All telemetry is strictly anonymized and aggregated."


class PublicRoadCondition(BaseModel):
    city: str = "Bengaluru"
    road_health_index: float  # e.g. 78.5 / 100
    potholes_reported: int
    surface_damage_reported: int
    waterlogged_zones: int
    missing_infrastructure: int
    repairs_completed_this_week: int
    status_summary: str


class PublicCongestionCorridor(BaseModel):
    corridor_name: str
    zone: str
    traffic_level: str  # Normal Flow, Moderate Traffic, Heavy Congestion, Severe Congestion
    average_speed_kmh: float
    delay_minutes: float
    advisory: str


class PublicCongestionSummary(BaseModel):
    city_average_speed_kmh: float
    network_traffic_status: str
    peak_hours_active: bool
    corridors: List[PublicCongestionCorridor]


class PublicWaterlogNotice(BaseModel):
    notice_id: str
    location_name: str
    zone: str
    water_depth_category: str  # Passable with Caution, Transit Lane Restricted, Hazardous Standing Water
    reported_time: str
    safe_passage_advice: str
    pumps_deployed: bool


class PublicHazardAlert(BaseModel):
    hazard_id: str
    category: str  # "Road Hazard", "Traffic Congestion", "Waterlogging"
    standard_label: str  # "Road hazard reported", "Heavy congestion", "Waterlogging"
    location_name: str
    zone: str
    description: str
    safety_recommendation: str
    reported_at: str
    citizen_acknowledgments: int
    status: str  # ACTIVE, VERIFIED, RESOLVED


class PublicTrafficTrendPoint(BaseModel):
    hour: str
    congestion_level: str  # Low, Moderate, Heavy, Severe
    relative_delay_index: float  # 1.0 = normal baseline
    recommended_for_travel: bool


class PublicMapHotspot(BaseModel):
    hotspot_id: str
    name: str
    category: str  # HAZARD, CONGESTION, WATERLOG
    lat: float
    lon: float
    public_label: str


# ── Public Safety Service Implementation ────────────────────────────────────

class PublicSafetyService:
    """Citizen-facing aggregator for urban safety and mobility alerts."""

    def __init__(self):
        # Pre-seed verified public hazards with exact requested phrasing
        self._hazards: Dict[str, PublicHazardAlert] = {
            "HAZ-001": PublicHazardAlert(
                hazard_id="HAZ-001",
                category="Road Hazard",
                standard_label="Road hazard reported",
                location_name="Road Segment A (MG Road Radial)",
                zone="Zone A (CBD)",
                description="Cluster of verified potholes observed on arterial lane. Road surface uneven.",
                safety_recommendation="Reduce vehicular speed to 25 km/h and exercise caution during lane changes.",
                reported_at="10 minutes ago",
                citizen_acknowledgments=42,
                status="ACTIVE",
            ),
            "HAZ-002": PublicHazardAlert(
                hazard_id="HAZ-002",
                category="Traffic Congestion",
                standard_label="Heavy congestion",
                location_name="Silk Board Transit Interchange Approach",
                zone="Zone A (CBD)",
                description="Significant corridor queueing towards BTM Layout. Flow speed reduced to 11 km/h.",
                safety_recommendation="Expect 18-minute additional travel time. Consider alternate route via 24th Main.",
                reported_at="15 minutes ago",
                citizen_acknowledgments=89,
                status="ACTIVE",
            ),
            "HAZ-003": PublicHazardAlert(
                hazard_id="HAZ-003",
                category="Waterlogging",
                standard_label="Waterlogging",
                location_name="Dairy Circle Underpass",
                zone="Zone A (CBD)",
                description="Standing water accumulation of approx 15cm observed following recent downpour.",
                safety_recommendation="Left curb lane restricted. Two-wheelers advised to take elevated flyover ramp.",
                reported_at="25 minutes ago",
                citizen_acknowledgments=64,
                status="ACTIVE",
            ),
            "HAZ-004": PublicHazardAlert(
                hazard_id="HAZ-004",
                category="Traffic Congestion",
                standard_label="Heavy congestion",
                location_name="Tin Factory Flyover Merge (Old Madras Rd)",
                zone="Zone B (North)",
                description="High vehicle volume at merge ramp leading to corridor bottleneck.",
                safety_recommendation="Maintain safe braking distances and follow lane discipline.",
                reported_at="30 minutes ago",
                citizen_acknowledgments=51,
                status="ACTIVE",
            ),
            "HAZ-005": PublicHazardAlert(
                hazard_id="HAZ-005",
                category="Road Hazard",
                standard_label="Road hazard reported",
                location_name="Outer Ring Road Bellandur EcoSpace Corridor",
                zone="Zone C (Tech East)",
                description="Surface raveling and road defect cluster detected near pedestrian footbridge.",
                safety_recommendation="Stay alert for braking vehicles in central lane.",
                reported_at="45 minutes ago",
                citizen_acknowledgments=37,
                status="ACTIVE",
            ),
        }

    def get_public_overview(self) -> PublicOverview:
        now_iso = datetime.now(timezone.utc).isoformat()
        return PublicOverview(
            city="Bengaluru",
            updated_at=now_iso,
            overall_road_condition_score=78.5,
            active_public_hazards_count=len(self._hazards),
            congested_corridors_count=5,
            waterlogged_locations_count=2,
            civic_advisory="Normal municipal operations active. Heavy traffic expected on arterial radials between 17:00 and 19:30.",
        )

    def get_public_road_condition(self) -> PublicRoadCondition:
        return PublicRoadCondition(
            city="Bengaluru",
            road_health_index=78.5,
            potholes_reported=42,
            surface_damage_reported=28,
            waterlogged_zones=15,
            missing_infrastructure=9,
            repairs_completed_this_week=34,
            status_summary="City road condition rating is GOOD (78.5/100). Rapid response teams actively dispatched for high-priority corridors.",
        )

    def get_public_congestion(self) -> PublicCongestionSummary:
        corridors = [
            PublicCongestionCorridor(
                corridor_name="Silk Board Junction to BTM Layout",
                zone="Zone A",
                traffic_level="Severe Congestion",
                average_speed_kmh=11.2,
                delay_minutes=18.0,
                advisory="Heavy transit delay. Consider Metro or Ring Road alternate.",
            ),
            PublicCongestionCorridor(
                corridor_name="Tin Factory Flyover Approach",
                zone="Zone B",
                traffic_level="Heavy Congestion",
                average_speed_kmh=13.4,
                delay_minutes=14.0,
                advisory="Bottleneck at merge point. Delay +14 min.",
            ),
            PublicCongestionCorridor(
                corridor_name="ITPL Main Road to Hope Farm",
                zone="Zone C",
                traffic_level="Heavy Congestion",
                average_speed_kmh=14.8,
                delay_minutes=12.0,
                advisory="Peak tech corridor commuting traffic.",
            ),
            PublicCongestionCorridor(
                corridor_name="MG Road - Brigade Road Interconnect",
                zone="Zone A",
                traffic_level="Moderate Traffic",
                average_speed_kmh=18.2,
                delay_minutes=6.0,
                advisory="Commercial hub moderate volume.",
            ),
            PublicCongestionCorridor(
                corridor_name="Kanakapura Radial Expressway",
                zone="Zone D",
                traffic_level="Normal Flow",
                average_speed_kmh=36.5,
                delay_minutes=2.0,
                advisory="Smooth flow with minimal delay.",
            ),
        ]
        return PublicCongestionSummary(
            city_average_speed_kmh=24.6,
            network_traffic_status="Moderate to Heavy (Evening Peak)",
            peak_hours_active=True,
            corridors=corridors,
        )

    def get_public_waterlogging(self) -> List[PublicWaterlogNotice]:
        return [
            PublicWaterlogNotice(
                notice_id="WLOG-01",
                location_name="Dairy Circle Underpass Approach",
                zone="Zone A",
                water_depth_category="Passable with Caution",
                reported_time="25 mins ago",
                safe_passage_advice="Use right-hand elevated lane. Two-wheelers avoid curb lane.",
                pumps_deployed=True,
            ),
            PublicWaterlogNotice(
                notice_id="WLOG-02",
                location_name="Hebbal Skywalk Bus Bay",
                zone="Zone B",
                water_depth_category="Transit Lane Restricted",
                reported_time="40 mins ago",
                safe_passage_advice="Bus boarding moved 30 meters north to avoid standing puddle.",
                pumps_deployed=True,
            ),
        ]

    def get_public_hazards(self, category: Optional[str] = None) -> List[PublicHazardAlert]:
        hazards = list(self._hazards.values())
        if category and category.lower() != "all":
            hazards = [h for h in hazards if h.category.lower() == category.lower()]
        return hazards

    def get_public_traffic_trends(self) -> List[PublicTrafficTrendPoint]:
        # 24-hour diurnal commuter travel curve
        trends: List[PublicTrafficTrendPoint] = []
        for h in range(24):
            h_str = f"{h:02d}:00"
            if 8 <= h <= 10:
                trends.append(PublicTrafficTrendPoint(hour=h_str, congestion_level="Severe", relative_delay_index=1.85, recommended_for_travel=False))
            elif 17 <= h <= 19:
                trends.append(PublicTrafficTrendPoint(hour=h_str, congestion_level="Heavy", relative_delay_index=1.75, recommended_for_travel=False))
            elif 11 <= h <= 16:
                trends.append(PublicTrafficTrendPoint(hour=h_str, congestion_level="Moderate", relative_delay_index=1.20, recommended_for_travel=True))
            else:
                trends.append(PublicTrafficTrendPoint(hour=h_str, congestion_level="Low", relative_delay_index=1.0, recommended_for_travel=True))
        return trends

    def get_public_map_hotspots(self) -> List[PublicMapHotspot]:
        return [
            PublicMapHotspot(hotspot_id="HOT-01", name="Road Segment A (MG Road Radial)", category="HAZARD", lat=12.9716, lon=77.5946, public_label="Road hazard reported"),
            PublicMapHotspot(hotspot_id="HOT-02", name="Silk Board Interchange", category="CONGESTION", lat=12.9172, lon=77.6229, public_label="Heavy congestion"),
            PublicMapHotspot(hotspot_id="HOT-03", name="Dairy Circle Underpass", category="WATERLOG", lat=12.9360, lon=77.5990, public_label="Waterlogging"),
            PublicMapHotspot(hotspot_id="HOT-04", name="Tin Factory Flyover", category="CONGESTION", lat=13.0035, lon=77.6625, public_label="Heavy congestion"),
            PublicMapHotspot(hotspot_id="HOT-05", name="Bellandur EcoSpace", category="HAZARD", lat=12.9260, lon=77.6760, public_label="Road hazard reported"),
        ]

    def acknowledge_hazard(self, hazard_id: str) -> Optional[PublicHazardAlert]:
        alert = self._hazards.get(hazard_id)
        if alert:
            alert.citizen_acknowledgments += 1
        return alert


# Singleton provider
_public_safety_service: Optional[PublicSafetyService] = None

def get_public_safety_service() -> PublicSafetyService:
    global _public_safety_service
    if _public_safety_service is None:
        _public_safety_service = PublicSafetyService()
    return _public_safety_service
