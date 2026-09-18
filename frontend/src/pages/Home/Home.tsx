// src/pages/Home/Home.tsx
// NovaFlow - Executive Command Dashboard (Faithful Reproduction of Reference Photo 5)

import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { LiveGisMap } from "../../components/LiveGisMap";
import { 
  Bus, Wrench, AlertTriangle, ShieldCheck, Activity, MapPin, 
  Droplet, TrafficCone, FileText, CheckCircle2, ChevronRight,
  TrendingUp, Clock, ShieldAlert, ArrowUpRight,
  Gauge, Flame, Users, Camera, Shield, Cpu, Navigation,
  Search, Play, Check, ChevronDown, SlidersHorizontal
} from "lucide-react";

interface HazardDefect {
  id: string;
  code: string;
  type: "POTHOLE" | "WATERLOGGING" | "DAMAGED_ROAD" | "TRAFFIC_INCIDENT" | "MISSING_INFRA" | "PEDESTRIAN_RISK";
  title: string;
  location: string;
  city: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM";
  depth_or_size: string;
  route_id: string;
  bus_source: string;
  detected_time: string;
  bus_passes: number;
  consensus_pct: number;
  status: "CONFIRMED" | "PENDING_CONSENSUS" | "DISPATCHED" | "INVESTIGATING";
  assigned_agency: string;
  coordinates: { lat: number; lon: number; variance_m: number };
  verified_buses: string[];
  evidence_description: string;
}

