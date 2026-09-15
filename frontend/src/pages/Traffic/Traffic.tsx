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
  car:         "#6366f1",
  bus:         "#22d3ee",
  truck:       "#f97316",
  two_wheeler: "#a78bfa",
  van:         "#34d399",
};

const DENSITY_COLORS = { low: "#22c55e", medium: "#f59e0b", high: "#ef4444" };

function DensityBar({ score, level }: { score: number; level: string }) {
  const color = DENSITY_COLORS[level as keyof typeof DENSITY_COLORS] ?? "#6b7280";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-400">Density</span>
        <span style={{ color }} className="font-semibold capitalize">{level}</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2">
        <div className="h-2 rounded-full transition-all" style={{ width: `${Math.round(score * 100)}%`, backgroundColor: color }} />
      </div>
      <div className="text-right text-xs text-gray-500">{Math.round(score * 100)}%</div>
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

const StatCard: React.FC<StatCardProps> = ({ title, value, sub, icon: Icon, color = "text-indigo-400", trend }) => (
  <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
    <div className="flex items-center justify-between mb-2">
      <span className="text-xs text-gray-400">{title}</span>
      <Icon size={16} className={color} />
    </div>
    <p className={`text-2xl font-bold ${color}`}>{value}</p>
    {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    {trend !== undefined && (
      <p className={`text-xs mt-1 ${trend >= 0 ? "text-green-400" : "text-red-400"}`}>
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
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6 space-y-6">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Activity size={26} className="text-indigo-400" />
            Vehicle Detection &amp; Tracking
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            ByteTrack multi-object tracking · Counting lines · Speed estimation · Density analysis
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-1 rounded-full border ${liveMode ? "bg-green-500/20 text-green-400 border-green-500/30" : "bg-gray-700 text-gray-400 border-gray-600"}`}>
            {liveMode ? "● LIVE" : "⏸ PAUSED"}
          </span>
          <button
            onClick={() => setLiveMode(l => !l)}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 transition"
          >
            <RefreshCw size={12} /> {liveMode ? "Pause" : "Resume"}
          </button>
        </div>
      </div>

      {/* ── Camera selector ─────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <Camera size={14} className="text-gray-500" />
        <span className="text-xs text-gray-500">Camera:</span>
        {["FRONT", "REAR", "LEFT", "RIGHT"].map(cam => (
          <button
            key={cam}
            onClick={() => setActiveCam(cam)}
            className={`text-xs px-3 py-1 rounded-lg border transition ${
              activeCam === cam
                ? "bg-indigo-600 border-indigo-500 text-white"
                : "bg-gray-800 border-gray-700 text-gray-400 hover:text-white"
            }`}
          >
            {cam}
          </button>
        ))}
        <span className="ml-2 text-xs text-gray-600">
          Active Tracks: <span className="text-indigo-400 font-bold">{snap.active_tracks}</span>
        </span>
      </div>

      {/* ── KPI Row ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <StatCard title="Total Vehicles"  value={snap.counts.total}        icon={TrendingUp} color="text-white"       sub="cumulative" />
        <StatCard title="Cars"            value={snap.counts.car}          icon={Car}        color="text-indigo-400" />
        <StatCard title="Two-Wheelers"    value={snap.counts.two_wheeler}  icon={Bike}       color="text-purple-400" />
        <StatCard title="Buses"           value={snap.counts.bus}          icon={Bus}        color="text-cyan-400"   />
        <StatCard title="Trucks"          value={snap.counts.truck}        icon={Truck}      color="text-orange-400" />
        <StatCard title="Avg Speed"       value={`${snap.avg_speed_kmh.all} km/h`} icon={Gauge} color="text-green-400" sub="all vehicles" />
        <StatCard title="Active Tracks"   value={snap.active_tracks}       icon={CircleDot}  color="text-yellow-400" sub="ByteTrack IDs" />
      </div>

      {/* ── Charts Row 1 ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Vehicle composition pie */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <Layers size={15} className="text-indigo-400" /> Vehicle Composition
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={90}
                   paddingAngle={3} dataKey="value">
                {pieData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
              </Pie>
              <Tooltip formatter={(v: number) => [v.toLocaleString(), ""]} />
              <Legend iconType="circle" iconSize={8}
                formatter={(value) => <span className="text-xs text-gray-400">{value}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Average speed per class bar */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <Gauge size={15} className="text-green-400" /> Avg Speed by Class (km/h)
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={speedBarData} barSize={24}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#9ca3af" }} />
              <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} unit=" km/h" domain={[0, 80]} />
              <Tooltip formatter={(v: number) => [`${v} km/h`, "Speed"]} />
              <Bar dataKey="speed" radius={[4, 4, 0, 0]}>
                {speedBarData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Density panel */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <BarChart3 size={15} className="text-yellow-400" /> Lane Density
          </h3>
          {snap.density.map(region => (
            <div key={region.name} className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-300">{region.name.replace("_", " ")}</span>
                <span className="text-xs text-gray-500">{region.total} vehicles</span>
              </div>
              <DensityBar score={region.density_score} level={region.density_level} />
              <div className="mt-3 grid grid-cols-3 gap-2">
                {Object.entries(region.occupancy).filter(([k]) => k !== "total").map(([cls, cnt]) => (
                  <div key={cls} className="text-center">
                    <p className="text-xs text-gray-500 capitalize">{cls.replace("_", " ")}</p>
                    <p className="text-sm font-bold" style={{ color: VEHICLE_COLORS[cls] ?? "#9ca3af" }}>{cnt}</p>
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
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <Wind size={15} className="text-blue-400" /> Speed History (km/h)
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={speedHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="time" tick={{ fontSize: 9, fill: "#6b7280" }} interval={4} />
              <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} unit=" km/h" domain={[0, 90]} />
              <Tooltip />
              <Legend iconSize={8} formatter={(v) => <span className="text-xs text-gray-400">{v}</span>} />
              <Line type="monotone" dataKey="car"        stroke={VEHICLE_COLORS.car}        strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="two_wheeler" stroke={VEHICLE_COLORS.two_wheeler} strokeWidth={2} dot={false} name="Two-Wheeler" />
              <Line type="monotone" dataKey="bus"        stroke={VEHICLE_COLORS.bus}        strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="truck"      stroke={VEHICLE_COLORS.truck}      strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Total vehicle count area chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <TrendingUp size={15} className="text-indigo-400" /> Vehicle Count Over Time
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={countHistory}>
              <defs>
                <linearGradient id="countGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="time" tick={{ fontSize: 9, fill: "#6b7280" }} interval={4} />
              <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} />
              <Tooltip />
              <Area type="monotone" dataKey="total" stroke="#6366f1" fill="url(#countGrad)"
                    strokeWidth={2} dot={false} name="Total Vehicles" />
            </AreaChart>
          </ResponsiveContainer>
          {countHistory.length === 0 && (
            <p className="text-center text-gray-600 text-xs -mt-24">Waiting for live data…</p>
          )}
        </div>
      </div>

      {/* ── Counting Lines summary ────────────────────────────────────────── */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
          <ArrowRight size={15} className="text-orange-400" /> Counting Line Summary
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
              <div key={line} className="bg-gray-800/60 border border-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-gray-200">{line.replace("_", " ")}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/30">
                    Total: {total}
                  </span>
                </div>
                <div className="grid grid-cols-5 gap-2">
                  {Object.entries(randomCounts).map(([cls, cnt]) => (
                    <div key={cls} className="text-center">
                      <p className="text-xs text-gray-500 capitalize">{cls.replace("_", " ").slice(0,4)}</p>
                      <p className="text-sm font-bold" style={{ color: VEHICLE_COLORS[cls] ?? "#9ca3af" }}>{cnt}</p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Track ID info footer ──────────────────────────────────────────── */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4 flex flex-wrap gap-6 text-xs text-gray-500">
        <div>
          <span className="text-gray-400 font-medium">Tracker: </span>ByteTrack (IoU + Hungarian matching)
        </div>
        <div>
          <span className="text-gray-400 font-medium">Min hits to confirm: </span>3 frames
        </div>
        <div>
          <span className="text-gray-400 font-medium">Max age (lost): </span>30 frames
        </div>
        <div>
          <span className="text-gray-400 font-medium">Boundary margin: </span>8 px
        </div>
        <div>
          <span className="text-gray-400 font-medium">Speed mode: </span>Pixel-scale (45 px/m)
        </div>
        <div>
          <span className="text-gray-400 font-medium">Counting lines: </span>Line_A (60%), Line_B (40%)
        </div>
      </div>

    </div>
  );
};

export default Traffic;
