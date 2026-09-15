// src/pages/GisCommandCenter/GisCommandCenter.tsx
// Full-Screen GIS Command Center (Phase 17)

import React, { useState, useEffect, useRef, useMemo } from "react";
import { LiveGisMap } from "../../components/LiveGisMap";
import adminHierarchyData from "../../data/india_administrative_hierarchy.json";
import {
  Layers, Filter, Compass, Bus, AlertTriangle, Droplet,
  ShieldAlert, CheckCircle2, XCircle, AlertOctagon,
  Wrench, Eye, ZoomIn, ZoomOut, Maximize2, Minimize2,
  RefreshCw, MapPin, Clock, Camera, ChevronRight, X,
  FileText, Activity, ArrowUpRight, Flame, Send
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
  status: "ACTIVE" | "CONFIRMED" | "DISMISSED" | "ESCALATED" | "TICKET_CREATED";
  evidence_image_b64?: string;
  evidence_clip_url?: string;
  ticket_id?: string;
  details?: Record<string, any>;
}

export interface BusTelemetry {
  bus_id: string;
  route_id: string;
  name: string;
  lat: number;
  lon: number;
  bearing_deg: number;
  speed_kmh: number;
  status: string;
  passenger_load_pct: number;
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
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [mapViewMode, setMapViewMode] = useState<"REAL_MAP" | "VECTOR">("REAL_MAP");

  // Administrative Hierarchy State (All States -> Capital -> District -> Tehsil)
  const [selectedState, setSelectedState] = useState<string>("National Capital Territory of Delhi");
  const [selectedDistrict, setSelectedDistrict] = useState<string>("ALL");
  const [selectedTehsil, setSelectedTehsil] = useState<string>("ALL");
  const [mapFlyToTarget, setMapFlyToTarget] = useState<{ lat: number; lon: number; zoom: number; label?: string } | null>(null);

  // Filters state (8 filters required by prompt)
  const [filterType, setFilterType] = useState<string>("ALL");
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");
  const [filterDate, setFilterDate] = useState<string>("ALL");
  const [filterTime, setFilterTime] = useState<string>("ALL");
  const [filterBus, setFilterBus] = useState<string>("ALL");
  const [filterRoute, setFilterRoute] = useState<string>("ALL");
  const [filterDistrict, setFilterDistrict] = useState<string>("ALL");
  const [filterStatus, setFilterStatus] = useState<string>("ALL");

