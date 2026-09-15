// src/pages/OriginDestination/OriginDestination.tsx
// Origin-Destination (OD) Traffic Analytics Module (Phase 21)
// Anonymized, Aggregated Macro Vehicle Movements Between Geographic Zones

import React, { useState, useEffect } from "react";
import {
  Compass, ShieldCheck, MapPin, ArrowRight, TrendingUp,
  Clock, Activity, RefreshCw, Layers, Sparkles,
  Info, BarChart3, Users, Car, Bus, ArrowUpRight
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend
} from "recharts";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface OdZone {
  zone_id: string;
  name: string;
  sub_regions: string[];
  city: string;
  centroid: { lat: number; lon: number };
  radius_meters: number;
  primary_land_use: string;
  daily_trip_generation: number;
  daily_trip_attraction: number;
}

export interface OdFlowVector {
  pair_key: string;
  origin_id: string;
  destination_id: string;
  origin_centroid: { lat: number; lon: number };
  destination_centroid: { lat: number; lon: number };
  daily_volume: number;
  morning_peak_volume: number;
  evening_peak_volume: number;
  flow_intensity: number;
  avg_duration_minutes: number;
  delay_minutes: number;
  corridor_route: string;
  mode_split: { public_bus: number; car: number; two_wheeler: number; commercial: number };
}

export interface OdMatrixCell {
  origin: string;
  destination: string;
  is_intrazonal: boolean;
  daily_volume: number;
  morning_peak_volume?: number;
  evening_peak_volume?: number;
  avg_duration_minutes: number;
  distance_km: number;
  corridor_route?: string;
}

export interface OdMatrixRow {
  origin_zone: string;
  destinations: OdMatrixCell[];
  total_origin_trips: number;
}

// ── Mock Initial Seed Data ────────────────────────────────────────────────────

const SEED_ZONES: OdZone[] = [
  {
    zone_id: "Zone A",
    name: "North Gateway & Transit Hub",
    sub_regions: ["Kashmere Gate", "Civil Lines", "ISBT Hub"],
    city: "Delhi NCR",
    centroid: { lat: 28.6675, lon: 77.2285 },
    radius_meters: 3200,
    primary_land_use: "Intermodal Transit Terminal & Residential Suburbs",
    daily_trip_generation: 42500,
    daily_trip_attraction: 38900,
  },
  {
    zone_id: "Zone B",
    name: "Central Commercial Core",
    sub_regions: ["Connaught Place", "Barakhamba", "Janpath"],
    city: "Delhi NCR",
    centroid: { lat: 28.6315, lon: 77.2167 },
    radius_meters: 2800,
    primary_land_use: "Commercial, Government Offices & Financial District",
    daily_trip_generation: 34200,
    daily_trip_attraction: 64800,
  },
  {
    zone_id: "Zone C",
    name: "South Tech Corridor & Trade Centre",
    sub_regions: ["Nehru Place", "Saket", "Okhla Phase III"],
    city: "Delhi NCR",
    centroid: { lat: 28.5494, lon: 77.2515 },
    radius_meters: 3600,
    primary_land_use: "IT Parks, Electronics Market & Retail Trade",
    daily_trip_generation: 39800,
    daily_trip_attraction: 48200,
  },
  {
    zone_id: "Zone D",
    name: "East Residential Gateway",
    sub_regions: ["Laxmi Nagar", "Anand Vihar ISBT", "Patparganj"],
    city: "Delhi NCR",
    centroid: { lat: 28.6469, lon: 77.3150 },
    radius_meters: 3400,
    primary_land_use: "High-Density Residential & Logistics Corridors",
    daily_trip_generation: 51600,
    daily_trip_attraction: 28400,
  },
];

