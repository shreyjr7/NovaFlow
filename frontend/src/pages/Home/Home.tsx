// src/pages/Home/Home.tsx
// NovaFlow - Government Municipal Transit & Road Safety Command Center

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Header } from "../../components/Header";
import { LiveGisMap } from "../../components/LiveGisMap";
import { 
  Bus, Wrench, AlertTriangle, ShieldCheck, Activity, MapPin, 
  Droplet, TrafficCone, FileText, CheckCircle2, ChevronRight,
  TrendingUp, Clock, ShieldAlert, Layers, ArrowUpRight,
  Gauge, Flame, Users, Camera, Shield, Database, Cpu, Navigation,
  HelpCircle, Settings, HardDrive, AlertOctagon, Sparkles
} from "lucide-react";

interface MunicipalEvent {
  event_id: string;
  type: string;
  title: string;
  location: string;
  agency: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM";
  priority_score: number;
  confidence: number;
  bus_id: string;
  timestamp: string;
  status: string;
}

const DEFAULT_MUNICIPAL_EVENTS: MunicipalEvent[] = [
  {
    event_id: "PWD-DEL-2026-081",
    type: "POTHOLE",
    title: "Severe Asphalt Depression (45cm)",
    location: "Outer Ring Road (Marathahalli Flyover), Bengaluru",
    agency: "BBMP Road Infrastructure Division",
    severity: "CRITICAL",
    priority_score: 92,
    confidence: 0.96,
    bus_id: "BUS_003",
    timestamp: "12 mins ago",
    status: "CONFIRMED_ASSIGNED"
  },
  {
    event_id: "PWD-DEL-2026-082",
    type: "WATERLOGGING",
    title: "Monsoon Water Accumulation (Lane 1-2)",
    location: "Ring Road near AIIMS Flyover, New Delhi",
    agency: "Delhi PWD Maintenance Zone 4",
    severity: "HIGH",
    priority_score: 84,
    confidence: 0.94,
    bus_id: "BUS_001",
    timestamp: "24 mins ago",
    status: "UNDER_REVIEW"
  },
  {
    event_id: "NHAI-MUM-2026-044",
    type: "DAMAGED_ROAD",
    title: "Corrosion & Concrete Spalling",
    location: "Western Express Highway (Andheri Flyover), Mumbai",
    agency: "NHAI Western Corridor Division",
    severity: "HIGH",
    priority_score: 79,
    confidence: 0.91,
    bus_id: "BUS_007",
    timestamp: "38 mins ago",
    status: "DISPATCHED"
  },
  {
    event_id: "PWD-DEL-2026-085",
    type: "TRAFFIC_INCIDENT",
    title: "Vehicle Breakdown / Bottleneck Formation",
    location: "Barakhamba Road Junction, Connaught Place, New Delhi",
    agency: "Delhi Traffic Police Safety Unit",
    severity: "CRITICAL",
    priority_score: 88,
    confidence: 0.95,
    bus_id: "BUS_006",
    timestamp: "45 mins ago",
    status: "POLICE_ALERTED"
  },
  {
    event_id: "BBMP-BLR-2026-102",
    type: "MISSING_INFRA",
    title: "Missing Median Divider Warning Hazard",
    location: "Hosur Road (Silk Board Junction Approach), Bengaluru",
    agency: "BBMP Traffic Engineering Cell",
    severity: "MEDIUM",
    priority_score: 68,
    confidence: 0.89,
    bus_id: "BUS_008",
    timestamp: "1 hour ago",
    status: "TICKET_OPEN"
  },
  {
    event_id: "PWD-DEL-2026-089",
    type: "PEDESTRIAN_RISK",
    title: "School Zone Crossing Incursion Hotspot",
    location: "Bishop Cotton School Corridor, Residency Road",
    agency: "Urban Transport Safety Authority",
    severity: "HIGH",
    priority_score: 82,
    confidence: 0.93,
    bus_id: "BUS_004",
    timestamp: "1.5 hours ago",
    status: "ACTIVE_MONITORING"
  }
];