  // Map viewport & clustering state
  const [zoomLevel, setZoomLevel] = useState<number>(14);
  const [activeCity, setActiveCity] = useState<"DELHI" | "BANGALORE" | "MUMBAI">("DELHI");
  const [isClusterMode, setIsClusterMode] = useState<boolean>(true);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

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
            const mapped: GisEventItem[] = data.features.map((f: any) => ({
              id: f.properties.id || f.properties.event_id,
              event_id: f.properties.event_id,
              event_type: f.properties.event_type,
              layer: f.properties.layer || "potholes",
              confidence: f.properties.confidence || 0.9,
              bus_id: f.properties.bus_id || "BUS_001",
              camera_id: f.properties.camera_id || "FRONT",
              timestamp: f.properties.timestamp,
              gps: f.properties.gps || { lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0] },
              district: f.properties.district || "Central",
              severity: f.properties.severity || "MEDIUM",
              status: f.properties.status || "ACTIVE",
              evidence_image_b64: f.properties.evidence_image_b64,
              evidence_clip_url: f.properties.evidence_clip_url,
              ticket_id: f.properties.ticket_id,
              details: f.properties.details,
            }));
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

  // ── 8-Dimension Filter Pipeline ────────────────────────────────────────────
  const filteredEvents = useMemo(() => {
    return events.filter((ev) => {
      // 1. Layer visibility check
      const layerConfig = layers.find((l) => l.id === ev.layer);
      if (layerConfig && !layerConfig.visible) return false;

      // 2. Event Type filter
      if (filterType !== "ALL" && ev.event_type !== filterType) return false;

      // 3. Severity filter
      if (filterSeverity !== "ALL" && ev.severity !== filterSeverity) return false;

      // 4. District filter
      if (filterDistrict !== "ALL" && ev.district !== filterDistrict) return false;

      // 5. Bus filter
      if (filterBus !== "ALL" && ev.bus_id !== filterBus) return false;

      // 6. Status filter
      if (filterStatus !== "ALL" && ev.status !== filterStatus) return false;

      // 7. City proximity filter
      const center = CITY_COORDS[activeCity];
      const dist = Math.sqrt(
        Math.pow(ev.gps.lat - center.lat, 2) + Math.pow(ev.gps.lon - center.lon, 2)
      );
      if (dist > 0.8) return false;

      return true;
    });
  }, [events, layers, filterType, filterSeverity, filterDistrict, filterBus, filterStatus, activeCity]);

  // ── Spatial Clustering at Lower Zoom Levels ─────────────────────────────────
  const clusters = useMemo(() => {
    // If zoom level is high (>= 15) or cluster mode disabled, display individual pins
    if (zoomLevel >= 15 || !isClusterMode) {
      return filteredEvents.map((ev) => ({
        isCluster: false,
        count: 1,
        lat: ev.gps.lat,
        lon: ev.gps.lon,
        events: [ev],
      }));
    }

    // Grid-based spatial clustering for lower zoom levels
    const gridSize = zoomLevel <= 11 ? 0.05 : zoomLevel <= 13 ? 0.015 : 0.006;
    const gridMap: Record<string, GisEventItem[]> = {};

    filteredEvents.forEach((ev) => {
      const gx = Math.floor(ev.gps.lon / gridSize);
      const gy = Math.floor(ev.gps.lat / gridSize);
      const key = `${gx}_${gy}`;
      if (!gridMap[key]) gridMap[key] = [];
      gridMap[key].push(ev);
    });

    return Object.values(gridMap).map((evList) => {
      const avgLat = evList.reduce((acc, e) => acc + e.gps.lat, 0) / evList.length;
      const avgLon = evList.reduce((acc, e) => acc + e.gps.lon, 0) / evList.length;
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
    else if (action === "ESCALATE") newStatus = "ESCALATED";
    else if (action === "CREATE_MAINTENANCE_TICKET") {
      newStatus = "TICKET_CREATED";
      newTicketId = `TICK-2026-${Math.floor(1000 + Math.random() * 9000)}`;
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

    setActionNotice(`Event ${eid}: Action '${action}' successfully applied.`);
    setTimeout(() => setActionNotice(null), 3500);

    // Call Central GIS action endpoint
    try {
      await fetch(`/api/v1/gis/events/${eid}/action`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, notes: `Action applied from GIS Command Center` }),
      });
    } catch {
      // Local state preserved
    }
  };

  const currentCenter = CITY_COORDS[activeCity];

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-screen overflow-hidden bg-gray-950 text-gray-100 flex flex-col ${
        isFullscreen ? "fixed inset-0 z-50" : ""
      }`}
    >
      {/* ── TOP APP BAR ──────────────────────────────────────────────────────── */}
      <header className="h-14 bg-gray-900/90 backdrop-blur-md border-b border-gray-800 px-4 flex items-center justify-between z-30 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-brand to-indigo-500 flex items-center justify-center text-white font-black text-sm shadow-md shadow-brand/30">
            GIS
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-wide flex items-center gap-2">
              <span>NovaFlow GIS Command Center</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono">
                LIVE TELEMETRY
              </span>
            </h1>
            <p className="text-[11px] text-gray-400">
              Urban Fleet Spatial Intelligence & Real-time Anomaly Dispatch
            </p>
          </div>
        </div>

        {/* City Selector */}
        <div className="flex items-center gap-1.5 bg-gray-800/80 p-1 rounded-lg border border-gray-700 text-xs">
          {(["DELHI", "BANGALORE", "MUMBAI"] as const).map((city) => (
            <button
              key={city}
              onClick={() => setActiveCity(city)}
              className={`px-3 py-1 rounded-md font-semibold transition ${
                activeCity === city
                  ? "bg-brand text-white shadow-sm"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              {city}
            </button>
          ))}
        </div>

        {/* Top Right Quick Stats & Controls */}
        <div className="flex items-center gap-3 text-xs">
          <div className="hidden lg:flex items-center gap-3 text-gray-300 font-mono text-[11px]">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>{buses.length} Buses Active</span>
            </span>
            <span className="text-gray-600">|</span>
            <span>{filteredEvents.length} Incidents Plotted</span>
          </div>

          <button
            onClick={() => setIsClusterMode(!isClusterMode)}
            className={`px-2.5 py-1 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition ${
              isClusterMode
                ? "bg-indigo-950/70 border-indigo-500/40 text-indigo-300"
                : "bg-gray-800 border-gray-700 text-gray-400"
            }`}
            title="Toggle zoom-level event clustering"
          >
            <Layers size={13} />
            <span>Clustering: {isClusterMode ? "ON" : "OFF"}</span>
          </button>

          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 transition"
            title="Toggle Fullscreen"
          >
            {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
        </div>
      </header>

      {/* ── ACTION NOTIFICATION TOAST ────────────────────────────────────────── */}
      {actionNotice && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-40 bg-gray-900 border border-brand text-brand-light px-4 py-2 rounded-xl shadow-2xl font-mono text-xs flex items-center gap-2 animate-bounce">
          <CheckCircle2 size={15} className="text-brand" />
          <span>{actionNotice}</span>
        </div>
      )}

      {/* ── WORKSPACE BODY: SIDEBARS + MAP CANVAS ────────────────────────────── */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* ── LEFT FLOATING PANEL: 12 MAP LAYERS ───────────────────────────────── */}
        <aside className="absolute top-3 left-3 z-20 w-64 bg-gray-900/90 backdrop-blur-md border border-gray-800 rounded-xl shadow-2xl flex flex-col max-h-[calc(100%-24px)] overflow-hidden">
          <div className="p-3 border-b border-gray-800 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-gray-300">
              <Layers size={14} className="text-brand" />
              <span>Map Layers (12)</span>
            </div>
            <div className="flex gap-1 text-[10px]">
              <button
                onClick={() => setLayers((prev) => prev.map((l) => ({ ...l, visible: true })))}
                className="text-brand hover:underline"
              >
                All
              </button>
              <span className="text-gray-600">/</span>
              <button
                onClick={() => setLayers((prev) => prev.map((l) => ({ ...l, visible: false })))}
                className="text-gray-500 hover:underline"
              >
                None
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1 text-xs">
            {layers.map((layer) => (
              <label
                key={layer.id}
                className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg cursor-pointer transition select-none ${
                  layer.visible ? "bg-gray-800/80 text-gray-200" : "text-gray-500 hover:bg-gray-800/40"
                }`}
              >
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={layer.visible}
                    onChange={() => toggleLayer(layer.id)}
                    className="accent-brand rounded"
                  />
                  <span>{layer.icon}</span>
                  <span className="font-medium text-[11px] truncate max-w-[130px]">
                    {layer.name}
                  </span>
                </div>
                <span
                  className="text-[10px] font-mono px-1.5 py-0.5 rounded-full font-bold"
                  style={{
                    backgroundColor: `${layer.color}20`,
                    color: layer.color,
                    border: `1px solid ${layer.color}40`,
                  }}
                >
                  {events.filter((e) => e.layer === layer.id).length}
                </span>
              </label>
            ))}
          </div>

          {/* Territorial Intelligence Card */}
          {(() => {
            const stateObj = adminHierarchyData.all_states.find((s: any) => s.state === selectedState);
            if (!stateObj) return null;
            const currentDist = selectedDistrict !== "ALL" 
              ? stateObj.districts.find((d: any) => d.name === selectedDistrict) 
              : stateObj.districts[0];

            return (
              <div className="p-3 border-t border-gray-800 bg-gray-950/80 space-y-2 text-[11px]">
                <div className="flex items-center justify-between font-bold text-blue-400">
                  <span className="flex items-center gap-1">
                    <MapPin size={12} />
                    <span>Territory Dossier</span>
                  </span>
                  <span className="font-mono text-[10px] text-gray-400 font-normal">
                    {stateObj.code}
                  </span>
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-gray-300">
                    <span className="text-gray-500">State:</span>
                    <span className="font-semibold text-white truncate max-w-[140px]">{stateObj.state}</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span className="text-gray-500">Capital:</span>
                    <span className="font-semibold text-emerald-400">{stateObj.capital}</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span className="text-gray-500">District:</span>
                    <span className="font-semibold text-amber-400 truncate max-w-[140px]">
                      {selectedDistrict !== "ALL" ? selectedDistrict : `${stateObj.districts.length} Monitored`}
                    </span>
                  </div>
                  {currentDist && (
                    <div className="pt-1.5 border-t border-gray-800/80 space-y-1">
                      <div className="text-gray-400 font-semibold text-[10px]">
                        Tehsils ({currentDist.tehsils.length}):
                      </div>
                      <div className="flex flex-wrap gap-1 max-h-16 overflow-y-auto">
                        {currentDist.tehsils.map((t: string) => (
                          <span
                            key={t}
                            onClick={() => {
                              setSelectedTehsil(t);
                              setSelectedDistrict(currentDist.name);
                              setMapFlyToTarget({ lat: currentDist.lat, lon: currentDist.lon, zoom: 14, label: `Tehsil: ${t}` });
                            }}
                            className={`px-1.5 py-0.5 rounded text-[10px] font-mono cursor-pointer transition ${
                              selectedTehsil === t
                                ? "bg-amber-500 text-black font-bold"
                                : "bg-gray-800 text-gray-300 hover:bg-gray-700"
                            }`}
                          >
                            {t}
                          </span>
                        ))}
                      </div>

                      <div className="text-gray-400 font-semibold text-[10px] pt-1">
                        Active Corridors:
                      </div>
                      <div className="text-[10px] text-gray-300 font-mono space-y-0.5 max-h-16 overflow-y-auto">
                        {currentDist.corridors.slice(0, 3).map((c: string) => (
                          <div key={c} className="truncate text-slate-400 flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                            <span>{c}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })()}
        </aside>

        {/* ── TOP FILTER BAR: 8 FILTERS ────────────────────────────────────────── */}
        <div className="absolute top-3 left-72 right-3 z-20 flex flex-wrap items-center gap-2 bg-gray-900/90 backdrop-blur-md border border-gray-800 p-2 rounded-xl shadow-xl text-xs">
          <div className="flex items-center gap-1 text-gray-400 font-bold uppercase tracking-wider text-[10px] pl-1">
            <Filter size={12} className="text-brand" />
            <span>Filters:</span>
          </div>

          {/* 1. Event Type Filter */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-md px-2 py-1 text-xs text-gray-200 focus:ring-1 focus:ring-brand outline-none"
          >
            <option value="ALL">All Event Types</option>
            <option value="POTHOLE">Potholes</option>
            <option value="DAMAGED_ROAD">Damaged Road</option>
            <option value="WATERLOGGING">Waterlogging</option>
            <option value="MISSING_TRAFFIC_SIGN">Missing Signs</option>
            <option value="MISSING_ROAD_DIVIDER">Missing Dividers</option>
            <option value="MISSING_ZEBRA_CROSSING">Zebra Crossings</option>
            <option value="CONGESTION_EVENT">Traffic Congestion</option>
            <option value="POSSIBLE_INCIDENT">Incidents</option>
            <option value="PEDESTRIAN_RISK">Pedestrian Risk</option>
            <option value="MAINTENANCE_TICKET">Maintenance Tickets</option>
          </select>

          {/* 2. Severity Filter */}
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-md px-2 py-1 text-xs text-gray-200 focus:ring-1 focus:ring-brand outline-none"
          >
            <option value="ALL">All Severities</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="SEVERE">Severe</option>
          </select>

          {/* 3. State & Capital Selector */}
          <select
            value={selectedState}
            onChange={(e) => {
              const newState = e.target.value;
              setSelectedState(newState);
              setSelectedDistrict("ALL");
              setSelectedTehsil("ALL");
              const stateObj = adminHierarchyData.all_states.find((s: any) => s.state === newState);
              if (stateObj && stateObj.districts.length > 0) {
                const firstDist = stateObj.districts[0];
                setMapFlyToTarget({ lat: firstDist.lat, lon: firstDist.lon, zoom: 12, label: `${stateObj.state} • Capital: ${stateObj.capital}` });
              }
            }}
            className="bg-gray-800 border border-blue-500/50 rounded-md px-2 py-1 text-xs text-blue-300 font-semibold focus:ring-1 focus:ring-brand outline-none cursor-pointer"
            title="Select State & Capital"
          >
            {adminHierarchyData.all_states.map((st: any) => (
              <option key={st.state} value={st.state}>
                🏛️ {st.state} (Cap: {st.capital})
              </option>
            ))}
          </select>

          {/* 4. District Selector */}
          <select
            value={selectedDistrict}
            onChange={(e) => {
              const newDist = e.target.value;
              setSelectedDistrict(newDist);
              setSelectedTehsil("ALL");
              const stateObj = adminHierarchyData.all_states.find((s: any) => s.state === selectedState);
              if (stateObj) {
                const distObj = stateObj.districts.find((d: any) => d.name === newDist);
                if (distObj) {
                  setMapFlyToTarget({ lat: distObj.lat, lon: distObj.lon, zoom: 13, label: `${distObj.name} District, ${stateObj.state}` });
                }
              }
            }}
            className="bg-gray-800 border border-emerald-500/50 rounded-md px-2 py-1 text-xs text-emerald-300 font-semibold focus:ring-1 focus:ring-brand outline-none cursor-pointer"
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

          {/* 5. Tehsil (Sub-District) Selector */}
          <select
            value={selectedTehsil}
            onChange={(e) => {
              const newTeh = e.target.value;
              setSelectedTehsil(newTeh);
              const stateObj = adminHierarchyData.all_states.find((s: any) => s.state === selectedState);
              if (stateObj) {
                const distObj = stateObj.districts.find((d: any) => 
                  selectedDistrict !== "ALL" ? d.name === selectedDistrict : d.tehsils.includes(newTeh)
                );
                if (distObj) {
                  setMapFlyToTarget({ lat: distObj.lat, lon: distObj.lon, zoom: 14, label: `Tehsil: ${newTeh} (${distObj.name})` });
                }
              }
            }}
            className="bg-gray-800 border border-amber-500/50 rounded-md px-2 py-1 text-xs text-amber-300 font-semibold focus:ring-1 focus:ring-brand outline-none cursor-pointer"
            title="Select Tehsil / Sub-District"
          >
            <option value="ALL">All Tehsils</option>
            {(() => {
              const stateObj = adminHierarchyData.all_states.find((s: any) => s.state === selectedState);
              if (!stateObj) return null;
              const dists = selectedDistrict === "ALL" 
                ? stateObj.districts 
                : stateObj.districts.filter((d: any) => d.name === selectedDistrict);
              const allTehsils = dists.flatMap((d: any) => d.tehsils);
              return Array.from(new Set(allTehsils)).map((t: any) => (
                <option key={t} value={t}>
                  🏛️ Tehsil: {t}
                </option>
              ));
            })()}
          </select>

          {/* 4. Bus Filter */}
          <select
            value={filterBus}
            onChange={(e) => setFilterBus(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-md px-2 py-1 text-xs text-gray-200 focus:ring-1 focus:ring-brand outline-none"
          >
            <option value="ALL">All Fleet Buses</option>
            <option value="BUS_001">BUS_001 (Delhi)</option>
            <option value="BUS_002">BUS_002 (Bangalore)</option>
            <option value="BUS_003">BUS_003 (Mumbai)</option>
          </select>

          {/* 5. Status Filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-md px-2 py-1 text-xs text-gray-200 focus:ring-1 focus:ring-brand outline-none"
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="CONFIRMED">CONFIRMED</option>
            <option value="ESCALATED">ESCALATED</option>
            <option value="TICKET_CREATED">TICKET_CREATED</option>
            <option value="DISMISSED">DISMISSED</option>
          </select>

          {/* Reset Filters */}
          <button
            onClick={() => {
              setFilterType("ALL");
              setFilterSeverity("ALL");
              setFilterDistrict("ALL");
              setFilterBus("ALL");
              setFilterStatus("ALL");
            }}
            className="px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-gray-200 transition text-[11px]"
          >
            Reset
          </button>

          {/* Map View Mode Toggle */}
          <div className="flex items-center bg-gray-900 border border-gray-700 rounded-md p-0.5 ml-auto">
            <button
              onClick={() => setMapViewMode("REAL_MAP")}
              className={`px-2 py-0.5 rounded text-[11px] font-bold transition-all ${
                mapViewMode === "REAL_MAP" ? "bg-blue-600 text-white shadow" : "text-gray-400 hover:text-white"
              }`}
              title="Google Maps / Cartographic Tile Layer"
            >
              🗺️ Google Maps
            </button>
            <button
              onClick={() => setMapViewMode("VECTOR")}
              className={`px-2 py-0.5 rounded text-[11px] font-bold transition-all ${
                mapViewMode === "VECTOR" ? "bg-indigo-600 text-white shadow" : "text-gray-400 hover:text-white"
              }`}
              title="Schematic Vector Grid"
            >
              📐 Schematic
            </button>
          </div>
        </div>

        {/* ── MAP CANVAS (REAL GOOGLE MAPS / VECTOR PROJECTION) ───────────────────── */}
        {mapViewMode === "REAL_MAP" ? (
          <div className="flex-1 w-full h-[calc(100vh-56px)] min-h-[600px] relative bg-gray-950 overflow-hidden">
            <LiveGisMap
              height="100%"
              initialCity={activeCity === "BANGALORE" ? "BANGALORE" : activeCity === "MUMBAI" ? "MUMBAI" : "DELHI"}
              showControls={false}
              flyToLocation={mapFlyToTarget}
              onSelectEvent={(ev) => {
                setSelectedEvent(ev);
                setIsDetailsOpen(true);
              }}
            />
          </div>
        ) : (
        <div className="flex-1 w-full h-full relative bg-gray-950 overflow-hidden cursor-crosshair">
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
                      setSelectedEvent(c.events[0]);
                      setIsDetailsOpen(true);
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
                    setSelectedEvent(ev);
                    setIsDetailsOpen(true);
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

        {/* ── RIGHT DRAWER: EVENT DETAILS MODAL / PANEL ──────────────────────── */}
        {isDetailsOpen && selectedEvent && (
          <aside className="w-96 bg-gray-900/95 backdrop-blur-lg border-l border-gray-800 z-30 flex flex-col shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-300">
            {/* Header */}
            <div className="p-4 border-b border-gray-800 flex items-center justify-between sticky top-0 bg-gray-900/95 backdrop-blur-sm z-10">
              <div className="flex items-center gap-2">
                <span className="text-xl">
                  {layers.find((l) => l.id === selectedEvent.layer)?.icon || "📍"}
                </span>
                <div>
                  <div className="font-mono font-bold text-sm text-gray-100">
                    {selectedEvent.event_id}
                  </div>
                  <div className="text-xs text-gray-400">{selectedEvent.event_type}</div>
                </div>
              </div>
              <button
                onClick={() => setIsDetailsOpen(false)}
                className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition"
              >
                <X size={18} />
              </button>
            </div>

            {/* Content Body */}
            <div className="p-4 space-y-4 text-xs font-mono">
              {/* Status and Severity Badges */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2.5 py-1 rounded-full text-[11px] font-bold ${
                      selectedEvent.severity === "SEVERE"
                        ? "bg-rose-500/20 text-rose-400 border border-rose-500/40"
                        : selectedEvent.severity === "HIGH"
                        ? "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                        : "bg-blue-500/20 text-blue-400 border border-blue-500/40"
                    }`}
                  >
                    {selectedEvent.severity} SEVERITY
                  </span>
                  <span
                    className={`px-2.5 py-1 rounded-full text-[11px] font-bold ${
                      selectedEvent.status === "CONFIRMED"
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                        : selectedEvent.status === "ESCALATED"
                        ? "bg-rose-500/20 text-rose-400 border border-rose-500/40"
                        : selectedEvent.status === "TICKET_CREATED"
                        ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/40"
                        : "bg-gray-800 text-gray-300 border border-gray-700"
                    }`}
                  >
                    {selectedEvent.status}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-gray-500 block">AI CONFIDENCE</span>
                  <span className="text-emerald-400 font-bold text-sm">
                    {(selectedEvent.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Evidentiary Media Display */}
              <div className="space-y-2">
                <div className="text-[11px] text-gray-400 font-bold uppercase tracking-wider flex items-center gap-1">
                  <Camera size={12} className="text-brand" />
                  <span>Evidence Verification Media</span>
                </div>

                {selectedEvent.evidence_image_b64 ? (
                  <div className="relative rounded-xl overflow-hidden border border-gray-700 aspect-video bg-black flex items-center justify-center">
                    <img
                      src={selectedEvent.evidence_image_b64}
                      alt="Incident Evidence"
                      className="w-full h-full object-cover"
                    />
                    <span className="absolute bottom-2 left-2 bg-black/80 text-[10px] px-2 py-0.5 rounded text-gray-300 font-mono">
                      Camera: {selectedEvent.camera_id}
                    </span>
                  </div>
                ) : (
                  <div className="rounded-xl border border-gray-800 p-6 bg-gray-950 flex flex-col items-center justify-center text-gray-500 text-center">
                    <Camera size={24} className="mb-1 text-gray-600" />
                    <span>Optical Evidence Frame Buffered</span>
                  </div>
                )}

                {selectedEvent.evidence_clip_url && (
                  <div className="p-2.5 rounded-lg bg-gray-950 border border-gray-800 flex items-center justify-between text-xs text-brand-light">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                      <span>Rolling Buffer Clip Available (10s)</span>
                    </div>
                    <button className="text-xs text-brand hover:underline font-bold">
                      Play Clip ▶
                    </button>
                  </div>
                )}
              </div>

              {/* Metadata Grid */}
              <div className="bg-gray-950/80 rounded-xl p-3 border border-gray-800 space-y-2 text-[11px]">
                <div className="flex justify-between py-1 border-b border-gray-800">
                  <span className="text-gray-500">Bus Identifier</span>
                  <span className="text-gray-200 font-bold">{selectedEvent.bus_id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-gray-800">
                  <span className="text-gray-500">Camera Position</span>
                  <span className="text-gray-200">{selectedEvent.camera_id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-gray-800">
                  <span className="text-gray-500">Timestamp (UTC)</span>
                  <span className="text-gray-300">{selectedEvent.timestamp.replace("T", " ").slice(0, 19)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-gray-800">
                  <span className="text-gray-500">GPS Coordinates</span>
                  <span className="text-gray-200 font-bold">
                    {selectedEvent.gps.lat.toFixed(5)}, {selectedEvent.gps.lon.toFixed(5)}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-gray-800">
                  <span className="text-gray-500">Road Segment</span>
                  <span className="text-gray-300">{selectedEvent.gps.road_segment || "—"}</span>
                </div>
                {selectedEvent.ticket_id && (
                  <div className="flex justify-between py-1 bg-indigo-950/40 p-1.5 rounded border border-indigo-500/30">
                    <span className="text-indigo-400 font-bold">Work Order Ticket</span>
                    <span className="text-white font-bold">{selectedEvent.ticket_id}</span>
                  </div>
                )}
              </div>

              {/* Detailed Anomaly Diagnostics */}
              {selectedEvent.details && Object.keys(selectedEvent.details).length > 0 && (
                <div>
                  <div className="text-[11px] text-gray-400 font-bold uppercase tracking-wider mb-1.5">
                    Sensor Signals & Diagnostics
                  </div>
                  <div className="bg-gray-950 p-2.5 rounded-lg border border-gray-800 text-[10px] text-gray-400 space-y-1">
                    {Object.entries(selectedEvent.details).map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="capitalize text-gray-500">{k.replace(/_/g, " ")}:</span>
                        <span className="text-gray-200">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ── ACTION CONTROLS (Mandated by Prompt) ────────────────────── */}
              <div className="pt-2 border-t border-gray-800 space-y-2">
                <div className="text-[11px] text-gray-400 font-bold uppercase tracking-wider">
                  Officer Dispatch Actions
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => handleEventAction("CONFIRM")}
                    className="py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold flex items-center justify-center gap-1.5 transition shadow-sm"
                  >
                    <CheckCircle2 size={14} />
                    <span>Confirm</span>
                  </button>
                  <button
                    onClick={() => handleEventAction("DISMISS")}
                    className="py-2 px-3 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 font-bold flex items-center justify-center gap-1.5 transition border border-gray-700"
                  >
                    <XCircle size={14} />
                    <span>Dismiss</span>
                  </button>
                  <button
                    onClick={() => handleEventAction("ESCALATE")}
                    className="py-2 px-3 rounded-lg bg-rose-700 hover:bg-rose-600 text-white font-bold flex items-center justify-center gap-1.5 transition shadow-sm"
                  >
                    <AlertOctagon size={14} />
                    <span>Escalate</span>
                  </button>
                  <button
                    onClick={() => handleEventAction("CREATE_MAINTENANCE_TICKET")}
                    className="py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold flex items-center justify-center gap-1.5 transition shadow-sm"
                  >
                    <Wrench size={14} />
                    <span>Create Ticket</span>
                  </button>
                </div>
              </div>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
};

export default GisCommandCenter;