const INITIAL_HAZARDS: HazardDefect[] = [
  {
    id: "DEF-001",
    code: "PWD-DEL-2026-081",
    type: "POTHOLE",
    title: "Severe Asphalt Pothole - Outer Ring Rd",
    location: "Outer Ring Road km 14.2, Near Marathahalli Flyover",
    city: "Bengaluru",
    severity: "CRITICAL",
    depth_or_size: "Depth: 8.5cm",
    route_id: "Route 335-E",
    bus_source: "DL-1PC-4821",
    detected_time: "14 mins ago",
    bus_passes: 3,
    consensus_pct: 94,
    status: "CONFIRMED",
    assigned_agency: "BBMP / PWD East Division Zone 4",
    coordinates: { lat: 12.9348, lon: 77.6101, variance_m: 0.42 },
    verified_buses: ["Bus #04 (DL-1PC-4821)", "Bus #12 (KA-01-F-9021)", "Bus #27 (DL-1PB-7744)"],
    evidence_description: "Deep edge shear with exposed aggregate. High tire puncture risk and sudden motorcycle swerving pattern detected."
  },
  {
    id: "DEF-002",
    code: "PWD-DEL-2026-082",
    type: "WATERLOGGING",
    title: "Waterlogging Hotspot - Underpass Lane 2",
    location: "Ring Road near AIIMS Flyover Underpass",
    city: "New Delhi",
    severity: "HIGH",
    depth_or_size: "Water Depth: 15cm",
    route_id: "Route 500-D",
    bus_source: "DL-1PB-7744",
    detected_time: "24 mins ago",
    bus_passes: 2,
    consensus_pct: 88,
    status: "CONFIRMED",
    assigned_agency: "Delhi PWD Drainage & Stormwater Cell",
    coordinates: { lat: 28.5672, lon: 77.2100, variance_m: 0.75 },
    verified_buses: ["Bus #01 (DL-1PB-7744)", "Bus #09 (DL-1PC-2201)"],
    evidence_description: "Submerged curbs and pooling across 2 lanes. Vehicle deceleration rate exceeds 65% on entry."
  },
  {
    id: "DEF-003",
    code: "NHAI-MUM-2026-044",
    type: "DAMAGED_ROAD",
    title: "Structural Concrete Spalling - Flyover Pier 4",
    location: "Western Express Highway (Andheri Flyover)",
    city: "Mumbai",
    severity: "HIGH",
    depth_or_size: "Area: 1.4m²",
    route_id: "Route 201-R",
    bus_source: "MH-02-CL-3310",
    detected_time: "38 mins ago",
    bus_passes: 2,
    consensus_pct: 91,
    status: "DISPATCHED",
    assigned_agency: "NHAI Western Corridor Division",
    coordinates: { lat: 19.1136, lon: 72.8697, variance_m: 0.58 },
    verified_buses: ["Bus #07 (MH-02-CL-3310)", "Bus #14 (MH-02-CL-8802)"],
    evidence_description: "Surface delamination and rebar visibility detected via edge vision inference."
  },
  {
    id: "DEF-004",
    code: "PWD-DEL-2026-085",
    type: "TRAFFIC_INCIDENT",
    title: "Traffic Bottleneck / Illegal Lane Incursion",
    location: "Barakhamba Road Junction, Connaught Place",
    city: "New Delhi",
    severity: "CRITICAL",
    depth_or_size: "Density: 88%",
    route_id: "Route 104-A",
    bus_source: "DL-1PC-9011",
    detected_time: "45 mins ago",
    bus_passes: 4,
    consensus_pct: 96,
    status: "INVESTIGATING",
    assigned_agency: "Delhi Traffic Police Safety Unit",
    coordinates: { lat: 28.6304, lon: 77.2273, variance_m: 0.35 },
    verified_buses: ["Bus #06", "Bus #08", "Bus #15", "Bus #19"],
    evidence_description: "Multiple stalled vehicles blocking BRT corridor with sudden queue propagation."
  },
  {
    id: "DEF-005",
    code: "BBMP-BLR-2026-102",
    type: "MISSING_INFRA",
    title: "Missing Median Divider Warning Hazard",
    location: "Hosur Road (Silk Board Junction Approach)",
    city: "Bengaluru",
    severity: "MEDIUM",
    depth_or_size: "Span: 12 meters",
    route_id: "Route 360-B",
    bus_source: "KA-01-F-9021",
    detected_time: "1 hour ago",
    bus_passes: 1,
    consensus_pct: 76,
    status: "PENDING_CONSENSUS",
    assigned_agency: "BBMP Traffic Engineering Cell",
    coordinates: { lat: 12.9176, lon: 77.6238, variance_m: 1.10 },
    verified_buses: ["Bus #12 (KA-01-F-9021)"],
    evidence_description: "Broken reflective delineator segment following nighttime collision."
  },
  {
    id: "DEF-006",
    code: "PWD-DEL-2026-089",
    type: "PEDESTRIAN_RISK",
    title: "School Zone Crossing Incursion Hotspot",
    location: "Bishop Cotton School Corridor, Residency Road",
    city: "Bengaluru",
    severity: "HIGH",
    depth_or_size: "Surge: 42 peds/min",
    route_id: "Route 138",
    bus_source: "KA-01-FA-4411",
    detected_time: "1.5 hours ago",
    bus_passes: 3,
    consensus_pct: 92,
    status: "CONFIRMED",
    assigned_agency: "Urban Transport Safety Authority",
    coordinates: { lat: 12.9716, lon: 77.5946, variance_m: 0.49 },
    verified_buses: ["Bus #04", "Bus #18", "Bus #22"],
    evidence_description: "High pedestrian jaywalking density outside marked signal phase."
  }
];

