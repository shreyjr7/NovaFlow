// src/pages/Hazards/Hazards.tsx
// BEL Smart Automation • NovaFlow — AI Hazard Detections Page
import React, { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle, Crosshair, Droplets, Construction, ShieldAlert,
  Search, Filter, RefreshCw, CheckCircle2, Eye, Wrench, Clock,
  MapPin, Camera, ExternalLink, X, ChevronRight, Layers, FileText,
  Activity, ArrowRight
} from "lucide-react";

export interface HazardItem {
  id: string;
  type: "POTHOLE" | "WATERLOGGING" | "DAMAGED_ROAD" | "ROAD_DEBRIS" | "CRACKS" | "DAMAGED_INFRA";
  title: string;
  confidence: number;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  location: string;
  coordinates: { lat: number; lon: number };
  detectedAt: string;
  busSource: string;
  cameraSensor: string;
  status: "Detected" | "Verified" | "Assigned" | "In Progress" | "Resolved";
  assignedWorkOrder?: string;
  imageSvg: string;
  evidenceNotes: string;
}

const makeHazardSvg = (color: string, label: string) => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" width="320" height="180">
    <rect width="320" height="180" fill="#0f172a"/>
    <path d="M40 180 L130 90 L190 90 L280 180 Z" fill="#1e293b"/>
    <line x1="160" y1="90" x2="160" y2="180" stroke="#f59e0b" stroke-width="2" stroke-dasharray="8 6"/>
    <ellipse cx="160" cy="140" rx="45" ry="18" fill="#000000" opacity="0.85"/>
    <rect x="110" y="118" width="100" height="44" rx="4" fill="none" stroke="${color}" stroke-width="2.5" stroke-dasharray="4 3"/>
    <rect x="110" y="102" width="100" height="16" fill="${color}" rx="2"/>
    <text x="115" y="114" font-family="monospace" font-size="9" font-weight="bold" fill="#ffffff">${label}</text>
    <circle cx="20" cy="20" r="4" fill="#22c55e"/>
    <text x="30" y="24" font-family="Arial" font-size="10" fill="#94a3b8">EDGE AI CAMERA</text>
  </svg>`;
  return `data:image/svg+xml;base64,${btoa(svg)}`;
};

const INITIAL_HAZARDS: HazardItem[] = [
  {
    id: "HAZ-2026-081",
    type: "POTHOLE",
    title: "Severe Asphalt Pothole (Depth 8.5cm)",
    confidence: 96,
    severity: "CRITICAL",
    location: "Outer Ring Road km 14.2, Near Marathahalli Flyover",
    coordinates: { lat: 12.9348, lon: 77.6101 },
    detectedAt: "12 mins ago",
    busSource: "Bus #04 (KA-01-F-4821)",
    cameraSensor: "FRONT CAM",
    status: "Verified",
    assignedWorkOrder: "WO-BLR-2026-104",
    imageSvg: makeHazardSvg("#dc2626", "POTHOLE 96%"),
    evidenceNotes: "Deep asphalt surface degradation detected across right transit lane. 3 bus confirmation consensus."
  },
  {
    id: "HAZ-2026-082",
    type: "WATERLOGGING",
    title: "Monsoon Waterlogging Hotspot (Depth 14cm)",
    confidence: 92,
    severity: "HIGH",
    location: "Ring Road near AIIMS Flyover Underpass Lane 2",
    coordinates: { lat: 28.5672, lon: 77.2100 },
    detectedAt: "24 mins ago",
    busSource: "Bus #01 (DL-1PB-7744)",
    cameraSensor: "FRONT CAM",
    status: "Assigned",
    assignedWorkOrder: "WO-DEL-2026-082",
    imageSvg: makeHazardSvg("#3b82f6", "WATERLOG 92%"),
    evidenceNotes: "Submerged curbs and drainage runoff backup. Deceleration rate exceeds 65% for passing transit buses."
  },
  {
    id: "HAZ-2026-083",
    type: "DAMAGED_ROAD",
    title: "Structural Concrete Spalling on Flyover Pier",
    confidence: 94,
    severity: "HIGH",
    location: "Western Express Highway, Andheri Flyover km 22",
    coordinates: { lat: 19.1136, lon: 72.8697 },
    detectedAt: "38 mins ago",
    busSource: "Bus #07 (MH-02-CL-3310)",
    cameraSensor: "FRONT CAM",
    status: "In Progress",
    assignedWorkOrder: "WO-MUM-2026-044",
    imageSvg: makeHazardSvg("#f97316", "SPALLING 94%"),
    evidenceNotes: "Exposed reinforcement rebar with surface spallation. NHAI Western Corridor maintenance team dispatched."
  },
  {
    id: "HAZ-2026-084",
    type: "CRACKS",
    title: "Longitudinal Alligator Cracking Pattern",
    confidence: 89,
    severity: "MEDIUM",
    location: "Connaught Place Radial Road 3, New Delhi",
    coordinates: { lat: 28.6315, lon: 77.2167 },
    detectedAt: "52 mins ago",
    busSource: "Bus #09 (DL-1PC-2201)",
    cameraSensor: "REAR CAM",
    status: "Detected",
    imageSvg: makeHazardSvg("#eab308", "CRACKS 89%"),
    evidenceNotes: "Interconnected crack lattice covering 4.2m² of road surface. Surface sealing recommended before monsoon."
  },
  {
    id: "HAZ-2026-085",
    type: "ROAD_DEBRIS",
    title: "Fallen Cargo Obstruction on Central Bus Lane",
    confidence: 95,
    severity: "CRITICAL",
    location: "Hosur Road, Silk Board Junction Flyover Approach",
    coordinates: { lat: 12.9176, lon: 77.6238 },
    detectedAt: "1.1 hours ago",
    busSource: "Bus #12 (KA-01-F-9021)",
    cameraSensor: "FRONT CAM",
    status: "Resolved",
    assignedWorkOrder: "WO-BLR-2026-099",
    imageSvg: makeHazardSvg("#dc2626", "DEBRIS 95%"),
    evidenceNotes: "Wooden pallet debris obstructing central bus rapid corridor. Municipal rapid response unit cleared roadway."
  },
  {
    id: "HAZ-2026-086",
    type: "DAMAGED_INFRA",
    title: "Missing Steel Median Divider Guardrail",
    confidence: 91,
    severity: "HIGH",
    location: "Bellary Road, Hebbal Flyover Down-Ramp",
    coordinates: { lat: 13.0358, lon: 77.5970 },
    detectedAt: "1.8 hours ago",
    busSource: "Bus #14 (KA-01-F-1102)",
    cameraSensor: "RIGHT CAM",
    status: "Assigned",
    assignedWorkOrder: "WO-BLR-2026-105",
    imageSvg: makeHazardSvg("#f97316", "INFRA 91%"),
    evidenceNotes: "12-meter median barrier break following vehicular collision. High head-on collision vulnerability."
  },
  {
    id: "HAZ-2026-087",
    type: "POTHOLE",
    title: "Medium Transverse Pothole (Depth 5.2cm)",
    confidence: 88,
    severity: "MEDIUM",
    location: "Old Madras Road near Indiranagar Metro Station",
    coordinates: { lat: 12.9784, lon: 77.6408 },
    detectedAt: "2.4 hours ago",
    busSource: "Bus #18 (KA-01-F-8821)",
    cameraSensor: "FRONT CAM",
    status: "Verified",
    imageSvg: makeHazardSvg("#eab308", "POTHOLE 88%"),
    evidenceNotes: "Expanding surface pothole in wheel track. BBMP PWD scheduled for night pothole patching shift."
  },
  {
    id: "HAZ-2026-088",
    type: "WATERLOGGING",
    title: "Curbside Stormwater Inundation (Depth 9cm)",
    confidence: 87,
    severity: "MEDIUM",
    location: "Dairy Circle Underpass Approach, Bannerghatta Rd",
    coordinates: { lat: 12.9372, lon: 77.6010 },
    detectedAt: "3.2 hours ago",
    busSource: "Bus #20 (KA-01-F-3341)",
    cameraSensor: "FRONT CAM",
    status: "In Progress",
    assignedWorkOrder: "WO-BLR-2026-094",
    imageSvg: makeHazardSvg("#3b82f6", "WATERLOG 87%"),
    evidenceNotes: "Drain grates choked with leaf litter causing 20m localized ponding. Mobile pumping rig active."
  }
];

export const Hazards: React.FC = () => {
  const [hazards, setHazards] = useState<HazardItem[]>(INITIAL_HAZARDS);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [inspectItem, setInspectItem] = useState<HazardItem | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Counters
  const totalCount = hazards.length;
  const potholesCount = hazards.filter(h => h.type === "POTHOLE").length;
  const waterloggingCount = hazards.filter(h => h.type === "WATERLOGGING").length;
  const damagedRoadCount = hazards.filter(h => h.type === "DAMAGED_ROAD").length;
  const cracksCount = hazards.filter(h => h.type === "CRACKS").length;
  const debrisCount = hazards.filter(h => h.type === "ROAD_DEBRIS").length;
  const infraCount = hazards.filter(h => h.type === "DAMAGED_INFRA").length;

  const filteredHazards = useMemo(() => {
    return hazards.filter(h => {
      const matchSearch =
        searchQuery === "" ||
        h.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        h.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        h.location.toLowerCase().includes(searchQuery.toLowerCase()) ||
        h.busSource.toLowerCase().includes(searchQuery.toLowerCase());
      const matchType = selectedType === "ALL" || h.type === selectedType;
      const matchSeverity = selectedSeverity === "ALL" || h.severity === selectedSeverity;
      const matchStatus = selectedStatus === "ALL" || h.status === selectedStatus;
      return matchSearch && matchType && matchSeverity && matchStatus;
    });
  }, [hazards, searchQuery, selectedType, selectedSeverity, selectedStatus]);

  const handleCreateWorkOrder = (hazard: HazardItem) => {
    const newWoId = `WO-AUTOPWD-${Math.floor(1000 + Math.random() * 9000)}`;
    setHazards(prev =>
      prev.map(h =>
        h.id === hazard.id ? { ...h, status: "Assigned", assignedWorkOrder: newWoId } : h
      )
    );
    if (inspectItem && inspectItem.id === hazard.id) {
      setInspectItem(prev => prev ? { ...prev, status: "Assigned", assignedWorkOrder: newWoId } : null);
    }
    setToastMessage(`Dispatched to PWD Work Order ${newWoId} for ${hazard.location}!`);
    setTimeout(() => setToastMessage(null), 5000);
  };

  return (
    <div className="p-3 sm:p-5 lg:p-8 space-y-5 max-w-[1600px] mx-auto text-[#16192E]">
      {/* ── Toast Notification ── */}
      {toastMessage && (
        <div className="fixed top-5 right-5 z-50 bg-emerald-700 text-white px-4 py-3 rounded-xl shadow-xl flex items-center gap-2 text-xs font-semibold animate-fadeIn">
          <CheckCircle2 size={16} />
          <span>{toastMessage}</span>
          <button onClick={() => setToastMessage(null)} className="ml-2 text-white/80 hover:text-white">
            <X size={14} />
          </button>
        </div>
      )}

      {/* ── Top Header & Breadcrumb ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-4">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#C85A17] flex items-center gap-2 mb-1">
            <span>BHARAT ELECTRONICS LIMITED (BEL)</span>
            <span className="text-slate-400">•</span>
            <span>SMART AUTOMATION</span>
          </div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl">
              <AlertTriangle size={22} />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold tracking-tight text-[#16192E]">
                AI Hazard Detections
              </h1>
              <p className="text-xs sm:text-sm text-[#64748B] mt-0.5">
                Real-time edge vision inference for potholes, waterlogging, structural cracking, and roadway hazards.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <Link
            to="/gis"
            className="px-3.5 py-2 rounded-lg bg-white border border-[#CBD5E1] text-[#16192E] hover:bg-slate-50 text-xs font-semibold flex items-center gap-2 shadow-2xs transition"
          >
            <Layers size={14} className="text-[#C85A17]" />
            <span>View on GIS Map</span>
          </Link>
          <Link
            to="/work-orders"
            className="px-3.5 py-2 rounded-lg bg-[#C85A17] hover:bg-[#B34D10] text-white text-xs font-bold flex items-center gap-2 shadow-2xs transition"
          >
            <Wrench size={14} />
            <span>PWD Work Orders</span>
          </Link>
        </div>
      </div>

      {/* ── Metric Cards Grid ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
        <div className="bg-white p-3.5 rounded-xl border border-[#E2E8F0] shadow-2xs">
          <div className="text-[11px] text-[#64748B] font-semibold">Total Detected</div>
          <div className="text-xl sm:text-2xl font-mono font-bold text-[#16192E] mt-1">{totalCount}</div>
          <div className="text-[10px] text-emerald-700 mt-0.5">Active monitoring</div>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-red-200 bg-red-50/20 shadow-2xs">
          <div className="text-[11px] text-red-800 font-semibold flex items-center gap-1">
            <Crosshair size={12} /> Potholes
          </div>
          <div className="text-xl sm:text-2xl font-mono font-bold text-red-700 mt-1">{potholesCount}</div>
          <div className="text-[10px] text-red-600 mt-0.5">Avg Conf 92%</div>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-blue-200 bg-blue-50/20 shadow-2xs">
          <div className="text-[11px] text-blue-800 font-semibold flex items-center gap-1">
            <Droplets size={12} /> Waterlogging
          </div>
          <div className="text-xl sm:text-2xl font-mono font-bold text-blue-700 mt-1">{waterloggingCount}</div>
          <div className="text-[10px] text-blue-600 mt-0.5">Underpass hotspots</div>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-orange-200 bg-orange-50/20 shadow-2xs">
          <div className="text-[11px] text-orange-800 font-semibold flex items-center gap-1">
            <Construction size={12} /> Road Damage
          </div>
          <div className="text-xl sm:text-2xl font-mono font-bold text-orange-700 mt-1">{damagedRoadCount}</div>
          <div className="text-[10px] text-orange-600 mt-0.5">Spalling & shear</div>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-amber-200 bg-amber-50/20 shadow-2xs">
          <div className="text-[11px] text-amber-800 font-semibold flex items-center gap-1">
            <Activity size={12} /> Cracks
          </div>
          <div className="text-xl sm:text-2xl font-mono font-bold text-amber-700 mt-1">{cracksCount}</div>
          <div className="text-[10px] text-amber-600 mt-0.5">Lattice & fissure</div>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
          <div className="text-[11px] text-[#64748B] font-semibold flex items-center gap-1">
            <AlertTriangle size={12} /> Road Debris
          </div>
          <div className="text-xl sm:text-2xl font-mono font-bold text-[#16192E] mt-1">{debrisCount}</div>
          <div className="text-[10px] text-slate-500 mt-0.5">Obstruction logs</div>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-purple-200 bg-purple-50/20 shadow-2xs">
          <div className="text-[11px] text-purple-800 font-semibold flex items-center gap-1">
            <ShieldAlert size={12} /> Infra Damage
          </div>
          <div className="text-xl sm:text-2xl font-mono font-bold text-purple-700 mt-1">{infraCount}</div>
          <div className="text-[10px] text-purple-600 mt-0.5">Median & barrier</div>
        </div>
      </div>

      {/* ── Filters & Search Toolbar ── */}
      <div className="bg-white p-3.5 rounded-xl border border-[#E2E8F0] shadow-2xs space-y-3">
        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-[#94A3B8] absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by ID, road segment, bus, or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg pl-9 pr-3 py-1.5 text-xs text-[#16192E] placeholder-[#94A3B8] focus:outline-none focus:border-[#16192E]"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-2 text-[#94A3B8] hover:text-[#16192E]"
              >
                <X size={14} />
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="bg-[#F8FAFC] border border-[#CBD5E1] text-[#16192E] text-xs font-semibold rounded-lg px-2.5 py-1.5 focus:outline-none"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-[#F8FAFC] border border-[#CBD5E1] text-[#16192E] text-xs font-semibold rounded-lg px-2.5 py-1.5 focus:outline-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="Detected">Detected</option>
              <option value="Verified">Verified</option>
              <option value="Assigned">Assigned</option>
              <option value="In Progress">In Progress</option>
              <option value="Resolved">Resolved</option>
            </select>
          </div>
        </div>

        {/* Hazard Type Quick Pills */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1 border-t border-[#E2E8F0]">
          <span className="text-[10px] font-bold text-[#64748B] uppercase mr-1">Hazard Category:</span>
          {[
            { id: "ALL", label: "All Hazards" },
            { id: "POTHOLE", label: "Potholes" },
            { id: "WATERLOGGING", label: "Waterlogging" },
            { id: "DAMAGED_ROAD", label: "Damaged Road" },
            { id: "CRACKS", label: "Cracks" },
            { id: "ROAD_DEBRIS", label: "Road Debris" },
            { id: "DAMAGED_INFRA", label: "Missing Infra" },
          ].map(pill => (
            <button
              key={pill.id}
              onClick={() => setSelectedType(pill.id)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition cursor-pointer ${
                selectedType === pill.id
                  ? "bg-[#16192E] text-white shadow-xs font-bold"
                  : "bg-[#F8FAFC] text-[#64748B] hover:text-[#16192E] hover:bg-[#EEF2F6] border border-[#E2E8F0]"
              }`}
            >
              {pill.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Detection Table ── */}
      <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
        <div className="p-4 border-b border-[#E2E8F0] flex items-center justify-between">
          <div className="font-bold text-sm text-[#16192E] flex items-center gap-2">
            <span>Detection Feed ({filteredHazards.length})</span>
            <span className="text-[10px] text-slate-500 font-mono font-normal">
              Autonomous Edge Vision Consensus
            </span>
          </div>
          <span className="text-xs text-[#64748B]">Showing verified camera captures</span>
        </div>

        <div className="overflow-x-auto touch-scroll">
          <table className="w-full text-left text-xs min-w-[850px]">
            <thead className="bg-[#F8FAFC] text-[#64748B] uppercase text-[10px] tracking-wider border-b border-[#E2E8F0]">
              <tr>
                <th className="py-3 px-4">Hazard ID</th>
                <th className="py-3 px-4">Visual Evidence</th>
                <th className="py-3 px-4">Type &amp; Confidence</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Location Segment</th>
                <th className="py-3 px-4">Source Telemetry</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2E8F0]">
              {filteredHazards.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-10 text-center text-[#64748B]">
                    No hazard detections match your current search/filter criteria.
                  </td>
                </tr>
              ) : (
                filteredHazards.map(item => {
                  const isPothole = item.type === "POTHOLE";
                  const isWater = item.type === "WATERLOGGING";
                  const isCritical = item.severity === "CRITICAL";
                  const isHigh = item.severity === "HIGH";

                  return (
                    <tr key={item.id} className="hover:bg-[#F8FAFC] transition">
                      <td className="py-3 px-4 font-mono font-bold text-[#16192E]">
                        {item.id}
                      </td>
                      <td className="py-3 px-4">
                        <div
                          onClick={() => setInspectItem(item)}
                          className="w-16 h-10 rounded border border-[#CBD5E1] overflow-hidden cursor-pointer hover:opacity-80 transition relative shrink-0 shadow-2xs"
                          title="Click to inspect evidence"
                        >
                          <img src={item.imageSvg} alt={item.title} className="w-full h-full object-cover" />
                          <div className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-transparent transition">
                            <Eye size={12} className="text-white drop-shadow" />
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-bold text-[#16192E] flex items-center gap-1.5">
                          {isPothole && <Crosshair size={13} className="text-red-500" />}
                          {isWater && <Droplets size={13} className="text-blue-500" />}
                          {!isPothole && !isWater && <Construction size={13} className="text-orange-500" />}
                          <span>{item.type.replace(/_/g, " ")}</span>
                        </div>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                            Confidence: {item.confidence}%
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            isCritical
                              ? "bg-rose-50 text-rose-700 border border-rose-200 font-extrabold"
                              : isHigh
                              ? "bg-orange-50 text-orange-700 border border-orange-200"
                              : "bg-amber-50 text-amber-700 border border-amber-200"
                          }`}
                        >
                          {item.severity}
                        </span>
                      </td>
                      <td className="py-3 px-4 max-w-[220px]">
                        <div className="font-semibold text-[#16192E] truncate" title={item.location}>
                          {item.location}
                        </div>
                        <div className="text-[10px] text-[#64748B] flex items-center gap-1 mt-0.5 font-mono">
                          <MapPin size={10} />
                          {item.coordinates.lat.toFixed(4)}, {item.coordinates.lon.toFixed(4)}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-mono text-[11px] text-[#16192E] font-medium">{item.busSource}</div>
                        <div className="text-[10px] text-[#64748B] flex items-center gap-1 mt-0.5">
                          <Clock size={10} /> {item.detectedAt} • {item.cameraSensor}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            item.status === "Resolved"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : item.status === "In Progress"
                              ? "bg-purple-50 text-purple-700 border border-purple-200"
                              : item.status === "Assigned"
                              ? "bg-blue-50 text-blue-700 border border-blue-200"
                              : "bg-amber-50 text-amber-700 border border-amber-200"
                          }`}
                        >
                          {item.status}
                        </span>
                        {item.assignedWorkOrder && (
                          <div className="text-[9px] font-mono text-slate-500 mt-0.5">
                            {item.assignedWorkOrder}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => setInspectItem(item)}
                            className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-[#16192E] transition"
                            title="Inspect Evidence"
                          >
                            <Eye size={14} />
                          </button>
                          {item.status !== "Assigned" && item.status !== "Resolved" && (
                            <button
                              onClick={() => handleCreateWorkOrder(item)}
                              className="px-2 py-1 rounded-lg bg-[#C85A17] hover:bg-[#B34D10] text-white text-[11px] font-bold flex items-center gap-1 shadow-2xs transition"
                              title="Dispatch Work Order"
                            >
                              <Wrench size={11} />
                              <span>Dispatch</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Evidence Inspection Modal ── */}
      {inspectItem && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-5">
          <div className="bg-white rounded-2xl border border-[#CBD5E1] shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-5 space-y-4 animate-fadeIn">
            <div className="flex items-start justify-between border-b border-[#E2E8F0] pb-3">
              <div>
                <div className="text-[10px] font-mono font-bold uppercase text-[#C85A17]">
                  EDGE CAMERA INFERENCE EVIDENCE
                </div>
                <h3 className="text-lg font-bold text-[#16192E] mt-0.5">
                  {inspectItem.title}
                </h3>
                <p className="text-xs text-[#64748B] mt-0.5">
                  ID: {inspectItem.id} • Detected by {inspectItem.busSource} ({inspectItem.cameraSensor})
                </p>
              </div>
              <button
                onClick={() => setInspectItem(null)}
                className="p-1.5 rounded-lg text-[#64748B] hover:text-[#16192E] hover:bg-slate-100"
              >
                <X size={18} />
              </button>
            </div>

            <div className="rounded-xl overflow-hidden border border-[#CBD5E1] relative shadow-inner">
              <img src={inspectItem.imageSvg} alt={inspectItem.title} className="w-full h-auto" />
              <div className="absolute top-3 left-3 bg-black/70 text-white text-[10px] font-mono px-2 py-1 rounded">
                AI INFERENCE CONFIDENCE: {inspectItem.confidence}%
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs bg-[#F8FAFC] p-3 rounded-xl border border-[#E2E8F0]">
              <div>
                <span className="text-[#64748B]">Location:</span>
                <p className="font-semibold text-[#16192E] mt-0.5">{inspectItem.location}</p>
              </div>
              <div>
                <span className="text-[#64748B]">GPS Coordinates:</span>
                <p className="font-mono text-[#16192E] mt-0.5">
                  {inspectItem.coordinates.lat.toFixed(5)}, {inspectItem.coordinates.lon.toFixed(5)}
                </p>
              </div>
              <div>
                <span className="text-[#64748B]">Severity Classification:</span>
                <p className="font-bold text-[#C85A17] mt-0.5">{inspectItem.severity}</p>
              </div>
              <div>
                <span className="text-[#64748B]">Current Workflow Status:</span>
                <p className="font-semibold text-emerald-700 mt-0.5">{inspectItem.status}</p>
              </div>
            </div>

            <div className="text-xs space-y-1">
              <span className="font-bold text-[#16192E]">Sensor Observations:</span>
              <p className="text-[#475569] leading-relaxed">{inspectItem.evidenceNotes}</p>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-[#E2E8F0]">
              <button
                onClick={() => setInspectItem(null)}
                className="px-4 py-2 rounded-lg border border-[#CBD5E1] text-[#16192E] hover:bg-slate-50 text-xs font-semibold"
              >
                Close
              </button>
              {inspectItem.status !== "Assigned" && inspectItem.status !== "Resolved" && (
                <button
                  onClick={() => handleCreateWorkOrder(inspectItem)}
                  className="px-4 py-2 rounded-lg bg-[#C85A17] hover:bg-[#B34D10] text-white text-xs font-bold flex items-center gap-2 shadow-sm"
                >
                  <Wrench size={14} />
                  <span>Assign to PWD Work Order</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Hazards;
