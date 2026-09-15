// src/components/CongestionMap.tsx
// Interactive GIS Map and Thermal Congestion Heatmap Component — Leaflet-based

import React, { useEffect, useRef, useState } from "react";
import L from "leaflet";
import {
  Layers, Flame, Gauge, AlertTriangle,
  CheckCircle2, ZoomIn, ZoomOut
} from "lucide-react";

export interface SegmentPolylinePoint {
  lat: number;
  lon: number;
}

export interface RoadSegmentData {
  segment_id:       string;
  name:             string;
  road_type:        string;
  city:             string;
  capacity_per_km:  number;
  free_flow_speed:  number;
  baseline_speed:   number;
  current_speed:    number;
  density:          number;
  congestion_score: number;
  severity:         "LOW" | "MEDIUM" | "HIGH" | "SEVERE";
  is_bottleneck:    boolean;
  active_vehicles:  number;
  speed_deficit_pct?: number;
  route_delay_minutes?: number;
  length_km?: number;
  polyline:         SegmentPolylinePoint[];
}

export interface CongestionHeatmapPoint {
  lat:        number;
  lon:        number;
  intensity:  number;
  severity:   "LOW" | "MEDIUM" | "HIGH" | "SEVERE";
  score:      number;
  segment_id: string;
  name:       string;
  speed_kmh:  number;
  density:    number;
  color?:     string;
  route_delay_minutes?: number;
}

interface CongestionMapProps {
  segments: RoadSegmentData[];
  heatmapPoints: CongestionHeatmapPoint[];
  selectedCity: string;
  onSelectSegment?: (segment: RoadSegmentData) => void;
  height?: string;
}

const SEVERITY_COLORS: Record<string, { stroke: string; bg: string; text: string; glow: string; label: string }> = {
  LOW: {
    stroke: "#10b981",
    bg: "bg-emerald-950/80 border-emerald-700/50",
    text: "text-emerald-400",
    glow: "rgba(16, 185, 129, 0.4)",
    label: "Low (Green)",
  },
  MEDIUM: {
    stroke: "#eab308",
    bg: "bg-yellow-950/80 border-yellow-700/50",
    text: "text-yellow-400",
    glow: "rgba(234, 179, 8, 0.5)",
    label: "Moderate (Yellow)",
  },
  HIGH: {
    stroke: "#f97316",
    bg: "bg-orange-950/80 border-orange-700/50",
    text: "text-orange-400",
    glow: "rgba(249, 115, 22, 0.6)",
    label: "High (Orange)",
  },
  SEVERE: {
    stroke: "#ef4444",
    bg: "bg-red-950/80 border-red-700/50",
    text: "text-red-400",
    glow: "rgba(239, 68, 68, 0.8)",
    label: "Severe (Red)",
  },
};

// City center reference for Leaflet map centering
const CITY_CENTERS: Record<string, { lat: number; lon: number; zoom: number }> = {
  Delhi:     { lat: 28.5800, lon: 77.2000, zoom: 12 },
  Mumbai:    { lat: 19.0600, lon: 72.8800, zoom: 12 },
  Bangalore: { lat: 12.9700, lon: 77.6500, zoom: 12 },
  All:       { lat: 22.0000, lon: 78.0000, zoom: 5  },
};

// Dark basemap tile URL (CartoDB dark for congestion visibility)
const DARK_TILE_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const DARK_TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>';

