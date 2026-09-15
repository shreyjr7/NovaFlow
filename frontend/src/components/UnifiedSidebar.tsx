// src/components/UnifiedSidebar.tsx
import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  MapPin, Wrench, Bus, TrafficCone, Flame, AlertTriangle,
  TrendingUp, Users, Camera, Navigation, Activity, FileText,
  Cpu, Shield, HardDrive, ShieldCheck, ShieldAlert, CheckCircle2,
  ChevronLeft, ChevronRight, LayoutDashboard
} from "lucide-react";

interface NavGroup {
  groupName: string;
  items: {
    name: string;
    path: string;
    icon: React.FC<{ size?: number; className?: string }>;
    badge?: string;
    color: string;
  }[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    groupName: "Command Operations",
    items: [
      { name: "Executive Portal", path: "/", icon: LayoutDashboard, color: "text-blue-400" },
      { name: "GIS Command Center", path: "/gis", icon: MapPin, badge: "LIVE", color: "text-emerald-400" },
      { name: "Fleet Live (20)", path: "/fleet", icon: Bus, badge: "20", color: "text-sky-400" },
    ],
  },
  {
    groupName: "Infrastructure & PWD",
    items: [
      { name: "PWD Work Orders", path: "/road-defects", icon: Wrench, badge: "42", color: "text-amber-400" },
      { name: "Route Delay Audit", path: "/route-delay", icon: Navigation, color: "text-cyan-400" },
      { name: "OD Corridor Matrix", path: "/od-analysis", icon: Activity, color: "text-pink-400" },
    ],
  },
  {
    groupName: "Traffic & Safety",
    items: [
      { name: "Traffic Speeds", path: "/traffic", icon: TrafficCone, color: "text-amber-400" },
      { name: "Congestion Heatmap", path: "/congestion", icon: Flame, badge: "HOT", color: "text-rose-400" },
      { name: "Incident Safety & Hit/Run", path: "/incidents", icon: AlertTriangle, badge: "ALERT", color: "text-red-400" },
      { name: "Pedestrian Conflict", path: "/pedestrian-safety", icon: Users, color: "text-indigo-400" },
      { name: "ANPR Plate Hotlist", path: "/anpr", icon: Camera, color: "text-teal-400" },
      { name: "Public Citizen Portal", path: "/public", icon: ShieldCheck, color: "text-emerald-400" },
    ],
  },
  {
    groupName: "Intelligence & Hardware",
    items: [
      { name: "Urban Analytics", path: "/urban-analytics", icon: TrendingUp, color: "text-purple-400" },
      { name: "Automated Reports", path: "/reports", icon: FileText, color: "text-indigo-400" },
      { name: "Edge Sensor Health", path: "/camera-health", icon: Cpu, badge: "OK", color: "text-emerald-400" },
      { name: "Evidence Custody", path: "/evidence-custody", icon: Shield, color: "text-amber-400" },
      { name: "Offline Spool Buffer", path: "/offline-buffer", icon: HardDrive, color: "text-sky-400" },
      { name: "Privacy & Blur", path: "/privacy", icon: ShieldAlert, color: "text-slate-400" },
      { name: "System Diagnostic", path: "/testing", icon: CheckCircle2, color: "text-purple-400" },
    ],
  },
];

export const UnifiedSidebar: React.FC = () => {
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const location = useLocation();

  return (
    <aside
      className={`bg-slate-950 border-r border-slate-800 transition-all duration-300 ease-in-out flex flex-col justify-between shrink-0 h-[calc(100vh-45px)] sticky top-[45px] z-40 ${
        collapsed ? "w-16" : "w-64"
      }`}
    >
      {/* Top Header / Toggle */}
      <div className="p-3 border-b border-slate-800 flex items-center justify-between">
        {!collapsed && (
          <div className="flex items-center gap-2 overflow-hidden">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-[11px] font-bold font-mono uppercase tracking-wider text-slate-300 truncate">
              Unified Consoles
            </span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-700/60 transition mx-auto"
          title={collapsed ? "Expand Navigation" : "Collapse Navigation"}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {/* Nav List */}
      <div className="flex-1 overflow-y-auto py-2 px-2 space-y-4">
        {NAV_GROUPS.map((group) => (
          <div key={group.groupName} className="space-y-1">
            {!collapsed && (
              <div className="text-[10px] font-bold font-mono tracking-wider text-slate-500 uppercase px-2 py-1">
                {group.groupName}
              </div>
            )}
            {group.items.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-2.5 py-2 rounded-xl text-xs font-medium transition-all group ${
                    isActive
                      ? "bg-blue-600 text-white font-bold shadow-md shadow-blue-600/30"
                      : "text-slate-300 hover:bg-slate-900 hover:text-white"
                  }`}
                  title={collapsed ? item.name : undefined}
                >
                  <Icon
                    size={17}
                    className={`shrink-0 transition-transform group-hover:scale-110 ${
                      isActive ? "text-white" : item.color
                    }`}
                  />
                  {!collapsed && (
                    <span className="truncate flex-1">{item.name}</span>
                  )}
                  {!collapsed && item.badge && (
                    <span
                      className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold ${
                        isActive
                          ? "bg-white/20 text-white"
                          : "bg-slate-800 text-slate-400 border border-slate-700"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </div>

      {/* Bottom Global Status Indicator */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/60">
        {!collapsed ? (
          <div className="text-[10px] text-slate-400 space-y-1">
            <div className="flex items-center justify-between">
              <span>Sync Engine:</span>
              <span className="text-emerald-400 font-mono font-bold">100% ONLINE</span>
            </div>
            <div className="text-[9px] text-slate-500 font-mono truncate">
              NovaFlow Civil Command v2.6
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
          </div>
        )}
      </div>
    </aside>
  );
};

export default UnifiedSidebar;
