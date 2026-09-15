// src/pages/Congestion/Congestion.tsx
// Traffic Bottleneck Detection & Congestion Intelligence Command Center (Phase 20)

import React, { useState, useEffect } from "react";
import {
  Flame, Gauge, AlertTriangle, Activity, TrendingUp,
  MapPin, Clock, RefreshCw, Filter, ShieldAlert,
  ArrowDownRight, BarChart3, Search, Calendar,
  Sun, Moon, Sunset, Sunrise, Layers, ArrowRight,
  Sparkles, CheckCircle2, ChevronRight, Car
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell, Legend, LineChart, Line
} from "recharts";

import CongestionMap, {
  RoadSegmentData,
  CongestionHeatmapPoint
} from "../../components/CongestionMap";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface CongestionEvent {
  event_id:         string;
  event_type:       string;
  road_segment:     string;
  segment_name:     string;
  density:          number;
  average_speed:    number;
  congestion_score: number;
  severity:         "LOW" | "MEDIUM" | "HIGH" | "SEVERE";
  timestamp:        string;
  location:         { lat: number; lon: number };
  vehicle_count:    number;
  duration_seconds: number;
  is_bottleneck:    boolean;
  bus_id?:          string;
  camera_id?:       string;
}

export interface TopSegment {
  rank: number;
  segment_id: string;
  name: string;
  city: string;
  road_type: string;
  congestion_score: number;
  severity: "LOW" | "MEDIUM" | "HIGH" | "SEVERE";
  severity_color: "green" | "yellow" | "orange" | "red";
  current_speed: number;
  baseline_speed: number;
  free_flow_speed: number;
  density: number;
  route_delay_minutes: number;
  active_vehicles: number;
  peak_hours: string;
}

// ── Seed Mock Data for Resilient Client Rendering ─────────────────────────────

