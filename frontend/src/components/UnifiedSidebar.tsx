// src/components/UnifiedSidebar.tsx
import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  MapPin, Wrench, Bus, TrafficCone, Flame, AlertTriangle,
  TrendingUp, Users, Camera, Navigation, Activity, FileText,
  Cpu, Shield, HardDrive, ShieldCheck, ShieldAlert, CheckCircle2,
  ChevronLeft, ChevronRight, LayoutDashboard, Video, X
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
    groupName: "CORE INTELLIGENCE",
    items: [
      { name: "Home Dashboard", path: "/", icon: LayoutDashboard, color: "text-slate-200" },
      { name: "Live GIS Command", path: "/gis", icon: MapPin, badge: "LIVE", color: "text-amber-400" },
      { name: "AI Road Scan", path: "/scan", icon: Video, badge: "NEW", color: "text-blue-400" },
      { name: "AI Hazard Detections", path: "/hazards", icon: AlertTriangle, badge: "AI", color: "text-rose-400" },
      { name: "PWD Work Orders", path: "/work-orders", icon: Wrench, badge: "PWD", color: "text-sky-400" },
      { name: "Fleet Analytics", path: "/analytics", icon: TrendingUp, badge: "TREND", color: "text-indigo-400" },
    ],
  },
  {
    groupName: "SENSORS & MOBILITY",
    items: [
      { name: "Transit Fleet Pool", path: "/fleet", icon: Bus, badge: "248", color: "text-slate-300" },
      { name: "Traffic Speeds", path: "/traffic", icon: TrafficCone, color: "text-slate-300" },
      { name: "Congestion Heatmap", path: "/congestion", icon: Flame, badge: "HOT", color: "text-orange-400" },
      { name: "Pedestrian Conflict", path: "/pedestrian-safety", icon: Users, color: "text-slate-300" },
      { name: "Incident Hotlist", path: "/incidents", icon: ShieldAlert, badge: "ALERT", color: "text-red-400" },
      { name: "ANPR Plate Hotlist", path: "/anpr", icon: Camera, color: "text-slate-300" },
    ],
  },
  {
    groupName: "MUNICIPAL & GOVERNANCE",
    items: [
      { name: "Citizen Public Portal", path: "/public", icon: ShieldCheck, color: "text-emerald-400" },
      { name: "Diagnostic Reports", path: "/reports", icon: FileText, color: "text-slate-300" },
      { name: "AI Model Governance", path: "/ai-models", icon: Activity, color: "text-slate-300" },
      { name: "Edge Device Health", path: "/camera-health", icon: Cpu, badge: "OK", color: "text-emerald-400" },
      { name: "System Diagnostics", path: "/testing", icon: CheckCircle2, color: "text-slate-300" },
      { name: "Admin Console", path: "/admin", icon: Shield, color: "text-slate-300" },
    ],
  },
];