export const CongestionMap: React.FC<CongestionMapProps> = ({
  segments,
  heatmapPoints,
  selectedCity,
  onSelectSegment,
  height = "520px",
}) => {
  const [viewMode, setViewMode] = useState<"corridors" | "heatmap" | "hybrid">("hybrid");
  const [activeSegment, setActiveSegment] = useState<RoadSegmentData | null>(segments[0] || null);

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const corridorLayerRef = useRef<L.LayerGroup | null>(null);
  const heatmapLayerRef = useRef<L.LayerGroup | null>(null);
  const markerLayerRef = useRef<L.LayerGroup | null>(null);

  // Filter segments by city
  const filteredSegments = selectedCity === "All"
    ? segments
    : segments.filter((s) => s.city.toLowerCase() === selectedCity.toLowerCase());

  const handleSegmentClick = (seg: RoadSegmentData) => {
    setActiveSegment(seg);
    if (onSelectSegment) onSelectSegment(seg);
  };

  // Initialize Leaflet map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const cityKey = selectedCity in CITY_CENTERS ? selectedCity : "Delhi";
    const center = CITY_CENTERS[cityKey];

    const map = L.map(mapContainerRef.current, {
      center: [center.lat, center.lon],
      zoom: center.zoom,
      zoomControl: false,
      attributionControl: true,
    });

    L.tileLayer(DARK_TILE_URL, {
      maxZoom: 19,
      attribution: DARK_TILE_ATTR,
    }).addTo(map);

    corridorLayerRef.current = L.layerGroup().addTo(map);
    heatmapLayerRef.current = L.layerGroup().addTo(map);
    markerLayerRef.current = L.layerGroup().addTo(map);

    mapRef.current = map;

    // Fix rendering when container resizes
    setTimeout(() => map.invalidateSize(), 150);
    setTimeout(() => map.invalidateSize(), 500);

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Fly to city when selectedCity changes
  useEffect(() => {
    if (!mapRef.current) return;
    const cityKey = selectedCity in CITY_CENTERS ? selectedCity : "Delhi";
    const center = CITY_CENTERS[cityKey];
    mapRef.current.flyTo([center.lat, center.lon], center.zoom, { duration: 1.2 });
  }, [selectedCity]);

  // Render corridors, heatmap circles, and markers
  useEffect(() => {
    if (!mapRef.current) return;

    // Clear all layers
    corridorLayerRef.current?.clearLayers();
    heatmapLayerRef.current?.clearLayers();
    markerLayerRef.current?.clearLayers();

    // 1. HEATMAP LAYER
    if (viewMode === "heatmap" || viewMode === "hybrid") {
      heatmapPoints.forEach((pt) => {
        let fillColor = "rgba(16, 185, 129, 0.35)";
        if (pt.intensity > 0.75) fillColor = "rgba(239, 68, 68, 0.55)";
        else if (pt.intensity > 0.55) fillColor = "rgba(249, 115, 22, 0.5)";
        else if (pt.intensity > 0.3) fillColor = "rgba(245, 158, 11, 0.4)";

        const radius = 200 + pt.intensity * 600; // meters

        L.circle([pt.lat, pt.lon], {
          radius,
          color: "transparent",
          fillColor,
          fillOpacity: viewMode === "heatmap" ? 0.7 : 0.45,
        }).bindTooltip(
          `<b>${pt.name}</b><br/>Score: ${pt.score.toFixed(1)}<br/>Speed: ${pt.speed_kmh.toFixed(1)} km/h`,
          { className: "congestion-tooltip" }
        ).addTo(heatmapLayerRef.current!);
      });
    }

    // 2. ROAD SEGMENT POLYLINES
    if (viewMode === "corridors" || viewMode === "hybrid") {
      filteredSegments.forEach((seg) => {
        if (!seg.polyline || seg.polyline.length < 2) return;

        const latlngs: L.LatLngExpression[] = seg.polyline.map((p) => [p.lat, p.lon]);
        const color = SEVERITY_COLORS[seg.severity]?.stroke || "#94a3b8";
        const isSelected = activeSegment?.segment_id === seg.segment_id;

        // Glow track (thicker, more transparent)
        L.polyline(latlngs, {
          color,
          weight: isSelected ? 10 : 6,
          opacity: 0.35,
          lineCap: "round",
          lineJoin: "round",
        }).addTo(corridorLayerRef.current!);

        // Main corridor line
        const mainLine = L.polyline(latlngs, {
          color,
          weight: isSelected ? 5 : 3,
          opacity: seg.severity === "SEVERE" ? 0.95 : 0.8,
          lineCap: "round",
          lineJoin: "round",
          dashArray: seg.severity === "SEVERE" ? "8, 6" : undefined,
        }).addTo(corridorLayerRef.current!);

        mainLine.bindTooltip(
          `<b>${seg.name}</b><br/>Speed: ${seg.current_speed.toFixed(1)} km/h | Score: ${seg.congestion_score.toFixed(1)}/100<br/>Severity: ${seg.severity}`,
          { sticky: true, className: "congestion-tooltip" }
        );

        mainLine.on("click", () => handleSegmentClick(seg));
      });
    }

    // 3. BOTTLENECK MARKERS
    if (viewMode === "corridors" || viewMode === "hybrid") {
      filteredSegments.forEach((seg) => {
        if (!seg.polyline || seg.polyline.length === 0) return;
        const mid = seg.polyline[Math.floor(seg.polyline.length / 2)];
        const color = SEVERITY_COLORS[seg.severity]?.stroke || "#94a3b8";
        const isSelected = activeSegment?.segment_id === seg.segment_id;

        // Only show markers for HIGH/SEVERE or selected
        if (seg.severity !== "HIGH" && seg.severity !== "SEVERE" && !isSelected) return;

        const markerIcon = L.divIcon({
          className: "congestion-marker",
          html: `<div style="
            width: ${isSelected ? "16px" : "12px"};
            height: ${isSelected ? "16px" : "12px"};
            background: ${color};
            border: 2px solid #0f172a;
            border-radius: 50%;
            box-shadow: 0 0 ${seg.is_bottleneck ? "12px" : "6px"} ${color};
            ${seg.is_bottleneck ? "animation: pulse 1.5s infinite;" : ""}
          "></div>`,
          iconSize: [isSelected ? 16 : 12, isSelected ? 16 : 12],
          iconAnchor: [isSelected ? 8 : 6, isSelected ? 8 : 6],
        });

        L.marker([mid.lat, mid.lon], { icon: markerIcon })
          .bindTooltip(
            `<b>${seg.name}</b>${seg.is_bottleneck ? "<br/>&#9888; Bottleneck Active" : ""}`,
            { className: "congestion-tooltip" }
          )
          .on("click", () => handleSegmentClick(seg))
          .addTo(markerLayerRef.current!);
      });
    }
  }, [viewMode, filteredSegments, heatmapPoints, activeSegment]);

  return (
    <div
      className="relative w-full rounded-2xl overflow-hidden border border-gray-800 bg-gray-950 shadow-2xl flex flex-col select-none"
      style={{ height }}
    >
      {/* Inject CSS for marker animation and tooltips */}
      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.6); opacity: 0.5; }
        }
        .congestion-tooltip {
          background: rgba(15, 23, 42, 0.92) !important;
          color: #e2e8f0 !important;
          border: 1px solid rgba(100, 116, 139, 0.4) !important;
          border-radius: 8px !important;
          padding: 6px 10px !important;
          font-size: 11px !important;
          font-family: ui-monospace, monospace !important;
          box-shadow: 0 4px 16px rgba(0,0,0,0.5) !important;
        }
        .congestion-tooltip .leaflet-tooltip-tip {
          border-top-color: rgba(15, 23, 42, 0.92) !important;
        }
        .congestion-marker { background: transparent !important; border: none !important; }
      `}</style>

      {/* Map Control Toolbar */}
      <div className="absolute top-4 left-4 z-[1000] flex flex-wrap items-center gap-2 bg-gray-900/90 backdrop-blur-md border border-gray-800 rounded-xl p-1.5 shadow-lg">
        <button
          onClick={() => setViewMode("hybrid")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            viewMode === "hybrid"
              ? "bg-indigo-600 text-white shadow-sm"
              : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          Hybrid GIS
        </button>
        <button
          onClick={() => setViewMode("heatmap")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            viewMode === "heatmap"
              ? "bg-gradient-to-r from-orange-500 to-red-600 text-white shadow-sm"
              : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
          }`}
        >
          <Flame className="w-3.5 h-3.5" />
          Congestion Heatmap
        </button>
        <button
          onClick={() => setViewMode("corridors")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            viewMode === "corridors"
              ? "bg-indigo-600 text-white shadow-sm"
              : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
          }`}
        >
          <Gauge className="w-3.5 h-3.5" />
          Corridors & Bottlenecks
        </button>
      </div>

      {/* Segment Count + Zoom Controls */}
      <div className="absolute top-4 right-4 z-[1000] flex items-center gap-2">
        <div className="bg-gray-900/90 backdrop-blur-md border border-gray-800 rounded-xl px-3 py-1.5 text-xs text-gray-300 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="font-mono">{filteredSegments.length} Segments Active</span>
        </div>
        <div className="flex bg-gray-900/90 backdrop-blur-md border border-gray-800 rounded-xl p-1">
          <button
            onClick={() => mapRef.current?.zoomIn()}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => mapRef.current?.zoomOut()}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Leaflet Map Container */}
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Selected Segment Inspection Card */}
      {activeSegment && (
        <div className="absolute bottom-4 left-4 z-[1000] max-w-sm bg-gray-900/95 backdrop-blur-md border border-gray-800 rounded-2xl p-4 shadow-2xl text-left animate-in fade-in slide-in-from-bottom-3 duration-200">
          <div className="flex items-start justify-between gap-3 mb-2">
            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-gray-500 block">
                {activeSegment.segment_id} • {activeSegment.city} • {activeSegment.road_type}
              </span>
              <h4 className="text-sm font-semibold text-white leading-snug line-clamp-2">
                {activeSegment.name}
              </h4>
            </div>
            <span
              className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border ${
                SEVERITY_COLORS[activeSegment.severity]?.bg
              } ${SEVERITY_COLORS[activeSegment.severity]?.text}`}
            >
              {activeSegment.severity}
            </span>
          </div>

          {/* Metric Bars */}
          <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-gray-800/80 text-xs">
            <div>
              <span className="text-gray-400 text-[11px] block">Current Speed</span>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                <span className="text-lg font-bold text-white font-mono">
                  {activeSegment.current_speed.toFixed(1)}
                </span>
                <span className="text-[11px] text-gray-500">km/h</span>
              </div>
              <span className="text-[10px] text-gray-500">
                Base: {activeSegment.baseline_speed.toFixed(0)} km/h
              </span>
            </div>

            <div>
              <span className="text-gray-400 text-[11px] block">Congestion Score</span>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                <span className={`text-lg font-bold font-mono ${SEVERITY_COLORS[activeSegment.severity]?.text}`}>
                  {activeSegment.congestion_score.toFixed(1)}
                </span>
                <span className="text-[11px] text-gray-500">/ 100</span>
              </div>
              <div className="flex items-center gap-2 text-[10px] text-gray-400 mt-0.5">
                <span>Delay: <strong className="text-amber-300">+{activeSegment.route_delay_minutes || 0}m</strong></span>
                <span>•</span>
                <span>Density: {(activeSegment.density * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>

          {/* Bottleneck Status Banner */}
          {activeSegment.is_bottleneck ? (
            <div className="mt-3 bg-red-950/60 border border-red-800/40 rounded-xl px-2.5 py-1.5 flex items-center gap-2 text-xs text-red-300">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 animate-bounce" />
              <span className="text-[11px] font-medium">
                Bottleneck active ({activeSegment.active_vehicles} queued vehicles)
              </span>
            </div>
          ) : (
            <div className="mt-3 bg-emerald-950/50 border border-emerald-800/30 rounded-xl px-2.5 py-1.5 flex items-center gap-2 text-xs text-emerald-300">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span className="text-[11px]">Corridor flowing within baseline tolerances</span>
            </div>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-4 right-4 z-[1000] bg-gray-900/90 backdrop-blur-md border border-gray-800 rounded-xl p-3 shadow-lg flex flex-col gap-1.5 text-xs text-gray-300">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">
          Congestion Severity
        </span>
        <div className="flex items-center gap-3">
          {Object.entries(SEVERITY_COLORS).map(([sev, styling]) => (
            <div key={sev} className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: styling.stroke }}
              />
              <span className="text-[11px] text-gray-400">{sev}</span>
            </div>
          ))}
        </div>

        {/* Heatmap Gradient Bar */}
        <div className="mt-1 pt-1.5 border-t border-gray-800 flex flex-col gap-1">
          <span className="text-[10px] text-gray-500">Thermal Heatmap Intensity</span>
          <div className="w-full h-1.5 rounded-full bg-gradient-to-r from-emerald-500 via-amber-500 via-orange-500 to-red-500" />
          <div className="flex justify-between text-[9px] text-gray-500 font-mono">
            <span>0% Free</span>
            <span>100% Jam</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CongestionMap;