export const Home: React.FC = () => {
  const [hazards, setHazards] = useState<HazardDefect[]>(INITIAL_HAZARDS);
  const [selectedHazardId, setSelectedHazardId] = useState<string>("DEF-001");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [dispatchSuccess, setDispatchSuccess] = useState<string | null>(null);
  const [isDispatching, setIsDispatching] = useState<boolean>(false);

  const [stats, setStats] = useState({
    activeDefects: 248,
    connectedBuses: 36,
    availabilityPct: 92,
    consensusVerified: 1842,
    consensusDelta: 8.4,
    avgAiConfidence: 94.6,
  });

  // Dynamic fetch to augment stats from real backend APIs
  useEffect(() => {
    fetch("/api/v1/demo/buses")
      .then((r) => r.json())
      .then((buses) => {
        if (Array.isArray(buses) && buses.length > 0) {
          setStats((prev) => ({
            ...prev,
            connectedBuses: buses.length,
          }));
        }
      })
      .catch(() => {});

    fetch("/api/v1/road-defects/summary")
      .then((r) => r.json())
      .then((data) => {
        if (data && data.total_defects) {
          setStats((prev) => ({
            ...prev,
            activeDefects: data.total_defects,
          }));
        }
      })
      .catch(() => {});
  }, []);

  const filteredHazards = useMemo(() => {
    return hazards.filter((h) => {
      const q = searchQuery.toLowerCase();
      return (
        h.title.toLowerCase().includes(q) ||
        h.location.toLowerCase().includes(q) ||
        h.code.toLowerCase().includes(q) ||
        h.bus_source.toLowerCase().includes(q)
      );
    });
  }, [hazards, searchQuery]);

  const selectedHazard = useMemo(() => {
    return hazards.find((h) => h.id === selectedHazardId) || hazards[0];
  }, [hazards, selectedHazardId]);

  const handleRunDispatch = () => {
    setIsDispatching(true);
    setTimeout(() => {
      setIsDispatching(false);
      setDispatchSuccess(
        `Work Order ${selectedHazard.code}-WO dispatched autonomously to ${selectedHazard.assigned_agency} with high priority!`
      );
      setHazards((prev) =>
        prev.map((h) => (h.id === selectedHazard.id ? { ...h, status: "DISPATCHED" } : h))
      );
      setTimeout(() => setDispatchSuccess(null), 6000);
    }, 700);
  };

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-[#16192E]">
      {/* ── Top Eyebrow & Page Header (Photo 5 Style) ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#C85A17] flex items-center gap-2 mb-1">
            <span>SIMULATION CENTRE</span>
            <span className="text-slate-400">──</span>
            <span>SIH PROBLEM STATEMENT 124</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-[#16192E] tracking-tight">
            Selector–Applicant Matchmaking
          </h1>
          <p className="text-xs sm:text-sm text-[#64748B] mt-1">
            Simulate optimal expert assignments against applicant skill profiles.
          </p>
        </div>

        {/* Top Action Buttons (Photo 5 Style) */}
        <div className="flex items-center gap-2.5 shrink-0">
          <Link
            to="/reports"
            className="px-4 py-2 rounded-lg bg-white border border-[#CBD5E1] text-[#16192E] hover:bg-slate-50 text-xs font-semibold flex items-center gap-2 shadow-sm transition"
          >
            <FileText size={14} className="text-[#64748B]" />
            <span>Export Report</span>
          </Link>
          <button
            onClick={handleRunDispatch}
            disabled={isDispatching}
            className="px-4 py-2 rounded-lg bg-[#C85A17] hover:bg-[#B34D10] text-white text-xs font-bold flex items-center gap-2 shadow-sm transition active:scale-95 disabled:opacity-75 cursor-pointer"
          >
            <Play size={13} fill="currentColor" />
            <span>{isDispatching ? "Simulating..." : "Simulate Match"}</span>
          </button>
        </div>
      </div>

      {/* Success Notification Banner */}
      {dispatchSuccess && (
        <div className="bg-emerald-50 border-l-4 border-emerald-500 p-3.5 rounded-r-xl text-emerald-800 text-xs font-semibold flex items-center justify-between shadow-sm animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
            <span>{dispatchSuccess}</span>
          </div>
          <Link to="/road-defects" className="underline text-emerald-900 font-bold hover:text-emerald-700 ml-4">
            View in Work Orders →
          </Link>
        </div>
      )}

      {/* ── Row of 4 Crisp White Metric Cards (Photo 5 Style) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1 */}
        <div className="bg-white rounded-xl p-4 border border-[#E2E8F0] shadow-[0_1px_3px_rgba(0,0,0,0.05)] flex flex-col justify-between">
          <div className="flex items-center justify-between text-[#64748B] text-xs font-medium mb-2">
            <span>Total Applicants</span>
            <div className="w-8 h-8 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-center text-[#64748B]">
              <Users size={16} />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-[#16192E] font-mono tracking-tight">
            {stats.activeDefects.toLocaleString()}
          </div>
          <div className="flex items-center gap-1.5 mt-2">
            <span className="bg-emerald-50 text-emerald-700 text-xs font-semibold px-1.5 py-0.5 rounded border border-emerald-200">
              +12
            </span>
            <span className="text-xs text-[#94A3B8] font-medium">this week</span>
          </div>
        </div>

        {/* Card 2 */}
        <div className="bg-white rounded-xl p-4 border border-[#E2E8F0] shadow-[0_1px_3px_rgba(0,0,0,0.05)] flex flex-col justify-between">
          <div className="flex items-center justify-between text-[#64748B] text-xs font-medium mb-2">
            <span>Active Experts</span>
            <div className="w-8 h-8 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-center text-[#64748B]">
              <ShieldCheck size={16} />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-[#16192E] font-mono tracking-tight">
            {stats.connectedBuses}
          </div>
          <div className="flex items-center gap-1.5 mt-2">
            <span className="bg-emerald-50 text-emerald-700 text-xs font-semibold px-1.5 py-0.5 rounded border border-emerald-200">
              {stats.availabilityPct}%
            </span>
            <span className="text-xs text-[#94A3B8] font-medium">availability</span>
          </div>
        </div>

        {/* Card 3 */}
        <div className="bg-white rounded-xl p-4 border border-[#E2E8F0] shadow-[0_1px_3px_rgba(0,0,0,0.05)] flex flex-col justify-between">
          <div className="flex items-center justify-between text-[#64748B] text-xs font-medium mb-2">
            <span>Matches Simulated</span>
            <div className="w-8 h-8 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-center text-[#64748B]">
              <Activity size={16} />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-[#16192E] font-mono tracking-tight">
            {stats.consensusVerified.toLocaleString()}
          </div>
          <div className="flex items-center gap-1.5 mt-2">
            <span className="bg-emerald-50 text-emerald-700 text-xs font-semibold px-1.5 py-0.5 rounded border border-emerald-200">
              +{stats.consensusDelta}%
            </span>
            <span className="text-xs text-[#94A3B8] font-medium">vs last cycle</span>
          </div>
        </div>

        {/* Card 4 */}
        <div className="bg-white rounded-xl p-4 border border-[#E2E8F0] shadow-[0_1px_3px_rgba(0,0,0,0.05)] flex flex-col justify-between">
          <div className="flex items-center justify-between text-[#64748B] text-xs font-medium mb-2">
            <span>Avg. Relevance</span>
            <div className="w-8 h-8 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-center text-[#64748B]">
              <Gauge size={16} />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-[#16192E] font-mono tracking-tight">
            {stats.avgAiConfidence}%
          </div>
          <div className="flex items-center gap-1.5 mt-2">
            <span className="bg-emerald-50 text-emerald-700 text-xs font-semibold px-1.5 py-0.5 rounded border border-emerald-200">
              +2.1%
            </span>
            <span className="text-xs text-[#94A3B8] font-medium">improvement</span>
          </div>
        </div>
      </div>

      {/* ── Master-Detail Split Grid (Photo 5 Exact Specification) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Card: Applicant / Hazard Pool (5 cols on lg) */}
        <div className="lg:col-span-6 xl:col-span-5 bg-white rounded-xl border border-[#E2E8F0] shadow-[0_1px_3px_rgba(0,0,0,0.05)] p-4 flex flex-col space-y-3.5">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-[#16192E]">Applicant Pool</h2>
                <span className="px-2 py-0.5 bg-[#F1F5F9] text-[#475569] font-semibold text-xs rounded-full">
                  {hazards.length} total
                </span>
              </div>
              <p className="text-xs text-[#64748B] mt-0.5">Select an applicant to simulate</p>
            </div>
            <Link to="/road-defects" className="text-xs font-bold text-[#C85A17] hover:underline flex items-center gap-1">
              <span>View All</span>
              <ChevronRight size={14} />
            </Link>
          </div>

          {/* Search Bar with Filter Icon */}
          <div className="relative flex items-center">
            <Search size={15} className="absolute left-3 text-[#94A3B8]" />
            <input
              type="text"
              placeholder="Search applicants..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-9 py-2 bg-white border border-[#CBD5E1] rounded-lg text-xs text-[#16192E] placeholder-[#94A3B8] focus:outline-none focus:border-[#C85A17] transition"
            />
            <SlidersHorizontal size={14} className="absolute right-3 text-[#94A3B8] cursor-pointer hover:text-[#16192E]" />
          </div>

          {/* Applicant / Hazard Cards List */}
          <div className="space-y-3 max-h-[580px] overflow-y-auto pr-1">
            {filteredHazards.map((item, idx) => {
              const isSelected = item.id === selectedHazard.id;
              // Map to Arjun Mehta style if selected
              const name = idx === 0 ? "Arjun Mehta" : item.title;
              const appCode = idx === 0 ? "APP-2024-0187" : item.code;
              const roleTitle = idx === 0 ? "Defence Systems Engineer" : item.type.replace(/_/g, " ");
              const skills = idx === 0 ? ["Embedded Systems", "C++", "Radar Systems"] : [item.severity, item.depth_or_size, item.route_id];
              const locationStr = idx === 0 ? "Pune, Maharashtra" : item.location;
              const expStr = idx === 0 ? "6 years" : `${item.bus_passes} passes`;

              return (
                <div
                  key={item.id}
                  onClick={() => setSelectedHazardId(item.id)}
                  className={`p-3.5 rounded-xl border transition cursor-pointer ${
                    isSelected
                      ? "bg-white border-[#CBD5E1] border-l-4 border-l-[#C85A17] shadow-sm"
                      : "bg-white border-[#E2E8F0] hover:border-[#CBD5E1] hover:bg-slate-50/50"
                  }`}
                >
                  {/* Top Line */}
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-[#E2E8F0] text-[#16192E] flex items-center justify-center font-bold text-xs shrink-0">
                        {idx === 0 ? "AM" : item.title.slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <h3 className="text-xs font-bold text-[#16192E] leading-tight">
                          {name}
                        </h3>
                        <div className="text-[10px] font-mono text-[#64748B]">
                          {appCode}
                        </div>
                      </div>
                    </div>

                    {/* Status badge */}
                    <span className="text-[11px] font-semibold text-emerald-700 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      <span>{idx === 0 ? "Cleared" : "Confirmed"}</span>
                    </span>
                  </div>

                  {/* Role Title */}
                  <div className="text-xs font-semibold text-[#334155] ml-10 mb-2">
                    {roleTitle}
                  </div>

                  {/* Skill Tag Pills */}
                  <div className="flex flex-wrap items-center gap-1.5 ml-10 mb-2.5">
                    {skills.map((s, sIdx) => (
                      <span
                        key={sIdx}
                        className="text-[11px] font-medium bg-[#F1F5F9] text-[#475569] px-2 py-0.5 rounded border border-[#E2E8F0]"
                      >
                        {s}
                      </span>
                    ))}
                  </div>

                  {/* Location & Experience */}
                  <div className="flex items-center justify-between text-xs text-[#64748B] ml-10 pt-1 border-t border-[#F1F5F9]">
                    <span className="truncate max-w-[220px]">{locationStr}</span>
                    <span className="shrink-0">{expStr}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Card: Match Simulation & Consensus (7 cols on lg - EXACT PHOTO 5 LAYOUT) */}
        <div className="lg:col-span-6 xl:col-span-7 bg-white rounded-xl border border-[#E2E8F0] shadow-[0_1px_3px_rgba(0,0,0,0.05)] p-5 flex flex-col justify-between">
          <div>
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3 mb-4">
              <div>
                <h2 className="text-base font-bold text-[#16192E]">
                  Match Simulation
                </h2>
                <p className="text-xs text-[#64748B]">
                  Applicant-to-expert relevance analysis
                </p>
              </div>
              <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold px-2 py-0.5 rounded-full flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span>LIVE</span>
              </span>
            </div>

            {/* Selected Applicant Box with Dropdown Chevron */}
            <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3 mb-6 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-[#E2E8F0] text-[#16192E] flex items-center justify-center font-bold text-xs shrink-0">
                  AM
                </div>
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-[#94A3B8]">
                    SELECTED APPLICANT
                  </div>
                  <div className="text-xs font-bold text-[#16192E]">
                    {selectedHazard.id === "DEF-001" ? "Arjun Mehta" : selectedHazard.title}
                  </div>
                </div>
              </div>
              <ChevronDown size={16} className="text-[#64748B] cursor-pointer" />
            </div>

            {/* ── CENTER DONUT GAUGE & RELEVANCE BLOCK (PHOTO 5 SIDE-BY-SIDE) ── */}
            <div className="flex flex-col sm:flex-row items-center gap-6 p-4 bg-[#FAFCFF] border border-[#E2E8F0] rounded-xl mb-6">
              {/* Donut Gauge on Left */}
              <div className="relative w-36 h-36 shrink-0 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  {/* Background Track Circle */}
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    stroke="#F1F5F9"
                    strokeWidth="10"
                    fill="none"
                  />
                  {/* Active Gauge Arc in Vibrant Burnt Orange */}
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    stroke="#C85A17"
                    strokeWidth="10"
                    strokeDasharray={251.2}
                    strokeDashoffset={251.2 - (251.2 * selectedHazard.consensus_pct) / 100}
                    strokeLinecap="round"
                    fill="none"
                    className="transition-all duration-700 ease-out"
                  />
                </svg>
                {/* Center Text inside Donut Ring */}
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span className="text-3xl font-black text-[#16192E] font-mono tracking-tight leading-none">
                    {selectedHazard.consensus_pct}%
                  </span>
                  <span className="text-[10px] font-extrabold text-[#94A3B8] tracking-widest uppercase mt-1">
                    RELEVANCE
                  </span>
                </div>
              </div>

              {/* Matchmaking Text & Action on Right */}
              <div className="flex-1 space-y-2">
                <div className="text-[10px] font-bold uppercase tracking-wider text-[#94A3B8]">
                  MATCHMAKING RELEVANCE
                </div>
                <h3 className="text-base font-bold text-[#16192E]">
                  Excellent Match Potential
                </h3>
                <p className="text-xs text-[#64748B] leading-relaxed">
                  Based on semantic skill mapping, domain expertise, and current expert availability. Cross-verified across 3 independent evaluation units.
                </p>
                <button
                  onClick={handleRunDispatch}
                  disabled={isDispatching}
                  className="px-4 py-2 rounded-lg bg-[#C85A17] hover:bg-[#B34D10] text-white text-xs font-bold flex items-center gap-2 shadow-sm transition active:scale-95 disabled:opacity-75 cursor-pointer mt-1"
                >
                  <Play size={13} fill="currentColor" />
                  <span>{isDispatching ? "Simulating Match..." : "Run Simulation"}</span>
                </button>
              </div>
            </div>

            {/* 4 Consensus Diagnostics Boxes */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-3">
                <div className="text-[10px] font-bold uppercase text-[#94A3B8] tracking-wider mb-1">
                  Spatial Centroid
                </div>
                <div className="text-xs font-mono font-bold text-[#16192E]">
                  {selectedHazard.coordinates.lat.toFixed(4)}°N, {selectedHazard.coordinates.lon.toFixed(4)}°E
                </div>
                <div className="text-[10px] text-emerald-700 font-semibold mt-0.5">
                  ±{selectedHazard.coordinates.variance_m}m variance
                </div>
              </div>

              <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-3">
                <div className="text-[10px] font-bold uppercase text-[#94A3B8] tracking-wider mb-1">
                  Independent Bus Passes
                </div>
                <div className="text-xs font-mono font-bold text-[#16192E]">
                  {selectedHazard.verified_buses.length} Fleet Vehicles
                </div>
                <div className="text-[10px] text-[#64748B] font-medium truncate mt-0.5">
                  {selectedHazard.verified_buses[0]}
                </div>
              </div>

              <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-3">
                <div className="text-[10px] font-bold uppercase text-[#94A3B8] tracking-wider mb-1">
                  Temporal Confirmation
                </div>
                <div className="text-xs font-mono font-bold text-[#16192E]">
                  45 mins window
                </div>
                <div className="text-[10px] text-emerald-700 font-semibold mt-0.5">
                  Multi-pass verified
                </div>
              </div>

              <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-3">
                <div className="text-[10px] font-bold uppercase text-[#94A3B8] tracking-wider mb-1">
                  Assigned Authority
                </div>
                <div className="text-xs font-bold text-[#16192E] truncate">
                  {selectedHazard.assigned_agency}
                </div>
                <div className="text-[10px] text-[#C85A17] font-medium mt-0.5">
                  Automated routing enabled
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Fast Links */}
          <div className="flex items-center justify-between text-xs text-[#64748B] pt-3 border-t border-[#E2E8F0]">
            <Link to="/road-defects" className="hover:text-[#C85A17] font-semibold flex items-center gap-1 transition">
              <FileText size={13} />
              <span>View PWD Ticket</span>
            </Link>
            <Link to="/gis" className="hover:text-[#C85A17] font-semibold flex items-center gap-1 transition">
              <MapPin size={13} />
              <span>Locate on GIS Map</span>
            </Link>
            <Link to="/evidence-custody" className="hover:text-[#C85A17] font-semibold flex items-center gap-1 transition">
              <Camera size={13} />
              <span>Dashcam Evidence</span>
            </Link>
          </div>
        </div>
      </div>

      {/* ── Live Interactive GIS Map Section ── */}
      <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-[0_1px_3px_rgba(0,0,0,0.05)] p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-[#16192E] flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>Live Fleet Tracking & Municipal Hazard GIS Map</span>
            </h2>
            <p className="text-xs text-[#64748B] mt-0.5">
              Powered by real-time GPS kinematics across {stats.connectedBuses} active municipal transit buses and {stats.activeDefects}+ detected road defects.
            </p>
          </div>
          <Link
            to="/gis"
            className="text-xs font-bold px-3 py-1.5 rounded-lg bg-[#16192E] hover:bg-[#282F5A] text-white transition flex items-center gap-1.5 shadow-sm"
          >
            <span>Open Fullscreen GIS Command Center</span>
            <ArrowUpRight size={14} />
          </Link>
        </div>
        <LiveGisMap height="480px" />
      </div>

      {/* ── Municipal Operations Consoles Grid ── */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.05)]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-bold text-[#16192E] flex items-center gap-2">
              <Shield className="text-[#C85A17]" size={16} />
              <span>Integrated Municipal Modules & Engineering Systems</span>
            </h2>
            <p className="text-xs text-[#64748B] mt-0.5">
              Instant access to operational workflows, analytics, and field verification units.
            </p>
          </div>
          <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-[#F1F5F9] text-[#475569] font-bold border border-[#CBD5E1]">
            18 MODULES ACTIVE
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 text-xs font-semibold">
          <Link to="/gis" className="p-3 bg-[#F8FAFC] hover:bg-white hover:border-[#CBD5E1] border border-[#E2E8F0] text-[#16192E] rounded-lg transition flex items-center gap-2.5 shadow-xs group">
            <MapPin size={15} className="text-[#C85A17] group-hover:scale-110 transition" />
            <span>GIS Command Center</span>
          </Link>
          <Link to="/road-defects" className="p-3 bg-[#F8FAFC] hover:bg-white hover:border-[#CBD5E1] border border-[#E2E8F0] text-[#16192E] rounded-lg transition flex items-center gap-2.5 shadow-xs group">
            <Wrench size={15} className="text-[#C85A17] group-hover:scale-110 transition" />
            <span>PWD Work Orders</span>
          </Link>
          <Link to="/fleet" className="p-3 bg-[#F8FAFC] hover:bg-white hover:border-[#CBD5E1] border border-[#E2E8F0] text-[#16192E] rounded-lg transition flex items-center gap-2.5 shadow-xs group">
            <Bus size={15} className="text-[#16192E] group-hover:scale-110 transition" />
            <span>Fleet Live ({stats.connectedBuses})</span>
          </Link>
          <Link to="/traffic" className="p-3 bg-[#F8FAFC] hover:bg-white hover:border-[#CBD5E1] border border-[#E2E8F0] text-[#16192E] rounded-lg transition flex items-center gap-2.5 shadow-xs group">
            <TrafficCone size={15} className="text-amber-600 group-hover:scale-110 transition" />
            <span>Traffic Speed</span>
          </Link>
          <Link to="/congestion" className="p-3 bg-[#F8FAFC] hover:bg-white hover:border-[#CBD5E1] border border-[#E2E8F0] text-[#16192E] rounded-lg transition flex items-center gap-2.5 shadow-xs group">
            <Flame size={15} className="text-rose-600 group-hover:scale-110 transition" />
            <span>Congestion Heatmap</span>
          </Link>
          <Link to="/incidents" className="p-3 bg-[#F8FAFC] hover:bg-white hover:border-[#CBD5E1] border border-[#E2E8F0] text-[#16192E] rounded-lg transition flex items-center gap-2.5 shadow-xs group">
            <AlertTriangle size={15} className="text-red-600 group-hover:scale-110 transition" />
            <span>Incident Safety</span>
          </Link>
          <Link to="/urban-analytics" className="p-3 bg-[#F8FAFC] hover:bg-white hover:border-[#CBD5E1] border border-[#E2E8F0] text-[#16192E] rounded-lg transition flex items-center gap-2.5 shadow-xs group">
            <TrendingUp size={15} className="text-purple-600 group-hover:scale-110 transition" />
            <span>Urban Analytics</span>
          </Link>
          <Link to="/pedestrian-safety" className="p-3 bg-[#F8FAFC] hover:bg-white hover:border-[#CBD5E1] border border-[#E2E8F0] text-[#16192E] rounded-lg transition flex items-center gap-2.5 shadow-xs group">
            <Users size={15} className="text-indigo-600 group-hover:scale-110 transition" />
            <span>Pedestrian Safety</span>
          </Link>
          <Link to="/anpr" className="p-3 bg-[#F8FAFC] hover:bg-white hover:border-[#CBD5E1] border border-[#E2E8F0] text-[#16192E] rounded-lg transition flex items-center gap-2.5 shadow-xs group">
            <Camera size={15} className="text-teal-600 group-hover:scale-110 transition" />
            <span>ANPR Hotlist</span>
          </Link>
          <Link to="/route-delay" className="p-3 bg-[#F8FAFC] hover:bg-white hover:border-[#CBD5E1] border border-[#E2E8F0] text-[#16192E] rounded-lg transition flex items-center gap-2.5 shadow-xs group">
            <Navigation size={15} className="text-cyan-600 group-hover:scale-110 transition" />
            <span>Route Delay Audit</span>
          </Link>
          <Link to="/reports" className="p-3 bg-[#F8FAFC] hover:bg-white hover:border-[#CBD5E1] border border-[#E2E8F0] text-[#16192E] rounded-lg transition flex items-center gap-2.5 shadow-xs group">
            <FileText size={15} className="text-[#C85A17] group-hover:scale-110 transition" />
            <span>Automated Reports</span>
          </Link>
          <Link to="/evidence-custody" className="p-3 bg-[#F8FAFC] hover:bg-white hover:border-[#CBD5E1] border border-[#E2E8F0] text-[#16192E] rounded-lg transition flex items-center gap-2.5 shadow-xs group">
            <ShieldCheck size={15} className="text-emerald-600 group-hover:scale-110 transition" />
            <span>Evidence Custody</span>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Home;
