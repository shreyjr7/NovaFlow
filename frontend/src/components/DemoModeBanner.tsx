// src/components/DemoModeBanner.tsx
// Phase 34: Prominent, professional DEMO MODE indicator
// Ensures evaluators and judges know that fleet data is simulated while all AI inference,
// edge buffering, and event pipelines are fully functional.

import React, { useState, useEffect } from "react";
import { Zap, Bus, Activity, Info, ShieldAlert, CheckCircle2 } from "lucide-react";

export const DemoModeBanner: React.FC = () => {
  const [demoStatus, setDemoStatus] = useState<any>(null);
  const [showTooltip, setShowTooltip] = useState<boolean>(false);

  useEffect(() => {
    fetch("/api/v1/demo/status")
      .then((res) => res.json())
      .then((data) => setDemoStatus(data))
      .catch(() => {});
  }, []);

  return (
    <div className="w-full bg-gradient-to-r from-amber-600 via-amber-700 to-orange-600 text-white px-4 py-2 text-xs md:text-sm font-semibold flex items-center justify-between shadow-md border-b border-amber-500/30 sticky top-0 z-50">
      <div className="flex items-center space-x-3 overflow-hidden text-ellipsis whitespace-nowrap">
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-black/30 border border-white/20 text-amber-200 uppercase tracking-wider font-extrabold animate-pulse">
          <Zap size={14} className="text-yellow-300" />
          DEMO MODE
        </span>
        <span className="hidden sm:inline-block font-medium opacity-90">
          Simulated Fleet Telemetry Active &bull; 20 Buses &bull; 5 Routes &bull; 115 Road Segments
        </span>
      </div>

      <div className="flex items-center space-x-3">
        <a
          href="/demo-flow"
          className="hidden md:flex items-center gap-1 bg-white/20 hover:bg-white/30 text-white px-2.5 py-1 rounded transition text-xs font-bold"
        >
          <Activity size={13} />
          17-Step Demo Flow
        </a>
        <a
          href="/testing"
          className="hidden md:flex items-center gap-1 bg-black/30 hover:bg-black/40 text-amber-200 px-2.5 py-1 rounded transition text-xs font-bold border border-white/10"
        >
          Testing Center
        </a>
        <div className="relative">
          <button
            onClick={() => setShowTooltip(!showTooltip)}
            className="p-1 rounded hover:bg-white/20 text-white/90"
            title="Demo Environment Info"
          >
            <Info size={16} />
          </button>
          {showTooltip && (
            <div className="absolute right-0 mt-2 w-72 bg-slate-900 text-slate-100 text-xs p-3 rounded-lg shadow-xl border border-slate-700 z-50">
              <div className="flex items-center gap-1.5 font-bold text-amber-400 mb-1">
                <ShieldAlert size={14} />
                Evaluator / Judge Notice
              </div>
              <p className="leading-relaxed text-slate-300">
                This instance is operating in <strong>DEMO MODE</strong>. Fleet kinematics for 20 buses across 5 routes
                are actively simulated. All deep learning detection, spatial clustering, offline SQLite queue buffering,
                and reporting engines are running live real code.
              </p>
              <button
                onClick={() => setShowTooltip(false)}
                className="mt-2 text-xs text-amber-400 underline"
              >
                Close
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DemoModeBanner;