const SEED_TOP_PAIRS = [
  { rank: 1, pair_key: "D → B", origin_name: "Zone D (East Gateway)", destination_name: "Zone B (CBD)", daily_volume: 19800, morning_peak_volume: 7940, avg_duration_minutes: 42.0, delay_minutes: 21.0, corridor_route: "Vikas Marg Inbound – Yamuna Bridge" },
  { rank: 2, pair_key: "A → B", origin_name: "Zone A (North Gateway)", destination_name: "Zone B (CBD)", daily_volume: 18450, morning_peak_volume: 6820, avg_duration_minutes: 26.5, delay_minutes: 12.5, corridor_route: "Subhash Marg – Delhi Gate" },
  { rank: 3, pair_key: "B → D", origin_name: "Zone B (CBD)", destination_name: "Zone D (East Gateway)", daily_volume: 16900, evening_peak_volume: 7150, avg_duration_minutes: 44.5, delay_minutes: 22.5, corridor_route: "Vikas Marg Outbound – ITO Chungi" },
  { rank: 4, pair_key: "D → C", origin_name: "Zone D (East Gateway)", destination_name: "Zone C (South Tech Hub)", daily_volume: 15200, morning_peak_volume: 6120, avg_duration_minutes: 48.0, delay_minutes: 23.0, corridor_route: "Noida Link Road – Kalindi Kunj" },
  { rank: 5, pair_key: "C → D", origin_name: "Zone C (South Tech Hub)", destination_name: "Zone D (East Gateway)", daily_volume: 14600, evening_peak_volume: 6480, avg_duration_minutes: 51.0, delay_minutes: 26.0, corridor_route: "Outer Ring Road – Mayur Vihar" },
  { rank: 6, pair_key: "A → C", origin_name: "Zone A (North Gateway)", destination_name: "Zone C (South Tech Hub)", daily_volume: 12600, morning_peak_volume: 4750, avg_duration_minutes: 52.0, delay_minutes: 24.0, corridor_route: "Ring Road – ITO – Ashram Flyover" },
];

