// src/components/LiveGisMap.tsx
// Phase 2: Complete GIS Map with Multi-Category Hazards, Filtering & Marker Clustering

import React, { useEffect, useRef, useState, useMemo, useCallback } from "react";
import L from "leaflet";
import { 
  Compass, Layers, RefreshCw, Key, Bus, AlertTriangle, 
  Droplet, ShieldAlert, CheckCircle2, Sliders, ExternalLink, MapPin, Globe, Check,
  Filter, Calendar, Clock, Gauge, Flame, Eye, X
} from "lucide-react";
import nationwideData from "../data/nationwide_gis_data.json";

export interface BusItem {
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
  passenger_occupancy_pct?: number;
  timestamp?: string;
  camera_status?: string;
  AI_status?: string;
  connection_status?: string;
}

export interface GisFeature {
  type: string;
  geometry: {
    type: string;
    coordinates: [number, number] | [number, number][];
  };
  properties: {
    event_id?: string;
    event_type?: string;
    layer?: string;
    confidence?: number;
    severity?: string;
    status?: string;
    address?: string;
    road_segment?: string;
    bus_id?: string;
    route_id?: string;
    timestamp?: string;
    district?: string;
    state_name?: string;
    state_code?: string;
    name?: string;
    color?: string;
    persistent_hazard_id?: string;
    independent_buses_count?: number;
    contributing_buses?: string | string[];
    persistence_badge?: string;
    last_detected_at?: string;
    ai_confidence?: number;
    observation_count?: number;
    details?: Record<string, any>;
  };
}

export interface LiveGisFilterState {
  category?: string; // ALL, ROAD_DAMAGE, WATERLOGGING, TRAFFIC, PEDESTRIAN_RISK, INCIDENT, ANPR
  severity?: string; // ALL, LOW, MEDIUM, HIGH, SEVERE
  status?: string;   // ALL, ACTIVE, CONFIRMED, ESCALATED, TICKET_CREATED, RESOLVED
  date?: string;     // ALL, TODAY, 24H, 7D
  district?: string; // ALL, or specific district name
  bus?: string;      // ALL, or specific bus_id
  route?: string;    // ALL, or specific route_id
  minConfidence?: number; // 0, 0.8, 0.85, 0.9, 0.95
  isClusterMode?: boolean;
}

export const CITIES: Record<string, { name: string; lat: number; lon: number; zoom: number }> = {
  DELHI: { name: "New Delhi (NCT of Delhi)", lat: 28.6139, lon: 77.2090, zoom: 13 },
  MUMBAI: { name: "Mumbai (Maharashtra)", lat: 19.1136, lon: 72.8697, zoom: 13 },
  BANGALORE: { name: "Bengaluru (Karnataka)", lat: 12.9716, lon: 77.5946, zoom: 13 },
  ...((nationwideData as any).CITIES || {}),
};

// Clean Google Maps and Esri public tiles with ZERO "API KEY REQUIRED" watermarks
const BASEMAP_PRESETS = [
  { 
    id: "google_streets", 
    name: "Google Maps (Roadmap)", 
    url: "https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", 
    subdomains: ["mt0", "mt1", "mt2", "mt3"],
    maxZoom: 22,
    maxNativeZoom: 20,
    attribution: "&copy; Google Maps" 
  },
  { 
    id: "google_hybrid", 
    name: "Google Maps (Satellite + Streets)", 
    url: "https://{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", 
    subdomains: ["mt0", "mt1", "mt2", "mt3"],
    maxZoom: 22,
    maxNativeZoom: 20,
    attribution: "&copy; Google Maps Imagery" 
  },
  { 
    id: "google_satellite", 
    name: "Google Maps (Satellite Only)", 
    url: "https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", 
    subdomains: ["mt0", "mt1", "mt2", "mt3"],
    maxZoom: 22,
    maxNativeZoom: 20,
    attribution: "&copy; Google Maps Satellite" 
  },
  { 
    id: "google_terrain", 
    name: "Google Maps (Terrain)", 
    url: "https://{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}", 
    subdomains: ["mt0", "mt1", "mt2", "mt3"],
    maxZoom: 22,
    maxNativeZoom: 20,
    attribution: "&copy; Google Maps Terrain" 
  },
  { 
    id: "esri_dark", 
    name: "Clean Dark Canvas (No Watermark)", 
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}", 
    subdomains: ["a", "b", "c"],
    maxZoom: 19,
    maxNativeZoom: 16,
    attribution: "&copy; Esri &copy; OpenStreetMap" 
  },
  { 
    id: "osm", 
    name: "OpenStreetMap Standard", 
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", 
    subdomains: ["a", "b", "c"],
    maxZoom: 19,
    maxNativeZoom: 19,
    attribution: "&copy; OpenStreetMap contributors" 
  },
];

// Fallback seed buses from nationwide GIS data for immediate rendering across all Indian states
const FALLBACK_BUSES: BusItem[] = ((nationwideData as any).FALLBACK_BUSES as BusItem[]) || [];

// Fallback seed hazards from nationwide GIS data across all Indian states
const FALLBACK_HAZARDS = ((nationwideData as any).FALLBACK_HAZARDS as any[]) || [];

export interface LiveGisMapProps {
  height?: string;
  initialCity?: keyof typeof CITIES;
  showControls?: boolean;
  flyToLocation?: { lat: number; lon: number; zoom?: number; label?: string } | null;
  filters?: LiveGisFilterState;
  onSelectEvent?: (event: any) => void;
  onSelectBus?: (bus: BusItem) => void;
}

