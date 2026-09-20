// src/pages/GisCommandCenter/GisCommandCenter.tsx
// Full-Screen GIS Command Center (Phase 17)

import React, { useState, useEffect, useRef, useMemo } from "react";
import { Link } from "react-router-dom";
import { LiveGisMap } from "../../components/LiveGisMap";
import { ErrorBoundary } from "../../components/ErrorBoundary";
import adminHierarchyData from "../../data/india_administrative_hierarchy.json";
import {
  Layers, Filter, Compass, Bus, AlertTriangle, Droplet,
  ShieldAlert, CheckCircle2, XCircle, AlertOctagon,
  Wrench, Eye, ZoomIn, ZoomOut, Maximize2, Minimize2,
  RefreshCw, MapPin, Clock, Camera, ChevronRight, X,
  FileText, Activity, ArrowUpRight, Flame, Send, ArrowLeft,
  Radio, Cpu, GripHorizontal, RotateCcw, Minus, Square, Move
} from "lucide-react";

// ── Layer & Filter Definitions ───────────────────────────────────────────────

export interface LayerConfig {
  id: string;
  name: string;
  category: string;
  color: string;
  icon: string;
  visible: boolean;
  count: number;
}

export interface GisEventItem {
  id: string;
  event_id: string;
  event_type: string;
  category?: string;
  layer: string;
  confidence: number;
  bus_id: string;
  camera_id: string;
  timestamp: string;
  gps: {
    lat: number;
    lon: number;
    bearing_deg?: number;
    road_segment?: string;
    address?: string;
  };
  district: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "SEVERE";
  status: "ACTIVE" | "CONFIRMED" | "DISMISSED" | "ESCALATED" | "TICKET_CREATED" | "UNDER_REPAIR" | "RESOLVED" | "UNVERIFIED";
  evidence_image_b64?: string;
  original_evidence_path?: string;
  annotated_evidence_path?: string;
  thumbnail_path?: string;
  source_video?: string;
  condition_type?: "DIRECT" | "POTENTIAL";
  condition_label?: string;
  is_derived?: boolean;
  maintenance_ticket_status?: string;
  frame_number?: number;
  track_id?: number;
  evidence_clip_url?: string;
  ticket_id?: string;
  persistent_hazard_id?: string;
  independent_buses_count?: number;
  contributing_buses?: string | string[];
  persistence_badge?: string;
  last_detected_at?: string;
  ai_confidence?: number;
  observation_count?: number;
  details?: Record<string, any>;
}

export interface BusTelemetry {
  bus_id: string;
  route_id: string;
  name?: string;
  lat: number;
  lon: number;
  latitude?: number;
  longitude?: number;
  bearing_deg: number;
  heading?: number;
  speed_kmh: number;
  speed?: number;
  status: string;
  passenger_load_pct?: number;
  timestamp?: string;
  camera_status?: string;
  AI_status?: string;
  connection_status?: string;
}

export function normalizeGisEvent(raw: any): GisEventItem {
  if (!raw) {
    return {
      id: "ev_fallback",
      event_id: "EV-0000",
      event_type: "POTHOLE",
      layer: "potholes",
      confidence: 0.9,
      bus_id: "BUS_001",
      camera_id: "FRONT",
      timestamp: new Date().toISOString(),
      gps: { lat: 28.6139, lon: 77.2090, bearing_deg: 0, road_segment: "Monitored Corridor", address: "Monitored Corridor" },
      district: "Metropolitan",
      severity: "MEDIUM",
      status: "ACTIVE",
    };
  }

  const p = raw.properties || raw;
  const lat = p.gps?.lat ?? p.lat ?? p.latitude ?? (raw.geometry?.coordinates?.[1]) ?? 28.6139;
  const lon = p.gps?.lon ?? p.lon ?? p.longitude ?? (raw.geometry?.coordinates?.[0]) ?? 77.2090;
  const road_segment = p.gps?.road_segment ?? p.road_segment ?? p.address ?? p.road ?? "Monitored Transit Corridor";
  const address = p.gps?.address ?? p.address ?? road_segment;
  const bearing_deg = p.gps?.bearing_deg ?? p.bearing_deg ?? 0;

  const event_type = String(p.event_type || p.type || "POTHOLE").toUpperCase();
  
  let layer = p.layer;
  if (!layer) {
    if (event_type.includes("POTHOLE")) layer = "potholes";
    else if (event_type.includes("DAMAGE") || event_type.includes("CRACK") || event_type.includes("DEBRIS")) layer = "road_damage";
    else if (event_type.includes("WATERLOG")) layer = "waterlogging";
    else if (event_type.includes("SIGN")) layer = "missing_signs";
    else if (event_type.includes("DIVIDER")) layer = "missing_dividers";
    else if (event_type.includes("ZEBRA")) layer = "zebra_crossing_issues";
    else if (event_type.includes("CONGESTION") || event_type.includes("CAR") || event_type.includes("BUS") || event_type.includes("TRUCK")) layer = "traffic_congestion";
    else if (event_type.includes("INCIDENT")) layer = "incidents";
    else if (event_type.includes("PEDESTRIAN")) layer = "pedestrian_risk";
    else if (event_type.includes("ANPR") || event_type.includes("PLATE") || event_type.includes("INTRUSION")) layer = "anpr_violations";
    else if (event_type.includes("TICKET")) layer = "maintenance_tickets";
    else layer = "potholes";
  }

  const sevRaw = String(p.severity || "MEDIUM").toUpperCase();
  const severity = (["LOW", "MEDIUM", "HIGH", "SEVERE"].includes(sevRaw) ? sevRaw : "MEDIUM") as "LOW" | "MEDIUM" | "HIGH" | "SEVERE";

  const statRaw = String(p.status || "ACTIVE").toUpperCase();
  const status = (["ACTIVE", "CONFIRMED", "DISMISSED", "ESCALATED", "TICKET_CREATED", "UNDER_REPAIR", "RESOLVED", "UNVERIFIED"].includes(statRaw)
    ? statRaw
    : statRaw === "IN_REPAIR" ? "UNDER_REPAIR" : "ACTIVE") as any;

  const category = p.category || (
    ["potholes", "road_damage", "missing_signs", "missing_dividers", "zebra_crossing_issues"].includes(layer)
      ? "ROAD_DAMAGE"
      : layer === "waterlogging"
      ? "WATERLOGGING"
      : layer === "traffic_congestion"
      ? "TRAFFIC"
      : layer === "pedestrian_risk"
      ? "PEDESTRIAN_RISK"
      : layer === "incidents"
      ? "INCIDENT"
      : layer === "anpr_violations"
      ? "ANPR"
      : "ROAD_DAMAGE"
  );

  const condType = p.condition_type || (layer === "traffic_congestion" || layer === "pedestrian_risk" || layer === "missing_signs" || layer === "missing_dividers" || layer === "incidents" ? "POTENTIAL" : "DIRECT");

  return {
    id: String(p.id || p.event_id || p.eventId || `ev_${Math.random().toString(36).slice(2, 8)}`),
    event_id: String(p.event_id || p.eventId || p.id || "EV-0000"),
    event_type,
    category,
    layer,
    confidence: typeof p.confidence === "number" ? p.confidence : 0.9,
    bus_id: String(p.bus_id || p.busId || "BUS_001"),
    camera_id: String(p.camera_id || "FRONT"),
    timestamp: typeof p.timestamp === "string" && p.timestamp ? p.timestamp : new Date().toISOString(),
    gps: {
      lat: Number(lat) || 0,
      lon: Number(lon) || 0,
      bearing_deg: Number(bearing_deg) || 0,
      road_segment: String(road_segment),
      address: String(address),
    },
    district: String(p.district || "Metropolitan"),
    severity,
    status,
    evidence_image_b64: p.evidence_image_b64 || p.annotated_evidence_path || p.evidence_path,
    original_evidence_path: p.original_evidence_path || p.evidence_path,
    annotated_evidence_path: p.annotated_evidence_path || p.evidence_image_b64 || p.evidence_path,
    thumbnail_path: p.thumbnail_path,
    source_video: p.source_video || p.video_file_name || "Live Dashcam Stream",
    condition_type: condType,
    condition_label: p.condition_label,
    is_derived: Boolean(p.is_derived || condType === "POTENTIAL"),
    maintenance_ticket_status: p.maintenance_ticket_status || (p.ticket_id ? "ASSIGNED" : undefined),
    frame_number: p.frame_number,
    track_id: p.track_id,
    evidence_clip_url: p.evidence_clip_url,
    ticket_id: p.ticket_id,
    persistent_hazard_id: p.persistent_hazard_id,
    independent_buses_count: p.independent_buses_count,
    contributing_buses: p.contributing_buses,
    persistence_badge: p.persistence_badge,
    last_detected_at: p.last_detected_at,
    ai_confidence: typeof p.ai_confidence === "number" ? p.ai_confidence : (typeof p.confidence === "number" ? p.confidence : 0.9),
    observation_count: p.observation_count,
    details: p.details || {},
  };
}

const INITIAL_LAYERS: LayerConfig[] = [
  { id: "bus_locations",        name: "Bus Locations",        category: "FLEET",       color: "#3b82f6", icon: "🚌", visible: true,  count: 3 },
  { id: "bus_routes",           name: "Bus Routes",           category: "FLEET",       color: "#6366f1", icon: "🛣", visible: true,  count: 3 },
  { id: "potholes",             name: "Potholes",             category: "DEFECTS",     color: "#f59e0b", icon: "🕳", visible: true,  count: 4 },
  { id: "road_damage",          name: "Road Damage",          category: "DEFECTS",     color: "#f97316", icon: "🚧", visible: true,  count: 3 },
  { id: "waterlogging",         name: "Waterlogging",         category: "DEFECTS",     color: "#06b6d4", icon: "💧", visible: true,  count: 2 },
  { id: "missing_signs",        name: "Missing Signs",        category: "SIGNS",       color: "#ec4899", icon: "🪧", visible: true,  count: 2 },
  { id: "missing_dividers",     name: "Missing Dividers",     category: "INFRA",       color: "#ef4444", icon: "⚠", visible: true,  count: 1 },
  { id: "zebra_crossing_issues",name: "Zebra Crossing Issues",category: "SAFETY",      color: "#84cc16", icon: "🦓", visible: true,  count: 2 },
  { id: "traffic_congestion",   name: "Traffic Congestion",   category: "TRAFFIC",     color: "#eab308", icon: "🚗", visible: true,  count: 3 },
  { id: "incidents",            name: "Incidents",            category: "SAFETY",      color: "#dc2626", icon: "🚨", visible: true,  count: 2 },
  { id: "pedestrian_risk",      name: "Pedestrian Risk",      category: "SAFETY",      color: "#a855f7", icon: "🚶", visible: true,  count: 2 },
  { id: "maintenance_tickets",  name: "Maintenance Tickets",  category: "MAINTENANCE", color: "#10b981", icon: "🔧", visible: true,  count: 2 },
];