export const OriginDestination: React.FC = () => {
  const [zones, setZones] = useState<OdZone[]>(SEED_ZONES);
  const [matrix, setMatrix] = useState<OdMatrixRow[]>([]);
  const [flows, setFlows] = useState<OdFlowVector[]>([]);
  const [topPairs, setTopPairs] = useState<any[]>(SEED_TOP_PAIRS);
  const [peakPeriods, setPeakPeriods] = useState<any[]>([]);
  const [selectedPair, setSelectedPair] = useState<any | null>(SEED_TOP_PAIRS[0]);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"flowmap" | "matrix" | "peaks">("flowmap");

  const fetchData = async () => {
    setIsRefreshing(true);
    try {
      // 1. Zones
      const zRes = await fetch("/api/v1/od/zones");
      if (zRes.ok) {
        const zJson = await zRes.json();
        if (zJson.zones) setZones(zJson.zones);
      }

      // 2. Matrix
      const mRes = await fetch("/api/v1/od/matrix");
      if (mRes.ok) {
        const mJson = await mRes.json();
        if (mJson.matrix) setMatrix(mJson.matrix);
      }

      // 3. Flow vectors
      const fRes = await fetch("/api/v1/od/flows");
      if (fRes.ok) {
        const fJson = await fRes.json();
        if (fJson.flows) {
          setFlows(fJson.flows);
          if (!selectedPair && fJson.flows.length > 0) setSelectedPair(fJson.flows[0]);
        }
      }

      // 4. Top Pairs
      const tRes = await fetch("/api/v1/od/top-pairs?limit=6");
      if (tRes.ok) {
        const tJson = await tRes.json();
        if (tJson.top_pairs) setTopPairs(tJson.top_pairs);
      }

      // 5. Peak periods
      const pRes = await fetch("/api/v1/od/peak-periods");
      if (pRes.ok) {
        const pJson = await pRes.json();
        if (pJson.peak_periods) setPeakPeriods(pJson.peak_periods);
      }
    } catch (e) {
      console.warn("Backend OD fetch failed, using realistic mock data", e);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // SVG coordinate projection helper
  // Map bounds covering Zone A (North), B (Central), C (South), D (East)
  const bounds = { minLat: 28.52, maxLat: 28.69, minLon: 77.19, maxLon: 77.34 };
  const projectCoords = (lat: number, lon: number) => {
    const latSpan = bounds.maxLat - bounds.minLat;
    const lonSpan = bounds.maxLon - bounds.minLon;
    const y = ((bounds.maxLat - lat) / latSpan) * 75 + 12.5;
    const x = ((lon - bounds.minLon) / lonSpan) * 75 + 12.5;
    return {
      x: Math.max(8, Math.min(92, x)),
      y: Math.max(8, Math.min(92, y)),
    };
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-4 sm:p-6 lg:p-8 space-y-6">
      {/* ── Top Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="p-2 bg-indigo-950/60 border border-indigo-800/50 rounded-xl text-indigo-400">
              <Compass className="w-5 h-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-white">
                  Origin-Destination Traffic Analytics
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  PHASE 21
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                Macro-level inter-zonal commuter flow modeling and directional travel desire lines
              </p>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <a
            href="/congestion"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 border border-gray-800 hover:bg-gray-800 text-gray-300 text-xs rounded-xl font-medium transition-all"
          >
            <span>Congestion Heatmap (Phase 20)</span>
          </a>

          <button
            onClick={fetchData}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs rounded-xl font-medium transition-all shadow-md"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            <span>{isRefreshing ? "Syncing..." : "Refresh OD"}</span>
          </button>
        </div>
      </div>

      {/* ── MANDATORY PRIVACY DISCLAIMER BANNER (Prompt Requirement) ────────── */}
      <div className="bg-gradient-to-r from-indigo-950/80 via-purple-950/70 to-gray-900/90 border border-indigo-700/50 rounded-2xl p-4 shadow-xl flex items-start gap-3">
        <div className="p-2 bg-indigo-500/20 rounded-xl text-indigo-400 shrink-0 mt-0.5">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-white tracking-wide uppercase">
              Demonstration OD Analysis
            </h2>
            <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              Zero PII • Anonymized
            </span>
          </div>
          <p className="text-xs text-indigo-200/90 leading-relaxed">
            This module processes strictly <strong>anonymized and aggregated macro vehicle movement observations</strong> across municipal zone boundary gates.
            <strong> Individual vehicle tracking, license plate correlation, and continuous GPS breadcrumbs are never exposed.</strong>
          </p>
        </div>
      </div>

      {/* ── Top Macro KPIs ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Inter-Zonal Trips */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400">Total Inter-Zonal Trips</span>
            <span className="p-1.5 bg-indigo-950/60 border border-indigo-700/40 rounded-lg text-indigo-400">
              <Car className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-white">169,450</span>
            <span className="text-xs text-gray-400">trips/day</span>
          </div>
          <div className="mt-2 text-[11px] text-gray-500">Across 12 directional corridors</div>
        </div>

        {/* Transit Fleet Mode Share */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400">Bus Fleet Mode Share</span>
            <span className="p-1.5 bg-emerald-950/60 border border-emerald-700/40 rounded-lg text-emerald-400">
              <Bus className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-emerald-400">43.8%</span>
            <span className="text-xs text-emerald-400/80 font-medium">Public Transit</span>
          </div>
          <div className="mt-2 text-[11px] text-gray-500">74,200 daily bus passenger trips</div>
        </div>

        {/* Average Inter-Zonal Transit Duration */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400">Avg Transit Duration</span>
            <span className="p-1.5 bg-amber-950/60 border border-amber-700/40 rounded-lg text-amber-400">
              <Clock className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-amber-400">38.4</span>
            <span className="text-xs text-gray-400">min/trip</span>
          </div>
          <div className="mt-2 text-[11px] text-gray-500">Delay overhead: +18.2 min vs free-flow</div>
        </div>

        {/* Highest Volume Corridor */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400">Busiest Desire Line</span>
            <span className="p-1.5 bg-red-950/60 border border-red-700/40 rounded-lg text-red-400">
              <TrendingUp className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3">
            <span className="text-sm font-bold font-mono text-white flex items-center gap-1.5">
              Zone D <ArrowRight className="w-3.5 h-3.5 text-indigo-400" /> Zone B
            </span>
            <span className="text-xs text-red-400 font-mono font-bold block mt-0.5">
              19,800 trips/day
            </span>
          </div>
          <div className="mt-2 text-[11px] text-gray-500">East Suburbs → Central Business District</div>
        </div>
      </div>

      {/* ── Tabs Navigation ─────────────────────────────────────────────────── */}
      <div className="flex border-b border-gray-800 gap-6 text-sm font-medium">
        <button
          onClick={() => setActiveTab("flowmap")}
          className={`pb-3 flex items-center gap-2 transition-all ${
            activeTab === "flowmap"
              ? "border-b-2 border-indigo-500 text-white font-bold"
              : "text-gray-400 hover:text-gray-200"
          }`}
        >
          <Compass className="w-4 h-4 text-indigo-400" />
          <span>Macro Flow Map</span>
        </button>

        <button
          onClick={() => setActiveTab("matrix")}
          className={`pb-3 flex items-center gap-2 transition-all ${
            activeTab === "matrix"
              ? "border-b-2 border-indigo-500 text-white font-bold"
              : "text-gray-400 hover:text-gray-200"
          }`}
        >
          <Layers className="w-4 h-4 text-indigo-400" />
          <span>OD Matrix (4 × 4)</span>
        </button>

        <button
          onClick={() => setActiveTab("peaks")}
          className={`pb-3 flex items-center gap-2 transition-all ${
            activeTab === "peaks"
              ? "border-b-2 border-indigo-500 text-white font-bold"
              : "text-gray-400 hover:text-gray-200"
          }`}
        >
          <Clock className="w-4 h-4 text-indigo-400" />
          <span>Peak Movement Periods & Tidal Shifts</span>
        </button>
      </div>

      {/* ── TAB 1: FLOW MAP & TOP PAIRS ─────────────────────────────────────── */}
      {activeTab === "flowmap" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Visual Vector Flow Map */}
          <div className="lg:col-span-2 bg-gray-900/90 border border-gray-800 rounded-2xl p-4 shadow-xl flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Compass className="w-4 h-4 text-indigo-400" />
                  Inter-Zonal Desire Lines & Directional Flow Arcs
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Flow width corresponds to daily volume; click any zone or flow vector to inspect corridor stats
                </p>
              </div>

              <div className="flex items-center gap-2 text-xs">
                <span className="flex items-center gap-1.5 text-gray-400">
                  <span className="w-2 h-2 rounded-full bg-indigo-500" />
                  Directional Vector
                </span>
              </div>
            </div>

            {/* SVG GIS Flow Map Canvas */}
            <div className="relative w-full h-[460px] bg-gray-950 rounded-xl overflow-hidden border border-gray-800/80">
              {/* Cartographic grid background */}
              <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] opacity-50" />

              <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                <defs>
                  {/* Arrowhead marker definition */}
                  <marker
                    id="flowArrow"
                    viewBox="0 0 10 10"
                    refX="6"
                    refY="5"
                    markerWidth="5"
                    markerHeight="5"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#818cf8" />
                  </marker>
                  <marker
                    id="flowArrowSelected"
                    viewBox="0 0 10 10"
                    refX="6"
                    refY="5"
                    markerWidth="6"
                    markerHeight="6"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 1 L 9 5 L 0 9 z" fill="#f43f5e" />
                  </marker>
                </defs>

                {/* 1. CURVED FLOW ARCS BETWEEN ZONES */}
                {flows.map((flow) => {
                  const p1 = projectCoords(flow.origin_centroid.lat, flow.origin_centroid.lon);
                  const p2 = projectCoords(flow.destination_centroid.lat, flow.destination_centroid.lon);
                  // Calculate quadratic curve control point
                  const midX = (p1.x + p2.x) / 2;
                  const midY = (p1.y + p2.y) / 2;
                  const dx = p2.x - p1.x;
                  const dy = p2.y - p1.y;
                  const ctrlX = midX - dy * 0.22;
                  const ctrlY = midY + dx * 0.22;

                  const isSelected = selectedPair?.pair_key === flow.pair_key;
                  const strokeWidth = isSelected ? 4.5 : Math.max(1.5, flow.flow_intensity * 4.0);
                  const strokeColor = isSelected ? "#f43f5e" : "#6366f1";

                  return (
                    <g
                      key={`arc-${flow.pair_key}`}
                      className="cursor-pointer transition-all hover:opacity-100"
                      onClick={() => setSelectedPair(flow)}
                    >
                      <path
                        d={`M ${p1.x} ${p1.y} Q ${ctrlX} ${ctrlY} ${p2.x} ${p2.y}`}
                        fill="none"
                        stroke={strokeColor}
                        strokeWidth={strokeWidth}
                        strokeOpacity={isSelected ? 1.0 : 0.65}
                        markerEnd={isSelected ? "url(#flowArrowSelected)" : "url(#flowArrow)"}
                      />
                    </g>
                  );
                })}

                {/* 2. ZONE CENTROID HUBS & PULSES */}
                {zones.map((zone) => {
                  const pt = projectCoords(zone.centroid.lat, zone.centroid.lon);
                  const isOrigin = selectedPair?.origin_id === zone.zone_id;
                  const isDest = selectedPair?.destination_id === zone.zone_id;

                  return (
                    <g
                      key={`hub-${zone.zone_id}`}
                      transform={`translate(${pt.x}, ${pt.y})`}
                      className="cursor-pointer"
                    >
                      {/* Outer pulse */}
                      <circle
                        r={isOrigin || isDest ? "6.5" : "4.8"}
                        fill="none"
                        stroke={isOrigin ? "#38bdf8" : (isDest ? "#f43f5e" : "#818cf8")}
                        strokeWidth="0.8"
                        className="animate-ping"
                        opacity="0.6"
                      />
                      {/* Hub Circle */}
                      <circle
                        r={isOrigin || isDest ? "4.5" : "3.6"}
                        fill={isOrigin ? "#0284c7" : (isDest ? "#e11d48" : "#4f46e5")}
                        stroke="#0f172a"
                        strokeWidth="1"
                      />
                      {/* Zone Label Tag */}
                      <text
                        x="0"
                        y="-6.5"
                        textAnchor="middle"
                        fill="#ffffff"
                        fontSize="3.2"
                        fontWeight="bold"
                        filter="drop-shadow(0 1px 2px rgb(0 0 0 / 0.8))"
                      >
                        {zone.zone_id}
                      </text>
                    </g>
                  );
                })}
              </svg>

              {/* Inset Legend */}
              <div className="absolute bottom-3 left-3 bg-gray-900/90 backdrop-blur-md border border-gray-800 rounded-xl p-2.5 text-[11px] text-gray-300 space-y-1">
                <div className="font-bold text-gray-400 uppercase text-[10px]">Movement Legend</div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
                  <span>Origin Zone Hub</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                  <span>Destination Zone Hub</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-4 h-0.5 bg-indigo-500 rounded" />
                  <span>Flow Volume Vector</span>
                </div>
              </div>
            </div>
          </div>

          {/* Flow Inspector & Top Desire Lines */}
          <div className="space-y-4">
            {/* Selected Desire Line Inspector Card */}
            {selectedPair && (
              <div className="bg-gradient-to-br from-gray-900 to-indigo-950/40 border border-indigo-800/60 rounded-2xl p-4 shadow-xl">
                <div className="flex items-center justify-between mb-3 border-b border-gray-800 pb-2.5">
                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-indigo-400 block font-bold">
                      Desire Line Inspector
                    </span>
                    <h4 className="text-base font-bold text-white flex items-center gap-2 mt-0.5">
                      {selectedPair.pair_key || `${selectedPair.origin_id} → ${selectedPair.destination_id}`}
                    </h4>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    #{selectedPair.rank || 1}
                  </span>
                </div>

                <div className="space-y-2.5 text-xs">
                  <div>
                    <span className="text-gray-400 text-[11px] block">Primary Transit Corridor</span>
                    <span className="font-medium text-gray-200">{selectedPair.corridor_route || "Main Arterial Expressway"}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-gray-800/60">
                    <div className="bg-gray-950/70 p-2.5 rounded-xl border border-gray-800/60">
                      <span className="text-[10px] text-gray-400 block">Daily Commuters</span>
                      <span className="text-base font-bold font-mono text-white">
                        {selectedPair.daily_volume.toLocaleString()}
                      </span>
                    </div>
                    <div className="bg-gray-950/70 p-2.5 rounded-xl border border-gray-800/60">
                      <span className="text-[10px] text-gray-400 block">Transit Time</span>
                      <span className="text-base font-bold font-mono text-amber-400">
                        {selectedPair.avg_duration_minutes}m
                      </span>
                    </div>
                  </div>

                  <div className="bg-red-950/40 border border-red-800/30 rounded-xl p-2.5 flex items-center justify-between text-[11px]">
                    <span className="text-red-300">Congestion Delay Overhead</span>
                    <span className="font-bold font-mono text-red-400">+{selectedPair.delay_minutes} min/trip</span>
                  </div>
                </div>
              </div>
            )}

            {/* Top OD Pairs Mini Leaderboard */}
            <div className="bg-gray-900/90 border border-gray-800 rounded-2xl p-4 shadow-xl">
              <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3 flex items-center gap-1.5">
                <BarChart3 className="w-3.5 h-3.5 text-indigo-400" />
                Top Origin-Destination Pairs
              </h4>

              <div className="space-y-2 font-mono">
                {topPairs.map((pair) => {
                  const isSelected = selectedPair?.pair_key === pair.pair_key;
                  return (
                    <div
                      key={pair.pair_key}
                      onClick={() => setSelectedPair(pair)}
                      className={`p-2.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                        isSelected
                          ? "bg-indigo-950/80 border-indigo-500/80 shadow-md"
                          : "bg-gray-950/60 border-gray-800/80 hover:bg-gray-800/60"
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="text-xs font-bold text-gray-400">#{pair.rank}</span>
                        <div>
                          <div className="text-xs font-bold text-white flex items-center gap-1 font-sans">
                            <span>{pair.pair_key}</span>
                          </div>
                          <div className="text-[10px] text-gray-500 font-sans truncate max-w-[140px]">
                            {pair.corridor_route}
                          </div>
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-xs font-bold text-indigo-300 font-mono">
                          {pair.daily_volume.toLocaleString()}
                        </div>
                        <div className="text-[10px] text-gray-500 font-sans">
                          +{pair.delay_minutes}m delay
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 2: CROSS-TABULAR OD MATRIX (4 × 4) ──────────────────────────── */}
      {activeTab === "matrix" && (
        <div className="bg-gray-900/90 border border-gray-800 rounded-2xl p-5 shadow-xl space-y-4">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              Origin-Destination Cross-Tabular Flow Matrix
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Aggregated daily vehicle movements (Origins in rows, Destinations in columns)
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-gray-300 border border-gray-800 rounded-xl overflow-hidden font-mono">
              <thead className="bg-gray-950 text-gray-400 uppercase tracking-wider text-[11px] border-b border-gray-800">
                <tr>
                  <th className="py-3 px-4 bg-gray-900 font-bold font-sans">Origin \ Destination</th>
                  <th className="py-3 px-4 text-center">Zone A (North)</th>
                  <th className="py-3 px-4 text-center">Zone B (CBD)</th>
                  <th className="py-3 px-4 text-center">Zone C (South Tech)</th>
                  <th className="py-3 px-4 text-center">Zone D (East Suburbs)</th>
                  <th className="py-3 px-4 text-right bg-gray-900 font-bold font-sans">Total Trips</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/70">
                {[
                  { origin: "Zone A (North Gateway)",       za: 9200,  zb: 18450, zc: 12600, zd: 8900,  total: 49150 },
                  { origin: "Zone B (Commercial CBD)",      za: 12400, zb: 14500, zc: 14100, zd: 16900, total: 57900 },
                  { origin: "Zone C (South Tech Corridor)", za: 11800, zb: 13900, zc: 18200, zd: 14600, total: 58500 },
                  { origin: "Zone D (East Residential)",    za: 8400,  zb: 19800, zc: 15200, zd: 11300, total: 54700 },
                ].map((row, idx) => (
                  <tr key={row.origin} className="hover:bg-gray-800/30 transition-colors">
                    <td className="py-3.5 px-4 font-bold font-sans text-white bg-gray-950/60">
                      {row.origin}
                    </td>

                    <td className={`py-3.5 px-4 text-center ${idx === 0 ? "bg-gray-800/30 text-gray-400 italic" : "text-white"}`}>
                      <div>{row.za.toLocaleString()}</div>
                      <span className="text-[10px] text-gray-500 font-sans">{idx === 0 ? "Intrazonal" : "trips"}</span>
                    </td>

                    <td className={`py-3.5 px-4 text-center ${idx === 1 ? "bg-gray-800/30 text-gray-400 italic" : "text-indigo-300 font-bold"}`}>
                      <div>{row.zb.toLocaleString()}</div>
                      <span className="text-[10px] text-gray-500 font-sans">{idx === 1 ? "Intrazonal" : "trips"}</span>
                    </td>

                    <td className={`py-3.5 px-4 text-center ${idx === 2 ? "bg-gray-800/30 text-gray-400 italic" : "text-white"}`}>
                      <div>{row.zc.toLocaleString()}</div>
                      <span className="text-[10px] text-gray-500 font-sans">{idx === 2 ? "Intrazonal" : "trips"}</span>
                    </td>

                    <td className={`py-3.5 px-4 text-center ${idx === 3 ? "bg-gray-800/30 text-gray-400 italic" : "text-white"}`}>
                      <div>{row.zd.toLocaleString()}</div>
                      <span className="text-[10px] text-gray-500 font-sans">{idx === 3 ? "Intrazonal" : "trips"}</span>
                    </td>

                    <td className="py-3.5 px-4 text-right font-bold text-white bg-gray-950/60">
                      {row.total.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── TAB 3: PEAK MOVEMENT PERIODS ────────────────────────────────────── */}
      {activeTab === "peaks" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            {
              title: "Morning Commuter Peak",
              time: "08:00 - 11:00",
              volume: "42,100 trips",
              direction: "Strong Inbound Surge → Zone B (CBD) & Zone C (Tech Hub)",
              dominant: ["D → B (7,940 trips)", "A → B (6,820 trips)", "D → C (6,120 trips)"],
              transitShare: "48.5% Public Transit",
              badgeColor: "bg-red-500/20 text-red-400 border-red-500/30",
            },
            {
              title: "Midday Commercial Circulation",
              time: "11:30 - 16:00",
              volume: "31,400 trips",
              direction: "Balanced Multi-Directional Inter-Business Trips",
              dominant: ["B → C (4,200 trips)", "C → B (3,820 trips)", "A → D (2,850 trips)"],
              transitShare: "36.2% Public Transit",
              badgeColor: "bg-amber-500/20 text-amber-400 border-amber-500/30",
            },
            {
              title: "Evening Commuter Peak (Tidal Reversal)",
              time: "17:30 - 21:00",
              volume: "46,800 trips",
              direction: "Strong Outbound Return → Zone D (East) & Zone A (North)",
              dominant: ["B → D (7,150 trips)", "C → D (6,480 trips)", "C → A (5,890 trips)"],
              transitShare: "46.0% Public Transit",
              badgeColor: "bg-red-500/20 text-red-400 border-red-500/30",
            },
            {
              title: "Nocturnal Logistics & Arterial Flow",
              time: "22:00 - 05:30",
              volume: "12,800 trips",
              direction: "Ring Road Freight Corridors & Inter-State Terminals",
              dominant: ["A → D (1,420 trips)", "D → A (1,380 trips)", "A → C (980 trips)"],
              transitShare: "12.0% Public Transit",
              badgeColor: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
            },
          ].map((period) => (
            <div key={period.title} className="bg-gray-900/90 border border-gray-800 rounded-2xl p-5 shadow-lg space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-white">{period.title}</h4>
                  <span className="text-xs font-mono text-gray-400 block mt-0.5">{period.time}</span>
                </div>
                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border uppercase font-mono ${period.badgeColor}`}>
                  {period.volume}
                </span>
              </div>

              <div className="text-xs space-y-2">
                <div className="bg-gray-950/70 p-2.5 rounded-xl border border-gray-800/60">
                  <span className="text-[10px] text-gray-500 block uppercase font-semibold">Tidal Flow Direction</span>
                  <span className="font-medium text-gray-200">{period.direction}</span>
                </div>

                <div>
                  <span className="text-[10px] text-gray-500 block uppercase font-semibold mb-1">Dominant Zone Pairs</span>
                  <div className="flex flex-wrap gap-1.5 font-mono">
                    {period.dominant.map((d) => (
                      <span key={d} className="px-2 py-0.5 bg-gray-800 rounded-md text-[11px] text-gray-300">
                        {d}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="text-[11px] text-emerald-400 font-semibold pt-1">
                  Fleet Utilization: {period.transitShare}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default OriginDestination;
