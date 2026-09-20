// src/components/GovernmentHeader.tsx
import React, { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { Shield, Activity, MapPin, Bus, AlertTriangle, FileText, CheckCircle2, Menu, X } from "lucide-react";

interface GovernmentHeaderProps {
  mobileSidebarOpen?: boolean;
  onToggleMobileSidebar?: () => void;
}

export const GovernmentHeader: React.FC<GovernmentHeaderProps> = ({
  mobileSidebarOpen = false,
  onToggleMobileSidebar,
}) => {
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
    <header className="w-full bg-[#16192E] text-slate-100 border-b border-[#232746] px-3 sm:px-5 py-2 sm:py-2.5 text-xs flex items-center justify-between shadow-md sticky top-0 z-50 pt-safe">
      {/* Left: Hamburger (Mobile) + Jurisdiction & National Crest */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        {/* Hamburger trigger for mobile drawer */}
        <button
          onClick={onToggleMobileSidebar}
          className="lg:hidden p-2 -ml-1 rounded-lg text-slate-300 hover:text-white hover:bg-[#202547] transition flex items-center justify-center cursor-pointer touch-manipulation"
          aria-label={mobileSidebarOpen ? "Close navigation menu" : "Open navigation menu"}
          title={mobileSidebarOpen ? "Close Menu" : "Open Menu"}
        >
          {mobileSidebarOpen ? <X size={20} className="text-amber-400" /> : <Menu size={20} />}
        </button>

        {/* Double-ring circular BEL government emblem */}
        <div className="w-8 h-8 sm:w-9 sm:h-9 shrink-0 rounded-full border border-slate-400/60 bg-[#1E2342] flex items-center justify-center text-white shadow-inner ring-1 sm:ring-2 ring-slate-500/20">
          <div className="w-6 h-6 sm:w-7 sm:h-7 rounded-full border border-amber-400/40 bg-gradient-to-br from-slate-800 to-[#16192E] flex items-center justify-center font-bold text-[10px] text-amber-400">
            BEL
          </div>
        </div>
        <div className="min-w-0">
          <div className="font-extrabold text-white text-xs sm:text-[13px] tracking-wide sm:tracking-wider uppercase flex items-center gap-2 font-sans truncate">
            <span className="truncate">Bharat Electronics Limited (BEL)</span>
            <span className="hidden md:inline-flex px-1.5 py-0.2 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono font-normal">
              NovaFlow
            </span>
          </div>
          <div className="hidden sm:block text-[11px] text-[#8E9BB0] font-medium truncate">
            Smart Automation &nbsp;|&nbsp; Urban Fleet Intelligence Dashboard
          </div>
          <div className="sm:hidden text-[10px] text-[#8E9BB0] font-medium truncate">
            Smart Automation • Urban Fleet
          </div>
        </div>
      </div>

      {/* Center: Live Operational Status */}
      <div className="hidden 2xl:flex items-center gap-2 px-3 py-1 text-[11px] font-medium text-slate-300">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse ring-2 ring-emerald-500/30" />
        <span className="text-slate-200">System Operational</span>
      </div>

      {/* Right: Navigation, Notifications, High Contrast Toggle */}
      <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
        {/* Quick Navigation Pills for the 4 Core Pillars */}
        <nav className="hidden lg:flex items-center gap-1 mr-1">
          <Link
            to="/"
            className={`px-2.5 py-1 rounded-md text-xs font-semibold transition ${
              location.pathname === "/"
                ? "bg-[#282F5A] text-white shadow-sm ring-1 ring-slate-400/30"
                : "text-[#8E9BB0] hover:text-white hover:bg-[#202547]"
            }`}
          >
            Home
          </Link>
          <Link
            to="/gis"
            className={`px-2.5 py-1 rounded-md text-xs font-semibold transition ${
              location.pathname === "/gis"
                ? "bg-[#C85A17] text-white shadow-sm"
                : "text-[#8E9BB0] hover:text-white hover:bg-[#202547]"
            }`}
          >
            GIS Dashboard
          </Link>
          <Link
            to="/scan"
            className={`px-2.5 py-1 rounded-md text-xs font-semibold transition ${
              location.pathname === "/scan" || location.pathname === "/ai-road-scan"
                ? "bg-[#2563EB] text-white shadow-sm ring-1 ring-blue-400/40"
                : "text-[#8E9BB0] hover:text-white hover:bg-[#202547]"
            }`}
          >
            AI Road Scan
          </Link>
          <Link
            to="/hazards"
            className={`px-2.5 py-1 rounded-md text-xs font-semibold transition ${
              location.pathname === "/hazards" || location.pathname === "/road-defects"
                ? "bg-[#282F5A] text-white shadow-sm ring-1 ring-slate-400/30"
                : "text-[#8E9BB0] hover:text-white hover:bg-[#202547]"
            }`}
          >
            AI Hazards
          </Link>
          <Link
            to="/work-orders"
            className={`px-2.5 py-1 rounded-md text-xs font-semibold transition ${
              location.pathname === "/work-orders"
                ? "bg-[#282F5A] text-white shadow-sm ring-1 ring-slate-400/30"
                : "text-[#8E9BB0] hover:text-white hover:bg-[#202547]"
            }`}
          >
            PWD Work Orders
          </Link>
          <Link
            to="/analytics"
            className={`px-2.5 py-1 rounded-md text-xs font-semibold transition ${
              location.pathname === "/analytics" || location.pathname === "/urban-analytics"
                ? "bg-[#282F5A] text-white shadow-sm ring-1 ring-slate-400/30"
                : "text-[#8E9BB0] hover:text-white hover:bg-[#202547]"
            }`}
          >
            Fleet Analytics
          </Link>
        </nav>

        {/* Notification Bell */}
        <button
          className="relative p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-[#202547] transition"
          title="Notifications"
        >
          <AlertTriangle size={16} />
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-amber-500 ring-2 ring-[#16192E]" />
        </button>

        {/* High Contrast Pill (Image Style - desktop/tablet) */}
        <button
          onClick={() => {}}
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#202547] hover:bg-[#282F5A] text-slate-200 border border-[#2E3558] transition shadow-sm"
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
