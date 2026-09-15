// src/components/CongestionMap.tsx
// Interactive GIS Map and Thermal Congestion Heatmap Component

import React, { useState } from "react";
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
    stroke: "#10b981", // Green
    bg: "bg-emerald-950/80 border-emerald-700/50",
    text: "text-emerald-400",
    glow: "rgba(16, 185, 129, 0.4)",
    label: "Low (Green)",
  },
  MEDIUM: {
    stroke: "#eab308", // Yellow (Moderate)
    bg: "bg-yellow-950/80 border-yellow-700/50",
    text: "text-yellow-400",
    glow: "rgba(234, 179, 8, 0.5)",
    label: "Moderate (Yellow)",
  },
  HIGH: {
    stroke: "#f97316", // Orange
    bg: "bg-orange-950/80 border-orange-700/50",
    text: "text-orange-400",
    glow: "rgba(249, 115, 22, 0.6)",
    label: "High (Orange)",
  },
  SEVERE: {
    stroke: "#ef4444", // Red
    bg: "bg-red-950/80 border-red-700/50",
    text: "text-red-400",
    glow: "rgba(239, 68, 68, 0.8)",
    label: "Severe (Red)",
  },
};

// City center reference bounds for GIS coordinate projection
const CITY_BOUNDS: Record<string, { minLat: number; maxLat: number; minLon: number; maxLon: number }> = {
  Delhi: { minLat: 28.48, maxLat: 28.65, minLon: 77.10, maxLon: 77.30 },
  Mumbai: { minLat: 19.00, maxLat: 19.12, minLon: 72.82, maxLon: 72.95 },
  Bangalore: { minLat: 12.88, maxLat: 13.06, minLon: 77.56, maxLon: 77.73 },
  All: { minLat: 12.5, maxLat: 29.0, minLon: 72.5, maxLon: 78.0 },
};

