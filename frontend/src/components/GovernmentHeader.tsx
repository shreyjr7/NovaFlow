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
    <header className="w-full bg-[#16192E] text-slate-100 border-b border-[#232746] px-5 py-2.5 text-xs flex flex-wrap items-center justify-between shadow-md sticky top-0 z-50">
      {/* Left: Jurisdiction & National Crest (Image Style) */}
      <div className="flex items-center gap-3">
        {/* Double-ring circular government emblem */}
        <div className="w-9 h-9 rounded-full border border-slate-400/60 bg-[#1E2342] flex items-center justify-center text-white shadow-inner ring-2 ring-slate-500/20">
          <div className="w-7 h-7 rounded-full border border-amber-400/40 bg-gradient-to-br from-slate-800 to-[#16192E] flex items-center justify-center">
            <Shield size={14} className="text-amber-400" />
          </div>
        </div>
        <div>
          <div className="font-extrabold text-white text-[13px] tracking-wider uppercase flex items-center gap-2 font-sans">
            <span>National Defence &amp; Surveillance</span>
          </div>
          <div className="text-[11px] text-[#8E9BB0] font-medium">
            Government of India &nbsp;|&nbsp; National Security &amp; Strategic Surveillance Directorate
          </div>
        </div>
      </div>

      {/* Center: Live Operational Status */}
      <div className="hidden lg:flex items-center gap-2 px-3 py-1 text-[11px] font-medium text-slate-300">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse ring-2 ring-emerald-500/30" />
        <span className="text-slate-200">System Operational</span>
      </div>

      {/* Right: Notifications, High Contrast Toggle, Officer Profile */}
      <div className="flex items-center gap-3">
        {/* Quick Navigation Pills */}
        <div className="hidden xl:flex items-center gap-1.5 mr-2">
          <Link
            to="/"
            className={`px-3 py-1 rounded-md text-xs font-semibold transition ${
              location.pathname === "/"
                ? "bg-[#282F5A] text-white shadow-sm"
                : "text-[#8E9BB0] hover:text-white hover:bg-[#202547]"
            }`}
          >
            Dashboard
          </Link>
          <Link
            to="/gis"
            className={`px-3 py-1 rounded-md text-xs font-semibold transition ${
              location.pathname === "/gis"
                ? "bg-[#C85A17] text-white shadow-sm"
                : "text-[#8E9BB0] hover:text-white hover:bg-[#202547]"
            }`}
          >
            GIS Map
          </Link>
          <Link
            to="/road-defects"
            className={`px-3 py-1 rounded-md text-xs font-semibold transition ${
              location.pathname === "/road-defects"
                ? "bg-[#282F5A] text-white shadow-sm"
                : "text-[#8E9BB0] hover:text-white hover:bg-[#202547]"
            }`}
          >
            Work Orders
          </Link>
        </div>

        {/* Notification Bell */}
        <button
          className="relative p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-[#202547] transition"
          title="Notifications"
        >
          <AlertTriangle size={16} />
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-amber-500 ring-2 ring-[#16192E]" />
        </button>

        {/* High Contrast Pill (Image Style) */}
        <button
          onClick={() => {}}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#202547] hover:bg-[#282F5A] text-slate-200 border border-[#2E3558] transition shadow-sm"
          title="Toggle High Contrast"
        >
          <span>🌙</span>
          <span>High Contrast</span>
        </button>

        {/* User / Officer Profile Capsule (Image Style: AM Admin User) */}
        <div className="flex items-center gap-2 pl-2 border-l border-[#232746] cursor-pointer group">
          <div className="w-8 h-8 rounded-full bg-[#282F5A] border border-slate-500/40 flex items-center justify-center text-xs font-bold text-white shadow-sm">
            AM
          </div>
          <div className="hidden sm:block text-left">
            <div className="text-xs font-bold text-white leading-tight flex items-center gap-1">
              <span>Admin User</span>
              <span className="text-[10px] text-slate-400 group-hover:text-white transition-transform">▾</span>
            </div>
            <div className="text-[10px] text-[#8E9BB0] leading-tight">
              Command Director
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default GovernmentHeader;
