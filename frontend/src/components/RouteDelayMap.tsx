// src/components/RouteDelayMap.tsx
// Interactive GIS Bus Route & Delayed Sections Visualizer (Phase 22)

import React, { useState } from "react";
import {
  MapPin, AlertTriangle, CheckCircle2, Clock,
  Layers, Droplets, Construction, Flame, ArrowRight
} from "lucide-react";

export interface CoordinatePoint {
  lat: number;
  lon: number;
}

export interface RouteSectionData {
  section_id: string;
  name: string;
  length_km: number;
  scheduled_time_minutes: number;
  observed_time_minutes: number;
  delay_minutes: number;
  is_delayed_section: boolean;
  delay_severity: string;  // NORMAL, MODERATE, SEVERE
  contributing_factor: string;
  polyline: CoordinatePoint[];
  active_defects_count?: number;
  active_congestion_events_count?: number;
}

export interface RouteStopData {
  stop_id: string;
  name: string;
  lat: number;
  lon: number;
  sequence: number;
  scheduled_arrival_offset_min: number;
  observed_delay_min: number;
}

interface RouteDelayMapProps {
  routeName: string;
  sections: RouteSectionData[];
  stops?: RouteStopData[];
  height?: string;
  onSelectSection?: (section: RouteSectionData) => void;
}

