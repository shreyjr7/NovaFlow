// src/components/DefectMap.tsx
// GIS map showing road defect events as coloured markers.
// Placeholder implementation – replace with react-leaflet in production.

import React from "react";
import { DefectEvent } from "../pages/RoadDefects/types";

const SEVERITY_COLORS: Record<string, string> = {
  HIGH:   "#ef4444",
  MEDIUM: "#f97316",
  LOW:    "#facc15",
};

const CLASS_ICONS: Record<string, string> = {
  pothole:              "🕳",
  damaged_road:         "🚧",
  waterlogging:         "💧",
  missing_road_divider: "⚠",
  missing_zebra:        "🦓",
  damaged_sign:         "🪧",
  missing_sign:         "❌",
};

interface DefectMapProps {
  events: DefectEvent[];
  height?: string;
}

const DefectMap: React.FC<DefectMapProps> = ({ events, height = "420px" }) => {
  return (
    <div
      className="relative bg-gray-900 border border-gray-700 rounded-xl overflow-hidden w-full"
      style={{ height }}
    >
      {/* Map canvas placeholder */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <p className="text-gray-600 text-sm">
          🗺  Replace with <code className="text-indigo-400">react-leaflet</code> &lt;MapContainer /&gt;
        </p>
      </div>

      {/* Simulated markers overlay */}
      <div className="absolute inset-0 pointer-events-none">
        {events.slice(0, 20).map((ev, i) => {
          // Scatter markers randomly within the div for visual demo
          const top  = 10 + ((i * 37 + 13) % 70);
          const left = 5  + ((i * 53 + 7)  % 85);
          const color = SEVERITY_COLORS[ev.severity || "MEDIUM"];
          const icon  = CLASS_ICONS[ev.cls] || "📍";
          return (
            <div
              key={ev.event_id}
              className="absolute flex flex-col items-center"
              style={{ top: `${top}%`, left: `${left}%` }}
              title={`${ev.label} – ${ev.severity} – conf ${(ev.confidence * 100).toFixed(0)}%`}
            >
              <span className="text-lg leading-none">{icon}</span>
              <div
                className="w-2 h-2 rounded-full mt-0.5"
                style={{ backgroundColor: color }}
              />
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 bg-gray-900/90 border border-gray-700 rounded-lg p-2 flex flex-col gap-1">
        {Object.entries(SEVERITY_COLORS).map(([sev, color]) => (
          <div key={sev} className="flex items-center gap-1.5 text-xs">
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-gray-300">{sev}</span>
          </div>
        ))}
      </div>

      {/* Event count badge */}
      <div className="absolute top-3 right-3 bg-gray-900/90 border border-gray-700 rounded-lg px-2 py-1 text-xs text-gray-300">
        {events.length} events
      </div>
    </div>
  );
};

export default DefectMap;