// Event Category Styling Matrix (Step 2)
export const EVENT_CATEGORY_CONFIG: Record<string, { icon: string; label: string; bg: string; border: string; text: string; category: string }> = {
  POTHOLE: {
    icon: "🕳️",
    label: "Pothole",
    bg: "bg-amber-600",
    border: "border-amber-300",
    text: "text-amber-400",
    category: "ROAD_DAMAGE"
  },
  DAMAGED_ROAD: {
    icon: "🚧",
    label: "Road Damage",
    bg: "bg-orange-600",
    border: "border-orange-300",
    text: "text-orange-400",
    category: "ROAD_DAMAGE"
  },
  ROAD_DAMAGE: {
    icon: "🚧",
    label: "Road Damage",
    bg: "bg-orange-600",
    border: "border-orange-300",
    text: "text-orange-400",
    category: "ROAD_DAMAGE"
  },
  ROAD_CRACK: {
    icon: "⚡",
    label: "Road Crack",
    bg: "bg-orange-700",
    border: "border-orange-400",
    text: "text-orange-300",
    category: "ROAD_DAMAGE"
  },
  DEBRIS: {
    icon: "🪨",
    label: "Road Debris",
    bg: "bg-amber-700",
    border: "border-amber-400",
    text: "text-amber-300",
    category: "ROAD_DAMAGE"
  },
  ROAD_DEBRIS: {
    icon: "🪨",
    label: "Road Debris",
    bg: "bg-amber-700",
    border: "border-amber-400",
    text: "text-amber-300",
    category: "ROAD_DAMAGE"
  },
  MISSING_TRAFFIC_SIGN: {
    icon: "🪧",
    label: "Missing Traffic Sign",
    bg: "bg-pink-600",
    border: "border-pink-300",
    text: "text-pink-400",
    category: "ROAD_DAMAGE"
  },
  POTENTIAL_MISSING_SIGN: {
    icon: "🪧",
    label: "Potential Missing Sign",
    bg: "bg-pink-700",
    border: "border-pink-400",
    text: "text-pink-300",
    category: "ROAD_DAMAGE"
  },
  MISSING_ROAD_DIVIDER: {
    icon: "⚠️",
    label: "Missing Road Divider",
    bg: "bg-rose-600",
    border: "border-rose-300",
    text: "text-rose-400",
    category: "ROAD_DAMAGE"
  },
  POTENTIAL_MISSING_DIVIDER: {
    icon: "⚠️",
    label: "Potential Missing Divider",
    bg: "bg-rose-700",
    border: "border-rose-400",
    text: "text-rose-300",
    category: "ROAD_DAMAGE"
  },
  MISSING_ZEBRA_CROSSING: {
    icon: "🦓",
    label: "Missing Zebra Crossing",
    bg: "bg-lime-600",
    border: "border-lime-300",
    text: "text-lime-400",
    category: "ROAD_DAMAGE"
  },
  DAMAGED_ZEBRA_CROSSING: {
    icon: "🦓",
    label: "Damaged Zebra Crossing",
    bg: "bg-lime-600",
    border: "border-lime-300",
    text: "text-lime-400",
    category: "ROAD_DAMAGE"
  },
  WATERLOGGING: {
    icon: "💧",
    label: "Waterlogging",
    bg: "bg-cyan-600",
    border: "border-cyan-300",
    text: "text-cyan-400",
    category: "WATERLOGGING"
  },
  CONGESTION_EVENT: {
    icon: "🚗",
    label: "Traffic Bottleneck",
    bg: "bg-yellow-600",
    border: "border-yellow-300",
    text: "text-yellow-400",
    category: "TRAFFIC"
  },
  POTENTIAL_CONGESTION: {
    icon: "🚗",
    label: "Potential Congestion",
    bg: "bg-yellow-700",
    border: "border-yellow-400",
    text: "text-yellow-300",
    category: "TRAFFIC"
  },
  POSSIBLE_INCIDENT: {
    icon: "🚨",
    label: "Incident Alert",
    bg: "bg-red-600",
    border: "border-red-300 animate-pulse",
    text: "text-red-400",
    category: "INCIDENT"
  },
  POTENTIAL_INCIDENT: {
    icon: "🚨",
    label: "Potential Incident",
    bg: "bg-red-700",
    border: "border-red-400 animate-pulse",
    text: "text-red-300",
    category: "INCIDENT"
  },
  PEDESTRIAN_RISK: {
    icon: "🚸",
    label: "Pedestrian Risk",
    bg: "bg-purple-600",
    border: "border-purple-300",
    text: "text-purple-400",
    category: "PEDESTRIAN_RISK"
  },
  POTENTIAL_PEDESTRIAN_RISK: {
    icon: "🚸",
    label: "Potential Pedestrian Risk",
    bg: "bg-purple-700",
    border: "border-purple-400",
    text: "text-purple-300",
    category: "PEDESTRIAN_RISK"
  },
  PEDESTRIAN: {
    icon: "🚶",
    label: "Pedestrian In Corridor",
    bg: "bg-purple-600",
    border: "border-purple-300",
    text: "text-purple-400",
    category: "PEDESTRIAN_RISK"
  },
  BUS: {
    icon: "🚌",
    label: "Transit Bus",
    bg: "bg-blue-600",
    border: "border-blue-300",
    text: "text-blue-400",
    category: "TRAFFIC"
  },
  CAR: {
    icon: "🚗",
    label: "Vehicle (Car)",
    bg: "bg-yellow-600",
    border: "border-yellow-300",
    text: "text-yellow-400",
    category: "TRAFFIC"
  },
  TRUCK: {
    icon: "🚚",
    label: "Vehicle (Truck)",
    bg: "bg-yellow-700",
    border: "border-yellow-400",
    text: "text-yellow-300",
    category: "TRAFFIC"
  },
  MOTORCYCLE: {
    icon: "🏍️",
    label: "Motorcycle",
    bg: "bg-yellow-600",
    border: "border-yellow-300",
    text: "text-yellow-400",
    category: "TRAFFIC"
  },
  MAINTENANCE_TICKET: {
    icon: "🔧",
    label: "Maintenance Work Order",
    bg: "bg-emerald-700",
    border: "border-emerald-400",
    text: "text-emerald-300",
    category: "MAINTENANCE"
  },
  ANPR_VIOLATION: {
    icon: "📸",
    label: "ANPR / Lane Violation",
    bg: "bg-fuchsia-600",
    border: "border-fuchsia-300",
    text: "text-fuchsia-400",
    category: "ANPR"
  },
};

