// src/pages/Traffic/Traffic.tsx
// Vehicle Detection + Tracking Dashboard

import React, { useState, useEffect, useRef } from "react";
import {
  Car, Bus, Truck, Bike, Wind, Gauge, BarChart3,
  Activity, TrendingUp, MapPin, Camera, RefreshCw,
  Layers, ArrowRight, CircleDot,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, AreaChart, Area,
  PieChart, Pie, Cell, Legend,
} from "recharts";

// ── Types ─────────────────────────────────────────────────────────────────────

interface VehicleCounts {
  car:        number;
  bus:        number;
  truck:      number;
  two_wheeler: number;
  van:        number;
  total:      number;
}

interface SpeedStats {
  car:        number;
  bus:        number;
  truck:      number;
  two_wheeler: number;
  van:        number;
  all:        number;
}

interface DensityRegion {
  name:          string;
  total:         number;
  density_score: number;
  density_level: "low" | "medium" | "high";
  occupancy:     VehicleCounts;
}

interface LiveSnapshot {
  timestamp:      string;
  active_tracks:  number;
  counts:         VehicleCounts;
  avg_speed_kmh:  SpeedStats;
  density:        DensityRegion[];
}

// ── Mock data generators ──────────────────────────────────────────────────────

function genSnapshot(t: number): LiveSnapshot {
  const r = (a: number, b: number) => Math.round(a + Math.random() * (b - a));
  return {
    timestamp:     new Date().toISOString(),
    active_tracks: r(4, 22),
    counts: {
      car:         r(120, 350),
      bus:         r(10, 40),
      truck:       r(8, 30),
      two_wheeler: r(200, 600),
      van:         r(15, 50),
      total:       0,
    },
    avg_speed_kmh: {
      car:         r(25, 60),
      bus:         r(18, 40),
      truck:       r(15, 35),
      two_wheeler: r(30, 65),
      van:         r(20, 50),
      all:         r(22, 55),
    },
    density: [
      {
        name:          "Main_Lane",
        total:         r(2, 18),
        density_score: Math.random(),
        density_level: (["low", "medium", "high"] as const)[Math.floor(Math.random() * 3)],
        occupancy:     { car: r(1, 8), bus: r(0, 2), truck: r(0, 2), two_wheeler: r(1, 6), van: r(0, 2), total: 0 },
      },
    ],
  };
}

// Pre-compute baseline
const BASE = genSnapshot(0);
BASE.counts.total = Object.values(BASE.counts).reduce((a, b) => a + b, 0) - BASE.counts.total;