export const CongestionMap: React.FC<CongestionMapProps> = ({
  segments,
  heatmapPoints,
  selectedCity,
  onSelectSegment,
  height = "520px",
}) => {
  const [viewMode, setViewMode] = useState<"corridors" | "heatmap" | "hybrid">("hybrid");
  const [activeSegment, setActiveSegment] = useState<RoadSegmentData | null>(segments[0] || null);
  const [zoomLevel, setZoomLevel] = useState<number>(1);

  // Filter segments by city
  const filteredSegments = selectedCity === "All"
    ? segments
    : segments.filter((s) => s.city.toLowerCase() === selectedCity.toLowerCase());

  // Derive bounding box for current view
  const cityKey = selectedCity in CITY_BOUNDS ? selectedCity : "Delhi";
  const bounds = CITY_BOUNDS[cityKey] || CITY_BOUNDS["Delhi"];

  // Helper to project GPS lat/lon to SVG 0-100% canvas coordinates
  const projectCoords = (lat: number, lon: number) => {
    const latSpan = bounds.maxLat - bounds.minLat || 0.1;
    const lonSpan = bounds.maxLon - bounds.minLon || 0.1;

    // Invert lat for SVG Y (high lat at top)
    const y = ((bounds.maxLat - lat) / latSpan) * 80 + 10;
    const x = ((lon - bounds.minLon) / lonSpan) * 80 + 10;
    return {
      x: Math.max(5, Math.min(95, x)),
      y: Math.max(5, Math.min(95, y)),
    };
  };

  const handleSegmentClick = (seg: RoadSegmentData) => {
    setActiveSegment(seg);
    if (onSelectSegment) onSelectSegment(seg);
  };

  return (
    <div
      className="relative w-full rounded-2xl overflow-hidden border border-gray-800 bg-gray-950 shadow-2xl flex flex-col select-none"
      style={{ height }}
    >
      {/* Map Control Toolbar */}
      <div className="absolute top-4 left-4 z-20 flex flex-wrap items-center gap-2 bg-gray-900/90 backdrop-blur-md border border-gray-800 rounded-xl p-1.5 shadow-lg">
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

      {/* Zoom / Map Utilities */}
      <div className="absolute top-4 right-4 z-20 flex items-center gap-2">
        <div className="bg-gray-900/90 backdrop-blur-md border border-gray-800 rounded-xl px-3 py-1.5 text-xs text-gray-300 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="font-mono">{filteredSegments.length} Segments Active</span>
        </div>
        <div className="flex bg-gray-900/90 backdrop-blur-md border border-gray-800 rounded-xl p-1">
          <button
            onClick={() => setZoomLevel((z) => Math.min(2, z + 0.2))}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setZoomLevel((z) => Math.max(0.8, z - 0.2))}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* SVG GIS Canvas */}
      <div className="relative w-full h-full overflow-hidden">
        {/* Dark Cartographic Vector Grid Background */}
        <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] opacity-40" />

        <svg
          className="absolute inset-0 w-full h-full transition-transform duration-300"
          style={{ transform: `scale(${zoomLevel})` }}
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
        >
          <defs>
            {/* Heatmap blur filter */}
            <filter id="heatBlur" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="blur" />
            </filter>

            {/* Pulsing severe bottleneck glow */}
            <filter id="severeGlow">
              <feGaussianBlur stdDeviation="2.5" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* 1. HEATMAP LAYER (when enabled) */}
          {(viewMode === "heatmap" || viewMode === "hybrid") && (
            <g id="heatmap-layer" filter="url(#heatBlur)" opacity={viewMode === "heatmap" ? "0.88" : "0.55"}>
              {heatmapPoints.map((pt, idx) => {
                const { x, y } = projectCoords(pt.lat, pt.lon);
                // Radial gradient color according to intensity
                let fillColor = "rgba(16, 185, 129, 0.4)";
                if (pt.intensity > 0.75) fillColor = "rgba(239, 68, 68, 0.9)";
                else if (pt.intensity > 0.55) fillColor = "rgba(249, 115, 22, 0.8)";
                else if (pt.intensity > 0.3) fillColor = "rgba(245, 158, 11, 0.6)";

                const radius = 4 + pt.intensity * 8;
                return (
                  <circle
                    key={`heat-${idx}`}
                    cx={x}
                    cy={y}
                    r={radius}
                    fill={fillColor}
                  />
                );
              })}
            </g>
          )}

          {/* 2. ROAD SEGMENT POLYLINES */}
          {(viewMode === "corridors" || viewMode === "hybrid") && (
            <g id="segments-layer">
              {filteredSegments.map((seg) => {
                if (!seg.polyline || seg.polyline.length < 2) return null;
                const pointsStr = seg.polyline
                  .map((p) => {
                    const { x, y } = projectCoords(p.lat, p.lon);
                    return `${x},${y}`;
                  })
                  .join(" ");

                const color = SEVERITY_COLORS[seg.severity]?.stroke || "#94a3b8";
                const isSelected = activeSegment?.segment_id === seg.segment_id;

                return (
                  <g key={`poly-${seg.segment_id}`} className="cursor-pointer" onClick={() => handleSegmentClick(seg)}>
                    {/* Shadow / Glow track */}
                    <polyline
                      points={pointsStr}
                      fill="none"
                      stroke={color}
                      strokeWidth={isSelected ? "4.5" : "2.8"}
                      strokeOpacity={seg.severity === "SEVERE" ? "0.9" : "0.7"}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      filter={seg.severity === "SEVERE" ? "url(#severeGlow)" : undefined}
                    />
                    {/* Inner high-contrast corridor lane */}
                    <polyline
                      points={pointsStr}
                      fill="none"
                      stroke="#ffffff"
                      strokeWidth={isSelected ? "1.5" : "0.8"}
                      strokeDasharray={seg.severity === "SEVERE" ? "2,2" : "none"}
                      strokeOpacity="0.8"
                      strokeLinecap="round"
                    />
                  </g>
                );
              })}
            </g>
          )}

          {/* 3. BOTTLENECK INCIDENT MARKERS & PULSES */}
          {(viewMode === "corridors" || viewMode === "hybrid") && (
            <g id="markers-layer">
              {filteredSegments.map((seg) => {
                if (!seg.polyline || seg.polyline.length === 0) return null;
                const mid = seg.polyline[Math.floor(seg.polyline.length / 2)];
                const { x, y } = projectCoords(mid.lat, mid.lon);
                const isSelected = activeSegment?.segment_id === seg.segment_id;
                const color = SEVERITY_COLORS[seg.severity]?.stroke || "#94a3b8";

                return (
                  <g
                    key={`marker-${seg.segment_id}`}
                    className="cursor-pointer transition-transform hover:scale-125"
                    onClick={() => handleSegmentClick(seg)}
                    transform={`translate(${x}, ${y})`}
                  >
                    {/* Pulsing ring for active bottlenecks */}
                    {seg.is_bottleneck && (
                      <circle
                        r={isSelected ? "4.5" : "3.2"}
                        fill="none"
                        stroke={color}
                        strokeWidth="0.8"
                        className="animate-ping"
                        opacity="0.75"
                      />
                    )}
                    {/* Center marker point */}
                    <circle
                      r={isSelected ? "2.5" : "1.8"}
                      fill={color}
                      stroke="#0f172a"
                      strokeWidth="0.7"
                    />
                  </g>
                );
              })}
            </g>
          )}
        </svg>

        {/* Selected Segment Inspection Card */}
        {activeSegment && (
          <div className="absolute bottom-4 left-4 z-20 max-w-sm bg-gray-900/95 backdrop-blur-md border border-gray-800 rounded-2xl p-4 shadow-2xl text-left animate-in fade-in slide-in-from-bottom-3 duration-200">
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
        <div className="absolute bottom-4 right-4 z-20 bg-gray-900/90 backdrop-blur-md border border-gray-800 rounded-xl p-3 shadow-lg flex flex-col gap-1.5 text-xs text-gray-300">
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
    </div>
  );
};

export default CongestionMap;