export const RouteDelayMap: React.FC<RouteDelayMapProps> = ({
  routeName,
  sections,
  stops = [],
  height = "480px",
  onSelectSection,
}) => {
  const [selectedSection, setSelectedSection] = useState<RouteSectionData | null>(
    sections.find((s) => s.is_delayed_section) || sections[0] || null
  );

  // Compute dynamic bounding box
  const allPoints: CoordinatePoint[] = [];
  sections.forEach((s) => s.polyline.forEach((p) => allPoints.push(p)));
  stops.forEach((st) => allPoints.push({ lat: st.lat, lon: st.lon }));

  let minLat = 28.58, maxLat = 28.66, minLon = 77.20, maxLon = 77.33;
  if (allPoints.length > 0) {
    minLat = Math.min(...allPoints.map((p) => p.lat)) - 0.012;
    maxLat = Math.max(...allPoints.map((p) => p.lat)) + 0.012;
    minLon = Math.min(...allPoints.map((p) => p.lon)) - 0.015;
    maxLon = Math.max(...allPoints.map((p) => p.lon)) + 0.015;
  }

  // Projection helper: GPS -> SVG 0..100% canvas coordinates
  const projectCoords = (lat: number, lon: number) => {
    const latSpan = maxLat - minLat || 0.05;
    const lonSpan = maxLon - minLon || 0.05;
    const y = ((maxLat - lat) / latSpan) * 76 + 12;
    const x = ((lon - minLon) / lonSpan) * 76 + 12;
    return {
      x: Math.max(6, Math.min(94, x)),
      y: Math.max(6, Math.min(94, y)),
    };
  };

  const handleSectionClick = (sec: RouteSectionData) => {
    setSelectedSection(sec);
    if (onSelectSection) onSelectSection(sec);
  };

  return (
    <div
      className="relative w-full rounded-2xl overflow-hidden border border-gray-800 bg-gray-950 shadow-2xl flex flex-col select-none"
      style={{ height }}
    >
      {/* Top Map Banner */}
      <div className="absolute top-4 left-4 z-20 bg-gray-900/90 backdrop-blur-md border border-gray-800 rounded-xl px-3.5 py-2 shadow-lg flex items-center gap-3">
        <div className="p-1.5 bg-indigo-500/20 rounded-lg text-indigo-400">
          <Layers className="w-4 h-4" />
        </div>
        <div>
          <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400 block font-bold">
            Live Route Geometry
          </span>
          <span className="text-xs font-bold text-white block">
            {routeName}
          </span>
        </div>
      </div>

      {/* Delayed Sections Alert Pill */}
      <div className="absolute top-4 right-4 z-20 flex items-center gap-2">
        <div className="bg-red-950/80 backdrop-blur-md border border-red-800/60 rounded-xl px-3 py-1.5 text-xs text-red-300 flex items-center gap-2 shadow-lg">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
          <span className="font-bold">
            {sections.filter((s) => s.is_delayed_section).length} Delayed Corridor Sections
          </span>
        </div>
      </div>

      {/* SVG GIS Canvas */}
      <div className="relative w-full h-full">
        {/* Dark Cartographic Vector Grid Background */}
        <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] opacity-40" />

        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          <defs>
            {/* Pulsing severe delay glow filter */}
            <filter id="delayGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="2.2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* 1. ROUTE POLYLINES */}
          {sections.map((sec) => {
            if (!sec.polyline || sec.polyline.length < 2) return null;
            const pointsStr = sec.polyline
              .map((p) => {
                const { x, y } = projectCoords(p.lat, p.lon);
                return `${x},${y}`;
              })
              .join(" ");

            const isSelected = selectedSection?.section_id === sec.section_id;
            const isDelayed = sec.is_delayed_section;

            // Normal: Cool Blue (#38bdf8), Delayed: Vivid Red/Orange (#ef4444 / #f97316)
            const strokeColor = isDelayed ? "#ef4444" : "#38bdf8";

            return (
              <g
                key={`sec-poly-${sec.section_id}`}
                className="cursor-pointer transition-all"
                onClick={() => handleSectionClick(sec)}
              >
                {/* Outer halo / glow for delayed sections */}
                {isDelayed && (
                  <polyline
                    points={pointsStr}
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth={isSelected ? "6.5" : "5.0"}
                    strokeOpacity="0.45"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    filter="url(#delayGlow)"
                  />
                )}

                {/* Main corridor stroke */}
                <polyline
                  points={pointsStr}
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={isSelected ? "4.0" : (isDelayed ? "3.2" : "2.4")}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeDasharray={isDelayed ? "4,1.5" : "none"}
                />

                {/* Center contrast line */}
                <polyline
                  points={pointsStr}
                  fill="none"
                  stroke="#ffffff"
                  strokeWidth="0.8"
                  strokeOpacity="0.8"
                  strokeLinecap="round"
                />
              </g>
            );
          })}

          {/* 2. DELAY WARNING ICONS AT MIDPOINT OF DELAYED SECTIONS */}
          {sections
            .filter((s) => s.is_delayed_section)
            .map((sec) => {
              const mid = sec.polyline[Math.floor(sec.polyline.length / 2)];
              const { x, y } = projectCoords(mid.lat, mid.lon);

              return (
                <g
                  key={`delay-marker-${sec.section_id}`}
                  transform={`translate(${x}, ${y})`}
                  className="cursor-pointer"
                  onClick={() => handleSectionClick(sec)}
                >
                  <circle r="3.2" fill="#ef4444" className="animate-ping" opacity="0.6" />
                  <circle r="2.4" fill="#991b1b" stroke="#f87171" strokeWidth="0.6" />
                  <text
                    x="0"
                    y="1.0"
                    textAnchor="middle"
                    fill="#ffffff"
                    fontSize="2.4"
                    fontWeight="bold"
                  >
                    !
                  </text>
                </g>
              );
            })}

          {/* 3. BUS STOP PINS */}
          {stops.map((stop) => {
            const { x, y } = projectCoords(stop.lat, stop.lon);
            const hasDelay = stop.observed_delay_min > 3.0;

            return (
              <g
                key={`stop-${stop.stop_id}`}
                transform={`translate(${x}, ${y})`}
                className="cursor-pointer group"
              >
                <circle
                  r="1.8"
                  fill={hasDelay ? "#f97316" : "#0284c7"}
                  stroke="#ffffff"
                  strokeWidth="0.6"
                />
                <text
                  x="0"
                  y="-2.8"
                  textAnchor="middle"
                  fill="#cbd5e1"
                  fontSize="2.2"
                  fontWeight="600"
                  className="opacity-80 group-hover:opacity-100"
                >
                  {stop.sequence}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Selected Section Inspection Card */}
        {selectedSection && (
          <div className="absolute bottom-4 left-4 z-20 max-w-sm bg-gray-900/95 backdrop-blur-md border border-gray-800 rounded-2xl p-4 shadow-2xl text-left animate-in fade-in duration-200">
            <div className="flex items-start justify-between gap-3 mb-2">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-gray-500 block">
                  {selectedSection.section_id} • {selectedSection.length_km} km
                </span>
                <h4 className="text-xs font-bold text-white leading-snug line-clamp-2">
                  {selectedSection.name}
                </h4>
              </div>

              <span
                className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border ${
                  selectedSection.is_delayed_section
                    ? "bg-red-950/80 text-red-400 border-red-800/60"
                    : "bg-emerald-950/80 text-emerald-400 border-emerald-800/60"
                }`}
              >
                {selectedSection.is_delayed_section ? "Delayed Section" : "Normal Flow"}
              </span>
            </div>

            {/* Travel Time Comparison */}
            <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-gray-800/80 text-xs">
              <div className="bg-gray-950/70 p-2 rounded-xl border border-gray-800/60">
                <span className="text-gray-400 text-[10px] block">Scheduled</span>
                <span className="text-sm font-bold text-white font-mono">
                  {selectedSection.scheduled_time_minutes} min
                </span>
              </div>

              <div className="bg-gray-950/70 p-2 rounded-xl border border-gray-800/60">
                <span className="text-gray-400 text-[10px] block">Observed</span>
                <span className={`text-sm font-bold font-mono ${selectedSection.is_delayed_section ? "text-red-400" : "text-emerald-400"}`}>
                  {selectedSection.observed_time_minutes} min
                </span>
              </div>
            </div>

            {/* Contributing Factor Alert */}
            <div className={`mt-2.5 p-2 rounded-xl border flex items-center justify-between text-xs ${
              selectedSection.is_delayed_section
                ? "bg-red-950/50 border-red-800/40 text-red-200"
                : "bg-gray-950/60 border-gray-800 text-gray-300"
            }`}>
              <div className="flex items-center gap-1.5">
                <AlertTriangle className={`w-3.5 h-3.5 ${selectedSection.is_delayed_section ? "text-red-400" : "text-gray-500"}`} />
                <span className="text-[11px] font-medium">{selectedSection.contributing_factor}</span>
              </div>
              <span className={`font-mono font-bold text-xs ${selectedSection.is_delayed_section ? "text-red-400" : "text-emerald-400"}`}>
                {selectedSection.delay_minutes > 0 ? `+${selectedSection.delay_minutes}m` : "On Time"}
              </span>
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="absolute bottom-4 right-4 z-20 bg-gray-900/90 backdrop-blur-md border border-gray-800 rounded-xl p-3 shadow-lg text-xs text-gray-300 space-y-1.5">
          <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block">
            Corridor Legend
          </span>
          <div className="flex items-center gap-2">
            <span className="w-4 h-1 rounded bg-sky-400" />
            <span className="text-[11px]">Normal Section (On Time)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-1 rounded bg-red-500" />
            <span className="text-[11px] text-red-300 font-semibold">Delayed Section (Highlight)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-500 border border-white" />
            <span className="text-[11px]">Bus Stop Node</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RouteDelayMap;