const SEED_EVENTS: GisEventItem[] = [
  {
    id: "g_1",
    event_id: "EV-DEL-0412",
    event_type: "POTHOLE",
    layer: "potholes",
    confidence: 0.94,
    bus_id: "BUS_001",
    camera_id: "FRONT",
    timestamp: "2026-09-15T04:30:00Z",
    gps: { lat: 28.6328, lon: 77.2195, bearing_deg: 45, road_segment: "CP_INNER_CIRCLE", address: "Radial Road 1, Connaught Place, New Delhi" },
    district: "Central",
    severity: "HIGH",
    status: "ACTIVE",
    evidence_image_b64: "https://images.unsplash.com/photo-1515162816999-a0c47dc192f7?w=600&auto=format&fit=crop&q=60",
    evidence_clip_url: "/clips/EV-DEL-0412.mp4",
    details: { depth_cm: 8.5, diameter_cm: 52, vehicle_bump_g_force: 1.8 },
  },
  {
    id: "g_2",
    event_id: "EV-DEL-0415",
    event_type: "DAMAGED_ROAD",
    layer: "road_damage",
    confidence: 0.89,
    bus_id: "BUS_001",
    camera_id: "FRONT",
    timestamp: "2026-09-15T04:22:00Z",
    gps: { lat: 28.6340, lon: 77.2225, bearing_deg: 90, road_segment: "BARAKHAMBA_RD", address: "Barakhamba Road Junction, New Delhi" },
    district: "Central",
    severity: "MEDIUM",
    status: "CONFIRMED",
    evidence_image_b64: "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=600&auto=format&fit=crop&q=60",
    details: { alligator_cracking: true, length_m: 6.2 },
  },
  {
    id: "g_3",
    event_id: "EV-DEL-0419",
    event_type: "WATERLOGGING",
    layer: "waterlogging",
    confidence: 0.92,
    bus_id: "BUS_001",
    camera_id: "FRONT",
    timestamp: "2026-09-15T04:15:00Z",
    gps: { lat: 28.6290, lon: 77.2270, bearing_deg: 180, road_segment: "TOLSTOY_MARG", address: "Tolstoy Marg Subway Underpass, New Delhi" },
    district: "Central",
    severity: "HIGH",
    status: "ACTIVE",
    evidence_clip_url: "/clips/EV-DEL-0419.mp4",
    details: { water_depth_cm: 18.0, submerged_lanes: 2 },
  },
  {
    id: "g_4",
    event_id: "EV-DEL-0422",
    event_type: "MISSING_TRAFFIC_SIGN",
    layer: "missing_signs",
    confidence: 0.87,
    bus_id: "BUS_001",
    camera_id: "LEFT",
    timestamp: "2026-09-15T03:50:00Z",
    gps: { lat: 28.6260, lon: 77.2230, bearing_deg: 240, road_segment: "JANPATH_RD", address: "Janpath South Crossing, New Delhi" },
    district: "Central",
    severity: "MEDIUM",
    status: "ACTIVE",
    details: { expected_sign: "PEDESTRIAN_CROSSING_AHEAD" },
  },
  {
    id: "g_5",
    event_id: "EV-DEL-0425",
    event_type: "MISSING_ROAD_DIVIDER",
    layer: "missing_dividers",
    confidence: 0.91,
    bus_id: "BUS_001",
    camera_id: "FRONT",
    timestamp: "2026-09-15T03:30:00Z",
    gps: { lat: 28.6280, lon: 77.2170, bearing_deg: 310, road_segment: "SANSAD_MARG", address: "Sansad Marg North Entrance, New Delhi" },
    district: "Central",
    severity: "SEVERE",
    status: "ESCALATED",
    details: { missing_span_meters: 24.0, collision_hazard: true },
  },
  {
    id: "g_6",
    event_id: "EV-BLR-0781",
    event_type: "MISSING_ZEBRA_CROSSING",
    layer: "zebra_crossing_issues",
    confidence: 0.88,
    bus_id: "BUS_002",
    camera_id: "FRONT",
    timestamp: "2026-09-15T04:10:00Z",
    gps: { lat: 12.9716, lon: 77.5946, bearing_deg: 60, road_segment: "MG_ROAD_SEG_1", address: "MG Road Metro Gate 2, Bangalore" },
    district: "South",
    severity: "LOW",
    status: "ACTIVE",
    details: { paint_wear_pct: 80, school_proximity_m: 140 },
  },
  {
    id: "g_7",
    event_id: "EV-BLR-0788",
    event_type: "CONGESTION_EVENT",
    layer: "traffic_congestion",
    confidence: 0.96,
    bus_id: "BUS_002",
    camera_id: "FRONT",
    timestamp: "2026-09-15T04:45:00Z",
    gps: { lat: 12.9738, lon: 77.6020, bearing_deg: 85, road_segment: "BRIGADE_ROAD", address: "Brigade Road Junction, Bangalore" },
    district: "South",
    severity: "HIGH",
    status: "ACTIVE",
    details: { avg_speed_kmh: 6.2, queue_length_m: 650, congestion_score: "HIGH" },
  },
  {
    id: "g_8",
    event_id: "EV-BLR-0792",
    event_type: "POSSIBLE_INCIDENT",
    layer: "incidents",
    confidence: 0.89,
    bus_id: "BUS_002",
    camera_id: "FRONT",
    timestamp: "2026-09-15T04:50:00Z",
    gps: { lat: 12.9755, lon: 77.6070, bearing_deg: 75, road_segment: "COMMERCIAL_STREET", address: "Commercial Street Cross, Bangalore" },
    district: "South",
    severity: "SEVERE",
    status: "CONFIRMED",
    evidence_clip_url: "/clips/EV-BLR-0792.mp4",
    evidence_image_b64: "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=600&auto=format&fit=crop&q=60",
    details: { anomalous_signals: ["HARD_DECELERATION", "TRAJECTORY_DEFLECTION"], vehicles_involved: ["KA03MN1209", "KA05AB8892"] },
  },
  {
    id: "g_9",
    event_id: "EV-MUM-0112",
    event_type: "PEDESTRIAN_RISK",
    layer: "pedestrian_risk",
    confidence: 0.91,
    bus_id: "BUS_003",
    camera_id: "FRONT",
    timestamp: "2026-09-15T04:05:00Z",
    gps: { lat: 18.9480, lon: 72.8235, bearing_deg: 15, road_segment: "CHURCHGATE", address: "Maharshi Karve Road School Crosswalk, Mumbai" },
    district: "West",
    severity: "HIGH",
    status: "ACTIVE",
    evidence_clip_url: "/clips/EV-MUM-0112.mp4",
    details: { school_zone: "St. Xavier's School Zone", school_hours_active: true, trajectory_towards_road: true },
  },
  {
    id: "g_10",
    event_id: "EV-MUM-0118",
    event_type: "MAINTENANCE_TICKET",
    layer: "maintenance_tickets",
    confidence: 1.0,
    bus_id: "BUS_003",
    camera_id: "FRONT",
    timestamp: "2026-09-15T03:15:00Z",
    gps: { lat: 18.9540, lon: 72.8248, bearing_deg: 20, road_segment: "MARINE_DRIVE", address: "Marine Drive Flyover North Pillar, Mumbai" },
    district: "West",
    severity: "HIGH",
    status: "TICKET_CREATED",
    ticket_id: "TICK-2026-0814",
    details: { work_order: "Road repaving and barrier re-anchoring", crew: "Mumbai Central Works Division 3" },
  },
];

const SEED_BUSES: BusTelemetry[] = [
  { bus_id: "BUS_001", route_id: "ROUTE_1", name: "Bus 101 (Electric Low-Floor)", lat: 28.6315, lon: 77.2205, bearing_deg: 65, speed_kmh: 32, status: "LIVE", passenger_load_pct: 64 },
  { bus_id: "BUS_002", route_id: "ROUTE_2", name: "Bus 204 (CNG Transit)", lat: 12.9730, lon: 77.6000, bearing_deg: 88, speed_kmh: 28, status: "LIVE", passenger_load_pct: 82 },
  { bus_id: "BUS_003", route_id: "ROUTE_3", name: "Bus 308 (Double Decker)", lat: 18.9510, lon: 72.8240, bearing_deg: 12, speed_kmh: 41, status: "LIVE", passenger_load_pct: 54 },
];

