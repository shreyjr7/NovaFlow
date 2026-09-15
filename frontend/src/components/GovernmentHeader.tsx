// src/components/GovernmentHeader.tsx
import React, { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { Shield, Activity, MapPin, Bus, AlertTriangle, FileText, CheckCircle2 } from "lucide-react";

export const GovernmentHeader: React.FC = () => {
  const [timeStr, setTimeStr] = useState<string>("");
  const location = useLocation();

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString("en-IN", { hour12: true, hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="w-full bg-slate-950 text-slate-200 border-b border-slate-800 px-4 py-2 text-xs flex flex-wrap items-center justify-between shadow-xl sticky top-0 z-50">
      {/* Left: Jurisdiction & Platform Crest */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-blue-600 flex items-center justify-center text-white font-bold shadow-sm">
            <Shield size={14} />
          </div>
          <div>
            <div className="font-extrabold text-white text-[12px] tracking-wide flex items-center gap-2">
              <span>MUNICIPAL TRANSIT & ROAD SAFETY COMMAND</span>
              <span className="hidden md:inline-block px-1.5 py-0.2 rounded text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-600/40 font-mono font-bold">
                PROD-ACTIVE
              </span>
            </div>
            <div className="text-[10px] text-slate-400 font-medium hidden sm:block">
              Integrated Urban Sensing Platform • Public Works & Traffic Department
            </div>
          </div>
        </div>
      </div>

      {/* Center: System Telemetry Status */}
      <div className="hidden lg:flex items-center gap-4 text-[11px] font-mono bg-slate-900/90 px-3 py-1 rounded-lg border border-slate-800">
        <div className="flex items-center gap-1.5 text-emerald-400">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>FLEET SENSING: ONLINE (20 BUSES)</span>
        </div>
        <span className="text-slate-600">|</span>
        <div className="flex items-center gap-1.5 text-blue-400">
          <Activity size={12} />
          <span>EDGE AI PIPELINE: 4 STREAMS</span>
        </div>
        <span className="text-slate-600">|</span>
        <div className="flex items-center gap-1.5 text-amber-400">
          <AlertTriangle size={12} />
          <span>AUTONOMOUS DISPATCH: ACTIVE</span>
        </div>
      </div>

      {/* Right: Quick Navigation & Live Clock */}
      <div className="flex items-center gap-2">
        <Link
          to="/"
          className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition flex items-center gap-1 ${
            location.pathname === "/"
              ? "bg-blue-600 text-white shadow-sm"
              : "bg-slate-900 text-slate-300 hover:text-white hover:bg-slate-800 border border-slate-700/60"
          }`}
        >
          <span>Command Home</span>
        </Link>
        <Link
          to="/gis"
          className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition flex items-center gap-1 ${
            location.pathname === "/gis"
              ? "bg-blue-600 text-white shadow-sm"
              : "bg-slate-900 text-slate-300 hover:text-white hover:bg-slate-800 border border-slate-700/60"
          }`}
        >
          <MapPin size={12} />
          <span>GIS Command</span>
        </Link>
        <Link
          to="/road-defects"
          className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition flex items-center gap-1 ${
            location.pathname === "/road-defects"
              ? "bg-blue-600 text-white shadow-sm"
              : "bg-slate-900 text-slate-300 hover:text-white hover:bg-slate-800 border border-slate-700/60"
          }`}
        >
          <span>Work Orders</span>
        </Link>
        <Link
          to="/reports"
          className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition flex items-center gap-1 ${
            location.pathname === "/reports"
              ? "bg-blue-600 text-white shadow-sm"
              : "bg-slate-900 text-slate-300 hover:text-white hover:bg-slate-800 border border-slate-700/60"
          }`}
        >
          <FileText size={12} />
          <span className="hidden sm:inline">Reports</span>
        </Link>

        {/* Live Clock */}
        {timeStr && (
          <div className="hidden xl:block font-mono text-[11px] text-slate-400 bg-slate-900 px-2.5 py-1 rounded border border-slate-800">
            {timeStr} IST
          </div>
        )}
      </div>
    </header>
  );
};

export default GovernmentHeader;