const INITIAL_SEGMENTS: RoadSegmentData[] = [
  {
    segment_id: "BLR_01",
    name: "Outer Ring Road – Marathahalli Bridge",
    road_type: "arterial",
    city: "Bangalore",
    capacity_per_km: 85,
    free_flow_speed: 45.0,
    baseline_speed: 30.0,
    current_speed: 8.5,
    density: 0.94,
    congestion_score: 92.5,
    severity: "SEVERE",
    is_bottleneck: true,
    active_vehicles: 48,
    speed_deficit_pct: 71.7,
    route_delay_minutes: 28.2,
    length_km: 4.9,
    polyline: [
      { lat: 12.9591, lon: 77.6971 },
      { lat: 12.9540, lon: 77.7020 },
      { lat: 12.9489, lon: 77.7070 },
    ],
  },
  {
    segment_id: "DEL_05",
    name: "ITO Junction – Vikas Marg Bridge",
    road_type: "arterial",
    city: "Delhi",
    capacity_per_km: 95,
    free_flow_speed: 45.0,
    baseline_speed: 28.0,
    current_speed: 11.0,
    density: 0.91,
    congestion_score: 89.5,
    severity: "SEVERE",
    is_bottleneck: true,
    active_vehicles: 46,
    speed_deficit_pct: 60.7,
    route_delay_minutes: 13.2,
    length_km: 3.2,
    polyline: [
      { lat: 28.6300, lon: 77.2400 },
      { lat: 28.6320, lon: 77.2480 },
      { lat: 28.6335, lon: 77.2560 },
    ],
  },
  {
    segment_id: "BLR_02",
    name: "Hosur Road – Central Silk Board",
    road_type: "arterial",
    city: "Bangalore",
    capacity_per_km: 90,
    free_flow_speed: 40.0,
    baseline_speed: 26.0,
    current_speed: 10.2,
    density: 0.89,
    congestion_score: 88.0,
    severity: "SEVERE",
    is_bottleneck: true,
    active_vehicles: 44,
    speed_deficit_pct: 60.8,
    route_delay_minutes: 22.4,
    length_km: 5.1,
    polyline: [
      { lat: 12.9170, lon: 77.6233 },
      { lat: 12.9122, lon: 77.6270 },
      { lat: 12.9075, lon: 77.6308 },
    ],
  },
  {
    segment_id: "DEL_01",
    name: "Ring Road – Dhaula Kuan to Mahipalpur",
    road_type: "expressway",
    city: "Delhi",
    capacity_per_km: 120,
    free_flow_speed: 70.0,
    baseline_speed: 45.0,
    current_speed: 14.2,
    density: 0.88,
    congestion_score: 86.4,
    severity: "SEVERE",
    is_bottleneck: true,
    active_vehicles: 42,
    speed_deficit_pct: 68.4,
    route_delay_minutes: 18.2,
    length_km: 5.4,
    polyline: [
      { lat: 28.5918, lon: 77.1675 },
      { lat: 28.5842, lon: 77.1545 },
      { lat: 28.5765, lon: 77.1420 },
    ],
  },
  {
    segment_id: "MUM_05",
    name: "Sion Circle – Dr. B.A. Road",
    road_type: "arterial",
    city: "Mumbai",
    capacity_per_km: 95,
    free_flow_speed: 45.0,
    baseline_speed: 29.0,
    current_speed: 12.8,
    density: 0.86,
    congestion_score: 84.8,
    severity: "SEVERE",
    is_bottleneck: true,
    active_vehicles: 41,
    speed_deficit_pct: 55.9,
    route_delay_minutes: 12.4,
    length_km: 3.7,
    polyline: [
      { lat: 19.0380, lon: 72.8630 },
      { lat: 19.0430, lon: 72.8660 },
      { lat: 19.0480, lon: 72.8690 },
    ],
  },
  {
    segment_id: "MUM_01",
    name: "Eastern Express Highway – Kurla Junction",
    road_type: "expressway",
    city: "Mumbai",
    capacity_per_km: 130,
    free_flow_speed: 80.0,
    baseline_speed: 52.0,
    current_speed: 16.0,
    density: 0.85,
    congestion_score: 83.2,
    severity: "SEVERE",
    is_bottleneck: true,
    active_vehicles: 51,
    speed_deficit_pct: 69.2,
    route_delay_minutes: 17.4,
    length_km: 5.8,
    polyline: [
      { lat: 19.0748, lon: 72.8856 },
      { lat: 19.0800, lon: 72.8900 },
      { lat: 19.0855, lon: 72.8940 },
    ],
  },
  {
    segment_id: "DEL_06",
    name: "Ashram Chowk – Mathura Road Underpass",
    road_type: "arterial",
    city: "Delhi",
    capacity_per_km: 105,
    free_flow_speed: 50.0,
    baseline_speed: 30.0,
    current_speed: 13.5,
    density: 0.84,
    congestion_score: 81.2,
    severity: "SEVERE",
    is_bottleneck: true,
    active_vehicles: 39,
    speed_deficit_pct: 55.0,
    route_delay_minutes: 13.3,
    length_km: 4.1,
    polyline: [
      { lat: 28.5710, lon: 77.2590 },
      { lat: 28.5745, lon: 77.2620 },
      { lat: 28.5780, lon: 77.2655 },
    ],
  },
  {
    segment_id: "BLR_04",
    name: "Whitefield Main Road – ITPL Gate",
    road_type: "arterial",
    city: "Bangalore",
    capacity_per_km: 80,
    free_flow_speed: 40.0,
    baseline_speed: 27.0,
    current_speed: 13.0,
    density: 0.81,
    congestion_score: 79.5,
    severity: "HIGH",
    is_bottleneck: true,
    active_vehicles: 35,
    speed_deficit_pct: 51.9,
    route_delay_minutes: 13.1,
    length_km: 4.2,
    polyline: [
      { lat: 12.9860, lon: 77.7280 },
      { lat: 12.9890, lon: 77.7340 },
      { lat: 12.9920, lon: 77.7400 },
    ],
  },
  {
    segment_id: "MUM_04",
    name: "JVLR – Powai Lake Corridor",
    road_type: "arterial",
    city: "Mumbai",
    capacity_per_km: 85,
    free_flow_speed: 50.0,
    baseline_speed: 34.0,
    current_speed: 17.2,
    density: 0.74,
    congestion_score: 73.5,
    severity: "HIGH",
    is_bottleneck: true,
    active_vehicles: 31,
    speed_deficit_pct: 49.4,
    route_delay_minutes: 11.9,
    length_km: 5.2,
    polyline: [
      { lat: 19.1240, lon: 72.8980 },
      { lat: 19.1280, lon: 72.9050 },
      { lat: 19.1310, lon: 72.9120 },
    ],
  },
  {
    segment_id: "DEL_02",
    name: "NH-48 – Dhaula Kuan to Shankar Vihar",
    road_type: "arterial",
    city: "Delhi",
    capacity_per_km: 90,
    free_flow_speed: 55.0,
    baseline_speed: 38.0,
    current_speed: 19.5,
    density: 0.72,
    congestion_score: 71.8,
    severity: "HIGH",
    is_bottleneck: true,
    active_vehicles: 29,
    speed_deficit_pct: 48.7,
    route_delay_minutes: 9.5,
    length_km: 4.8,
    polyline: [
      { lat: 28.5971, lon: 77.1690 },
      { lat: 28.6050, lon: 77.1680 },
      { lat: 28.6130, lon: 77.1670 },
    ],
  },
];