interface UnifiedSidebarProps {
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const UnifiedSidebar: React.FC<UnifiedSidebarProps> = ({
  mobileOpen = false,
  onCloseMobile,
}) => {
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const location = useLocation();

  // Navigation Links renderer
  const renderNavList = (isMobile: boolean = false) => (
    <div className="flex-1 overflow-y-auto py-2 px-2 space-y-4 touch-scroll">
      {NAV_GROUPS.map((group) => (
        <div key={group.groupName} className="space-y-1">
          {(!collapsed || isMobile) && (
            <div className="text-[10px] font-bold font-mono tracking-wider text-slate-400/80 uppercase px-2 py-1">
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
                onClick={() => {
                  if (isMobile && onCloseMobile) {
                    onCloseMobile();
                  }
                }}
                className={`flex items-center gap-3 px-2.5 py-2.5 rounded-xl text-xs font-medium transition-all group min-h-[42px] touch-manipulation ${
                  isActive
                    ? "bg-[#282F5A] text-white font-bold shadow-sm ring-1 ring-slate-400/30"
                    : "text-slate-300 hover:bg-[#1E2342] hover:text-white active:bg-[#282F5A]"
                }`}
                title={collapsed && !isMobile ? item.name : undefined}
              >
                <Icon
                  size={18}
                  className={`shrink-0 transition-transform group-hover:scale-110 ${
                    isActive ? "text-amber-400" : item.color
                  }`}
                />
                {(!collapsed || isMobile) && (
                  <span className="truncate flex-1">{item.name}</span>
                )}
                {(!collapsed || isMobile) && item.badge && (
                  <span
                    className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold ${
                      isActive
                        ? "bg-amber-500 text-[#16192E]"
                        : "bg-[#1E2342] text-slate-300 border border-[#2B325E]"
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
  );

  return (
    <>
      {/* ── MOBILE BACKDROP OVERLAY (<lg) ─────────────────────────────────── */}
      <div
        className={`fixed inset-0 bg-black/60 backdrop-blur-xs z-40 lg:hidden transition-opacity duration-300 ${
          mobileOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={onCloseMobile}
        aria-hidden="true"
      />

      {/* ── MOBILE OFF-CANVAS SLIDE-OUT DRAWER (<lg) ───────────────────────── */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] bg-[#16192E] border-r border-[#232746] shadow-2xl flex flex-col justify-between h-full transform transition-transform duration-300 ease-in-out lg:hidden pt-safe pb-safe ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Mobile Navigation Drawer"
      >
        {/* Drawer Header */}
        <div className="p-3.5 border-b border-[#232746] flex items-center justify-between bg-[#121528]">
          <div className="flex items-center gap-2 overflow-hidden">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            <span className="text-xs font-bold font-mono uppercase tracking-wider text-slate-200 truncate">
              BEL Fleet Command
            </span>
          </div>
          <button
            onClick={onCloseMobile}
            className="p-1.5 rounded-lg bg-[#1E2342] hover:bg-[#282F5A] text-slate-300 hover:text-white border border-[#2B325E] transition cursor-pointer"
            title="Close Drawer"
            aria-label="Close Drawer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Drawer Links */}
        {renderNavList(true)}

        {/* Drawer Footer Status */}
        <div className="p-3 border-t border-[#232746] bg-[#121528]">
          <div className="text-[10px] text-slate-400 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Sync Engine:</span>
              <span className="text-emerald-400 font-mono font-bold">100% ONLINE</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Platform:</span>
              <span className="text-slate-300 font-mono font-semibold">BEL NovaFlow v3.0</span>
            </div>
          </div>
        </div>
      </aside>

      {/* ── DESKTOP DOCKED SIDEBAR (≥lg) ─────────────────────────────────── */}
      <aside
        className={`hidden lg:flex bg-[#16192E] border-r border-[#232746] transition-all duration-300 ease-in-out flex-col justify-between shrink-0 h-full z-40 ${
          collapsed ? "w-16" : "w-64"
        }`}
        aria-label="Desktop Sidebar"
      >
        {/* Top Header / Toggle */}
        <div className="p-3 border-b border-[#232746] flex items-center justify-between">
          {!collapsed && (
            <div className="flex items-center gap-2 overflow-hidden">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              <span className="text-[11px] font-bold font-mono uppercase tracking-wider text-slate-300 truncate">
                BEL Smart Automation
              </span>
            </div>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 rounded-lg bg-[#1E2342] hover:bg-[#282F5A] text-slate-300 hover:text-white border border-[#2B325E] transition mx-auto cursor-pointer"
            title={collapsed ? "Expand Navigation" : "Collapse Navigation"}
          >
            {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          </button>
        </div>

        {/* Desktop Nav List */}
        {renderNavList(false)}

        {/* Bottom Global Status Indicator */}
        <div className="p-3 border-t border-[#232746] bg-[#121528]">
          {!collapsed ? (
            <div className="text-[10px] text-slate-400 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Sync Engine:</span>
                <span className="text-emerald-400 font-mono font-bold">100% ONLINE</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Platform:</span>
                <span className="text-slate-300 font-mono font-semibold">BEL NovaFlow v3.0</span>
              </div>
            </div>
          ) : (
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 mx-auto" title="100% Online" />
          )}
        </div>
      </aside>
    </>
  );
};

export default UnifiedSidebar;