// Speed history for line chart (last 20 readings)
const SPEED_HISTORY: { time: string; car: number; two_wheeler: number; bus: number; truck: number }[] = Array.from({ length: 20 }, (_, i) => ({
  time:        `-${(20 - i) * 3}s`,
  car:         20 + Math.round(Math.random() * 35),
  two_wheeler: 25 + Math.round(Math.random() * 40),
  bus:         15 + Math.round(Math.random() * 20),
  truck:       12 + Math.round(Math.random() * 18),
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

const VEHICLE_COLORS: Record<string, string> = {
  car:         "#3b82f6",
  bus:         "#0ea5e9",
  truck:       "#ea580c",
  two_wheeler: "#8b5cf6",
  van:         "#10b981",
};

const DENSITY_COLORS = { low: "#16a34a", medium: "#d97706", high: "#dc2626" };

function DensityBar({ score, level }: { score: number; level: string }) {
  const color = DENSITY_COLORS[level as keyof typeof DENSITY_COLORS] ?? "#64748b";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-[#64748B]">Density</span>
        <span style={{ color }} className="font-semibold capitalize">{level}</span>
      </div>
      <div className="w-full bg-[#E2E8F0] rounded-full h-2">
        <div className="h-2 rounded-full transition-all" style={{ width: `${Math.round(score * 100)}%`, backgroundColor: color }} />
      </div>
      <div className="text-right text-xs text-[#64748B]">{Math.round(score * 100)}%</div>
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: number | string;
  sub?: string;
  icon: React.FC<{ size?: number; className?: string }>;
  color?: string;
  trend?: number;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, sub, icon: Icon, color = "text-[#C85A17]", trend }) => (
  <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-sm">
    <div className="flex items-center justify-between mb-2">
      <span className="text-xs font-medium text-[#64748B]">{title}</span>
      <Icon size={16} className={color} />
    </div>
    <p className="text-2xl font-bold text-[#16192E] tracking-tight">{value}</p>
    {sub && <p className="text-xs text-[#64748B] mt-1">{sub}</p>}
    {trend !== undefined && (
      <p className={`text-xs mt-1 font-medium ${trend >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
        {trend >= 0 ? "▲" : "▼"} {Math.abs(trend)}% vs last hr
      </p>
    )}
  </div>
);

// ── Main component ────────────────────────────────────────────────────────────

const Traffic: React.FC = () => {
  const [snap, setSnap] = useState<LiveSnapshot>(BASE);
  const [speedHistory, setSpeedHistory] = useState(SPEED_HISTORY);
  const [countHistory, setCountHistory] = useState<{ time: string; total: number }[]>([]);
  const [liveMode, setLiveMode] = useState(true);
  const [activeCam, setActiveCam] = useState("FRONT");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Simulate live updates every 2s
  useEffect(() => {
    if (!liveMode) return;
    intervalRef.current = setInterval(() => {
      const s = genSnapshot(Date.now());
      s.counts.total = s.counts.car + s.counts.bus + s.counts.truck + s.counts.two_wheeler + s.counts.van;
      setSnap(s);

      const now = new Date().toLocaleTimeString("en-IN", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
      setSpeedHistory(prev => [
        ...prev.slice(-19),
        { time: now, car: s.avg_speed_kmh.car, two_wheeler: s.avg_speed_kmh.two_wheeler,
          bus: s.avg_speed_kmh.bus, truck: s.avg_speed_kmh.truck },
      ]);
      setCountHistory(prev => [
        ...prev.slice(-19),
        { time: now, total: s.counts.total },
      ]);
    }, 2000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [liveMode]);

  const pieData = [
    { name: "Car",         value: snap.counts.car,         fill: VEHICLE_COLORS.car },
    { name: "Two-Wheeler", value: snap.counts.two_wheeler,  fill: VEHICLE_COLORS.two_wheeler },
    { name: "Bus",         value: snap.counts.bus,          fill: VEHICLE_COLORS.bus },
    { name: "Truck",       value: snap.counts.truck,        fill: VEHICLE_COLORS.truck },
    { name: "Van",         value: snap.counts.van,          fill: VEHICLE_COLORS.van },
  ];

  const speedBarData = [
    { name: "Car",         speed: snap.avg_speed_kmh.car,         fill: VEHICLE_COLORS.car },
    { name: "2-Wheeler",   speed: snap.avg_speed_kmh.two_wheeler,  fill: VEHICLE_COLORS.two_wheeler },
    { name: "Bus",         speed: snap.avg_speed_kmh.bus,          fill: VEHICLE_COLORS.bus },
    { name: "Truck",       speed: snap.avg_speed_kmh.truck,        fill: VEHICLE_COLORS.truck },
    { name: "Van",         speed: snap.avg_speed_kmh.van,          fill: VEHICLE_COLORS.van },
  ];

  return (
    <div className="min-h-screen bg-transparent text-[#16192E] p-3 sm:p-5 lg:p-6 space-y-4 sm:space-y-6">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-[#16192E] tracking-tight flex items-center gap-2">
            <Activity size={24} className="text-[#C85A17] shrink-0" />
            <span>Vehicle Detection &amp; Tracking</span>
          </h1>
          <p className="text-xs sm:text-sm text-[#64748B] mt-1">
            ByteTrack multi-object tracking · Counting lines · Speed estimation · Density analysis
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2.5 py-1 rounded-full font-medium border ${liveMode ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-slate-100 text-[#64748B] border-[#CBD5E1]"}`}>
            {liveMode ? "● LIVE" : "⏸ PAUSED"}
          </span>
          <button
            onClick={() => setLiveMode(l => !l)}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-white border border-[#CBD5E1] rounded-lg hover:bg-[#F8FAFC] text-[#16192E] font-medium shadow-2xs transition cursor-pointer"
          >
            <RefreshCw size={12} /> {liveMode ? "Pause" : "Resume"}
          </button>
        </div>
      </div>

      {/* ── Camera selector ─────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 flex-wrap text-xs">
        <Camera size={14} className="text-[#64748B] shrink-0" />
        <span className="font-medium text-[#64748B]">Camera:</span>
        {["FRONT", "REAR", "LEFT", "RIGHT"].map(cam => (
          <button
            key={cam}
            onClick={() => setActiveCam(cam)}
            className={`px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-lg border font-medium transition cursor-pointer ${
              activeCam === cam
                ? "bg-[#16192E] border-[#16192E] text-white shadow-xs"
                : "bg-white border-[#CBD5E1] text-[#64748B] hover:text-[#16192E] hover:bg-[#F8FAFC]"
            }`}
          >
            {cam}
          </button>
        ))}
        <span className="text-[#64748B]">
          Active Tracks: <span className="text-[#C85A17] font-bold">{snap.active_tracks}</span>
        </span>
      </div>

      {/* ── KPI Row ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-2.5 sm:gap-3">
        <StatCard title="Total Vehicles"  value={snap.counts.total}        icon={TrendingUp} color="text-[#C85A17]"       sub="cumulative" />
        <StatCard title="Cars"            value={snap.counts.car}          icon={Car}        color="text-blue-600" />
        <StatCard title="Two-Wheelers"    value={snap.counts.two_wheeler}  icon={Bike}       color="text-purple-600" />
        <StatCard title="Buses"           value={snap.counts.bus}          icon={Bus}        color="text-cyan-600"   />
        <StatCard title="Trucks"          value={snap.counts.truck}        icon={Truck}      color="text-orange-600" />
        <StatCard title="Avg Speed"       value={`${snap.avg_speed_kmh.all} km/h`} icon={Gauge} color="text-emerald-600" sub="all vehicles" />
        <StatCard title="Active Tracks"   value={snap.active_tracks}       icon={CircleDot}  color="text-amber-600" sub="ByteTrack IDs" />
      </div>

      {/* ── Charts Row 1 ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Vehicle composition pie */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-sm">
          <h3 className="text-sm font-bold text-[#16192E] mb-4 flex items-center gap-2">
            <Layers size={15} className="text-[#C85A17]" /> Vehicle Composition
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85}
                   paddingAngle={3} dataKey="value">
                {pieData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: "#FFFFFF", borderColor: "#CBD5E1", color: "#16192E", borderRadius: "8px", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)" }}
                formatter={(v: number) => [v.toLocaleString(), ""]}
              />
              <Legend iconType="circle" iconSize={8}
                formatter={(value) => <span className="text-xs text-[#64748B] font-medium">{value}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Average speed per class bar */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-sm">
          <h3 className="text-sm font-bold text-[#16192E] mb-4 flex items-center gap-2">
            <Gauge size={15} className="text-emerald-600" /> Avg Speed by Class (km/h)
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={speedBarData} barSize={24}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#64748B" }} />
              <YAxis tick={{ fontSize: 10, fill: "#64748B" }} unit=" km/h" domain={[0, 80]} />
              <Tooltip
                contentStyle={{ backgroundColor: "#FFFFFF", borderColor: "#CBD5E1", color: "#16192E", borderRadius: "8px", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)" }}
                formatter={(v: number) => [`${v} km/h`, "Speed"]}
              />
              <Bar dataKey="speed" radius={[4, 4, 0, 0]}>
                {speedBarData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Density panel */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-sm">
          <h3 className="text-sm font-bold text-[#16192E] mb-4 flex items-center gap-2">
            <BarChart3 size={15} className="text-[#C85A17]" /> Lane Density
          </h3>
          {snap.density.map(region => (
            <div key={region.name} className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-[#16192E]">{region.name.replace("_", " ")}</span>
                <span className="text-xs font-medium text-[#64748B]">{region.total} vehicles</span>
              </div>
              <DensityBar score={region.density_score} level={region.density_level} />
              <div className="mt-3 grid grid-cols-3 gap-2">
                {Object.entries(region.occupancy).filter(([k]) => k !== "total").map(([cls, cnt]) => (
                  <div key={cls} className="text-center bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-2">
                    <p className="text-[11px] font-medium text-[#64748B] capitalize">{cls.replace("_", " ")}</p>
                    <p className="text-sm font-bold" style={{ color: VEHICLE_COLORS[cls] ?? "#64748b" }}>{cnt}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Charts Row 2 ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Speed history line chart */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-sm">
          <h3 className="text-sm font-bold text-[#16192E] mb-4 flex items-center gap-2">
            <Wind size={15} className="text-[#C85A17]" /> Speed History (km/h)
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={speedHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="time" tick={{ fontSize: 9, fill: "#64748B" }} interval={4} />
              <YAxis tick={{ fontSize: 10, fill: "#64748B" }} unit=" km/h" domain={[0, 90]} />
              <Tooltip
                contentStyle={{ backgroundColor: "#FFFFFF", borderColor: "#CBD5E1", color: "#16192E", borderRadius: "8px", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)" }}
              />
              <Legend iconSize={8} formatter={(v) => <span className="text-xs text-[#64748B] font-medium">{v}</span>} />
              <Line type="monotone" dataKey="car"        stroke={VEHICLE_COLORS.car}        strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="two_wheeler" stroke={VEHICLE_COLORS.two_wheeler} strokeWidth={2} dot={false} name="Two-Wheeler" />
              <Line type="monotone" dataKey="bus"        stroke={VEHICLE_COLORS.bus}        strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="truck"      stroke={VEHICLE_COLORS.truck}      strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Total vehicle count area chart */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-sm">
          <h3 className="text-sm font-bold text-[#16192E] mb-4 flex items-center gap-2">
            <TrendingUp size={15} className="text-[#C85A17]" /> Vehicle Count Over Time
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={countHistory}>
              <defs>
                <linearGradient id="countGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#C85A17" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#C85A17" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="time" tick={{ fontSize: 9, fill: "#64748B" }} interval={4} />
              <YAxis tick={{ fontSize: 10, fill: "#64748B" }} />
              <Tooltip
                contentStyle={{ backgroundColor: "#FFFFFF", borderColor: "#CBD5E1", color: "#16192E", borderRadius: "8px", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)" }}
              />
              <Area type="monotone" dataKey="total" stroke="#C85A17" fill="url(#countGrad)"
                    strokeWidth={2} dot={false} name="Total Vehicles" />
            </AreaChart>
          </ResponsiveContainer>
          {countHistory.length === 0 && (
            <p className="text-center text-[#64748B] text-xs -mt-24">Waiting for live data…</p>
          )}
        </div>
      </div>

      {/* ── Counting Lines summary ────────────────────────────────────────── */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-sm">
        <h3 className="text-sm font-bold text-[#16192E] mb-4 flex items-center gap-2">
          <ArrowRight size={15} className="text-[#C85A17]" /> Counting Line Summary
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {["Line_A", "Line_B"].map(line => {
            const randomCounts = {
              car: Math.round(snap.counts.car * 0.55),
              bus: Math.round(snap.counts.bus * 0.55),
              truck: Math.round(snap.counts.truck * 0.55),
              two_wheeler: Math.round(snap.counts.two_wheeler * 0.55),
              van: Math.round(snap.counts.van * 0.55),
            };
            const total = Object.values(randomCounts).reduce((a, b) => a + b, 0);
            return (
              <div key={line} className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-semibold text-[#16192E]">{line.replace("_", " ")}</span>
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-orange-50 text-[#C85A17] border border-orange-200 font-semibold">
                    Total: {total}
                  </span>
                </div>
                <div className="grid grid-cols-5 gap-2">
                  {Object.entries(randomCounts).map(([cls, cnt]) => (
                    <div key={cls} className="text-center bg-white border border-[#E2E8F0] rounded p-2">
                      <p className="text-[11px] text-[#64748B] font-medium capitalize">{cls.replace("_", " ").slice(0,4)}</p>
                      <p className="text-sm font-bold" style={{ color: VEHICLE_COLORS[cls] ?? "#64748b" }}>{cnt}</p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Track ID info footer ──────────────────────────────────────────── */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 flex flex-wrap gap-6 text-xs text-[#64748B] shadow-sm">
        <div>
          <span className="text-[#16192E] font-semibold">Tracker: </span>ByteTrack (IoU + Hungarian matching)
        </div>
        <div>
          <span className="text-[#16192E] font-semibold">Min hits to confirm: </span>3 frames
        </div>
        <div>
          <span className="text-[#16192E] font-semibold">Max age (lost): </span>30 frames
        </div>
        <div>
          <span className="text-[#16192E] font-semibold">Boundary margin: </span>8 px
        </div>
        <div>
          <span className="text-[#16192E] font-semibold">Speed mode: </span>Pixel-scale (45 px/m)
        </div>
        <div>
          <span className="text-[#16192E] font-semibold">Counting lines: </span>Line_A (60%), Line_B (40%)
        </div>
      </div>

    </div>
  );
};

export default Traffic;