const SEVERITY_BADGES: Record<string, { bg: string; text: string; border: string; label: string }> = {
  LOW:    { bg: "bg-emerald-950/70", text: "text-emerald-400", border: "border-emerald-700/60", label: "Low (Green)" },
  MEDIUM: { bg: "bg-yellow-950/70",  text: "text-yellow-400",  border: "border-yellow-700/60",  label: "Moderate (Yellow)" },
  HIGH:   { bg: "bg-orange-950/70",  text: "text-orange-400",  border: "border-orange-700/60",  label: "High (Orange)" },
  SEVERE: { bg: "bg-red-950/70",     text: "text-red-400",     border: "border-red-700/60",     label: "Severe (Red)" },
};

export const Congestion: React.FC = () => {
  const [selectedCity, setSelectedCity] = useState<string>("All");
  const [dateRange, setDateRange] = useState<"today" | "yesterday" | "last_7_days" | "last_30_days">("today");
  const [timeOfDay, setTimeOfDay] = useState<"all" | "morning" | "afternoon" | "evening" | "night">("all");
  const [searchTerm, setSearchTerm] = useState<string>("");

  const [segments, setSegments] = useState<RoadSegmentData[]>(INITIAL_SEGMENTS);
  const [topSegments, setTopSegments] = useState<TopSegment[]>(INITIAL_SEGMENTS.map((s, idx) => ({
    rank: idx + 1,
    segment_id: s.segment_id,
    name: s.name,
    city: s.city,
    road_type: s.road_type,
    congestion_score: s.congestion_score,
    severity: s.severity,
    severity_color: s.severity === "SEVERE" ? "red" : (s.severity === "HIGH" ? "orange" : (s.severity === "MEDIUM" ? "yellow" : "green")),
    current_speed: s.current_speed,
    baseline_speed: s.baseline_speed,
    free_flow_speed: s.free_flow_speed,
    density: s.density,
    route_delay_minutes: s.route_delay_minutes || 10.5,
    active_vehicles: s.active_vehicles,
    peak_hours: "08:30 - 10:30 & 18:00 - 20:30",
  })));

  const [heatmapPoints, setHeatmapPoints] = useState<CongestionHeatmapPoint[]>([]);
  const [analyticsData, setAnalyticsData] = useState<any>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [lastRefreshed, setLastRefreshed] = useState<string>("Just now");

  // Fetch live data from backend API with fallback to local seed data
  const fetchData = async () => {
    setIsRefreshing(true);
    try {
      const cityQuery = selectedCity !== "All" ? `&city=${encodeURIComponent(selectedCity)}` : "";
      const baseParams = `date_range=${dateRange}&time_of_day=${timeOfDay}${cityQuery}`;

      // 1. Fetch Segments
      const segRes = await fetch(`/api/v1/congestion/segments?${baseParams}`);
      if (segRes.ok) {
        const segJson = await segRes.json();
        if (segJson.segments && segJson.segments.length > 0) {
          setSegments(segJson.segments);
        }
      }

      // 2. Fetch Heatmap
      const heatRes = await fetch(`/api/v1/congestion/heatmap?${baseParams}`);
      if (heatRes.ok) {
        const heatJson = await heatRes.json();
        if (heatJson.points) {
          setHeatmapPoints(heatJson.points);
        }
      }

      // 3. Fetch Top 10 Segments
      const topRes = await fetch(`/api/v1/congestion/top-segments?limit=10&${baseParams}`);
      if (topRes.ok) {
        const topJson = await topRes.json();
        if (topJson.top_segments) {
          setTopSegments(topJson.top_segments);
        }
      }

      // 4. Fetch Full Analytics
      const anaRes = await fetch(`/api/v1/congestion/analytics?${baseParams}`);
      if (anaRes.ok) {
        const anaJson = await anaRes.json();
        setAnalyticsData(anaJson);
      }

      setLastRefreshed(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    } catch (e) {
      console.warn("Backend fetch failed, using realistic client simulation store", e);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 20000);
    return () => clearInterval(interval);
  }, [selectedCity, dateRange, timeOfDay]);

  // Derived metrics
  const filteredSegments = selectedCity === "All"
    ? segments
    : segments.filter((s) => s.city.toLowerCase() === selectedCity.toLowerCase());

  const activeBottlenecks = filteredSegments.filter((s) => s.is_bottleneck || s.severity === "SEVERE" || s.severity === "HIGH");

  const avgSpeed = filteredSegments.length > 0
    ? (filteredSegments.reduce((acc, s) => acc + s.current_speed, 0) / filteredSegments.length).toFixed(1)
    : "18.4";

  const avgDensity = filteredSegments.length > 0
    ? ((filteredSegments.reduce((acc, s) => acc + s.density, 0) / filteredSegments.length) * 100).toFixed(0)
    : "72";

  const avgScore = filteredSegments.length > 0
    ? (filteredSegments.reduce((acc, s) => acc + s.congestion_score, 0) / filteredSegments.length).toFixed(1)
    : "74.5";

  const totalRouteDelay = filteredSegments.reduce((acc, s) => acc + (s.route_delay_minutes || 0), 0).toFixed(1);
  const avgRouteDelay = filteredSegments.length > 0
    ? (parseFloat(totalRouteDelay) / filteredSegments.length).toFixed(1)
    : "14.2";

  // Distribution for Donut Chart
  const severityDistribution = [
    { name: "Severe (Red)",       value: filteredSegments.filter((s) => s.severity === "SEVERE").length, color: "#ef4444" },
    { name: "High (Orange)",      value: filteredSegments.filter((s) => s.severity === "HIGH").length,   color: "#f97316" },
    { name: "Moderate (Yellow)",  value: filteredSegments.filter((s) => s.severity === "MEDIUM").length, color: "#eab308" },
    { name: "Low (Green)",        value: filteredSegments.filter((s) => s.severity === "LOW").length,    color: "#10b981" },
  ];

  // 24h Diurnal Curve Data
  const diurnalData = analyticsData?.hourly_diurnal_profile || [
    { hour: "06:00", congestion_score: 35.0, average_speed_kmh: 42.0 },
    { hour: "07:00", congestion_score: 55.0, average_speed_kmh: 30.0 },
    { hour: "08:00", congestion_score: 82.0, average_speed_kmh: 15.0 },
    { hour: "09:00", congestion_score: 91.0, average_speed_kmh: 11.5 },
    { hour: "10:00", congestion_score: 86.0, average_speed_kmh: 14.0 },
    { hour: "11:00", congestion_score: 68.0, average_speed_kmh: 22.0 },
    { hour: "12:00", congestion_score: 54.0, average_speed_kmh: 28.0 },
    { hour: "14:00", congestion_score: 50.0, average_speed_kmh: 31.0 },
    { hour: "16:00", congestion_score: 62.0, average_speed_kmh: 25.0 },
    { hour: "17:00", congestion_score: 79.0, average_speed_kmh: 17.0 },
    { hour: "18:00", congestion_score: 93.0, average_speed_kmh: 9.8 },
    { hour: "19:00", congestion_score: 95.0, average_speed_kmh: 8.5 },
    { hour: "20:00", congestion_score: 84.0, average_speed_kmh: 16.0 },
    { hour: "21:00", congestion_score: 60.0, average_speed_kmh: 26.0 },
    { hour: "22:00", congestion_score: 32.0, average_speed_kmh: 44.0 },
    { hour: "00:00", congestion_score: 15.0, average_speed_kmh: 52.0 },
  ];

  // Top segments table search filter
  const displayedTopSegments = topSegments.filter((s) => {
    return (
      searchTerm === "" ||
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.segment_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.city.toLowerCase().includes(searchTerm.toLowerCase())
    );
  });

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-4 sm:p-6 lg:p-8 space-y-6">
      {/* ── Top Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-gray-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="p-2 bg-red-950/60 border border-red-800/50 rounded-xl text-red-400">
              <Flame className="w-5 h-5 animate-pulse" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-white">
                  Traffic Congestion Analytics & Heatmap
                </h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  PHASE 20
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                Live thermal GIS corridor mapping, historical diurnal peak hours, route delay overhead, and Top 10 bottlenecks
              </p>
            </div>
          </div>
        </div>

        {/* Global Controls: Cities & Live Refresh */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-1 flex items-center">
            {["All", "Delhi", "Mumbai", "Bangalore"].map((city) => (
              <button
                key={city}
                onClick={() => setSelectedCity(city)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  selectedCity === city
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
                }`}
              >
                {city === "All" ? "All Metros" : city}
              </button>
            ))}
          </div>

          <button
            onClick={fetchData}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3 py-1.5 bg-gray-900 border border-gray-800 hover:bg-gray-800 text-gray-300 text-xs rounded-xl font-medium transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-indigo-400" : ""}`} />
            <span>{isRefreshing ? "Syncing..." : "Sync Live"}</span>
          </button>

          <a
            href="/od-analysis"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-950/60 border border-indigo-800/60 hover:bg-indigo-900 text-indigo-300 text-xs rounded-xl font-medium transition-all"
          >
            <span>Origin-Destination (Phase 21)</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* ── Heatmap Multi-Tier Filters Bar (Prompt Requirement) ──────────────── */}
      <div className="bg-gray-900/90 border border-gray-800 rounded-2xl p-4 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        {/* Date Range Filters */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs text-gray-400 mr-1 font-semibold uppercase tracking-wider">
            <Calendar className="w-3.5 h-3.5 text-indigo-400" />
            <span>Date Range:</span>
          </div>
          {[
            { id: "today", label: "Today" },
            { id: "yesterday", label: "Yesterday" },
            { id: "last_7_days", label: "Last 7 days" },
            { id: "last_30_days", label: "Last 30 days" },
          ].map((d) => (
            <button
              key={d.id}
              onClick={() => setDateRange(d.id as any)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                dateRange === d.id
                  ? "bg-gradient-to-r from-red-600 to-orange-600 text-white shadow-md font-bold"
                  : "bg-gray-800/80 text-gray-400 hover:text-gray-200 hover:bg-gray-700"
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>

        {/* Time of Day Filters */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs text-gray-400 mr-1 font-semibold uppercase tracking-wider">
            <Clock className="w-3.5 h-3.5 text-amber-400" />
            <span>Time of Day:</span>
          </div>
          {[
            { id: "all", label: "All Day", icon: Layers },
            { id: "morning", label: "Morning (06-12)", icon: Sunrise },
            { id: "afternoon", label: "Afternoon (12-17)", icon: Sun },
            { id: "evening", label: "Evening (17-22)", icon: Sunset },
            { id: "night", label: "Night (22-06)", icon: Moon },
          ].map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                onClick={() => setTimeOfDay(t.id as any)}
                className={`flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                  timeOfDay === t.id
                    ? "bg-amber-600 text-white shadow-md font-bold"
                    : "bg-gray-800/80 text-gray-400 hover:text-gray-200 hover:bg-gray-700"
                }`}
              >
                <Icon className="w-3 h-3" />
                <span>{t.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Key Performance Indicators (6 Cards) ─────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3.5">
        {/* 1. Network Congestion Score */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-gray-400">Congestion Score</span>
            <span className="p-1 bg-amber-950/60 border border-amber-700/40 rounded-lg text-amber-400">
              <Gauge className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-2xl font-bold font-mono text-amber-400">{avgScore}</span>
            <span className="text-[11px] text-gray-500">/ 100</span>
          </div>
          <div className="mt-1 text-[10px] text-gray-500">Weighted corridor index</div>
        </div>

        {/* 2. Average Speed */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-gray-400">Average Speed</span>
            <span className="p-1 bg-blue-950/60 border border-blue-700/40 rounded-lg text-blue-400">
              <Activity className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-2xl font-bold font-mono text-blue-400">{avgSpeed}</span>
            <span className="text-[11px] text-gray-500">km/h</span>
          </div>
          <div className="mt-1 text-[10px] text-gray-500">Across monitored corridors</div>
        </div>

        {/* 3. Vehicle Density */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-gray-400">Vehicle Density</span>
            <span className="p-1 bg-orange-950/60 border border-orange-700/40 rounded-lg text-orange-400">
              <Car className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-2xl font-bold font-mono text-orange-400">{avgDensity}%</span>
            <span className="text-[11px] text-gray-500">Occupancy</span>
          </div>
          <div className="mt-1 text-[10px] text-gray-500">Road capacity saturation</div>
        </div>

        {/* 4. Route Delay */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-gray-400">Avg Route Delay</span>
            <span className="p-1 bg-red-950/60 border border-red-700/40 rounded-lg text-red-400">
              <ArrowDownRight className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-2xl font-bold font-mono text-red-400">+{avgRouteDelay}</span>
            <span className="text-[11px] text-gray-500">min/trip</span>
          </div>
          <div className="mt-1 text-[10px] text-gray-500">Loss vs free-flow conditions</div>
        </div>

        {/* 5. Peak Hours Window */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-gray-400">Peak Hours</span>
            <span className="p-1 bg-purple-950/60 border border-purple-700/40 rounded-lg text-purple-400">
              <Clock className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2">
            <span className="text-xs font-bold font-mono text-purple-300 block">08:30 - 10:30</span>
            <span className="text-xs font-bold font-mono text-purple-300 block">18:00 - 20:30</span>
          </div>
          <div className="mt-1 text-[10px] text-gray-500">AM & PM rush windows</div>
        </div>

        {/* 6. Active Bottlenecks */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-gray-400">Active Bottlenecks</span>
            <span className="p-1 bg-red-950/60 border border-red-800/40 rounded-lg text-red-400">
              <ShieldAlert className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-2xl font-bold font-mono text-red-400">{activeBottlenecks.length}</span>
            <span className="text-[11px] text-red-400/80 font-medium">Corridors</span>
          </div>
          <div className="mt-1 text-[10px] text-gray-500">Severe traffic choke points</div>
        </div>
      </div>

      {/* ── Central GIS Map & Thermal Heatmap Section ────────────────────────── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-300">
              Live GIS Road Corridor & Congestion Heatmap
            </h2>
            <div className="flex items-center gap-1 text-[11px] bg-gray-900 px-2.5 py-0.5 rounded-full border border-gray-800">
              <span className="text-emerald-400 font-bold">Green: Low</span> •{" "}
              <span className="text-yellow-400 font-bold">Yellow: Moderate</span> •{" "}
              <span className="text-orange-400 font-bold">Orange: High</span> •{" "}
              <span className="text-red-400 font-bold">Red: Severe</span>
            </div>
          </div>
          <span className="text-xs text-gray-500">
            Filters: <strong className="text-gray-300 capitalize">{dateRange.replace(/_/g, " ")}</strong> | <strong className="text-gray-300 capitalize">{timeOfDay}</strong> • Synced: {lastRefreshed}
          </span>
        </div>

        <CongestionMap
          segments={filteredSegments}
          heatmapPoints={heatmapPoints}
          selectedCity={selectedCity}
          height="540px"
        />
      </div>

      {/* ── Top 10 Congested Road Segments Table (Prompt Requirement) ────────── */}
      <div className="bg-gray-900/90 border border-gray-800 rounded-2xl p-5 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-red-400" />
              Top 10 Congested Road Segments
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Ranked by real-time congestion score, speed deficit, and commuter route delay overhead
            </p>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-gray-500 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search segment or city..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-gray-300">
            <thead className="bg-gray-950/80 text-gray-400 uppercase tracking-wider text-[10px] border-b border-gray-800">
              <tr>
                <th className="py-2.5 px-3">Rank</th>
                <th className="py-2.5 px-3">Corridor Name</th>
                <th className="py-2.5 px-3">City</th>
                <th className="py-2.5 px-3">Congestion Score</th>
                <th className="py-2.5 px-3">Severity Color</th>
                <th className="py-2.5 px-3">Current Speed</th>
                <th className="py-2.5 px-3">Vehicle Density</th>
                <th className="py-2.5 px-3">Route Delay</th>
                <th className="py-2.5 px-3">Peak Hours Window</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 font-mono">
              {displayedTopSegments.slice(0, 10).map((seg) => {
                const badge = SEVERITY_BADGES[seg.severity] || SEVERITY_BADGES["MEDIUM"];
                return (
                  <tr key={seg.segment_id} className="hover:bg-gray-800/40 transition-colors">
                    <td className="py-3 px-3 font-bold text-gray-200">
                      <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-[11px] ${
                        seg.rank === 1 ? "bg-red-500/20 text-red-400 border border-red-500/40" :
                        seg.rank <= 3 ? "bg-orange-500/20 text-orange-400 border border-orange-500/40" :
                        "bg-gray-800 text-gray-300"
                      }`}>
                        #{seg.rank}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-sans font-medium text-white">
                      <div>{seg.name}</div>
                      <div className="text-[10px] text-gray-500 font-mono">{seg.segment_id} • {seg.road_type}</div>
                    </td>
                    <td className="py-3 px-3 font-sans text-gray-400">{seg.city}</td>
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-sm">{seg.congestion_score.toFixed(1)}</span>
                        <div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${
                              seg.severity === "SEVERE" ? "bg-red-500" :
                              seg.severity === "HIGH" ? "bg-orange-500" :
                              seg.severity === "MEDIUM" ? "bg-yellow-500" : "bg-emerald-500"
                            }`}
                            style={{ width: `${seg.congestion_score}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border uppercase ${badge.bg} ${badge.text} ${badge.border}`}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span className="text-red-400 font-bold">{seg.current_speed.toFixed(1)} km/h</span>{" "}
                      <span className="text-[10px] text-gray-500 font-sans">(Base: {seg.baseline_speed.toFixed(0)})</span>
                    </td>
                    <td className="py-3 px-3">
                      <span className="text-amber-400 font-bold">{(seg.density * 100).toFixed(0)}%</span>
                      <span className="text-[10px] text-gray-500 block font-sans">{seg.active_vehicles} veh/corridor</span>
                    </td>
                    <td className="py-3 px-3">
                      <span className="text-red-400 font-bold text-sm">+{seg.route_delay_minutes.toFixed(1)} min</span>
                    </td>
                    <td className="py-3 px-3 font-sans text-[11px] text-gray-400">
                      {seg.peak_hours}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Analytical Visualizations Grid ───────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 1. 24-Hour Diurnal Congestion & Speed Curve */}
        <div className="lg:col-span-2 bg-gray-900/80 border border-gray-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-indigo-400" />
                24-Hour Diurnal Congestion Curve vs Speed (AM & PM Peak Windows)
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">
                Hourly congestion score spikes align with morning office inbound (08:30-10:30) and evening return (18:00-20:30)
              </p>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={diurnalData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <defs>
                  <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="speedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis dataKey="hour" stroke="#6b7280" tick={{ fontSize: 11 }} />
                <YAxis stroke="#6b7280" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#111827", borderColor: "#374151", borderRadius: "0.75rem", fontSize: "12px" }}
                  itemStyle={{ color: "#e5e7eb" }}
                />
                <Area type="monotone" dataKey="congestion_score" name="Congestion Score" stroke="#ef4444" strokeWidth={2.5} fillOpacity={1} fill="url(#scoreGrad)" />
                <Area type="monotone" dataKey="average_speed_kmh" name="Average Speed (km/h)" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#speedGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 2. Congestion Severity Breakdown Donut */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
          <div className="mb-2">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-indigo-400" />
              Network Congestion Breakdown
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Proportion of road corridors by color severity
            </p>
          </div>
          <div className="h-56 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={severityDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {severityDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: "#111827", borderColor: "#374151", borderRadius: "0.75rem", fontSize: "12px" }}
                />
                <Legend
                  formatter={(val) => <span className="text-xs text-gray-300">{val}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Congestion;