export const Home: React.FC = () => {
  const [stats, setStats] = useState({
    activeBuses: 20,
    onlineDevices: 20,
    detectedDefects: 525,
    activeWorkOrders: 42,
    safetyIndex: 94.2,
    monitoredRoutes: 5,
  });

  const [activeEvents, setActiveEvents] = useState<MunicipalEvent[]>(DEFAULT_MUNICIPAL_EVENTS);

  useEffect(() => {
    // Attempt dynamic stats update from backend
    fetch("/api/v1/demo/buses")
      .then((r) => r.json())
      .then((buses) => {
        if (Array.isArray(buses) && buses.length > 0) {
          setStats((prev) => ({ ...prev, activeBuses: buses.length, onlineDevices: buses.length }));
        }
      })
      .catch(() => {});

    fetch("/api/v1/road-defects/summary")
      .then((r) => r.json())
      .then((summary) => {
        if (summary && summary.total_defects) {
          setStats((prev) => ({ ...prev, detectedDefects: summary.total_defects }));
        }
      })
      .catch(() => {});
  }, []);

  return (
    <div className="container mx-auto px-4 py-6 space-y-8 max-w-7xl">
      {/* Brand Header */}
      <Header />

      {/* Official Government Executive Banner */}
      <section className="bg-gradient-to-r from-slate-900 via-slate-850 to-blue-950 border border-slate-800 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400 text-xs font-mono font-bold border border-blue-500/30">
                GOVERNMENT OF INDIA • CIVIL TRANSPORT COMMAND
              </span>
              <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-mono font-bold">
                ● LIVE SYSTEM
              </span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Autonomous Municipal Road Perception & Transit Intelligence
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed">
              Public bus fleets continuously inspect road pavement integrity, traffic bottlenecks, and pedestrian conflict hotspots without requiring dedicated road survey vehicles.
            </p>
          </div>

          {/* Quick Authority Action CTAs */}
          <div className="flex flex-wrap md:flex-col gap-2.5 shrink-0">
            <Link
              to="/gis"
              className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-blue-600/30 transition-all"
            >
              <MapPin size={15} />
              <span>Open GIS Command Center</span>
            </Link>
            <Link
              to="/road-defects"
              className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-bold text-xs flex items-center justify-center gap-2 transition-all"
            >
              <Wrench size={15} className="text-amber-400" />
              <span>Municipal Work Orders</span>
            </Link>
            <Link
              to="/reports"
              className="px-4 py-2.5 rounded-xl bg-indigo-600/80 hover:bg-indigo-600 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-md transition-all"
            >
              <FileText size={15} />
              <span>Intelligence Reports</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Real-time KPI Statistics Grid */}
      <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Active Buses</span>
            <Bus size={15} className="text-blue-400" />
          </div>
          <div className="text-2xl font-black text-white font-mono">{stats.activeBuses}</div>
          <div className="text-[10px] text-emerald-400 mt-0.5">100% On-Route</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Edge AI Units</span>
            <Activity size={15} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-white font-mono">{stats.onlineDevices}</div>
          <div className="text-[10px] text-slate-400 mt-0.5">NVIDIA Jetson AGX</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Road Defects</span>
            <Wrench size={15} className="text-amber-400" />
          </div>
          <div className="text-2xl font-black text-white font-mono">{stats.detectedDefects}</div>
          <div className="text-[10px] text-amber-400 mt-0.5">Clustered & Centroided</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Work Orders</span>
            <FileText size={15} className="text-purple-400" />
          </div>
          <div className="text-2xl font-black text-white font-mono">{stats.activeWorkOrders}</div>
          <div className="text-[10px] text-purple-400 mt-0.5">Assigned to PWD/NHAI</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Transit Corridors</span>
            <MapPin size={15} className="text-indigo-400" />
          </div>
          <div className="text-2xl font-black text-white font-mono">{stats.monitoredRoutes}</div>
          <div className="text-[10px] text-indigo-400 mt-0.5">115 Road Segments</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Safety Index</span>
            <ShieldCheck size={15} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-white font-mono">{stats.safetyIndex}%</div>
          <div className="text-[10px] text-emerald-400 mt-0.5">Compliant Rating</div>
        </div>
      </section>

      {/* Live Interactive GIS Map Section */}
      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping" />
              <span>Live Fleet Tracking & Municipal Hazard GIS Map</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Powered by Google Maps with real-time GPS kinematics across 20 active municipal transit buses and 525+ detected road defects.
            </p>
          </div>
          <Link
            to="/gis"
            className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30 hover:bg-blue-600/30 transition flex items-center gap-1"
          >
            <span>Open Fullscreen GIS Command Center</span>
            <span>→</span>
          </Link>
        </div>
        <LiveGisMap height="520px" />
      </section>

      {/* Active Municipal Hazards & Incident Dispatch Stream */}
      <section className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <ShieldAlert className="text-amber-400" size={20} />
              <span>Active Municipal Hazards & Work Order Dispatch</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Verified by cross-bus temporal confirmation and forwarded to respective municipal engineering cells.
            </p>
          </div>
          <Link
            to="/road-defects"
            className="text-xs font-bold text-blue-400 hover:text-blue-300 flex items-center gap-1"
          >
            <span>Manage All Work Orders</span>
            <ArrowUpRight size={14} />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {activeEvents.map((ev) => (
            <div
              key={ev.event_id}
              className="bg-slate-900/90 border border-slate-800 hover:border-slate-700 rounded-xl p-4 shadow-lg transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                    ev.severity === "CRITICAL"
                      ? "bg-red-950 text-red-300 border border-red-500/30"
                      : ev.severity === "HIGH"
                      ? "bg-amber-950 text-amber-300 border border-amber-500/30"
                      : "bg-blue-950 text-blue-300 border border-blue-500/30"
                  }`}>
                    {ev.severity} • PRIORITY {ev.priority_score}
                  </span>
                  <span className="text-[11px] text-slate-500 font-mono">{ev.timestamp}</span>
                </div>

                <h4 className="text-sm font-bold text-white mb-1">{ev.title}</h4>
                <div className="text-xs text-slate-300 font-medium flex items-start gap-1.5 mb-2">
                  <MapPin size={13} className="text-blue-400 shrink-0 mt-0.5" />
                  <span>{ev.location}</span>
                </div>

                <div className="text-[11px] text-slate-400 mb-3 bg-slate-950 p-2 rounded border border-slate-800/80">
                  <div className="flex justify-between mb-0.5">
                    <span>Assigned Agency:</span>
                    <strong className="text-slate-200">{ev.agency}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Source Sensor:</span>
                    <strong className="text-slate-200">{ev.bus_id} (AI Conf {((ev.confidence)*100).toFixed(0)}%)</strong>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
                <span className="text-[10px] font-mono text-emerald-400 font-semibold">{ev.status}</span>
                <Link
                  to="/road-defects"
                  className="px-2.5 py-1 text-xs font-bold rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 hover:bg-blue-600/30 transition flex items-center gap-1"
                >
                  <span>Dispatch Crew</span>
                  <ChevronRight size={13} />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Municipal Operations Quick Links */}
      <section className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Shield className="text-blue-400" size={18} />
              <span>Integrated Municipal Departments & Consoles</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Instant access to all operational modules, intelligence dashboards, and dispatch workflows.
            </p>
          </div>
          <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-500/30 font-bold">
            18 MODULES ACTIVE
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 text-xs font-medium">
          <Link to="/gis" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-blue-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <MapPin size={16} className="text-blue-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">GIS Command Center</span>
          </Link>
          <Link to="/road-defects" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-amber-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <Wrench size={16} className="text-amber-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">PWD Work Orders</span>
          </Link>
          <Link to="/fleet" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-blue-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <Bus size={16} className="text-blue-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">Fleet Live (20)</span>
          </Link>
          <Link to="/traffic" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-amber-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <TrafficCone size={16} className="text-amber-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">Traffic Speed</span>
          </Link>
          <Link to="/congestion" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-rose-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <Flame size={16} className="text-rose-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">Congestion Heatmap</span>
          </Link>
          <Link to="/incidents" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-red-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <AlertTriangle size={16} className="text-red-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">Incident Safety</span>
          </Link>
          <Link to="/urban-analytics" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-purple-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <TrendingUp size={16} className="text-purple-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">Urban Analytics</span>
          </Link>
          <Link to="/pedestrian-safety" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-indigo-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <Users size={16} className="text-indigo-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">Pedestrian Zones</span>
          </Link>
          <Link to="/anpr" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-teal-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <Camera size={16} className="text-teal-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">ANPR Hotlist</span>
          </Link>
          <Link to="/route-delay" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-cyan-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <Navigation size={16} className="text-cyan-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">Route Delay Audit</span>
          </Link>
          <Link to="/od-analysis" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-pink-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <Activity size={16} className="text-pink-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">OD Matrix Corridor</span>
          </Link>
          <Link to="/reports" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-indigo-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <FileText size={16} className="text-indigo-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">Automated Reports</span>
          </Link>
          <Link to="/camera-health" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-emerald-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <Cpu size={16} className="text-emerald-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">Edge Sensor Health</span>
          </Link>
          <Link to="/evidence-custody" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-amber-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <Shield size={16} className="text-amber-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">Evidence Custody</span>
          </Link>
          <Link to="/offline-buffer" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-sky-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <HardDrive size={16} className="text-sky-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">Offline Spool Buffer</span>
          </Link>
          <Link to="/public" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-emerald-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <ShieldCheck size={16} className="text-emerald-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">Public Safety Portal</span>
          </Link>
          <Link to="/privacy" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-slate-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <ShieldAlert size={16} className="text-slate-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">Privacy & Redaction</span>
          </Link>
          <Link to="/testing" className="p-3 bg-slate-800/80 hover:bg-slate-750 hover:border-purple-500/50 rounded-xl border border-slate-700 text-slate-200 transition flex items-center gap-2.5 shadow-sm group">
            <CheckCircle2 size={16} className="text-purple-400 group-hover:scale-110 transition" />
            <span className="group-hover:text-white">System Diagnostics</span>
          </Link>
        </div>
      </section>
    </div>
  );
};

export default Home;