export const GisCommandCenter: React.FC = () => {
  // ── States ─────────────────────────────────────────────────────────────────
  const [layers, setLayers] = useState<LayerConfig[]>(INITIAL_LAYERS);
  const [events, setEvents] = useState<GisEventItem[]>(SEED_EVENTS);
  const [buses, setBuses] = useState<BusTelemetry[]>(SEED_BUSES);
  const [selectedEvent, setSelectedEvent] = useState<GisEventItem | null>(null);
  const [selectedBus, setSelectedBus] = useState<BusTelemetry | null>(null);
  const [busDetailData, setBusDetailData] = useState<any | null>(null);
  const [drawerEvidenceMode, setDrawerEvidenceMode] = useState<"ANNOTATED" | "ORIGINAL">("ANNOTATED");
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [mapViewMode, setMapViewMode] = useState<"REAL_MAP" | "VECTOR">("REAL_MAP");

  // Administrative Hierarchy State (All States -> Capital -> District -> Tehsil)
  const [selectedState, setSelectedState] = useState<string>("National Capital Territory of Delhi");
  const [selectedDistrict, setSelectedDistrict] = useState<string>("ALL");
  const [selectedTehsil, setSelectedTehsil] = useState<string>("ALL");
  const [mapFlyToTarget, setMapFlyToTarget] = useState<{ lat: number; lon: number; zoom: number; label?: string } | null>(null);

  // Filters state (Step 3: Multi-Category & Multi-Dimensional Filters)
  const [filterCategory, setFilterCategory] = useState<string>("ALL");
  const [filterType, setFilterType] = useState<string>("ALL");
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");
  const [filterDate, setFilterDate] = useState<string>("ALL");
  const [filterTime, setFilterTime] = useState<string>("ALL");
  const [filterBus, setFilterBus] = useState<string>("ALL");
  const [filterRoute, setFilterRoute] = useState<string>("ALL");
  const [filterDistrict, setFilterDistrict] = useState<string>("ALL");
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [filterMinConfidence, setFilterMinConfidence] = useState<number>(0);

  // Map viewport & clustering state
  const [zoomLevel, setZoomLevel] = useState<number>(14);
  const [activeCity, setActiveCity] = useState<"DELHI" | "BANGALORE" | "MUMBAI">("DELHI");
  const [isClusterMode, setIsClusterMode] = useState<boolean>(true);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // Mobile responsiveness states (<lg)
  const [mobileGisTab, setMobileGisTab] = useState<"MAP" | "INTEL">("MAP");
  const [mobileLayersOpen, setMobileLayersOpen] = useState<boolean>(false);

  // ── Movable / Draggable Floating Windows & Controls State ────────────────
  const [showLayersPanel, setShowLayersPanel] = useState<boolean>(false);
  const [isLayersMinimized, setIsLayersMinimized] = useState<boolean>(false);
  const [layersPos, setLayersPos] = useState<{ x: number; y: number }>({ x: 16, y: 70 });

  const [showIntelPanel, setShowIntelPanel] = useState<boolean>(false);
  const [isIntelMinimized, setIsIntelMinimized] = useState<boolean>(false);
  const [intelPos, setIntelPos] = useState<{ x: number; y: number }>(() => ({
    x: typeof window !== "undefined" ? Math.max(16, window.innerWidth - 410) : 800,
    y: 70,
  }));

  const [showFiltersBar, setShowFiltersBar] = useState<boolean>(true);
  const [isFilterBarMinimized, setIsFilterBarMinimized] = useState<boolean>(false);
  const [filterBarPos, setFilterBarPos] = useState<{ x: number; y: number }>(() => ({
    x: 16,
    y: 56,
  }));
  const [activeWindowZ, setActiveWindowZ] = useState<"LAYERS" | "INTEL" | "FILTERS">("FILTERS");

  // Reset positions to default corners
  const resetLayersPos = () => setLayersPos({ x: 16, y: 70 });
  const resetIntelPos = () => setIntelPos({
    x: typeof window !== "undefined" ? Math.max(16, window.innerWidth - 410) : 800,
    y: 70,
  });
  const resetFilterBarPos = () => setFilterBarPos({ x: 16, y: 56 });

  // Generic Drag Handler using Pointer Events
  const handlePanelDragStart = (
    e: React.PointerEvent<HTMLDivElement>,
    panel: "LAYERS" | "INTEL" | "FILTERS"
  ) => {
    if ((e.target as HTMLElement).closest("button, input, select, a, label")) {
      return;
    }
    e.preventDefault();
    setActiveWindowZ(panel);

    const startX = e.clientX;
    const startY = e.clientY;
    const currentPos = panel === "LAYERS" ? layersPos : panel === "INTEL" ? intelPos : filterBarPos;
    const setPos = panel === "LAYERS" ? setLayersPos : panel === "INTEL" ? setIntelPos : setFilterBarPos;
    const initialX = currentPos.x;
    const initialY = currentPos.y;
    const panelWidth = panel === "LAYERS" ? 280 : panel === "INTEL" ? 390 : 720;

    const target = e.currentTarget;
    try {
      target.setPointerCapture(e.pointerId);
    } catch {}

    const handlePointerMove = (moveEv: PointerEvent) => {
      const dx = moveEv.clientX - startX;
      const dy = moveEv.clientY - startY;

      const maxX = Math.max(10, window.innerWidth - panelWidth - 10);
      const maxY = Math.max(10, window.innerHeight - 100);

      const nextX = Math.max(10, Math.min(maxX, initialX + dx));
      const nextY = Math.max(10, Math.min(maxY, initialY + dy));

      setPos({ x: nextX, y: nextY });
    };

    const handlePointerUp = (upEv: PointerEvent) => {
      try {
        target.releasePointerCapture(upEv.pointerId);
      } catch {}
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);
  };

  const containerRef = useRef<HTMLDivElement>(null);

  // City center coordinates
  const CITY_COORDS = {
    DELHI:     { lat: 28.6315, lon: 77.2205, name: "New Delhi (Connaught Place)" },
    BANGALORE: { lat: 12.9738, lon: 77.6020, name: "Bangalore (MG Road & Brigade)" },
    MUMBAI:    { lat: 18.9510, lon: 72.8240, name: "Mumbai (Marine Drive & Churchgate)" },
  };

  // Toggle Layer visibility
  const toggleLayer = (layerId: string) => {
    setLayers((prev) =>
      prev.map((l) => (l.id === layerId ? { ...l, visible: !l.visible } : l))
    );
  };

  // Toggle all layers in category
  const toggleCategory = (cat: string, makeVisible: boolean) => {
    setLayers((prev) =>
      prev.map((l) => (l.category === cat ? { ...l, visible: makeVisible } : l))
    );
  };

  // Fetch live events from GIS backend API
  useEffect(() => {
    const fetchFeatures = async () => {
      try {
        const res = await fetch("/api/v1/gis/features");
        if (res.ok) {
          const data = await res.json();
          if (data.features && data.features.length > 0) {
            const mapped: GisEventItem[] = data.features.map((f: any) => normalizeGisEvent(f));
            setEvents(mapped);
          }
        }
      } catch {
        // Fall back gracefully to seeded offline events
      }
    };
    fetchFeatures();
    const timer = setInterval(fetchFeatures, 5000);
    return () => clearInterval(timer);
  }, []);

  // Fetch live buses from /api/v1/buses (Phase 8: Connected Transit Edge Nodes)
  useEffect(() => {
    const fetchBusesData = async () => {
      try {
        const res = await fetch("/api/v1/buses");
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            const mapped: BusTelemetry[] = data.map((b: any) => ({
              bus_id: b.bus_id,
              route_id: b.route_id || "R-01",
              name: b.name || `Connected Bus ${b.bus_id}`,
              lat: b.latitude ?? b.current_lat ?? b.lat ?? 28.6139,
              lon: b.longitude ?? b.current_lon ?? b.lon ?? 77.2090,
              latitude: b.latitude ?? b.current_lat,
              longitude: b.longitude ?? b.current_lon,
              bearing_deg: b.heading ?? b.bearing_deg ?? 0,
              heading: b.heading ?? b.bearing_deg ?? 0,
              speed_kmh: b.speed ?? b.speed_kmh ?? 0,
              speed: b.speed ?? b.speed_kmh ?? 0,
              status: b.status || "LIVE",
              passenger_load_pct: b.passenger_load_pct ?? 62,
              timestamp: b.timestamp,
              camera_status: b.camera_status || "ACTIVE",
              AI_status: b.AI_status || "ONLINE",
              connection_status: b.connection_status || "CONNECTED",
            }));
            setBuses(mapped);
          }
        }
      } catch (err) {
        console.debug("Bus fetch error:", err);
      }
    };
    fetchBusesData();
    const bTimer = setInterval(fetchBusesData, 6000);
    return () => clearInterval(bTimer);
  }, []);

  // Listen to inspect-bus-edge-node custom events from map marker popups
  useEffect(() => {
    const handleInspectBus = (e: any) => {
      const busId = e.detail;
      const found = buses.find((b) => b.bus_id === busId);
      if (found) {
        setSelectedBus(found);
        setSelectedEvent(null);
        setIsDetailsOpen(true);
        setMapFlyToTarget({ lat: found.lat, lon: found.lon, zoom: 16, label: found.bus_id });
      }
    };
    window.addEventListener("inspect-bus-edge-node", handleInspectBus);
    return () => window.removeEventListener("inspect-bus-edge-node", handleInspectBus);
  }, [buses]);

  // Load detailed telemetry and recent hazards when selectedBus changes
  useEffect(() => {
    if (!selectedBus) {
      setBusDetailData(null);
      return;
    }
    const loadBusDetail = async () => {
      try {
        const res = await fetch(`/api/v1/buses/${selectedBus.bus_id}`);
        if (res.ok) {
          const data = await res.json();
          setBusDetailData(data);
        }
      } catch (e) {
        console.debug("Bus detail fetch note:", e);
      }
    };
    loadBusDetail();
  }, [selectedBus]);

  // Helper to match category filter (comprehensive category & keyword mapping)
  const matchesCategoryItem = (ev: GisEventItem, targetCategory: string): boolean => {
    if (!targetCategory || targetCategory === "ALL") return true;
    const directCat = (ev.category || (ev as any).category || "").toUpperCase();
    if (directCat === targetCategory.toUpperCase()) return true;

    const evType = String(ev.event_type || "").toUpperCase();
    const lyr = String(ev.layer || "").toLowerCase();

    if (targetCategory === "ROAD_DAMAGE") {
      if (["potholes", "road_damage", "missing_signs", "missing_dividers", "zebra_crossing_issues"].includes(lyr)) return true;
      return ["POTHOLE", "DAMAGE", "CRACK", "DEBRIS", "SIGN", "DIVIDER", "ZEBRA"].some((k) => evType.includes(k));
    }
    if (targetCategory === "WATERLOGGING") {
      if (lyr === "waterlogging") return true;
      return evType.includes("WATERLOG") || evType.includes("FLOOD") || evType.includes("PUDDLE");
    }
    if (targetCategory === "TRAFFIC") {
      if (lyr === "traffic_congestion") return true;
      return ["CONGESTION", "TRAFFIC", "BUS", "CAR", "TRUCK", "MOTORCYCLE", "VEHICLE"].some((k) => evType.includes(k));
    }
    if (targetCategory === "PEDESTRIAN_RISK") {
      if (lyr === "pedestrian_risk") return true;
      return evType.includes("PEDESTRIAN");
    }
    if (targetCategory === "INCIDENT") {
      if (lyr === "incidents") return true;
      return evType.includes("INCIDENT") || evType.includes("COLLISION") || evType.includes("ACCIDENT");
    }
    if (targetCategory === "ANPR") {
      if (lyr === "anpr_violations") return true;
      return evType.includes("ANPR") || evType.includes("PLATE") || evType.includes("INTRUSION");
    }
    return false;
  };

  // Helper to match date filter
  const matchesDateFilter = (timestampStr: string | undefined, dateFilter: string): boolean => {
    if (!dateFilter || dateFilter === "ALL") return true;
    if (!timestampStr) return true;
    const evDate = new Date(timestampStr);
    if (isNaN(evDate.getTime())) return true;
    const now = new Date();
    const diffHours = (now.getTime() - evDate.getTime()) / (1000 * 60 * 60);

    if (dateFilter === "TODAY") {
      return evDate.toDateString() === now.toDateString() || Math.abs(diffHours) <= 24;
    }
    if (dateFilter === "24H") {
      return Math.abs(diffHours) <= 24;
    }
    if (dateFilter === "7D") {
      return Math.abs(diffHours) <= 168;
    }
    return true;
  };

  // Live Counts per Category for Instant Visual Feedback on Pills
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {
      ALL: events.length,
      ROAD_DAMAGE: 0,
      WATERLOGGING: 0,
      TRAFFIC: 0,
      PEDESTRIAN_RISK: 0,
      INCIDENT: 0,
      ANPR: 0,
    };
    events.forEach((ev) => {
      if (matchesCategoryItem(ev, "ROAD_DAMAGE")) counts.ROAD_DAMAGE++;
      if (matchesCategoryItem(ev, "WATERLOGGING")) counts.WATERLOGGING++;
      if (matchesCategoryItem(ev, "TRAFFIC")) counts.TRAFFIC++;
      if (matchesCategoryItem(ev, "PEDESTRIAN_RISK")) counts.PEDESTRIAN_RISK++;
      if (matchesCategoryItem(ev, "INCIDENT")) counts.INCIDENT++;
      if (matchesCategoryItem(ev, "ANPR")) counts.ANPR++;
    });
    return counts;
  }, [events]);

  // ── Multi-Dimensional Filter Pipeline (Step 3) ───────────────────────────
  const filteredEvents = useMemo(() => {
    return events.filter((ev) => {
      // 1. Layer visibility check
      const layerConfig = layers.find((l) => l.id === ev.layer);
      if (layerConfig && !layerConfig.visible) return false;

      // 2. Step 3: Category Quick Filter
      if (filterCategory !== "ALL") {
        if (!matchesCategoryItem(ev, filterCategory)) return false;
      }

      // 3. Event Type filter
      if (filterType !== "ALL" && ev.event_type !== filterType) return false;

      // 4. Severity filter
      if (filterSeverity !== "ALL" && ev.severity !== filterSeverity) return false;

      // 5. District filter
      if (selectedDistrict !== "ALL") {
        const dTarget = selectedDistrict.toLowerCase();
        const evDist = String(ev.district || "").toLowerCase();
        const evAddr = String(ev.gps?.address || ev.gps?.road_segment || "").toLowerCase();
        if (!evDist.includes(dTarget) && !evAddr.includes(dTarget)) return false;
      }

      // 6. Bus filter
      if (filterBus !== "ALL" && ev.bus_id !== filterBus) return false;

      // 7. Route filter
      if (filterRoute !== "ALL" && (ev as any).route_id !== filterRoute) return false;

      // 8. Date filter
      if (!matchesDateFilter(ev.timestamp, filterDate)) return false;

      // 9. Confidence threshold
      if (filterMinConfidence > 0 && (ev.confidence || 0) < filterMinConfidence) return false;

      // 10. Status filter
      if (filterStatus !== "ALL") {
        const evStat = (ev.status || "").toUpperCase();
        const targetStat = filterStatus.toUpperCase();
        if (evStat !== targetStat && !(targetStat === "UNDER_REPAIR" && evStat === "IN_REPAIR")) {
          return false;
        }
      }

      return true;
    });
  }, [events, layers, filterCategory, filterType, filterSeverity, selectedDistrict, filterBus, filterRoute, filterDate, filterMinConfidence, filterStatus]);

  // ── Spatial Clustering at Lower Zoom Levels ─────────────────────────────────
  const clusters = useMemo(() => {
    // If zoom level is high (>= 15) or cluster mode disabled, display individual pins
    if (zoomLevel >= 15 || !isClusterMode) {
      return filteredEvents.map((ev) => ({
        isCluster: false,
        count: 1,
        lat: ev.gps?.lat ?? (ev as any).lat ?? 0,
        lon: ev.gps?.lon ?? (ev as any).lon ?? 0,
        events: [ev],
      }));
    }

    // Grid-based spatial clustering for lower zoom levels
    const gridSize = zoomLevel <= 11 ? 0.05 : zoomLevel <= 13 ? 0.015 : 0.006;
    const gridMap: Record<string, GisEventItem[]> = {};

    filteredEvents.forEach((ev) => {
      const lat = ev.gps?.lat ?? (ev as any).lat ?? 0;
      const lon = ev.gps?.lon ?? (ev as any).lon ?? 0;
      const gx = Math.floor(lon / gridSize);
      const gy = Math.floor(lat / gridSize);
      const key = `${gx}_${gy}`;
      if (!gridMap[key]) gridMap[key] = [];
      gridMap[key].push(ev);
    });

    return Object.values(gridMap).map((evList) => {
      const avgLat = evList.reduce((acc, e) => acc + (e.gps?.lat ?? (e as any).lat ?? 0), 0) / (evList.length || 1);
      const avgLon = evList.reduce((acc, e) => acc + (e.gps?.lon ?? (e as any).lon ?? 0), 0) / (evList.length || 1);
      return {
        isCluster: evList.length > 1,
        count: evList.length,
        lat: avgLat,
        lon: avgLon,
        events: evList,
      };
    });
  }, [filteredEvents, zoomLevel, isClusterMode]);

  // ── Action Handlers: Confirm, Dismiss, Escalate, Create Maintenance Ticket ──
  const handleEventAction = async (
    action: "CONFIRM" | "DISMISS" | "ESCALATE" | "CREATE_MAINTENANCE_TICKET"
  ) => {
    if (!selectedEvent) return;
    const eid = selectedEvent.event_id;

    let newStatus: GisEventItem["status"] = "ACTIVE";
    let newTicketId: string | undefined = undefined;

    if (action === "CONFIRM") newStatus = "CONFIRMED";
    else if (action === "DISMISS") newStatus = "DISMISSED";
    else if (action === "DISPATCH_REPAIR" || action === "CREATE_MAINTENANCE_TICKET") {
      newStatus = "UNDER_REPAIR";
      newTicketId = `WO-2026-${Math.floor(1000 + Math.random() * 9000)}`;
    } else if (action === "RESOLVE") {
      newStatus = "RESOLVED";
    } else if (action === "REOPEN") {
      newStatus = "UNVERIFIED";
    }

    // Optimistic UI update
    setEvents((prev) =>
      prev.map((e) =>
        e.event_id === eid ? { ...e, status: newStatus, ticket_id: newTicketId || e.ticket_id } : e
      )
    );
    setSelectedEvent((prev) =>
      prev && prev.event_id === eid
        ? { ...prev, status: newStatus, ticket_id: newTicketId || prev.ticket_id }
        : prev
    );

    setActionNotice(`Event ${eid}: Transitioned to '${newStatus}'`);
    setTimeout(() => setActionNotice(null), 3500);

    // Call Central events status transition endpoint (Step 6)
    try {
      await fetch(`/api/v1/events/${eid}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_status: newStatus.toLowerCase(), actor: "GIS_OPERATOR" }),
      });
      await fetch(`/api/v1/gis/events/${eid}/action`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, notes: `Action applied from GIS Command Center` }),
      });
    } catch {
      // Local state preserved
    }
  };

  const handleGenerateWorkOrder = async () => {
    const target = selectedEvent || events.find((e) => e.status === "ACTIVE" || e.status === "UNVERIFIED" || e.status === "CONFIRMED") || events[0];
    if (target) {
      const ticketId = `WO-2026-${Math.floor(1000 + Math.random() * 9000)}`;
      setEvents((prev) =>
        prev.map((e) =>
          e.event_id === target.event_id ? { ...e, status: "UNDER_REPAIR", ticket_id: ticketId } : e
        )
      );
      setSelectedEvent((prev) =>
        prev && prev.event_id === target.event_id
          ? { ...prev, status: "UNDER_REPAIR", ticket_id: ticketId }
          : { ...target, status: "UNDER_REPAIR", ticket_id: ticketId }
      );
      setActionNotice(`⚡ Automated Work Order Generated: ${ticketId} dispatched for ${target.event_type} (${target.gps?.road_segment || target.gps?.address || 'Monitored Corridor'})`);
      setTimeout(() => setActionNotice(null), 4500);

      try {
        await fetch(`/api/v1/events/${target.event_id}/status`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ target_status: "under_repair", actor: "AUTONOMOUS_DISPATCH_AI" }),
        });
      } catch {
        // Local state preserved
      }
    } else {
      setActionNotice("All detected anomalies are currently resolved or under active repair.");
      setTimeout(() => setActionNotice(null), 3000);
    }
  };

  const currentCenter = CITY_COORDS[activeCity];

  // Group layers into Image 1's three visual sets (Defects, Bottlenecks, Edge Nodes)
  const surfaceLayers = layers.filter((l) => l.category === "DEFECTS" || l.id === "potholes" || l.id === "road_damage" || l.id === "waterlogging");
  const hazardLayers = layers.filter((l) => l.category === "SAFETY" || l.category === "TRAFFIC" || l.id === "incidents" || l.id === "pedestrian_risk" || l.id === "traffic_congestion");
  const edgeLayers = layers.filter((l) => l.category === "FLEET" || l.category === "INFRA" || l.category === "SIGNS" || l.category === "MAINTENANCE");

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full overflow-hidden bg-[#0A0C16] text-slate-100 flex flex-col ${
        isFullscreen ? "fixed inset-0 z-50 h-screen" : ""
      }`}
    >
      {/* ── TOP APP BAR: FLEET SENSING OVERLAY - LIVE ─────────── */}
      <header className="min-h-14 bg-[#16192E] border-b border-[#232746] px-3 sm:px-4 py-2 sm:py-0 flex flex-wrap items-center justify-between gap-2 z-30 shrink-0 shadow-md">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-[#1E2342] border border-[#2B325E] flex items-center justify-center text-white font-black text-sm shadow-md shrink-0">
            <Radio size={16} className="text-amber-400 animate-pulse" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xs sm:text-sm font-extrabold tracking-wide flex items-center gap-1.5 sm:gap-2 text-white truncate">
              <span className="truncate">FLEET SENSING OVERLAY</span>
              <span className="text-[9px] sm:text-[10px] px-1.5 sm:px-2 py-0.2 sm:py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-500/40 font-mono font-bold shrink-0">
                LIVE
              </span>
            </h1>
            <p className="hidden sm:block text-[11px] text-slate-400 font-medium truncate">
              National Geospatial Urban Sensing Grid • PWD & Traffic Integration
            </p>
          </div>
        </div>

        {/* City Selector */}
        <div className="flex items-center gap-1 bg-[#0E101E] p-0.5 sm:p-1 rounded-lg border border-[#232746] text-[11px] sm:text-xs font-semibold shrink-0">
          {(["DELHI", "BANGALORE", "MUMBAI"] as const).map((city) => (
            <button
              key={city}
              onClick={() => {
                setActiveCity(city);
                const coords = CITY_COORDS[city];
                setMapFlyToTarget({ lat: coords.lat, lon: coords.lon, zoom: 13, label: coords.name });
              }}
              className={`px-2 sm:px-3 py-1 rounded-md transition cursor-pointer ${
                activeCity === city
                  ? "bg-[#282F5A] text-white shadow-sm font-bold"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {city}
            </button>
          ))}
        </div>

        {/* Top Right Quick Stats & Controls */}
        <div className="flex items-center gap-1.5 sm:gap-2.5 text-xs shrink-0">
          <div className="hidden xl:flex items-center gap-2.5 text-slate-400 font-mono text-[11px] bg-[#0E101E] px-3 py-1 rounded-md border border-[#232746]">
            <span className="flex items-center gap-1 text-white font-bold">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>{buses.length} Buses Active</span>
            </span>
            <span className="text-slate-600">|</span>
            <span className="text-emerald-400 font-bold bg-emerald-950/80 px-1.5 py-0.2 rounded border border-emerald-500/30">
              Consensus: 98.4%
            </span>
            <span className="text-slate-600">|</span>
            <span className="text-white font-bold">{filteredEvents.length} Hazards</span>
          </div>

          {/* Map View Mode Toggle */}
          <div className="flex items-center bg-[#0E101E] border border-[#232746] rounded-lg p-0.5">
            <button
              onClick={() => setMapViewMode("REAL_MAP")}
              className={`px-2 sm:px-2.5 py-1 rounded text-[10px] sm:text-[11px] font-bold transition cursor-pointer ${
                mapViewMode === "REAL_MAP" ? "bg-[#282F5A] text-white shadow-sm" : "text-slate-400 hover:text-white"
              }`}
              title="Google Maps Roadmap / Cartographic Tiles"
            >
              🗺️ Map
            </button>
            <button
              onClick={() => setMapViewMode("VECTOR")}
              className={`px-2 sm:px-2.5 py-1 rounded text-[10px] sm:text-[11px] font-bold transition cursor-pointer ${
                mapViewMode === "VECTOR" ? "bg-[#282F5A] text-white shadow-sm" : "text-slate-400 hover:text-white"
              }`}
              title="Schematic Vector Grid"
            >
              📐 Grid
            </button>
          </div>

          {/* Clustering Toggle (hidden on small mobile) */}
          <button
            onClick={() => setIsClusterMode(!isClusterMode)}
            className={`hidden sm:flex px-2.5 py-1 rounded-lg border text-xs font-semibold items-center gap-1.5 transition cursor-pointer ${
              isClusterMode
                ? "bg-emerald-950/80 text-emerald-400 border-emerald-500/40"
                : "bg-[#0E101E] border-[#232746] text-slate-400 hover:text-white"
            }`}
            title="Toggle marker clustering for dense hazard clusters"
          >
            <span className={`w-2 h-2 rounded-full ${isClusterMode ? "bg-emerald-400" : "bg-slate-500"}`} />
            <span>Clusters: {isClusterMode ? "ON" : "OFF"}</span>
          </button>

          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 rounded-lg bg-[#1E2342] hover:bg-[#282F5A] text-slate-300 hover:text-white border border-[#2B325E] transition cursor-pointer"
            title="Toggle Fullscreen"
          >
            {isFullscreen ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          </button>
        </div>
      </header>

      {/* ── MOBILE VIEW SWITCHER (<lg) ─────────────────────────── */}
      <div className="flex lg:hidden items-center justify-between p-2 bg-[#121528] border-b border-[#232746] gap-2 shrink-0 z-20">
        <button
          onClick={() => setMobileGisTab("MAP")}
          className={`flex-1 py-1.5 px-2.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 touch-manipulation cursor-pointer ${
            mobileGisTab === "MAP"
              ? "bg-[#C85A17] text-white shadow-sm"
              : "bg-[#1E2342] text-slate-300 hover:text-white"
          }`}
        >
          <span>🗺️ Live Map</span>
        </button>
        <button
          onClick={() => setMobileGisTab("INTEL")}
          className={`flex-1 py-1.5 px-2.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 touch-manipulation cursor-pointer ${
            mobileGisTab === "INTEL"
              ? "bg-[#C85A17] text-white shadow-sm"
              : "bg-[#1E2342] text-slate-300 hover:text-white"
          }`}
        >
          <span>📋 Intel Feed ({filteredEvents.length})</span>
        </button>
        <button
          onClick={() => setMobileLayersOpen((v) => !v)}
          className={`py-1.5 px-2.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1 border border-[#2B325E] touch-manipulation cursor-pointer ${
            mobileLayersOpen ? "bg-amber-600 text-white" : "bg-[#1E2342] text-slate-300"
          }`}
          title="Toggle Map Layers"
        >
          <Layers size={14} />
          <span className="hidden xs:inline">Layers</span>
        </button>
      </div>

      {/* ── ACTION NOTIFICATION TOAST ────────────────────────────────────────── */}
      {actionNotice && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-40 bg-[#1F2243] border border-amber-400 text-white px-4 py-2 rounded-xl shadow-2xl font-mono text-xs flex items-center gap-2 animate-bounce">
          <CheckCircle2 size={15} className="text-amber-400 shrink-0" />
          <span>{actionNotice}</span>
        </div>
      )}

      {/* ── WORKSPACE BODY: SIDEBARS + MAP CANVAS ────────────────────────────── */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* ── LEFT FLOATING PANEL: MAP LAYERS ────────────────────── */}
        {/* ── TOP MAP HUD QUICK ACCESS TOOLBAR ──────────────────────── */}
        <div style={{ zIndex: 1300 }} className="absolute top-3 left-3 z-[1300] flex flex-wrap items-center gap-2 pointer-events-auto">
          {/* Toggle Map Layers Button */}
          <button
            onClick={() => {
              setShowLayersPanel((v) => !v);
              setActiveWindowZ("LAYERS");
            }}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-xl border backdrop-blur-md cursor-pointer ${
              showLayersPanel
                ? "bg-[#C85A17] text-white border-amber-500 shadow-orange-900/40"
                : "bg-[#131628]/90 text-slate-300 border-[#2B325E] hover:text-white hover:bg-[#1E2342]"
            }`}
            title="Open / Close Map Layers panel"
          >
            <Layers size={14} className={showLayersPanel ? "text-white" : "text-amber-400"} />
            <span>Map Layers</span>
            <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-black/40 text-amber-300">
              {layers.filter((l) => l.visible).length}/{layers.length}
            </span>
          </button>

          {/* Toggle Fleet & Intel Sidebar Button */}
          <button
            onClick={() => {
              setShowIntelPanel((v) => !v);
              setActiveWindowZ("INTEL");
            }}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-xl border backdrop-blur-md cursor-pointer ${
              showIntelPanel
                ? "bg-[#2563EB] text-white border-blue-400 shadow-blue-900/40"
                : "bg-[#131628]/90 text-slate-300 border-[#2B325E] hover:text-white hover:bg-[#1E2342]"
            }`}
            title="Open / Close Fleet & Intelligence Feed"
          >
            <Activity size={14} className={showIntelPanel ? "text-white" : "text-cyan-400"} />
            <span>Fleet & Intel</span>
            <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-black/40 text-cyan-300">
              {filteredEvents.length} Plotted
            </span>
          </button>

          {/* Toggle Category Filters Bar Button */}
          <button
            onClick={() => {
              setShowFiltersBar((v) => {
                const next = !v;
                if (next) setActiveWindowZ("FILTERS");
                return next;
              });
            }}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-xl border backdrop-blur-md cursor-pointer ${
              showFiltersBar
                ? "bg-[#1E2342] text-white border-amber-500/60 shadow-amber-900/40"
                : "bg-[#131628]/90 text-slate-300 border-[#2B325E] hover:text-white hover:bg-[#1E2342]"
            }`}
            title="Show / Hide Category Quick Filters"
          >
            <Filter size={14} className="text-amber-400" />
            <span>Categories & Filters</span>
            {filterCategory !== "ALL" && (
              <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-amber-500 text-black font-extrabold">
                {filterCategory}
              </span>
            )}
          </button>
        </div>

        {/* ── MOVABLE / DRAGGABLE FLOATING PANEL: MAP LAYERS (Image 2) ────────────────────── */}
        {showLayersPanel && (
          <aside
            style={{
              left: `${layersPos.x}px`,
              top: `${layersPos.y}px`,
              zIndex: activeWindowZ === "LAYERS" ? 1200 : 1040,
            }}
            onPointerDown={() => setActiveWindowZ("LAYERS")}
            className="absolute w-72 max-w-[calc(100vw-24px)] bg-[#131628]/95 backdrop-blur-md border border-[#232746] rounded-xl shadow-2xl flex flex-col overflow-hidden text-slate-100 transition-shadow animate-in fade-in zoom-in-95 duration-150 select-none"
          >
            {/* Movable Window Header */}
            <div
              onPointerDown={(e) => handlePanelDragStart(e, "LAYERS")}
              className="p-2.5 border-b border-[#232746] flex items-center justify-between bg-[#16192E] cursor-grab active:cursor-grabbing hover:bg-[#1C203B] transition"
              title="Click and drag to move panel"
            >
              <div className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wider text-white select-none">
                <GripHorizontal size={15} className="text-slate-500 hover:text-amber-400" />
                <Layers size={14} className="text-amber-400" />
                <span>Map Layers</span>
                <span className="text-[10px] text-slate-400 font-mono font-normal">
                  ({layers.filter((l) => l.visible).length}/{layers.length})
                </span>
              </div>
              <div className="flex items-center gap-1 text-[10px] font-semibold">
                <button
                  onClick={() => setLayers((prev) => prev.map((l) => ({ ...l, visible: true })))}
                  className="px-1 text-amber-400 hover:text-amber-300 hover:underline cursor-pointer"
                >
                  All
                </button>
                <span className="text-slate-600">/</span>
                <button
                  onClick={() => setLayers((prev) => prev.map((l) => ({ ...l, visible: false })))}
                  className="px-1 text-slate-400 hover:text-slate-200 hover:underline cursor-pointer"
                >
                  None
                </button>
                <button
                  onClick={resetLayersPos}
                  className="p-1 text-slate-400 hover:text-cyan-400 rounded cursor-pointer transition ml-0.5"
                  title="Reset Position"
                >
                  <RotateCcw size={12} />
                </button>
                <button
                  onClick={() => setIsLayersMinimized((v) => !v)}
                  className="p-1 text-slate-400 hover:text-amber-400 rounded cursor-pointer transition"
                  title={isLayersMinimized ? "Expand Panel" : "Minimize Panel"}
                >
                  {isLayersMinimized ? <Square size={12} /> : <Minus size={12} />}
                </button>
                <button
                  onClick={() => setShowLayersPanel(false)}
                  className="p-1 text-slate-400 hover:text-rose-400 rounded cursor-pointer transition"
                  title="Close Layers Panel"
                >
                  <X size={13} />
                </button>
              </div>
            </div>

            {/* Window Body (collapsible) */}
            {!isLayersMinimized && (
              <div className="flex-1 flex flex-col max-h-[calc(100vh-180px)] overflow-hidden">
                {/* Grouped Layer List */}
          <div className="flex-1 overflow-y-auto p-2.5 space-y-3 text-xs">
            {/* 🟢 Group 1: PWD Surface Defects */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400 px-1">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span>PWD Surface Defects</span>
                </span>
                <span className="font-mono text-[9px] text-slate-400">
                  {events.filter((e) => surfaceLayers.some((sl) => sl.id === e.layer)).length}
                </span>
              </div>
              <div className="space-y-0.5">
                {surfaceLayers.map((layer) => (
                  <label
                    key={layer.id}
                    className={`flex items-center justify-between px-2 py-1 rounded-lg cursor-pointer transition select-none ${
                      layer.visible ? "bg-[#1E2342] text-white font-semibold" : "text-slate-400 hover:bg-[#16192E]"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <input
                        type="checkbox"
                        checked={layer.visible}
                        onChange={() => toggleLayer(layer.id)}
                        className="accent-amber-500 rounded"
                      />
                      <span>{layer.icon}</span>
                      <span className="text-[11px] truncate max-w-[130px]">{layer.name}</span>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded font-bold bg-amber-950/80 text-amber-400 border border-amber-500/30">
                      {events.filter((e) => e.layer === layer.id).length}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* 🔴 Group 2: Bottlenecks & Hazards */}
            <div className="space-y-1 pt-1 border-t border-[#232746]">
              <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400 px-1">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                  <span>Bottlenecks & Hazards</span>
                </span>
                <span className="font-mono text-[9px] text-slate-400">
                  {events.filter((e) => hazardLayers.some((hl) => hl.id === e.layer)).length}
                </span>
              </div>
              <div className="space-y-0.5">
                {hazardLayers.map((layer) => (
                  <label
                    key={layer.id}
                    className={`flex items-center justify-between px-2 py-1 rounded-lg cursor-pointer transition select-none ${
                      layer.visible ? "bg-[#1E2342] text-white font-semibold" : "text-slate-400 hover:bg-[#16192E]"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <input
                        type="checkbox"
                        checked={layer.visible}
                        onChange={() => toggleLayer(layer.id)}
                        className="accent-rose-500 rounded"
                      />
                      <span>{layer.icon}</span>
                      <span className="text-[11px] truncate max-w-[130px]">{layer.name}</span>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded font-bold bg-rose-950/80 text-rose-400 border border-rose-500/30">
                      {events.filter((e) => e.layer === layer.id).length}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* 🔵 Group 3: Active Edge Nodes */}
            <div className="space-y-1 pt-1 border-t border-[#232746]">
              <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400 px-1">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-cyan-400" />
                  <span>Active Edge Nodes</span>
                </span>
                <span className="font-mono text-[9px] text-slate-400">
                  {buses.length} Live
                </span>
              </div>
              <div className="space-y-0.5">
                {edgeLayers.map((layer) => (
                  <label
                    key={layer.id}
                    className={`flex items-center justify-between px-2 py-1 rounded-lg cursor-pointer transition select-none ${
                      layer.visible ? "bg-[#1E2342] text-white font-semibold" : "text-slate-400 hover:bg-[#16192E]"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <input
                        type="checkbox"
                        checked={layer.visible}
                        onChange={() => toggleLayer(layer.id)}
                        className="accent-cyan-500 rounded"
                      />
                      <span>{layer.icon}</span>
                      <span className="text-[11px] truncate max-w-[130px]">{layer.name}</span>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded font-bold bg-cyan-950/80 text-cyan-400 border border-cyan-500/30">
                      {layer.id === "bus_locations" ? buses.length : events.filter((e) => e.layer === layer.id).length}
                    </span>
                  </label>
                ))}
              </div>

              {/* Connected Edge Fleet Node List (Phase 8) */}
              <div className="mt-2 space-y-1">
                <div className="text-[9px] font-bold uppercase tracking-wider text-cyan-400 px-1 flex items-center justify-between">
                  <span>Connected Fleet Nodes</span>
                  <span className="text-slate-400 font-mono text-[8px]">{buses.length} online</span>
                </div>
                <div className="space-y-1 max-h-36 overflow-y-auto pr-0.5">
                  {buses.map((b) => (
                    <div
                      key={b.bus_id}
                      onClick={() => {
                        setSelectedBus(b);
                        setSelectedEvent(null);
                        setIsDetailsOpen(true);
                        setShowIntelPanel(true);
                        setActiveWindowZ("INTEL");
                        setMapFlyToTarget({ lat: b.lat, lon: b.lon, zoom: 16, label: b.bus_id });
                      }}
                      className={`flex items-center justify-between p-1.5 rounded-lg border cursor-pointer text-[10px] transition ${
                        selectedBus?.bus_id === b.bus_id
                          ? "bg-blue-900/40 border-blue-500/60 text-white"
                          : "bg-[#16192E] hover:bg-[#1E2342] border-[#232746] text-slate-300"
                      }`}
                    >
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                          b.AI_status === "INFERENCING" ? "bg-amber-400 animate-pulse" : "bg-emerald-400"
                        }`} />
                        <span className="font-bold font-mono text-white truncate">{b.bus_id}</span>
                        <span className="text-[9px] text-slate-400 truncate">({b.route_id})</span>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <span className="text-[9px] font-mono font-bold text-cyan-300">{Math.round(b.speed_kmh)} km/h</span>
                        <span className={`text-[8px] px-1 py-0.2 rounded font-mono ${
                          b.AI_status === "INFERENCING"
                            ? "bg-amber-950 text-amber-300 border border-amber-500/40"
                            : "bg-blue-950 text-blue-300 border border-blue-800/40"
                        }`}>
                          {b.AI_status || "ONLINE"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Territorial Intelligence Card at bottom */}
          {(() => {
            const stateObj = adminHierarchyData.all_states.find((s: any) => s.state === selectedState);
            if (!stateObj) return null;
            const currentDist = selectedDistrict !== "ALL"
              ? stateObj.districts.find((d: any) => d.name === selectedDistrict)
              : stateObj.districts[0];

            return (
              <div className="p-2.5 border-t border-[#232746] bg-[#0B0D18] space-y-1.5 text-[11px]">
                <div className="flex items-center justify-between font-bold text-white">
                  <span className="flex items-center gap-1">
                    <MapPin size={12} className="text-amber-400" />
                    <span>Territory Dossier</span>
                  </span>
                  <span className="font-mono text-[10px] text-slate-400 font-normal">
                    {stateObj.code}
                  </span>
                </div>

                <div className="space-y-0.5 text-[10px]">
                  <div className="flex justify-between text-slate-400">
                    <span>State:</span>
                    <span className="font-semibold text-[#1F2243] truncate max-w-[130px]">{stateObj.state}</span>
                  </div>
                  <div className="flex justify-between text-[#4F546F]">
                    <span>District:</span>
                    <span className="font-semibold text-amber-700 truncate max-w-[130px]">
                      {selectedDistrict !== "ALL" ? selectedDistrict : `${stateObj.districts.length} Monitored`}
                    </span>
                  </div>
                </div>
              </div>
            );
          })()}
              </div>
            )}
          </aside>
        )}

        {/* ── MOVABLE / DRAGGABLE FLOATING PANEL: CATEGORY PILLS & MULTI-DIMENSIONAL FILTERS ─────── */}
        {showFiltersBar && (
          <aside
            style={{
              left: `${filterBarPos.x}px`,
              top: `${filterBarPos.y}px`,
              zIndex: activeWindowZ === "FILTERS" ? 1200 : 1050,
            }}
            onPointerDown={() => setActiveWindowZ("FILTERS")}
            className="absolute max-w-[calc(100vw-24px)] sm:max-w-4xl bg-white/95 backdrop-blur-md border border-[#CBD5E1] rounded-xl shadow-2xl flex flex-col text-xs text-[#1F2243] pointer-events-auto transition-shadow animate-in fade-in zoom-in-95 duration-150 select-none"
          >
            {/* Movable Window Header */}
            <div
              onPointerDown={(e) => handlePanelDragStart(e, "FILTERS")}
              className="p-2 border-b border-[#E2E8F0] flex items-center justify-between bg-[#F8FAFC] rounded-t-xl cursor-grab active:cursor-grabbing hover:bg-[#F1F5F9] transition"
              title="Click and drag to move filter bar"
            >
              <div className="flex items-center gap-1.5 text-[11px] font-extrabold uppercase tracking-wider text-[#1F2243] select-none">
                <GripHorizontal size={15} className="text-slate-400 hover:text-amber-600" />
                <Filter size={13} className="text-amber-600" />
                <span>Categories & Filters</span>
                {filterCategory !== "ALL" && (
                  <span className="font-mono text-[9px] px-1.5 py-0.2 rounded bg-amber-500 text-black font-extrabold">
                    {filterCategory}
                  </span>
                )}
                <span className="text-[10px] text-slate-500 font-mono font-normal hidden sm:inline">
                  ({filteredEvents.length} active events)
                </span>
              </div>
              <div className="flex items-center gap-1 text-[10px] font-semibold">
                <button
                  type="button"
                  onClick={resetFilterBarPos}
                  className="p-1 text-slate-400 hover:text-cyan-600 rounded cursor-pointer transition"
                  title="Reset Filter Bar Position"
                >
                  <RotateCcw size={12} />
                </button>
                <button
                  type="button"
                  onClick={() => setIsFilterBarMinimized((v) => !v)}
                  className="p-1 text-slate-400 hover:text-amber-600 rounded cursor-pointer transition"
                  title={isFilterBarMinimized ? "Expand Filter Bar" : "Minimize Filter Bar"}
                >
                  {isFilterBarMinimized ? <Square size={12} /> : <Minus size={12} />}
                </button>
                <button
                  type="button"
                  onClick={() => setShowFiltersBar(false)}
                  className="p-1 text-slate-400 hover:text-rose-600 rounded cursor-pointer transition"
                  title="Close Filter Bar"
                >
                  <X size={13} />
                </button>
              </div>
            </div>

            {/* Window Body (collapsible) */}
            {!isFilterBarMinimized && (
              <div className="p-2 sm:p-2.5 flex flex-col gap-2 max-h-[50vh] sm:max-h-none overflow-y-auto sm:overflow-visible">
                {/* Row 1: Category Quick Filters */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#E2E8F0] pb-2">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-[10px] font-extrabold uppercase tracking-wider text-[#4F546F] mr-1 flex items-center gap-1">
                      <Filter size={12} className="text-amber-600" />
                      Categories:
                    </span>
                    {[
                      { id: "ALL", label: "All", icon: "🌐" },
                      { id: "ROAD_DAMAGE", label: "Road Damage", icon: "🕳️" },
                      { id: "WATERLOGGING", label: "Waterlogging", icon: "💧" },
                      { id: "TRAFFIC", label: "Traffic", icon: "🚗" },
                      { id: "PEDESTRIAN_RISK", label: "Pedestrian Risk", icon: "🚸" },
                      { id: "INCIDENT", label: "Incident", icon: "🚨" },
                      { id: "ANPR", label: "ANPR", icon: "📸" },
                    ].map((cat) => {
                      const isActive = filterCategory === cat.id;
                      const count = categoryCounts[cat.id] ?? 0;
                      return (
                        <button
                          type="button"
                          key={cat.id}
                          onClick={() => setFilterCategory(cat.id)}
                          className={`px-2.5 py-1 rounded-full text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer select-none ${
                            isActive
                              ? "bg-[#1F2243] text-white shadow-sm ring-1 ring-[#1F2243]"
                              : "bg-[#F1F5F9] text-[#4F546F] hover:text-[#1F2243] hover:bg-[#E2E8F0]"
                          }`}
                        >
                          <span>{cat.icon}</span>
                          <span>{cat.label}</span>
                          <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${
                            isActive ? "bg-white/20 text-white" : "bg-slate-200 text-slate-700"
                          }`}>
                            {count}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Row 2: Multi-Dimensional Dropdowns */}
                <div className="flex flex-wrap items-center gap-2 pt-0.5">
                  {/* Severity Filter */}
                  <select
                    value={filterSeverity}
                    onChange={(e) => setFilterSeverity(e.target.value)}
                    className="bg-[#F8FAFC] border border-[#CBD5E1] rounded-md px-2 py-1 text-xs text-[#1F2243] font-medium outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer"
                  >
                    <option value="ALL">All Severities</option>
                    <option value="LOW">Low Severity</option>
                    <option value="MEDIUM">Medium Severity</option>
                    <option value="HIGH">High Severity</option>
                    <option value="SEVERE">Severe Hazard</option>
                  </select>

                  {/* Status Filter */}
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="bg-[#F8FAFC] border border-[#CBD5E1] rounded-md px-2 py-1 text-xs text-[#1F2243] font-medium outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer"
                  >
                    <option value="ALL">All Statuses</option>
                    <option value="ACTIVE">⚡ Active / Live</option>
                    <option value="CONFIRMED">✓ Confirmed</option>
                    <option value="ESCALATED">🚨 Escalated</option>
                    <option value="UNDER_REPAIR">🔧 Under Repair</option>
                    <option value="RESOLVED">✓ Resolved</option>
                    <option value="UNVERIFIED">⏳ Unverified</option>
                    <option value="DISMISSED">✕ Dismissed</option>
                  </select>

                  {/* Date Filter */}
                  <select
                    value={filterDate}
                    onChange={(e) => setFilterDate(e.target.value)}
                    className="bg-[#F8FAFC] border border-[#CBD5E1] rounded-md px-2 py-1 text-xs text-[#1F2243] font-medium outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer"
                  >
                    <option value="ALL">All Dates</option>
                    <option value="TODAY">Today Only</option>
                    <option value="24H">Past 24 Hours</option>
                    <option value="7D">Past 7 Days</option>
                  </select>

                  {/* Confidence Filter */}
                  <select
                    value={filterMinConfidence}
                    onChange={(e) => setFilterMinConfidence(Number(e.target.value))}
                    className="bg-[#F8FAFC] border border-[#CBD5E1] rounded-md px-2 py-1 text-xs text-[#1F2243] font-medium outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer"
                  >
                    <option value={0}>All Confidences</option>
                    <option value={0.80}>≥ 80% Confidence</option>
                    <option value={0.85}>≥ 85% Confidence</option>
                    <option value={0.90}>≥ 90% Confidence</option>
                    <option value={0.95}>≥ 95% Confidence</option>
                  </select>

                  {/* State Selector */}
                  <select
                    value={selectedState}
                    onChange={(e) => {
                      const newState = e.target.value;
                      setSelectedState(newState);
                      setSelectedDistrict("ALL");
                      setFilterDistrict("ALL");
                      setSelectedTehsil("ALL");
                      const stateObj = adminHierarchyData.all_states.find((s: any) => s.state === newState);
                      if (stateObj && stateObj.districts.length > 0) {
                        const firstDist = stateObj.districts[0];
                        setMapFlyToTarget({ lat: firstDist.lat, lon: firstDist.lon, zoom: 12, label: `${stateObj.state} • Capital: ${stateObj.capital}` });
                      }
                    }}
                    className="bg-[#F8FAFC] border border-blue-400 rounded-md px-2 py-1 text-xs text-blue-800 font-semibold outline-none cursor-pointer"
                    title="Select State & Capital"
                  >
                    {adminHierarchyData.all_states.map((st: any) => (
                      <option key={st.state} value={st.state}>
                        🏛️ {st.state} (Cap: {st.capital})
                      </option>
                    ))}
                  </select>

                  {/* District Selector */}
                  <select
                    value={selectedDistrict}
                    onChange={(e) => {
                      const newDist = e.target.value;
                      setSelectedDistrict(newDist);
                      setFilterDistrict(newDist);
                      setSelectedTehsil("ALL");
                      const stateObj = adminHierarchyData.all_states.find((s: any) => s.state === selectedState);
                      if (stateObj) {
                        const distObj = stateObj.districts.find((d: any) => d.name === newDist);
                        if (distObj) {
                          setMapFlyToTarget({ lat: distObj.lat, lon: distObj.lon, zoom: 13, label: `${distObj.name} District, ${stateObj.state}` });
                        }
                      }
                    }}
                    className="bg-[#F8FAFC] border border-emerald-400 rounded-md px-2 py-1 text-xs text-emerald-800 font-semibold outline-none cursor-pointer"
                    title="Select District"
                  >
                    <option value="ALL">All Districts</option>
                    {(() => {
                      const stateObj = adminHierarchyData.all_states.find((s: any) => s.state === selectedState);
                      return stateObj ? stateObj.districts.map((d: any) => (
                        <option key={d.name} value={d.name}>
                          📍 {d.name}
                        </option>
                      )) : null;
                    })()}
                  </select>

                  {/* Reset Filters */}
                  <button
                    type="button"
                    onClick={() => {
                      setFilterCategory("ALL");
                      setFilterType("ALL");
                      setFilterSeverity("ALL");
                      setFilterDistrict("ALL");
                      setFilterBus("ALL");
                      setFilterRoute("ALL");
                      setFilterDate("ALL");
                      setFilterStatus("ALL");
                      setFilterMinConfidence(0);
                      setSelectedDistrict("ALL");
                      setSelectedTehsil("ALL");
                      setActionNotice("Filters reset to default view.");
                      setTimeout(() => setActionNotice(null), 2500);
                    }}
                    className="px-2.5 py-1 rounded bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#4F546F] hover:text-[#1F2243] transition text-[11px] font-semibold ml-auto border border-[#CBD5E1] cursor-pointer"
                  >
                    Reset Filters
                  </button>
                </div>
              </div>
            )}
          </aside>
        )}

        {/* ── MAP CANVAS (REAL GOOGLE MAPS / VECTOR PROJECTION) ───────────────────── */}
        {mapViewMode === "REAL_MAP" ? (
          <div className={`flex-1 w-full h-[calc(100vh-56px)] min-h-[450px] relative z-0 isolate bg-gray-950 overflow-hidden ${
            mobileGisTab === "INTEL" ? "hidden lg:block" : "block"
          }`}>
            <LiveGisMap
              height="100%"
              initialCity={activeCity === "BANGALORE" ? "BANGALORE" : activeCity === "MUMBAI" ? "MUMBAI" : "DELHI"}
              showControls={false}
              flyToLocation={mapFlyToTarget}
              filters={{
                category: filterCategory,
                severity: filterSeverity,
                status: filterStatus,
                date: filterDate,
                district: selectedDistrict,
                bus: filterBus,
                route: filterRoute,
                minConfidence: filterMinConfidence,
                isClusterMode: isClusterMode,
              }}
              onSelectEvent={(ev) => {
                const norm = normalizeGisEvent(ev);
                setSelectedEvent(norm);
                setIsDetailsOpen(true);
                setShowIntelPanel(true);
                setActiveWindowZ("INTEL");
                setMobileGisTab("INTEL");
              }}
            />
          </div>
        ) : (
        <div className={`flex-1 w-full h-full relative z-0 isolate bg-gray-950 overflow-hidden cursor-default ${
          mobileGisTab === "INTEL" ? "hidden lg:block" : "block"
        }`}>
          {/* Cartographic Vector Grid Background (CartoDB Dark Tile Simulation) */}
          <div
            className="absolute inset-0 opacity-40"
            style={{
              backgroundImage: `
                radial-gradient(circle at 50% 50%, rgba(99, 102, 241, 0.08) 0%, transparent 80%),
                linear-gradient(to right, #1f2937 1px, transparent 1px),
                linear-gradient(to bottom, #1f2937 1px, transparent 1px)
              `,
              backgroundSize: "60px 60px",
            }}
          />

          {/* Transit Route Polylines Layer */}
          {layers.find((l) => l.id === "bus_routes")?.visible && (
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
              <defs>
                <linearGradient id="routeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#a855f7" stopOpacity="0.8" />
                </linearGradient>
              </defs>
              <polyline
                points="240,420 380,360 520,380 650,490 540,580 340,540 240,420"
                fill="none"
                stroke="url(#routeGrad)"
                strokeWidth="4"
                strokeDasharray="8 4"
                className="animate-pulse"
              />
              <polyline
                points="420,220 540,280 690,320 840,410"
                fill="none"
                stroke="#10b981"
                strokeWidth="4"
                strokeDasharray="6 3"
              />
            </svg>
          )}

          {/* Live Bus Fleet Layer */}
          {layers.find((l) => l.id === "bus_locations")?.visible && (
            <div className="absolute inset-0 pointer-events-none z-20">
              {buses.map((bus, idx) => {
                const posX = 35 + idx * 24;
                const posY = 40 + (idx % 2) * 18;
                return (
                  <div
                    key={bus.bus_id}
                    className="absolute pointer-events-auto cursor-pointer transform -translate-x-1/2 -translate-y-1/2 group"
                    style={{ left: `${posX}%`, top: `${posY}%` }}
                    onClick={() => {
                      // Focus bus
                      setActionNotice(`Telemetry: ${bus.name} — Speed: ${bus.speed_kmh} km/h`);
                    }}
                  >
                    <div className="relative flex items-center justify-center">
                      <span className="w-9 h-9 rounded-full bg-blue-600/30 border border-blue-400 flex items-center justify-center text-sm text-white shadow-lg shadow-blue-500/50">
                        🚌
                      </span>
                      <span className="absolute -bottom-4 bg-gray-900/90 text-[10px] font-mono font-bold text-blue-300 px-1.5 py-0.2 rounded border border-gray-700 whitespace-nowrap">
                        {bus.bus_id} • {bus.speed_kmh}km/h
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* ── Clusters & Event Markers Layer ───────────────────────────────── */}
          <div className="absolute inset-0 z-20">
            {clusters.map((c, i) => {
              // Project relative offset based on coordinate differences
              const offsetX = ((c.lon - currentCenter.lon) * 12000) % 75;
              const offsetY = ((currentCenter.lat - c.lat) * 12000) % 70;
              const posX = Math.max(12, Math.min(88, 50 + offsetX));
              const posY = Math.max(15, Math.min(85, 48 + offsetY));

              if (c.isCluster) {
                // Cluster Marker
                return (
                  <div
                    key={`cluster_${i}`}
                    className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer group"
                    style={{ left: `${posX}%`, top: `${posY}%` }}
                    onClick={() => {
                      setZoomLevel((z) => Math.min(16, z + 2));
                      setSelectedEvent(normalizeGisEvent(c.events[0]));
                      setIsDetailsOpen(true);
                      setShowIntelPanel(true);
                      setActiveWindowZ("INTEL");
                    }}
                  >
                    <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-brand to-purple-600 text-white font-mono font-black text-xs flex items-center justify-center shadow-xl shadow-brand/50 border-2 border-white/80 group-hover:scale-110 transition">
                      {c.count}
                    </div>
                    <span className="absolute -bottom-4 left-1/2 -translate-x-1/2 text-[9px] font-mono bg-gray-900/90 text-gray-300 px-1 rounded whitespace-nowrap">
                      Cluster ({c.count})
                    </span>
                  </div>
                );
              }

              // Individual Event Marker
              const ev = c.events[0];
              const layerCfg = layers.find((l) => l.id === ev.layer);
              const color = layerCfg?.color || "#f59e0b";
              const isSelected = selectedEvent?.event_id === ev.event_id;

              return (
                <div
                  key={ev.event_id}
                  className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer group transition-all duration-200"
                  style={{ left: `${posX}%`, top: `${posY}%` }}
                  onClick={() => {
                    setSelectedEvent(normalizeGisEvent(ev));
                    setIsDetailsOpen(true);
                    setShowIntelPanel(true);
                    setActiveWindowZ("INTEL");
                  }}
                >
                  <div
                    className={`relative p-2 rounded-xl flex items-center justify-center shadow-xl transition-transform duration-200 group-hover:scale-125 ${
                      isSelected
                        ? "ring-4 ring-white scale-125 z-30"
                        : "border border-gray-700"
                    }`}
                    style={{
                      backgroundColor: `${color}30`,
                      borderColor: color,
                      boxShadow: `0 0 16px ${color}50`,
                    }}
                  >
                    <span className="text-base leading-none">{layerCfg?.icon || "📍"}</span>
                    {ev.severity === "SEVERE" && (
                      <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
                    )}
                  </div>
                  <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 bg-gray-900/95 text-[10px] font-mono text-gray-200 px-1.5 py-0.5 rounded border border-gray-800 whitespace-nowrap shadow-md group-hover:block hidden">
                    {ev.event_id} • {(ev.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              );
            })}
          </div>

          {/* ── Zoom Controls & City Indicator ────────────────────────────────── */}
          <div className="absolute bottom-6 left-6 z-20 flex flex-col gap-2">
            <div className="bg-gray-900/90 backdrop-blur-md border border-gray-800 p-2 rounded-xl shadow-xl flex flex-col gap-1.5">
              <button
                onClick={() => setZoomLevel((z) => Math.min(18, z + 1))}
                className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 transition"
                title="Zoom In"
              >
                <ZoomIn size={16} />
              </button>
              <button
                onClick={() => setZoomLevel((z) => Math.max(10, z - 1))}
                className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 transition"
                title="Zoom Out"
              >
                <ZoomOut size={16} />
              </button>
            </div>

            <div className="bg-gray-900/90 backdrop-blur-md border border-gray-800 px-3 py-1.5 rounded-xl text-xs font-mono text-gray-400">
              <div className="text-white font-bold">{currentCenter.name}</div>
              <div className="text-[10px] text-gray-500">
                {currentCenter.lat.toFixed(4)}°N, {currentCenter.lon.toFixed(4)}°E • Zoom {zoomLevel}x
              </div>
            </div>
          </div>
        </div>
        )}

        {/* ── MOVABLE / DRAGGABLE FLOATING PANEL: INTELLIGENCE & FLEET SIDEBAR (Image 3) ──── */}
        {showIntelPanel && (
          <aside
            style={{
              left: `${intelPos.x}px`,
              top: `${intelPos.y}px`,
              zIndex: activeWindowZ === "INTEL" ? 1200 : 1040,
            }}
            onPointerDown={() => setActiveWindowZ("INTEL")}
            className="absolute w-[390px] max-w-[calc(100vw-24px)] bg-[#131628]/95 backdrop-blur-md border border-[#232746] rounded-xl shadow-2xl flex flex-col overflow-hidden text-slate-100 transition-shadow animate-in fade-in zoom-in-95 duration-150 select-none"
          >
            {/* Movable Window Header */}
            <div
              onPointerDown={(e) => handlePanelDragStart(e, "INTEL")}
              className="p-2.5 border-b border-[#232746] flex items-center justify-between bg-[#16192E] cursor-grab active:cursor-grabbing hover:bg-[#1C203B] transition"
              title="Click and drag to move panel"
            >
              <div className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wider text-white select-none truncate">
                <GripHorizontal size={15} className="text-slate-500 hover:text-amber-400 shrink-0" />
                <Activity size={14} className="text-cyan-400 shrink-0" />
                <span className="truncate">Fleet & Detection Intelligence</span>
              </div>
              <div className="flex items-center gap-1 text-[10px] font-semibold shrink-0">
                <button
                  onClick={resetIntelPos}
                  className="p-1 text-slate-400 hover:text-cyan-400 rounded cursor-pointer transition"
                  title="Reset Position"
                >
                  <RotateCcw size={12} />
                </button>
                <button
                  onClick={() => setIsIntelMinimized((v) => !v)}
                  className="p-1 text-slate-400 hover:text-amber-400 rounded cursor-pointer transition"
                  title={isIntelMinimized ? "Expand Panel" : "Minimize Panel"}
                >
                  {isIntelMinimized ? <Square size={12} /> : <Minus size={12} />}
                </button>
                <button
                  onClick={() => setShowIntelPanel(false)}
                  className="p-1 text-slate-400 hover:text-rose-400 rounded cursor-pointer transition"
                  title="Close Intel Panel"
                >
                  <X size={13} />
                </button>
              </div>
            </div>

            {/* Window Body (collapsible) */}
            {!isIntelMinimized && (
              <div className="flex-1 flex flex-col max-h-[calc(100vh-180px)] overflow-hidden">
          <ErrorBoundary fallbackTitle="Intelligence Drawer Interruption">
            {isDetailsOpen && selectedBus ? (
              /* ── BUS EDGE NODE INSPECTOR VIEW (Phase 8) ────────────────────── */
              <div className="flex-1 flex flex-col h-full overflow-y-auto animate-in slide-in-from-right duration-200 touch-scroll">
                {/* Inspector Header */}
                <div className="p-3.5 border-b border-[#232746] flex items-center justify-between bg-[#16192E] sticky top-0 z-10">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setIsDetailsOpen(false);
                        setSelectedBus(null);
                      }}
                      className="px-2 py-1 rounded-md bg-[#1E2342] hover:bg-[#282F5A] text-slate-300 hover:text-white border border-[#2B325E] transition flex items-center gap-1 text-xs font-bold cursor-pointer"
                      title="Return to Stream"
                    >
                      <ArrowLeft size={13} />
                      <span>Stream</span>
                    </button>
                    <span className="text-slate-600">|</span>
                    <span className="font-mono font-black text-sm text-white">
                      🚌 {selectedBus.bus_id}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold font-mono border ${
                      selectedBus.AI_status === "INFERENCING"
                        ? "bg-amber-950/80 text-amber-300 border-amber-500/50 animate-pulse"
                        : "bg-emerald-950/80 text-emerald-300 border-emerald-500/50"
                    }`}>
                      AI: {selectedBus.AI_status || "ONLINE"}
                    </span>
                  </div>
                </div>

                {/* Inspector Body */}
                <div className="p-4 space-y-3.5 text-xs text-slate-200">
                  {/* Bus Identity Card */}
                  <div className="bg-[#0B0D18] border border-[#232746] rounded-xl p-3.5 space-y-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400 font-mono">
                          Transit Corridor Node
                        </div>
                        <div className="text-sm font-extrabold text-white">
                          {selectedBus.name || `Connected Bus ${selectedBus.bus_id}`}
                        </div>
                      </div>
                      <span className="px-2 py-1 rounded-lg bg-blue-950 text-blue-300 border border-blue-800/60 font-mono font-extrabold text-xs">
                        {selectedBus.route_id}
                      </span>
                    </div>

                    {/* Real-time Kinematics Grid */}
                    <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#232746]/80 text-[11px]">
                      <div>
                        <span className="text-[9px] uppercase tracking-wider text-slate-400 font-mono block">Instant Speed</span>
                        <span className="text-lg font-black text-cyan-300 font-mono">
                          {Math.round(selectedBus.speed_kmh || selectedBus.speed || 0)} <span className="text-xs font-normal">km/h</span>
                        </span>
                      </div>
                      <div>
                        <span className="text-[9px] uppercase tracking-wider text-slate-400 font-mono block">Compass Bearing</span>
                        <span className="text-lg font-black text-amber-300 font-mono flex items-center gap-1">
                          <span style={{ display: "inline-block", transform: `rotate(${selectedBus.bearing_deg || selectedBus.heading || 0}deg)` }}>⬆</span>
                          {Math.round(selectedBus.bearing_deg || selectedBus.heading || 0)}°
                        </span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-[9px] uppercase tracking-wider text-slate-400 font-mono block">GPS Coordinate</span>
                        <span className="font-mono text-slate-300">
                          📍 {(selectedBus.latitude || selectedBus.lat).toFixed(5)}°N, {(selectedBus.longitude || selectedBus.lon).toFixed(5)}°E
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Edge Sensing & AI Health Card */}
                  <div className="bg-[#0B0D18] border border-[#232746] rounded-xl p-3.5 space-y-2.5">
                    <div className="text-[10px] uppercase font-bold tracking-wider text-cyan-400 font-mono flex items-center gap-1.5">
                      <Cpu size={13} />
                      <span>Edge Hardware & AI Pipeline</span>
                    </div>
                    <div className="grid grid-cols-3 gap-1.5 text-center">
                      <div className="p-2 rounded-lg bg-[#16192E] border border-[#232746]">
                        <div className="text-[8px] uppercase text-slate-400 font-mono">Camera</div>
                        <div className={`text-[10px] font-black font-mono mt-0.5 ${
                          selectedBus.camera_status === "ACTIVE" || selectedBus.camera_status === "STREAMING" ? "text-emerald-400" : "text-amber-400"
                        }`}>
                          {selectedBus.camera_status || "ACTIVE"}
                        </div>
                      </div>
                      <div className="p-2 rounded-lg bg-[#16192E] border border-[#232746]">
                        <div className="text-[8px] uppercase text-slate-400 font-mono">AI State</div>
                        <div className={`text-[10px] font-black font-mono mt-0.5 ${
                          selectedBus.AI_status === "INFERENCING" ? "text-amber-400" : "text-emerald-400"
                        }`}>
                          {selectedBus.AI_status || "ONLINE"}
                        </div>
                      </div>
                      <div className="p-2 rounded-lg bg-[#16192E] border border-[#232746]">
                        <div className="text-[8px] uppercase text-slate-400 font-mono">Uplink</div>
                        <div className="text-[10px] font-black font-mono text-cyan-400 mt-0.5">
                          {selectedBus.connection_status || "CONNECTED"}
                        </div>
                      </div>
                    </div>
                    <div className="text-[10px] text-slate-400 pt-1 flex items-center justify-between border-t border-[#232746]/60">
                      <span>Edge Computer:</span>
                      <span className="text-white font-mono font-bold">NVIDIA Jetson Orin Nano</span>
                    </div>
                  </div>

                  {/* Recent Hazards Detected by this Bus */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-[11px] font-bold">
                      <span className="text-white uppercase tracking-wide flex items-center gap-1">
                        <AlertTriangle size={13} className="text-amber-400" />
                        <span>Hazards Reported by {selectedBus.bus_id}</span>
                      </span>
                      <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-1.5 py-0.2 rounded border border-cyan-800/40">
                        {busDetailData?.total_detections_count ?? (events.filter(e => e.bus_id === selectedBus.bus_id).length)} Total
                      </span>
                    </div>

                    {(() => {
                      const hazards = busDetailData?.recent_hazards?.length
                        ? busDetailData.recent_hazards
                        : events.filter(e => e.bus_id === selectedBus.bus_id).slice(0, 6);

                      if (!hazards || hazards.length === 0) {
                        return (
                          <div className="p-4 rounded-xl bg-[#0B0D18] border border-[#232746] text-center text-slate-400 text-xs">
                            No recent hazards reported along {selectedBus.route_id}. Transit corridor is currently clear.
                          </div>
                        );
                      }

                      return (
                        <div className="space-y-1.5 max-h-56 overflow-y-auto pr-0.5">
                          {hazards.map((h: any, idx: number) => {
                            const hType = (h.type || h.event_type || "POTHOLE").toUpperCase();
                            const sev = (h.severity || "MEDIUM").toUpperCase();
                            return (
                              <div
                                key={h.id || idx}
                                onClick={() => {
                                  setSelectedEvent(normalizeGisEvent(h));
                                  setSelectedBus(null);
                                }}
                                className="p-2 rounded-lg bg-[#0B0D18] hover:bg-[#16192E] border border-[#232746] hover:border-amber-500/50 transition cursor-pointer flex items-center justify-between text-xs"
                              >
                                <div className="flex items-center gap-2 min-w-0">
                                  <span className="text-base shrink-0">
                                    {hType.includes("POTHOLE") ? "🕳" : hType.includes("WATERLOG") ? "💧" : hType.includes("CONGESTION") ? "🚗" : "🚧"}
                                  </span>
                                  <div className="min-w-0">
                                    <div className="font-bold text-white truncate text-[11px]">
                                      {hType.replace(/_/g, " ")}
                                    </div>
                                    <div className="text-[9px] text-slate-400 font-mono">
                                      {h.timestamp ? new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Recently"}
                                    </div>
                                  </div>
                                </div>
                                <div className="text-right shrink-0">
                                  <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded font-mono block ${
                                    sev === "CRITICAL" || sev === "SEVERE" ? "bg-rose-950 text-rose-300 border border-rose-500/40" : "bg-amber-950 text-amber-300 border border-amber-500/40"
                                  }`}>
                                    {sev}
                                  </span>
                                  <span className="text-[9px] text-cyan-300 font-mono block mt-0.5">
                                    {Math.round((h.confidence ?? 0.85) * 100)}% conf
                                  </span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      );
                    })()}
                  </div>

                  {/* Action CTA: Launch AI Road Scan for this Bus */}
                  <div className="pt-2">
                    <Link
                      to={`/scan?busId=${encodeURIComponent(selectedBus.bus_id)}&routeId=${encodeURIComponent(selectedBus.route_id)}`}
                      className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-extrabold py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-blue-500/30 transition border border-blue-400/40 text-xs"
                    >
                      <Camera size={14} />
                      <span>Launch AI Road Scan for {selectedBus.bus_id}</span>
                      <ChevronRight size={14} />
                    </Link>
                  </div>
                </div>
              </div>
            ) : isDetailsOpen && selectedEvent ? (
              /* ── EVENT DETAIL INSPECTOR VIEW ───────────────────────────────── */
              <div className="flex-1 flex flex-col h-full overflow-y-auto animate-in slide-in-from-right duration-200 touch-scroll">
                {/* Inspector Header */}
                <div className="p-3.5 border-b border-[#232746] flex items-center justify-between bg-[#16192E] sticky top-0 z-10">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setIsDetailsOpen(false)}
                      className="px-2 py-1 rounded-md bg-[#1E2342] hover:bg-[#282F5A] text-slate-300 hover:text-white border border-[#2B325E] transition flex items-center gap-1 text-xs font-bold cursor-pointer"
                      title="Return to Intelligence Stream"
                    >
                      <ArrowLeft size={13} />
                      <span>Stream</span>
                    </button>
                    <button
                      onClick={() => setMobileGisTab("MAP")}
                      className="lg:hidden px-2 py-1 rounded-md bg-[#C85A17] hover:bg-[#B34D10] text-white transition flex items-center gap-1 text-xs font-bold cursor-pointer"
                      title="View on Live Map"
                    >
                      <MapPin size={13} />
                      <span>Map</span>
                    </button>
                    <span className="text-slate-600">|</span>
                    <span className="font-mono font-bold text-xs text-white truncate max-w-[100px] xs:max-w-none">
                      {selectedEvent.event_id || selectedEvent.id || "EV-0000"}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      selectedEvent.status === "CONFIRMED"
                        ? "bg-amber-100 text-amber-800 border border-amber-300"
                        : selectedEvent.status === "UNDER_REPAIR" || selectedEvent.status === "TICKET_CREATED"
                        ? "bg-purple-100 text-purple-800 border border-purple-300"
                        : selectedEvent.status === "RESOLVED"
                        ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                        : "bg-slate-100 text-slate-700 border border-slate-300"
                    }`}
                  >
                    {selectedEvent.status || "ACTIVE"}
                  </span>
                </div>

                {/* Inspector Body */}
                <div className="p-4 space-y-3.5 text-xs">
                  {/* Title & Category */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">
                        {layers.find((l) => l.id === selectedEvent.layer)?.icon || "📍"}
                      </span>
                      <div>
                        <div className="font-extrabold text-sm text-[#1F2243]">
                          {selectedEvent.event_type.replace(/_/g, " ") || "HAZARD"}
                        </div>
                        <div className="text-[11px] text-[#4F546F]">
                          {selectedEvent.gps?.road_segment || selectedEvent.gps?.address || "Monitored Transit Corridor"}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-[9px] text-[#64748B] block font-mono">AI MODEL CONFIDENCE</span>
                      <span className="text-emerald-600 font-extrabold text-sm font-mono">
                        {(((selectedEvent.ai_confidence ?? selectedEvent.confidence ?? 0.9)) * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>

                  {/* Multi-Bus Hazard Confirmation Banner (Phase 12) */}
                  {(selectedEvent.persistence_badge || (selectedEvent.independent_buses_count && selectedEvent.independent_buses_count > 1)) ? (
                    <div className="p-2.5 rounded-lg bg-blue-950/70 border border-blue-500/50 text-blue-200 flex items-center justify-between shadow-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-base">🛡️</span>
                        <div>
                          <div className="font-extrabold text-white text-xs tracking-wide">
                            {selectedEvent.persistence_badge || `CONFIRMED BY ${selectedEvent.independent_buses_count || 1} BUSES`}
                          </div>
                          <div className="text-[10px] text-blue-300 font-medium">
                            Independent consensus: {Array.isArray(selectedEvent.contributing_buses) ? selectedEvent.contributing_buses.join(", ") : (selectedEvent.contributing_buses || selectedEvent.bus_id)}
                            {selectedEvent.observation_count ? ` • ${selectedEvent.observation_count} observations` : ""}
                          </div>
                        </div>
                      </div>
                      <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded bg-blue-900/80 text-blue-300 border border-blue-400/50">
                        PERSISTENT
                      </span>
                    </div>
                  ) : null}

                  {/* Condition Certainty Advisory Banner */}
                  <div className={`p-2.5 rounded-lg border text-xs flex items-center justify-between ${
                    selectedEvent.condition_type === "POTENTIAL"
                      ? "bg-amber-950/40 border-amber-500/40 text-amber-200"
                      : "bg-emerald-950/40 border-emerald-500/40 text-emerald-200"
                  }`}>
                    <div className="flex items-center gap-2">
                      <span className="text-sm">
                        {selectedEvent.condition_type === "POTENTIAL" ? "⚠️" : "✓"}
                      </span>
                      <div>
                        <div className="font-bold">
                          {selectedEvent.condition_type === "POTENTIAL"
                            ? "Potential Condition (Advisory)"
                            : "Direct Model Detection (Confirmed)"}
                        </div>
                        <div className="text-[10px] opacity-80">
                          {selectedEvent.condition_label || (selectedEvent.condition_type === "POTENTIAL"
                            ? "Derived geospatial anomaly pattern"
                            : "Direct optical feature confirmation")}
                        </div>
                      </div>
                    </div>
                    <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border ${
                      selectedEvent.condition_type === "POTENTIAL"
                        ? "bg-amber-900/60 text-amber-300 border-amber-500/40"
                        : "bg-emerald-900/60 text-emerald-300 border-emerald-500/40"
                    }`}>
                      {selectedEvent.condition_type || "CONFIRMED"}
                    </span>
                  </div>

                  {/* Optical Evidence Frame with Dual-Mode Toggle */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="text-[10px] text-[#4F546F] font-bold uppercase tracking-wider flex items-center gap-1">
                        <Camera size={12} className="text-amber-600" />
                        <span>Optical Evidence Frame</span>
                      </div>
                      <div className="flex items-center bg-[#F1F5F9] rounded-md p-0.5 border border-[#CBD5E1] text-[10px]">
                        <button
                          onClick={() => setDrawerEvidenceMode("ANNOTATED")}
                          className={`px-2 py-0.5 rounded font-bold transition ${
                            drawerEvidenceMode === "ANNOTATED"
                              ? "bg-[#1F2243] text-white shadow-sm"
                              : "text-[#4F546F] hover:text-[#1F2243]"
                          }`}
                        >
                          AI Annotated
                        </button>
                        <button
                          onClick={() => setDrawerEvidenceMode("ORIGINAL")}
                          className={`px-2 py-0.5 rounded font-bold transition ${
                            drawerEvidenceMode === "ORIGINAL"
                              ? "bg-[#1F2243] text-white shadow-sm"
                              : "text-[#4F546F] hover:text-[#1F2243]"
                          }`}
                        >
                          Clean Original
                        </button>
                      </div>
                    </div>

                    {(() => {
                      const displayImg = drawerEvidenceMode === "ORIGINAL"
                        ? selectedEvent.original_evidence_path || selectedEvent.evidence_image_b64
                        : selectedEvent.annotated_evidence_path || selectedEvent.evidence_image_b64;

                      return displayImg ? (
                        <div className="relative rounded-xl overflow-hidden border border-[#CBD5E1] aspect-video bg-black flex items-center justify-center shadow-sm group">
                          <img
                            src={displayImg}
                            alt="Incident Evidence"
                            className="w-full h-full object-cover"
                          />
                          <span className="absolute bottom-2 left-2 bg-[#1F2243]/90 text-[10px] px-2 py-0.5 rounded text-white font-mono border border-white/20">
                            {drawerEvidenceMode === "ORIGINAL" ? "RAW FRAME" : "AI DETECTIONS"} • {selectedEvent.bus_id}
                          </span>
                          {selectedEvent.frame_number ? (
                            <span className="absolute bottom-2 right-2 bg-black/70 text-[9px] px-1.5 py-0.5 rounded text-slate-300 font-mono">
                              Frame #{selectedEvent.frame_number}
                            </span>
                          ) : null}
                        </div>
                      ) : (
                        <div className="rounded-xl border border-[#CBD5E1] p-5 bg-[#F8FAFC] flex flex-col items-center justify-center text-[#64748B] text-center">
                          <Camera size={22} className="mb-1 text-slate-400" />
                          <span className="text-[11px]">Optical Frame Stream Buffered</span>
                        </div>
                      );
                    })()}

                    {selectedEvent.evidence_clip_url && (
                      <div className="p-2 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-between text-xs text-amber-900 font-medium">
                        <div className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                          <span>10s Rolling Buffer Clip Ready</span>
                        </div>
                        <span className="text-xs text-amber-700 hover:underline font-bold cursor-pointer">
                          Play Clip ▶
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Telemetry & Metadata Grid */}
                  <div className="bg-[#F8FAFC] rounded-xl p-3 border border-[#E2E8F0] space-y-1.5 text-[11px]">
                    <div className="flex justify-between py-0.5 border-b border-[#E2E8F0]">
                      <span className="text-[#64748B]">Source Bus Node</span>
                      <span className="text-[#1F2243] font-bold font-mono">{selectedEvent.bus_id}</span>
                    </div>
                    <div className="flex justify-between py-0.5 border-b border-[#E2E8F0]">
                      <span className="text-[#64748B]">Source Feed / Video</span>
                      <span className="text-[#1F2243] font-mono text-[10px] truncate max-w-[180px]">
                        {selectedEvent.source_video || "Onboard Dashcam"}
                      </span>
                    </div>
                    {selectedEvent.track_id ? (
                      <div className="flex justify-between py-0.5 border-b border-[#E2E8F0]">
                        <span className="text-[#64748B]">ByteTracker ID</span>
                        <span className="text-[#1F2243] font-mono font-bold">Track #{selectedEvent.track_id}</span>
                      </div>
                    ) : null}
                    <div className="flex justify-between py-0.5 border-b border-[#E2E8F0]">
                      <span className="text-[#64748B]">Camera Sensor</span>
                      <span className="text-[#1F2243] font-semibold">{selectedEvent.camera_id || "FRONT"}</span>
                    </div>
                    <div className="flex justify-between py-0.5 border-b border-[#E2E8F0]">
                      <span className="text-[#64748B]">Timestamp</span>
                      <span className="text-[#1F2243] font-mono">
                        {selectedEvent.timestamp ? selectedEvent.timestamp.replace("T", " ").slice(0, 19) : "Live"}
                      </span>
                    </div>
                    <div className="flex justify-between py-0.5 border-b border-[#E2E8F0]">
                      <span className="text-[#64748B]">GPS Position</span>
                      <span className="text-[#1F2243] font-mono font-semibold">
                        {selectedEvent.gps?.lat != null ? selectedEvent.gps.lat.toFixed(4) : "—"}°N,{" "}
                        {selectedEvent.gps?.lon != null ? selectedEvent.gps.lon.toFixed(4) : "—"}°E
                      </span>
                    </div>
                    {selectedEvent.independent_buses_count && selectedEvent.independent_buses_count > 1 ? (
                      <div className="flex justify-between py-0.5 border-b border-[#E2E8F0]">
                        <span className="text-[#2563EB] font-semibold">Independent Observations</span>
                        <span className="text-[#1D4ED8] font-mono font-bold">
                          {selectedEvent.independent_buses_count} Buses ({selectedEvent.observation_count || selectedEvent.independent_buses_count} detections)
                        </span>
                      </div>
                    ) : null}
                    {selectedEvent.last_detected_at ? (
                      <div className="flex justify-between py-0.5 border-b border-[#E2E8F0]">
                        <span className="text-[#64748B]">Last Detected At</span>
                        <span className="text-[#1F2243] font-mono">
                          {new Date(selectedEvent.last_detected_at).toLocaleString()}
                        </span>
                      </div>
                    ) : null}
                    <div className="flex justify-between py-1 bg-amber-50/80 px-2 rounded border border-amber-300/80 font-bold text-amber-900">
                      <span>Maintenance Ticket:</span>
                      <span className="font-mono">
                        {selectedEvent.ticket_id
                          ? `${selectedEvent.ticket_id} (${selectedEvent.maintenance_ticket_status || 'ASSIGNED'})`
                          : "None (Pending Dispatch)"}
                      </span>
                    </div>
                  </div>

                  {/* Sensor Diagnostics */}
                  {selectedEvent.details && typeof selectedEvent.details === "object" && Object.keys(selectedEvent.details).length > 0 && (
                    <div className="space-y-1">
                      <div className="text-[10px] text-[#4F546F] font-bold uppercase tracking-wider">
                        Sensor Signals & Anomaly Telemetry
                      </div>
                      <div className="bg-[#F8FAFC] p-2 rounded-lg border border-[#E2E8F0] text-[10px] text-[#4F546F] space-y-0.5">
                        {Object.entries(selectedEvent.details).map(([k, v]) => (
                          <div key={k} className="flex justify-between">
                            <span className="capitalize text-[#64748B]">{k.replace(/_/g, " ")}:</span>
                            <span className="text-[#1F2243] font-mono font-semibold">{String(v)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Lifecycle State Actions */}
                  <div className="pt-2 border-t border-[#E2E8F0] space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-[#4F546F] font-bold uppercase tracking-wider">
                        Lifecycle State Machine
                      </span>
                      <span className="text-[10px] font-mono font-bold text-amber-700">
                        {(selectedEvent.status || "UNVERIFIED").toUpperCase()}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      {(selectedEvent.status === "UNVERIFIED" || selectedEvent.status === "ACTIVE") && (
                        <>
                          <button
                            onClick={() => handleEventAction("CONFIRM")}
                            className="py-2 px-2.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-bold flex items-center justify-center gap-1.5 transition shadow-sm"
                          >
                            <CheckCircle2 size={13} />
                            <span>Confirm Event</span>
                          </button>
                          <button
                            onClick={() => handleEventAction("DISMISS")}
                            className="py-2 px-2.5 rounded-lg bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#4F546F] font-bold flex items-center justify-center gap-1.5 transition border border-[#CBD5E1]"
                          >
                            <XCircle size={13} />
                            <span>Dismiss False</span>
                          </button>
                        </>
                      )}

                      {selectedEvent.status === "CONFIRMED" && (
                        <>
                          <button
                            onClick={() => handleEventAction("DISPATCH_REPAIR")}
                            className="py-2 px-2.5 rounded-lg bg-[#1F2243] hover:bg-[#2E335C] text-white font-bold flex items-center justify-center gap-1.5 transition shadow-sm"
                          >
                            <Wrench size={13} className="text-amber-400" />
                            <span>Dispatch Repair</span>
                          </button>
                          <button
                            onClick={() => handleEventAction("DISMISS")}
                            className="py-2 px-2.5 rounded-lg bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#4F546F] font-bold flex items-center justify-center gap-1.5 transition border border-[#CBD5E1]"
                          >
                            <XCircle size={13} />
                            <span>Dismiss</span>
                          </button>
                        </>
                      )}

                      {(selectedEvent.status === "UNDER_REPAIR" || selectedEvent.status === "TICKET_CREATED") && (
                        <>
                          <button
                            onClick={() => handleEventAction("RESOLVE")}
                            className="py-2 px-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold flex items-center justify-center gap-1.5 transition shadow-sm"
                          >
                            <CheckCircle2 size={13} />
                            <span>Verify & Resolve</span>
                          </button>
                          <button
                            onClick={() => handleEventAction("DISMISS")}
                            className="py-2 px-2.5 rounded-lg bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#4F546F] font-bold flex items-center justify-center gap-1.5 transition border border-[#CBD5E1]"
                          >
                            <XCircle size={13} />
                            <span>Dismiss</span>
                          </button>
                        </>
                      )}

                      {(selectedEvent.status === "RESOLVED" || selectedEvent.status === "DISMISSED") && (
                        <button
                          onClick={() => handleEventAction("REOPEN")}
                          className="col-span-2 py-2 px-3 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-bold flex items-center justify-center gap-1.5 transition shadow-sm"
                        >
                          <RefreshCw size={13} />
                          <span>Reopen (Watchdog Alert)</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* ── MAIN INTELLIGENCE FEED ──── */
              <div className="flex-1 flex flex-col h-full overflow-y-auto p-3.5 space-y-3.5 bg-[#131628] touch-scroll">
                {/* 1. TOP CONSENSUS & HARDWARE KPI CARDS */}
                <div className="grid grid-cols-2 gap-2.5">
                  {/* Multi-Bus Consensus Card */}
                  <div className="bg-[#0B0D18] border border-[#232746] rounded-xl p-3 shadow-sm hover:border-[#3A4378] transition">
                    <div className="text-[10px] font-bold font-mono uppercase text-slate-400 tracking-wide flex items-center justify-between">
                      <span>Multi-Bus Consensus</span>
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    </div>
                    <div className="mt-1 flex items-baseline justify-between">
                      <span className="text-xl font-black text-white">98.4%</span>
                      <span className="text-[9px] font-bold text-emerald-400 bg-emerald-950/80 px-1.5 py-0.2 rounded border border-emerald-500/30">
                        Met
                      </span>
                    </div>
                    <div className="mt-2 w-full bg-[#1C203B] h-1.5 rounded-full overflow-hidden">
                      <div className="bg-gradient-to-r from-amber-500 to-emerald-400 h-full rounded-full" style={{ width: "98.4%" }} />
                    </div>
                    <div className="mt-1.5 text-[9px] text-slate-400 truncate">
                      Temporal Threshold Met
                    </div>
                  </div>

                  {/* Active Edge Nodes Card */}
                  <div className="bg-[#0B0D18] border border-[#232746] rounded-xl p-3 shadow-sm hover:border-[#3A4378] transition">
                    <div className="text-[10px] font-bold font-mono uppercase text-slate-400 tracking-wide flex items-center justify-between">
                      <span>Active Edge Nodes</span>
                      <Cpu size={12} className="text-cyan-400" />
                    </div>
                    <div className="mt-1 flex items-baseline justify-between">
                      <span className="text-xl font-black text-white">
                        42 <span className="text-xs text-slate-400 font-normal">of 48</span>
                      </span>
                      <span className="text-[9px] font-bold text-cyan-400 bg-cyan-950/80 px-1.5 py-0.2 rounded border border-cyan-500/30">
                        Online
                      </span>
                    </div>
                    <div className="mt-2 w-full bg-[#1C203B] h-1.5 rounded-full overflow-hidden">
                      <div className="bg-cyan-500 h-full rounded-full" style={{ width: "87.5%" }} />
                    </div>
                    <div className="mt-1.5 text-[9px] text-slate-400 truncate">
                      Jetson / RPi Cluster
                    </div>
                  </div>
                </div>

                {/* 2. DETECTION LIFECYCLE STEPPER */}
                <div className="bg-[#0B0D18] border border-[#232746] rounded-xl p-3 shadow-sm space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-extrabold font-mono uppercase tracking-wider text-white">
                      Detection Lifecycle
                    </span>
                    <span className="text-[10px] font-semibold text-amber-400 bg-amber-950/80 px-2 py-0.5 rounded-full border border-amber-500/30 font-mono">
                      12 awaiting dispatch
                    </span>
                  </div>

                  {/* 4 Steps Horizontal Stepper */}
                  <div className="grid grid-cols-4 gap-1 pt-1">
                    {/* Step 1: Unverified */}
                    <div
                      className="flex flex-col items-center text-center cursor-pointer group"
                      onClick={() => setFilterStatus("UNVERIFIED")}
                      title="Filter: Unverified"
                    >
                      <div className="w-8 h-8 rounded-full bg-[#16192E] border-2 border-[#2B325E] text-slate-300 flex items-center justify-center font-bold text-xs shadow-sm group-hover:border-amber-400">
                        01
                      </div>
                      <span className="text-[10px] font-semibold text-slate-400 mt-1 truncate max-w-full">
                        Unverified
                      </span>
                    </div>

                    {/* Step 2: Confirmed */}
                    <div
                      className="flex flex-col items-center text-center cursor-pointer group"
                      onClick={() => setFilterStatus("CONFIRMED")}
                      title="Filter: Confirmed"
                    >
                      <div className="w-8 h-8 rounded-full bg-amber-500/20 border-2 border-amber-400 text-amber-400 flex items-center justify-center font-bold text-xs shadow-sm">
                        02
                      </div>
                      <span className="text-[10px] font-semibold text-amber-400 mt-1 truncate max-w-full font-bold">
                        Confirmed
                      </span>
                    </div>

                    {/* Step 3: Under Repair */}
                    <div
                      className="flex flex-col items-center text-center cursor-pointer group"
                      onClick={() => setFilterStatus("UNDER_REPAIR")}
                      title="Filter: Under Repair"
                    >
                      <div className="w-8 h-8 rounded-full bg-[#16192E] border-2 border-[#2B325E] text-slate-300 flex items-center justify-center font-bold text-xs shadow-sm group-hover:border-purple-400">
                        03
                      </div>
                      <span className="text-[10px] font-semibold text-slate-400 mt-1 truncate max-w-full">
                        Under Repair
                      </span>
                    </div>

                    {/* Step 4: Resolved */}
                    <div
                      className="flex flex-col items-center text-center cursor-pointer group"
                      onClick={() => setFilterStatus("RESOLVED")}
                      title="Filter: Resolved"
                    >
                      <div className="w-8 h-8 rounded-full bg-[#16192E] border-2 border-[#2B325E] text-slate-300 flex items-center justify-center font-bold text-xs shadow-sm group-hover:border-emerald-400">
                        04
                      </div>
                      <span className="text-[10px] font-semibold text-slate-400 mt-1 truncate max-w-full">
                        Resolved
                      </span>
                    </div>
                  </div>
                </div>

                {/* 3. RECENT DETECTIONS FEED */}
                <div className="space-y-2 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-extrabold font-mono uppercase tracking-wider text-white">
                      Recent Detections
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {filteredEvents.length} Plotted
                    </span>
                  </div>

                  <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                    {filteredEvents.slice(0, 8).map((ev, idx) => {
                      const isSelected = selectedEvent?.event_id === ev.event_id;
                      const confPct = ((ev.confidence ?? 0.9) * 100).toFixed(0);
                      const isRoadDamage = ev.event_type.includes("POTHOLE") || ev.event_type.includes("DAMAGE");
                      const isCongestion = ev.event_type.includes("CONGESTION");

                      // Relative time presentation ("02m ago", "05m ago")
                      const timeLabel = idx === 0 ? "02m ago" : idx === 1 ? "05m ago" : idx === 2 ? "11m ago" : `${idx * 4}m ago`;

                      return (
                        <div
                          key={ev.event_id}
                          onClick={() => {
                            setSelectedEvent(ev);
                            setIsDetailsOpen(true);
                            setMapFlyToTarget({ lat: ev.gps.lat, lon: ev.gps.lon, zoom: 15, label: ev.event_id });
                          }}
                          className={`p-2.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between group ${
                            isSelected
                              ? "bg-[#1B203B] border-amber-400 shadow-md ring-1 ring-amber-400/40"
                              : "bg-[#0B0D18] border-[#232746] hover:bg-[#161A32] hover:border-[#384074]"
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <div
                              className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm shrink-0 ${
                                isRoadDamage
                                  ? "bg-amber-950/80 text-amber-400 border border-amber-500/30"
                                  : isCongestion
                                  ? "bg-rose-950/80 text-rose-400 border border-rose-500/30"
                                  : "bg-sky-950/80 text-sky-400 border border-sky-500/30"
                              }`}
                            >
                              {isRoadDamage ? (
                                <Wrench size={15} />
                              ) : isCongestion ? (
                                <Flame size={15} />
                              ) : (
                                <AlertTriangle size={15} />
                              )}
                            </div>
                            <div className="min-w-0">
                              <div className="text-xs font-bold text-white truncate group-hover:text-amber-400">
                                {ev.event_type.replace(/_/g, " ")}
                              </div>
                              <div className="text-[10px] text-slate-400 truncate">
                                {ev.gps?.road_segment || ev.gps?.address || "Monitored Corridor"} •{" "}
                                <span className="font-mono text-[9px] text-slate-500">{timeLabel}</span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0 pl-2">
                            <span className="text-[10px] font-bold font-mono px-1.5 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-500/30">
                              {confPct}%
                            </span>
                            <ChevronRight
                              size={14}
                              className="text-slate-500 group-hover:text-amber-400 transition-transform group-hover:translate-x-0.5"
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* 4. FULL-WIDTH AUTOMATED WORK ORDER BUTTON */}
                <div className="pt-2 mt-auto border-t border-[#232746]">
                  <button
                    onClick={handleGenerateWorkOrder}
                    className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-[#EA580C] to-[#F97316] hover:from-[#C2410C] hover:to-[#EA580C] text-white font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-orange-600/30 active:scale-[0.98] transition-all cursor-pointer"
                  >
                    <span>⚡</span>
                    <span>Automated Work Order: Generate (WO-2026)</span>
                  </button>
                </div>
              </div>
            )}
          </ErrorBoundary>
              </div>
            )}
          </aside>
        )}
      </div>
    </div>
  );
};

export default GisCommandCenter;