export const LiveGisMap: React.FC<LiveGisMapProps> = ({ 
  height = "520px", 
  initialCity = "DELHI",
  showControls = true,
  flyToLocation,
  filters,
  onSelectEvent,
  onSelectBus,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);

  // Layers
  const busLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const defectLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const routesLayerGroupRef = useRef<L.LayerGroup | null>(null);

  // Events Cache
  const allEventsRef = useRef<any[]>(FALLBACK_HAZARDS);

  // Initial key from ENV or localStorage
  const envKey = (import.meta as any).env?.VITE_GOOGLE_MAPS_API_KEY || "";
  const storedKey = localStorage.getItem("novaflow_google_maps_key") || "";
  const initialKey = storedKey || envKey;

  // State: Default directly to Google Maps (Roadmap)
  const [selectedCity, setSelectedCity] = useState<keyof typeof CITIES>(initialCity);
  const [activeBasemap, setActiveBasemap] = useState<string>("google_streets");
  const [googleApiKey, setGoogleApiKey] = useState<string>(initialKey);
  const [showKeyModal, setShowKeyModal] = useState<boolean>(false);
  const [tempApiKey, setTempApiKey] = useState<string>(initialKey);
  
  // Local filter states (active when standalone or fallbacks)
  const [localCategory, setLocalCategory] = useState<string>("ALL");
  const [localSeverity, setLocalSeverity] = useState<string>("ALL");
  const [localStatus, setLocalStatus] = useState<string>("ALL");
  const [localDate, setLocalDate] = useState<string>("ALL");
  const [localBus, setLocalBus] = useState<string>("ALL");
  const [localRoute, setLocalRoute] = useState<string>("ALL");
  const [localMinConfidence, setLocalMinConfidence] = useState<number>(0);
  const [localClusterMode, setLocalClusterMode] = useState<boolean>(true);

  // Consolidated effective filters (passed props take precedence)
  const effectiveCategory = filters?.category ?? localCategory;
  const effectiveSeverity = filters?.severity ?? localSeverity;
  const effectiveStatus = filters?.status ?? localStatus;
  const effectiveDate = filters?.date ?? localDate;
  const effectiveDistrict = filters?.district ?? "ALL";
  const effectiveBus = filters?.bus ?? localBus;
  const effectiveRoute = filters?.route ?? localRoute;
  const effectiveMinConfidence = filters?.minConfidence ?? localMinConfidence;
  const isClusterMode = filters?.isClusterMode ?? localClusterMode;

  const [busesCount, setBusesCount] = useState<number>(FALLBACK_BUSES.length);
  const [eventsCount, setEventsCount] = useState<number>(FALLBACK_HAZARDS.length);
  const [clusterCount, setClusterCount] = useState<number>(0);
  const [isLive, setIsLive] = useState<boolean>(true);
  const [lastUpdated, setLastUpdated] = useState<string>("Live");

  // Save API Key
  const handleSaveApiKey = () => {
    const key = tempApiKey.trim();
    localStorage.setItem("novaflow_google_maps_key", key);
    setGoogleApiKey(key);
    setShowKeyModal(false);
    if (key) {
      setActiveBasemap("google_streets");
    }
  };

  // Helper to build tile layer with smooth high-zoom fallback
  const createTileLayer = (presetId: string, apiKey: string): L.TileLayer => {
    const preset = BASEMAP_PRESETS.find(p => p.id === presetId) || BASEMAP_PRESETS[0];
    const tileUrl = (presetId.startsWith("google") && apiKey)
      ? `${preset.url}&key=${apiKey}`
      : preset.url;

    const isGoogle = presetId.startsWith("google");

    return L.tileLayer(tileUrl, {
      maxZoom: 22,
      maxNativeZoom: isGoogle ? 20 : 19,
      subdomains: preset.subdomains,
      attribution: preset.attribution,
      crossOrigin: true,
    });
  };

  // Helper to match category filter (comprehensive category & keyword mapping)
  const matchesCategory = (item: any, targetCategory: string): boolean => {
    if (!targetCategory || targetCategory === "ALL") return true;
    const p = item.properties || item;
    const directCat = (p.category || item.category || "").toUpperCase();
    if (directCat === targetCategory.toUpperCase()) return true;

    const evType = String(p.event_type || p.type || item.event_type || item.type || "").toUpperCase();
    const configCat = EVENT_CATEGORY_CONFIG[evType]?.category;
    if (configCat && configCat === targetCategory.toUpperCase()) return true;

    const layer = String(p.layer || item.layer || "").toLowerCase();
    if (targetCategory === "ROAD_DAMAGE") {
      return (
        ["potholes", "road_damage", "missing_signs", "missing_dividers", "zebra_crossing_issues"].includes(layer) ||
        ["POTHOLE", "DAMAGE", "CRACK", "DEBRIS", "SIGN", "DIVIDER", "ZEBRA"].some(k => evType.includes(k))
      );
    }
    if (targetCategory === "WATERLOGGING") {
      return layer === "waterlogging" || evType.includes("WATERLOG") || evType.includes("FLOOD") || evType.includes("PUDDLE");
    }
    if (targetCategory === "TRAFFIC") {
      return layer === "traffic_congestion" || ["CONGESTION", "TRAFFIC", "BUS", "CAR", "TRUCK", "MOTORCYCLE", "VEHICLE"].some(k => evType.includes(k));
    }
    if (targetCategory === "PEDESTRIAN_RISK") {
      return layer === "pedestrian_risk" || evType.includes("PEDESTRIAN");
    }
    if (targetCategory === "INCIDENT") {
      return layer === "incidents" || evType.includes("INCIDENT") || evType.includes("COLLISION") || evType.includes("ACCIDENT");
    }
    if (targetCategory === "ANPR") {
      return layer === "anpr_violations" || evType.includes("ANPR") || evType.includes("PLATE") || evType.includes("INTRUSION");
    }
    return false;
  };

  // Helper to match date filter
  const matchesDate = (timestampStr: string | undefined, dateFilter: string): boolean => {
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

  // Helper: Render individual event marker with full attributes (Step 2)
  const renderSingleEventMarker = (item: any) => {
    const p = item.properties || item;
    const lat = item.lat ?? item.geometry?.coordinates?.[1] ?? p.lat;
    const lon = item.lon ?? item.geometry?.coordinates?.[0] ?? p.lon;
    if (typeof lat !== "number" || typeof lon !== "number") return;

    const evType = (p.event_type || "POTHOLE").toUpperCase();
    const config = EVENT_CATEGORY_CONFIG[evType] || EVENT_CATEGORY_CONFIG.POTHOLE;
    const iconHtml = config.icon;
    const pinColor = `${config.bg} ${config.border} text-white`;

    const conf = typeof p.confidence === "number" ? p.confidence : 0.9;
    const confPct = (conf * 100).toFixed(0);
    const shortLabel = config.label.split(" ")[0];

    const customIcon = L.divIcon({
      className: "custom-defect-marker",
      html: `
        <div style="display: flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 9999px; background: rgba(31, 34, 67, 0.94); border: 1.5px solid ${evType.includes('POTHOLE') || evType.includes('DAMAGE') ? '#E67E22' : '#38BDF8'}; color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 10px; font-weight: 700; box-shadow: 0 4px 12px rgba(0,0,0,0.35); white-space: nowrap; cursor: pointer;">
          <span style="font-size: 11px;">${iconHtml}</span>
          <span style="color: #F1F5F9;">${shortLabel}</span>
          <span style="color: #FBBF24; font-family: monospace;">${confPct}%</span>
        </div>
      `,
      iconSize: [100, 24],
      iconAnchor: [50, 12],
    });

    const marker = L.marker([lat, lon], { icon: customIcon });

    marker.on("click", () => {
      const road_segment = p.road_segment || p.address || p.gps?.road_segment || "Monitored Transit Corridor";
      const address = p.address || p.road_segment || p.gps?.address || "Monitored Transit Corridor";
      const normalizedPayload = {
        ...p,
        id: p.id || p.event_id || p.eventId || `ev_${Math.random().toString(36).slice(2, 7)}`,
        event_id: p.event_id || p.eventId || p.id || "EV-0000",
        event_type: evType,
        layer: p.layer || (evType.includes("POTHOLE") ? "potholes" : evType.includes("DAMAGE") ? "road_damage" : evType.includes("WATERLOG") ? "waterlogging" : evType.includes("SIGN") ? "missing_signs" : evType.includes("DIVIDER") ? "missing_dividers" : evType.includes("ZEBRA") ? "zebra_crossing_issues" : evType.includes("CONGESTION") ? "traffic_congestion" : evType.includes("INCIDENT") ? "incidents" : evType.includes("PEDESTRIAN") ? "pedestrian_risk" : "potholes"),
        confidence: typeof p.confidence === "number" ? p.confidence : 0.9,
        severity: (p.severity || "MEDIUM").toUpperCase(),
        status: (p.status || "ACTIVE").toUpperCase(),
        bus_id: p.bus_id || p.busId || "BUS_001",
        camera_id: p.camera_id || "FRONT",
        timestamp: p.timestamp || new Date().toISOString(),
        gps: {
          lat,
          lon,
          road_segment,
          address,
          bearing_deg: p.bearing_deg || p.gps?.bearing_deg || 0,
        },
        district: p.district || "Metropolitan",
        evidence_image_b64: p.evidence_image_b64 || p.annotated_evidence_path || p.evidence_path,
        evidence_path: p.evidence_path || p.original_evidence_path,
        original_evidence_path: p.original_evidence_path || p.evidence_path,
        annotated_evidence_path: p.annotated_evidence_path || p.evidence_image_b64,
        thumbnail_path: p.thumbnail_path,
        source_video: p.source_video || p.video_file_name || "Live Dashcam Stream",
        condition_type: p.condition_type || (config.category === "ROAD_DAMAGE" && !evType.includes("SIGN") && !evType.includes("DIVIDER") ? "DIRECT" : "POTENTIAL"),
        condition_label: p.condition_label,
        is_derived: Boolean(p.is_derived),
        ticket_id: p.ticket_id,
        maintenance_ticket_status: p.maintenance_ticket_status || (p.ticket_id ? "ASSIGNED" : "NONE"),
        frame_number: p.frame_number,
        track_id: p.track_id,
        persistent_hazard_id: p.persistent_hazard_id,
        independent_buses_count: p.independent_buses_count,
        contributing_buses: p.contributing_buses,
        persistence_badge: p.persistence_badge,
        last_detected_at: p.last_detected_at,
        ai_confidence: typeof p.ai_confidence === "number" ? p.ai_confidence : p.confidence,
        observation_count: p.observation_count,
        details: p.details || {},
      };
      if (onSelectEvent) onSelectEvent(normalizedPayload);
    });

    // Detailed popup showing all required attributes + multi-bus confirmation & visual evidence
    const formattedDate = p.timestamp ? new Date(p.timestamp).toLocaleString() : new Date().toLocaleString();
    const lastDetectedStr = p.last_detected_at ? new Date(p.last_detected_at).toLocaleString() : formattedDate;
    const conditionBadge = p.condition_type === "POTENTIAL"
      ? `<span style="font-size: 8px; font-weight: 800; padding: 1px 5px; border-radius: 3px; background: rgba(234, 179, 8, 0.25); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.5);">POTENTIAL</span>`
      : `<span style="font-size: 8px; font-weight: 800; padding: 1px 5px; border-radius: 3px; background: rgba(34, 197, 94, 0.25); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.5);">CONFIRMED</span>`;

    const thumbUrl = p.thumbnail_path || p.annotated_evidence_path || p.evidence_image_b64 || p.original_evidence_path;
    const thumbHtml = thumbUrl ? `
      <div style="margin-bottom: 6px; border-radius: 6px; overflow: hidden; max-height: 110px; background: #0b0d18; display: flex; align-items: center; justify-content: center; border: 1px solid #334155;">
        <img src="${thumbUrl}" alt="Evidence Frame" style="width: 100%; height: 110px; object-fit: cover;" onerror="this.style.display='none'" />
      </div>
    ` : "";

    const ticketHtml = p.ticket_id
      ? `<strong style="color: #34d399;">${p.ticket_id}</strong> <span style="font-size: 8px; color: #a7f3d0;">(${p.maintenance_ticket_status || 'ASSIGNED'})</span>`
      : `<span style="color: #94a3b8;">No Ticket Dispatched</span>`;

    // Multi-Bus Confirmation Banner (Phase 12)
    const busCount = p.independent_buses_count || 1;
    const multiBusBadgeHtml = (p.persistence_badge || busCount > 1) ? `
      <div style="margin-top: 6px; padding: 4px 6px; border-radius: 4px; background: rgba(37, 99, 235, 0.2); border: 1px solid #3b82f6; color: #93c5fd; font-size: 9px; font-weight: 800; display: flex; align-items: center; justify-content: space-between;">
        <span>🛡️ ${p.persistence_badge || `CONFIRMED BY ${busCount} BUSES`}</span>
        <span style="color: #bfdbfe; font-size: 8px;">Obs: ${p.observation_count || busCount}</span>
      </div>
    ` : "";

    marker.bindPopup(`
      <div style="font-family: ui-monospace, monospace; font-size: 11px; min-width: 240px; max-width: 280px; line-height: 1.4; color: #e2e8f0; padding: 3px;">
        ${thumbHtml}
        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #334155; padding-bottom: 6px; margin-bottom: 6px;">
          <span style="font-weight: bold; color: #f59e0b; display: flex; align-items: center; gap: 4px;">
            ${config.icon} ${config.label}
          </span>
          <div style="display: flex; align-items: center; gap: 4px;">
            ${conditionBadge}
            <span style="font-size: 9px; font-weight: bold; padding: 1px 5px; border-radius: 3px; background: ${p.severity === 'SEVERE' ? '#ef4444' : p.severity === 'HIGH' ? '#f97316' : '#3b82f6'}; color: white;">
              ${p.severity || 'HIGH'}
            </span>
          </div>
        </div>
        <div style="font-weight: 600; color: #ffffff; margin-bottom: 4px; font-size: 11px;">
          ${p.address || p.road_segment || 'Monitored Transit Corridor'}
        </div>
        ${multiBusBadgeHtml}
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 10px; color: #94a3b8; margin-top: 6px;">
          <div>Bus: <strong style="color: #60a5fa;">${p.bus_id || 'BUS_001'}</strong></div>
          <div>AI Conf: <strong style="color: #34d399;">${confPct}%</strong></div>
          <div>Status: <strong style="color: #cbd5e1;">${p.status || 'ACTIVE'}</strong></div>
          <div>Video: <strong style="color: #a78bfa; word-break: break-all;">${p.source_video || 'Live Stream'}</strong></div>
        </div>
        <div style="font-size: 10px; color: #94a3b8; margin-top: 4px; border-top: 1px solid #1e293b; padding-top: 4px;">
          Ticket: ${ticketHtml}
        </div>
        <div style="font-size: 9px; color: #64748b; margin-top: 4px;">
          📍 ${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E • 🕒 ${lastDetectedStr}
        </div>
      </div>
    `);

    defectLayerGroupRef.current?.addLayer(marker);
  };

  // Step 4: Clustering & Marker Render Engine
  const renderEvents = useCallback((rawEvents: any[]) => {
    if (!defectLayerGroupRef.current || !mapRef.current) return;
    defectLayerGroupRef.current.clearLayers();

    // 1. Apply Step 3 Multi-Dimensional Filters
    const filtered = rawEvents.filter((ev) => {
      const p = ev.properties || ev;

      if (!matchesCategory(ev, effectiveCategory)) return false;
      if (effectiveSeverity !== "ALL" && (p.severity || "").toUpperCase() !== effectiveSeverity.toUpperCase()) return false;
      if (effectiveStatus !== "ALL") {
        const itemStat = (p.status || "").toUpperCase();
        const targetStat = effectiveStatus.toUpperCase();
        if (itemStat !== targetStat && !(targetStat === "UNDER_REPAIR" && itemStat === "IN_REPAIR")) {
          return false;
        }
      }
      if (effectiveDistrict !== "ALL") {
        const dTarget = effectiveDistrict.toLowerCase();
        const itemDist = String(p.district || ev.district || "").toLowerCase();
        const itemAddr = String(p.address || ev.address || p.road_segment || "").toLowerCase();
        if (!itemDist.includes(dTarget) && !itemAddr.includes(dTarget)) return false;
      }
      if (effectiveBus !== "ALL" && p.bus_id !== effectiveBus) return false;
      if (effectiveRoute !== "ALL" && p.route_id !== effectiveRoute) return false;
      if (effectiveMinConfidence > 0 && (p.confidence || 0) < effectiveMinConfidence) return false;
      if (!matchesDate(p.timestamp, effectiveDate)) return false;

      return true;
    });

    setEventsCount(filtered.length);

    const currentZoom = mapRef.current.getZoom();

    // Step 4: Zoomed out -> Cluster (Zoom <= 12)
    if (isClusterMode && currentZoom <= 12) {
      const cellSize = currentZoom <= 6 ? 2.2 : currentZoom <= 8 ? 0.8 : currentZoom <= 10 ? 0.3 : 0.1;
      const clusterMap: Record<string, { lat: number; lon: number; count: number; events: any[] }> = {};

      filtered.forEach((item) => {
        const p = item.properties || item;
        const lat = item.lat ?? item.geometry?.coordinates?.[1] ?? p.lat;
        const lon = item.lon ?? item.geometry?.coordinates?.[0] ?? p.lon;
        if (typeof lat !== "number" || typeof lon !== "number") return;

        const key = `${Math.floor(lon / cellSize)}_${Math.floor(lat / cellSize)}`;
        if (!clusterMap[key]) {
          clusterMap[key] = { lat: 0, lon: 0, count: 0, events: [] };
        }
        clusterMap[key].events.push(item);
      });

      const clusterList = Object.values(clusterMap);
      setClusterCount(clusterList.filter(c => c.events.length > 1).length);

      clusterList.forEach((cl) => {
        let sumLat = 0;
        let sumLon = 0;
        cl.events.forEach((e) => {
          const p = e.properties || e;
          const lat = e.lat ?? e.geometry?.coordinates?.[1] ?? p.lat;
          const lon = e.lon ?? e.geometry?.coordinates?.[0] ?? p.lon;
          sumLat += lat;
          sumLon += lon;
        });
        cl.lat = sumLat / cl.events.length;
        cl.lon = sumLon / cl.events.length;
        cl.count = cl.events.length;

        if (cl.count > 1) {
          const clusterIcon = L.divIcon({
            className: "custom-cluster-marker",
            html: `
              <div class="relative flex items-center justify-center cursor-pointer group">
                <div class="absolute -inset-1.5 rounded-full bg-blue-500/30 animate-ping"></div>
                <div class="w-11 h-11 rounded-full bg-gradient-to-tr from-indigo-700 via-blue-600 to-purple-600 border-2 border-white/90 text-white font-mono font-black text-xs flex flex-col items-center justify-center shadow-2xl transform transition-transform group-hover:scale-125">
                  <span class="leading-none font-bold text-[11px]">● ${cl.count}</span>
                  <span class="text-[7px] font-sans font-medium uppercase tracking-tighter opacity-80">Events</span>
                </div>
              </div>
            `,
            iconSize: [44, 44],
            iconAnchor: [22, 22],
          });

          const marker = L.marker([cl.lat, cl.lon], { icon: clusterIcon });
          marker.bindTooltip(`
            <div style="font-family: ui-monospace, monospace; font-size: 11px; padding: 4px;">
              <strong style="color: #60a5fa;">● Cluster of ${cl.count} Events</strong>
              <div style="color: #94a3b8; font-size: 10px; margin-top: 2px;">Click to zoom into corridor</div>
            </div>
          `, { className: "cluster-tooltip", offset: [0, -10] });

          marker.on("click", () => {
            mapRef.current?.flyTo([cl.lat, cl.lon], Math.min(15, currentZoom + 3), { duration: 1.0 });
          });

          defectLayerGroupRef.current?.addLayer(marker);
        } else {
          renderSingleEventMarker(cl.events[0]);
        }
      });
    } else {
      // Step 4: Zoom in -> Individual Events (Zoom >= 13 or clustering off)
      setClusterCount(0);
      filtered.forEach((item) => {
        renderSingleEventMarker(item);
      });
    }
  }, [
    effectiveCategory, effectiveSeverity, effectiveStatus, effectiveDistrict, effectiveDate,
    effectiveBus, effectiveRoute, effectiveMinConfidence, isClusterMode
  ]);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const city = CITIES[selectedCity] || CITIES["DELHI"];
    const map = L.map(mapContainerRef.current, {
      center: [city.lat, city.lon],
      zoom: city.zoom,
      zoomControl: true,
      attributionControl: true,
    });

    const tiles = createTileLayer(activeBasemap, googleApiKey).addTo(map);
    tileLayerRef.current = tiles;

    // Feature Layer Groups
    routesLayerGroupRef.current = L.layerGroup().addTo(map);
    defectLayerGroupRef.current = L.layerGroup().addTo(map);
    busLayerGroupRef.current = L.layerGroup().addTo(map);

    mapRef.current = map;

    // Re-render markers on zoom/pan for dynamic clustering
    map.on("zoomend", () => {
      renderEvents(allEventsRef.current);
    });

    // Invalidate size when DOM resolves
    const timer1 = setTimeout(() => map.invalidateSize(), 150);
    const timer2 = setTimeout(() => map.invalidateSize(), 500);

    const onResize = () => {
      if (mapRef.current) mapRef.current.invalidateSize();
    };
    window.addEventListener("resize", onResize);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      window.removeEventListener("resize", onResize);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Re-run clustering when filters change
  useEffect(() => {
    if (mapRef.current) {
      renderEvents(allEventsRef.current);
    }
  }, [renderEvents]);

  // Update map center when initialCity prop changes
  useEffect(() => {
    if (initialCity && CITIES[initialCity] && mapRef.current) {
      jumpToCity(initialCity);
    }
  }, [initialCity]);

  // Support dynamic fly-to location (State / Capital / District / Tehsil jump)
  useEffect(() => {
    if (flyToLocation && mapRef.current && flyToLocation.lat && flyToLocation.lon) {
      const targetZoom = flyToLocation.zoom || 13;
      mapRef.current.flyTo([flyToLocation.lat, flyToLocation.lon], targetZoom, {
        duration: 1.5,
        easeLinearity: 0.25,
      });

      if (flyToLocation.label) {
        L.popup({ closeButton: true, autoClose: true })
          .setLatLng([flyToLocation.lat, flyToLocation.lon])
          .setContent(`
            <div style="font-family: sans-serif; font-size: 12px; padding: 4px;">
              <strong style="color: #2563eb;">📍 ${flyToLocation.label}</strong>
              <div style="color: #64748b; font-size: 10px; margin-top: 2px;">Coordinated Municipal Transit Node</div>
            </div>
          `)
          .openOn(mapRef.current);
      }
    }
  }, [flyToLocation]);

  // Update Basemap when activeBasemap or googleApiKey changes
  useEffect(() => {
    if (!mapRef.current) return;

    if (tileLayerRef.current) {
      mapRef.current.removeLayer(tileLayerRef.current);
    }

    const newTiles = createTileLayer(activeBasemap, googleApiKey).addTo(mapRef.current);
    newTiles.bringToBack();
    tileLayerRef.current = newTiles;
  }, [activeBasemap, googleApiKey]);

  // Jump to city
  const jumpToCity = (cityKey: keyof typeof CITIES) => {
    setSelectedCity(cityKey);
    const city = CITIES[cityKey];
    if (mapRef.current) {
      mapRef.current.flyTo([city.lat, city.lon], city.zoom, { duration: 1.2 });
    }
  };

  // Fetch & Render Features (Defects, Incidents, Congestion, Routes)
  const fetchFeaturesAndRoutes = async () => {
    try {
      // 1. Transit Routes Polylines
      const routesRes = await fetch("/api/v1/gis/routes");
      if (routesRes.ok && routesLayerGroupRef.current) {
        const routesData = await routesRes.json();
        routesLayerGroupRef.current.clearLayers();

        if (routesData.features) {
          routesData.features.forEach((feat: GisFeature) => {
            if (feat.geometry && feat.geometry.type === "LineString") {
              const coords = (feat.geometry.coordinates as [number, number][]).map(
                ([lon, lat]) => [lat, lon] as [number, number]
              );
              const color = feat.properties.color || "#6366f1";
              
              const polyline = L.polyline(coords, {
                color: color,
                weight: 5,
                opacity: 0.8,
                lineJoin: "round",
              });

              polyline.bindPopup(`
                <div style="font-family: ui-monospace, monospace; font-size: 11px; padding: 4px;">
                  <strong style="color: ${color};">● ${feat.properties.name || feat.properties.route_id}</strong>
                  <div style="color: #94a3b8; font-size: 10px; margin-top: 2px;">Monitored Public Transit Corridor</div>
                </div>
              `);

              if (routesLayerGroupRef.current) {
                routesLayerGroupRef.current.addLayer(polyline);
              }
            }
          });
        }
      }

      // 2. Events & Defects
      const featuresRes = await fetch("/api/v1/gis/features");
      if (featuresRes.ok) {
        const data = await featuresRes.json();
        if (data.features && data.features.length > 0) {
          allEventsRef.current = data.features;
          renderEvents(data.features);
        } else {
          renderEvents(FALLBACK_HAZARDS);
        }
      } else {
        renderEvents(FALLBACK_HAZARDS);
      }
    } catch {
      renderEvents(FALLBACK_HAZARDS);
    }
  };

  // Fetch & Update Live Buses (Phase 8: Edge Nodes with Kinematics & AI Status)
  const fetchLiveBuses = async () => {
    try {
      let res = await fetch("/api/v1/buses");
      if (!res.ok) {
        res = await fetch("/api/v1/demo/buses");
      }
      if (!res.ok || !busLayerGroupRef.current) return;
      const data = await res.json();
      const buses: BusItem[] = Array.isArray(data) ? data.map((b: any) => ({
        ...b,
        lat: b.latitude ?? b.current_lat ?? b.lat ?? 28.6139,
        lon: b.longitude ?? b.current_lon ?? b.lon ?? 77.2090,
        speed_kmh: b.speed ?? b.speed_kmh ?? 0,
        bearing_deg: b.heading ?? b.bearing_deg ?? 0,
        camera_status: b.camera_status || "ACTIVE",
        AI_status: b.AI_status || "ONLINE",
        connection_status: b.connection_status || "CONNECTED",
      })) : [];

      if (!buses || buses.length === 0) return;
      
      setBusesCount(buses.length);
      busLayerGroupRef.current.clearLayers();

      buses.forEach((b) => {
        const isInferencing = b.AI_status === "INFERENCING";
        const isStreaming = b.camera_status === "STREAMING" || b.camera_status === "ACTIVE";
        const headingDeg = b.heading ?? b.bearing_deg ?? 0;

        const busIcon = L.divIcon({
          className: "custom-bus-marker",
          html: `
            <div class="relative flex items-center justify-center cursor-pointer group" style="width: 42px; height: 42px;">
              ${isInferencing ? '<div class="absolute inset-0 rounded-full bg-amber-400/40 animate-ping"></div>' : ''}
              <div class="w-9 h-9 rounded-full ${isInferencing ? 'bg-gradient-to-tr from-amber-600 to-yellow-500 border-2 border-yellow-200 shadow-amber-500/50' : 'bg-gradient-to-tr from-blue-700 to-indigo-600 border-2 border-white shadow-blue-500/50'} shadow-lg flex items-center justify-center text-white text-xs font-bold transform transition-transform group-hover:scale-110">
                <span style="display: inline-block; transform: rotate(${headingDeg}deg); font-size: 14px;">🚌</span>
              </div>
              <div class="absolute -top-1 -right-1 w-3 h-3 rounded-full ${isInferencing ? 'bg-amber-400 animate-pulse' : isStreaming ? 'bg-emerald-400' : 'bg-slate-400'} border border-slate-900 shadow"></div>
              <div class="absolute -bottom-4 bg-gray-950/95 text-cyan-300 text-[9px] px-1.5 py-0.2 rounded border border-cyan-500/40 whitespace-nowrap shadow font-mono font-bold">
                ${b.bus_id} • ${Math.round(b.speed_kmh)}km/h
              </div>
            </div>
          `,
          iconSize: [42, 42],
          iconAnchor: [21, 21],
        });

        const marker = L.marker([b.lat, b.lon], { icon: busIcon });
        marker.on("click", () => {
          if (onSelectBus) onSelectBus(b);
        });

        const aiBadgeColor = isInferencing ? '#f59e0b' : b.AI_status === 'ONLINE' ? '#10b981' : '#64748b';
        const camBadgeColor = b.camera_status === 'ACTIVE' || b.camera_status === 'STREAMING' ? '#10b981' : '#f97316';

        marker.bindPopup(`
          <div style="font-family: ui-monospace, monospace; font-size: 11px; padding: 4px; min-width: 220px; color: #e2e8f0;">
            <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #334155; padding-bottom: 4px; margin-bottom: 6px;">
              <span style="font-weight: bold; color: #60a5fa; font-size: 12px;">
                🚌 ${b.name || b.bus_id}
              </span>
              <span style="font-size: 8px; font-weight: 800; padding: 1px 5px; border-radius: 3px; background: rgba(59, 130, 246, 0.2); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.4);">
                ${b.route_id}
              </span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 10px; margin-bottom: 6px;">
              <div>Speed: <strong style="color: #34d399;">${Math.round(b.speed_kmh)} km/h</strong></div>
              <div>Heading: <strong style="color: #cbd5e1;">${Math.round(headingDeg)}°</strong></div>
              <div>Camera: <strong style="color: ${camBadgeColor};">${b.camera_status || 'ACTIVE'}</strong></div>
              <div>AI State: <strong style="color: ${aiBadgeColor};">${b.AI_status || 'ONLINE'}</strong></div>
            </div>
            <div style="font-size: 9px; color: #94a3b8; border-top: 1px solid #1e293b; padding-top: 4px;">
              GPS: ${b.lat.toFixed(4)}°N, ${b.lon.toFixed(4)}°E
            </div>
            <div style="margin-top: 6px; text-align: center;">
              <button onclick="window.dispatchEvent(new CustomEvent('inspect-bus-edge-node', { detail: '${b.bus_id}' }))" style="width: 100%; background: #2563eb; color: white; border: none; border-radius: 4px; padding: 4px 8px; font-size: 10px; font-weight: bold; cursor: pointer;">
                Inspect Edge Node & Hazards →
              </button>
            </div>
          </div>
        `);

        busLayerGroupRef.current?.addLayer(marker);
      });

      setLastUpdated(new Date().toLocaleTimeString());
    } catch {
      // Keep fallbacks active
    }
  };

  // Initial load and periodic polling
  useEffect(() => {
    fetchFeaturesAndRoutes();
    fetchLiveBuses();

    const interval = setInterval(() => {
      if (isLive) {
        fetchLiveBuses();
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [isLive]);

  return (
    <div 
      className="relative w-full h-full overflow-hidden border border-gray-800 bg-gray-950 shadow-2xl flex flex-col select-none"
      style={{ height, minHeight: height === "100%" ? "100%" : height }}
    >
      {/* Standalone Top Filter Bar (Active when showControls is true) */}
      {showControls && (
        <div className="absolute top-3 left-3 right-3 z-[1000] flex flex-wrap items-center justify-between gap-2 pointer-events-none">
          {/* Left: Category Quick Pills (Step 3) */}
          <div className="flex items-center gap-1 bg-gray-900/90 backdrop-blur-md px-2 py-1.5 rounded-xl border border-gray-700 shadow-xl pointer-events-auto">
            {[
              { id: "ALL", label: "All Events", icon: "🌐" },
              { id: "ROAD_DAMAGE", label: "Road Damage", icon: "🕳️" },
              { id: "WATERLOGGING", label: "Waterlogging", icon: "💧" },
              { id: "TRAFFIC", label: "Traffic", icon: "🚗" },
              { id: "PEDESTRIAN_RISK", label: "Pedestrian Risk", icon: "🚸" },
              { id: "INCIDENT", label: "Incident", icon: "🚨" },
              { id: "ANPR", label: "ANPR", icon: "📸" },
            ].map((cat) => (
              <button
                key={cat.id}
                onClick={() => setLocalCategory(cat.id)}
                className={`text-[11px] px-2 py-1 rounded-lg font-medium transition-all flex items-center gap-1 ${
                  effectiveCategory === cat.id 
                    ? "bg-blue-600 text-white shadow font-bold" 
                    : "text-gray-400 hover:text-white hover:bg-gray-800"
                }`}
              >
                <span>{cat.icon}</span>
                <span className="hidden sm:inline">{cat.label}</span>
              </button>
            ))}
          </div>

          {/* Right: Basemap Switcher & Cluster Mode Toggle (Step 4) */}
          <div className="flex items-center gap-2 bg-gray-900/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-gray-700 shadow-xl pointer-events-auto">
            {/* Clustering toggle */}
            <button
              onClick={() => setLocalClusterMode(!isClusterMode)}
              className={`text-xs px-2.5 py-1 rounded-lg font-semibold flex items-center gap-1.5 transition-all border ${
                isClusterMode 
                  ? "bg-indigo-950/90 text-indigo-300 border-indigo-500/50" 
                  : "bg-gray-800 text-gray-400 border-gray-700 hover:text-white"
              }`}
              title="Toggle Zoom-Level Marker Clustering"
            >
              <span>●</span>
              <span>Clusters: {isClusterMode ? "ON" : "OFF"}</span>
            </button>

            {/* Basemap Dropdown */}
            <select
              value={activeBasemap}
              onChange={(e) => setActiveBasemap(e.target.value)}
              className="text-xs bg-gray-800 text-gray-200 border border-gray-600 rounded-lg px-2.5 py-1 outline-none font-medium cursor-pointer"
            >
              {BASEMAP_PRESETS.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>

            {/* Refresh Toggle */}
            <button
              onClick={() => { fetchLiveBuses(); fetchFeaturesAndRoutes(); }}
              className="p-1 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
              title="Refresh Map Telemetry"
            >
              <RefreshCw size={14} className={isLive ? "animate-spin-slow" : ""} />
            </button>
          </div>
        </div>
      )}

      {/* Map Container Canvas */}
      <div 
        ref={mapContainerRef} 
        style={{ height: "100%", width: "100%", minHeight: height === "100%" ? "100%" : height }} 
        className="w-full h-full flex-1 z-0 bg-gray-950"
      />

      {/* Bottom Floating Stats Bar (Step 2 & Step 4 Live Metrics) */}
      <div className="absolute bottom-3 left-3 right-3 z-[1000] flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        {/* Telemetry Counter Pill */}
        <div className="bg-gray-900/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-gray-700 shadow-xl pointer-events-auto flex items-center gap-3 text-xs font-mono">
          <div className="flex items-center gap-1.5 text-blue-400 font-semibold">
            <Bus size={14} />
            <span>{busesCount} Live Buses</span>
          </div>
          <span className="text-gray-600">|</span>
          <div className="flex items-center gap-1.5 text-amber-400 font-semibold">
            <AlertTriangle size={14} />
            <span>{eventsCount} Detected Events</span>
          </div>
          {clusterCount > 0 && isClusterMode && (
            <>
              <span className="text-gray-600">|</span>
              <div className="flex items-center gap-1.5 text-indigo-400 font-semibold">
                <span>●</span>
                <span>{clusterCount} Active Clusters</span>
              </div>
            </>
          )}
          {lastUpdated && (
            <>
              <span className="text-gray-600">|</span>
              <span className="text-gray-400 text-[11px]">Sync: {lastUpdated}</span>
            </>
          )}
        </div>

        {/* Quick Severity Legend Indicator */}
        <div className="bg-gray-900/90 backdrop-blur-md px-2.5 py-1.5 rounded-xl border border-gray-700 shadow-xl pointer-events-auto hidden md:flex items-center gap-2 text-[10px] font-semibold text-gray-300">
          <span className="text-gray-500 uppercase tracking-wider text-[9px]">Severity:</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500" /> Low</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500" /> Med</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500" /> High</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" /> Severe</span>
        </div>
      </div>

      {/* Google Maps API Key Modal */}
      {showKeyModal && (
        <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center gap-3 border-b border-gray-800 pb-3 mb-4">
              <div className="p-2.5 rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30">
                <Globe size={22} />
              </div>
              <div>
                <h4 className="text-base font-bold text-white">Google Maps API Connection</h4>
                <p className="text-xs text-gray-400">Enable Official Google Maps Roadmap, Satellite, and Terrain</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  Google Maps API Key
                </label>
                <input
                  type="text"
                  value={tempApiKey}
                  onChange={(e) => setTempApiKey(e.target.value)}
                  placeholder="Paste your Google Maps API Key (AIzaSy...)"
                  className="w-full px-3 py-2 text-sm bg-gray-950 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 font-mono"
                />
                <p className="text-[11px] text-gray-400 mt-1.5">
                  NovaFlow provides clean, watermark-free Google Maps tiles. If you have an official Google Cloud key, paste it here for full high-throughput quota.
                </p>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  onClick={() => {
                    localStorage.removeItem("novaflow_google_maps_key");
                    setGoogleApiKey("");
                    setTempApiKey("");
                    setActiveBasemap("google_streets");
                    setShowKeyModal(false);
                  }}
                  className="text-xs text-rose-400 hover:underline"
                >
                  Clear Key
                </button>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowKeyModal(false)}
                    className="text-xs px-3 py-1.5 rounded-lg border border-gray-700 text-gray-300 hover:bg-gray-800"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveApiKey}
                    className="text-xs px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 font-semibold text-white shadow-lg"
                  >
                    Save & Activate
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LiveGisMap;
