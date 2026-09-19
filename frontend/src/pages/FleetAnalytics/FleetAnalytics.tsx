// src/pages/FleetAnalytics/FleetAnalytics.tsx
// BEL Smart Automation • NovaFlow — Fleet Analytics & Infrastructure Intelligence

import React, { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  BarChart3, TrendingUp, Bus, Wrench, AlertTriangle, ShieldCheck,
  Clock, Gauge, Download, Filter, RefreshCw, Calendar, MapPin,
  CheckCircle2, ChevronRight, Activity, ArrowUpRight, ArrowDownRight,
  Layers, Droplet, Construction, PieChart as PieIcon
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from "recharts";

// 24-hour fleet bus telemetry data
const DIURNAL_UTILIZATION_DATA = [
  { hour: "00:00", activeBuses: 42, idleBuses: 206, utilization: 16.9 },
  { hour: "02:00", activeBuses: 28, idleBuses: 220, utilization: 11.3 },
  { hour: "04:00", activeBuses: 56, idleBuses: 192, utilization: 22.5 },
  { hour: "06:00", activeBuses: 178, idleBuses: 70, utilization: 71.7 },
  { hour: "08:00", activeBuses: 236, idleBuses: 12, utilization: 95.1 },
  { hour: "10:00", activeBuses: 244, idleBuses: 4, utilization: 98.4 },
  { hour: "12:00", activeBuses: 215, idleBuses: 33, utilization: 86.7 },
  { hour: "14:00", activeBuses: 208, idleBuses: 40, utilization: 83.8 },
  { hour: "16:00", activeBuses: 230, idleBuses: 18, utilization: 92.7 },
  { hour: "18:00", activeBuses: 248, idleBuses: 0, utilization: 100.0 },
  { hour: "20:00", activeBuses: 222, idleBuses: 26, utilization: 89.5 },
  { hour: "22:00", activeBuses: 114, idleBuses: 134, utilization: 45.9 }
];

// Route Delay & Congestion data
const ROUTE_PERFORMANCE_DATA = [
  { route: "Route 335-E (Outer Ring Rd)", avgDelayMin: 14.2, busCount: 38, speedKmH: 24.5, defectsOnRoute: 28 },
  { route: "Route 500-D (AIIMS Ring Rd)", avgDelayMin: 11.8, busCount: 42, speedKmH: 28.2, defectsOnRoute: 22 },
  { route: "Route 201-R (WEH Mumbai)", avgDelayMin: 16.5, busCount: 35, speedKmH: 21.0, defectsOnRoute: 34 },
  { route: "Route 102-A (Connaught Place)", avgDelayMin: 6.4, busCount: 26, speedKmH: 34.0, defectsOnRoute: 8 },
  { route: "Route 412-B (Hosur Highway)", avgDelayMin: 9.1, busCount: 32, speedKmH: 31.4, defectsOnRoute: 15 },
  { route: "Route 180-C (Eastern Freeway)", avgDelayMin: 4.8, busCount: 24, speedKmH: 42.8, defectsOnRoute: 6 }
];

// Hazard distribution
const HAZARD_TYPE_DATA = [
  { name: "Potholes", value: 847, color: "#DC2626" },
  { name: "Waterlogging", value: 164, color: "#2563EB" },
  { name: "Damaged Road", value: 142, color: "#D97706" },
  { name: "Road Debris", value: 78, color: "#7C3AED" },
  { name: "Cracks / Fatigue", value: 38, color: "#0D9488" },
  { name: "Damaged Infra", value: 15, color: "#64748B" }
];

// Weekly PWD turnaround & resolution
const RESOLUTION_VELOCITY_DATA = [
  { day: "Mon", detected: 142, repaired: 128, turnaroundHours: 4.8 },
  { day: "Tue", detected: 165, repaired: 151, turnaroundHours: 4.5 },
  { day: "Wed", detected: 188, repaired: 174, turnaroundHours: 4.2 },
  { day: "Thu", detected: 210, repaired: 196, turnaroundHours: 4.0 },
  { day: "Fri", detected: 224, repaired: 210, turnaroundHours: 3.9 },
  { day: "Sat", detected: 195, repaired: 185, turnaroundHours: 4.1 },
  { day: "Sun", detected: 160, repaired: 155, turnaroundHours: 3.8 }
];

// Corridor Road Quality Index (RQI)
const CORRIDOR_RQI = [
  { corridor: "Outer Ring Road (Marathahalli - Silk Board)", city: "Bengaluru", rqi: 62, status: "Needs Resurfacing", activeDefects: 48, busTripsDaily: 340 },
  { corridor: "Western Express Highway (Andheri - Bandra)", city: "Mumbai", rqi: 68, status: "Moderate Degradation", activeDefects: 36, busTripsDaily: 410 },
  { corridor: "Inner Ring Road (AIIMS - Moolchand)", city: "New Delhi", rqi: 74, status: "Fair Condition", activeDefects: 24, busTripsDaily: 520 },
  { corridor: "Hosur Road Expressway Elevated Sector", city: "Bengaluru", rqi: 82, status: "Good Condition", activeDefects: 12, busTripsDaily: 290 },
  { corridor: "Eastern Freeway (CST - Chembur)", city: "Mumbai", rqi: 88, status: "Optimal Condition", activeDefects: 6, busTripsDaily: 260 },
  { corridor: "Barapullah Elevated Corridor", city: "New Delhi", rqi: 91, status: "Optimal Condition", activeDefects: 4, busTripsDaily: 310 }
];

export const FleetAnalytics: React.FC = () => {
  const [cityFilter, setCityFilter] = useState("ALL");
  const [timeRange, setTimeRange] = useState("7D");

  const filteredCorridors = useMemo(() => {
    if (cityFilter === "ALL") return CORRIDOR_RQI;
    return CORRIDOR_RQI.filter(c => c.city.toLowerCase().includes(cityFilter.toLowerCase()));
  }, [cityFilter]);

  const handleExportCsv = () => {
    const headers = "Corridor,City,RQI,Status,Active Defects,Daily Bus Trips\n";
    const rows = filteredCorridors.map(c =>
      `"${c.corridor}","${c.city}",${c.rqi},"${c.status}",${c.activeDefects},${c.busTripsDaily}`
    ).join("\n");

    const blob = new Blob([headers + rows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `Fleet_Analytics_RQI_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-full pb-16 bg-[#F8FAFC]">
      {/* Top Banner */}
      <div className="bg-[#1B254B] border-b border-[#2D3A6E] text-white px-4 sm:px-6 lg:px-8 py-5">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#93C5FD] mb-1.5">
              <Activity className="w-3.5 h-3.5 text-[#60A5FA]" />
              <span>Bharat Electronics Limited (BEL) • Transit Intelligence</span>
            </div>
            <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <BarChart3 className="w-7 h-7 text-[#60A5FA]" />
              Fleet Analytics & Infrastructure Intelligence
            </h1>
            <p className="text-sm text-[#94A3B8] mt-1">
              Cross-city transit performance, road degradation telemetry, route delay patterns, and PWD repair turnaround metrics.
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Time Filter */}
            <div className="inline-flex rounded-md shadow-sm border border-[#475569] bg-[#2D3A6E] p-0.5 text-xs font-medium text-white">
              {(["24H", "7D", "30D"] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTimeRange(t)}
                  className={`px-3 py-1.5 rounded transition ${timeRange === t ? "bg-[#2563EB] text-white font-bold" : "hover:text-[#93C5FD]"}`}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* City Filter */}
            <select
              value={cityFilter}
              onChange={(e) => setCityFilter(e.target.value)}
              className="px-3 py-1.5 text-xs sm:text-sm font-semibold rounded-md bg-[#2D3A6E] border border-[#475569] text-white focus:outline-none"
            >
              <option value="ALL">All Cities (Delhi, BLR, Mumbai)</option>
              <option value="Delhi">New Delhi</option>
              <option value="Bengaluru">Bengaluru</option>
              <option value="Mumbai">Mumbai</option>
            </select>

            <button
              onClick={handleExportCsv}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs sm:text-sm font-semibold transition shadow-sm"
            >
              <Download className="w-4 h-4" />
              <span>Export CSV</span>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        {/* KPI Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5 mb-6">
          <div className="bg-white border border-[#CBD5E1] rounded-lg p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#64748B]">Fleet Utilization</span>
              <Gauge className="w-4 h-4 text-[#2563EB]" />
            </div>
            <div className="mt-2 text-2xl font-black text-[#1E293B]">92.8%</div>
            <p className="text-[11px] text-[#059669] font-medium mt-0.5">248 of 267 buses active</p>
          </div>

          <div className="bg-white border border-[#CBD5E1] rounded-lg p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#64748B]">Distance Covered</span>
              <Bus className="w-4 h-4 text-[#7C3AED]" />
            </div>
            <div className="mt-2 text-2xl font-black text-[#1E293B]">34,820 <span className="text-xs font-normal">km</span></div>
            <p className="text-[11px] text-[#059669] font-medium mt-0.5">↑ 4.2% vs yesterday</p>
          </div>

          <div className="bg-white border border-[#CBD5E1] rounded-lg p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#DC2626]">Potholes Logged</span>
              <AlertTriangle className="w-4 h-4 text-[#DC2626]" />
            </div>
            <div className="mt-2 text-2xl font-black text-[#DC2626]">847</div>
            <p className="text-[11px] text-[#64748B] font-medium mt-0.5">721 repaired (85.1%)</p>
          </div>

          <div className="bg-white border border-[#CBD5E1] rounded-lg p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#059669]">Avg PWD Turnaround</span>
              <Clock className="w-4 h-4 text-[#059669]" />
            </div>
            <div className="mt-2 text-2xl font-black text-[#059669]">4.2 <span className="text-xs font-normal">hrs</span></div>
            <p className="text-[11px] text-[#059669] font-medium mt-0.5">↓ 1.4h SLA improvement</p>
          </div>

          <div className="bg-white border border-[#CBD5E1] rounded-lg p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#D97706]">Delay Reduction</span>
              <TrendingUp className="w-4 h-4 text-[#D97706]" />
            </div>
            <div className="mt-2 text-2xl font-black text-[#D97706]">18.4%</div>
            <p className="text-[11px] text-[#059669] font-medium mt-0.5">via dynamic detour alerts</p>
          </div>

          <div className="bg-white border border-[#CBD5E1] rounded-lg p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#2563EB]">Edge Inference</span>
              <Activity className="w-4 h-4 text-[#2563EB]" />
            </div>
            <div className="mt-2 text-2xl font-black text-[#1E293B]">24 <span className="text-xs font-normal">ms</span></div>
            <p className="text-[11px] text-[#64748B] font-medium mt-0.5">YOLOv8s + TensorRT</p>
          </div>
        </div>

        {/* Charts Grid 1: Fleet 24h Diurnal Curve & Route Performance */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Chart 1: Diurnal Fleet Utilization */}
          <div className="bg-white border border-[#CBD5E1] rounded-lg p-4 sm:p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm sm:text-base font-bold text-[#1E293B]">
                  Fleet Deployment & Utilization Profile (24h)
                </h3>
                <p className="text-xs text-[#64748B]">Active transit buses scanning road infrastructure hourly</p>
              </div>
              <span className="px-2 py-0.5 text-xs font-semibold rounded bg-[#EFF6FF] text-[#2563EB]">
                Peak: 248 Buses
              </span>
            </div>
            <div className="h-64 sm:h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={DIURNAL_UTILIZATION_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorBuses" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0.05}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="hour" stroke="#64748B" fontSize={11} />
                  <YAxis stroke="#64748B" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#1E293B", border: "none", borderRadius: "8px", color: "#FFF", fontSize: "12px" }}
                  />
                  <Area type="monotone" dataKey="activeBuses" stroke="#2563EB" strokeWidth={2.5} fillOpacity={1} fill="url(#colorBuses)" name="Active Buses" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Route Delay Analysis */}
          <div className="bg-white border border-[#CBD5E1] rounded-lg p-4 sm:p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm sm:text-base font-bold text-[#1E293B]">
                  Corridor Delays & Active Road Hazards
                </h3>
                <p className="text-xs text-[#64748B]">Average schedule deviation (minutes) per key arterial route</p>
              </div>
              <span className="px-2 py-0.5 text-xs font-semibold rounded bg-[#FEF2F2] text-[#DC2626]">
                Worst: WEH Mumbai (16.5m)
              </span>
            </div>
            <div className="h-64 sm:h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={ROUTE_PERFORMANCE_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="route" stroke="#64748B" fontSize={10} tickFormatter={(val) => val.split(" ")[1]} />
                  <YAxis stroke="#64748B" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#1E293B", border: "none", borderRadius: "8px", color: "#FFF", fontSize: "12px" }}
                  />
                  <Bar dataKey="avgDelayMin" fill="#F59E0B" radius={[4, 4, 0, 0]} name="Delay (min)" />
                  <Bar dataKey="defectsOnRoute" fill="#DC2626" radius={[4, 4, 0, 0]} name="Hazards on Route" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Charts Grid 2: Hazard Type Breakdown & PWD Resolution Velocity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Chart 3: Defect Distribution */}
          <div className="bg-white border border-[#CBD5E1] rounded-lg p-4 sm:p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm sm:text-base font-bold text-[#1E293B]">
                  AI Hazard Classification Breakdown
                </h3>
                <p className="text-xs text-[#64748B]">Distribution of 1,284 verified defects across road networks</p>
              </div>
              <span className="px-2 py-0.5 text-xs font-semibold rounded bg-[#F1F5F9] text-[#475569]">
                1,284 Total
              </span>
            </div>
            <div className="h-64 sm:h-72 w-full flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={HAZARD_TYPE_DATA}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={95}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {HAZARD_TYPE_DATA.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: "#1E293B", border: "none", borderRadius: "8px", color: "#FFF", fontSize: "12px" }}
                  />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: "11px" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 4: Daily Resolution Velocity */}
          <div className="bg-white border border-[#CBD5E1] rounded-lg p-4 sm:p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm sm:text-base font-bold text-[#1E293B]">
                  PWD Repair Resolution Velocity (Weekly)
                </h3>
                <p className="text-xs text-[#64748B]">Daily potholes detected vs verified repairs completed</p>
              </div>
              <span className="px-2 py-0.5 text-xs font-semibold rounded bg-[#DCFCE7] text-[#15803D]">
                85.1% Completion Rate
              </span>
            </div>
            <div className="h-64 sm:h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={RESOLUTION_VELOCITY_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="day" stroke="#64748B" fontSize={11} />
                  <YAxis stroke="#64748B" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#1E293B", border: "none", borderRadius: "8px", color: "#FFF", fontSize: "12px" }}
                  />
                  <Line type="monotone" dataKey="detected" stroke="#DC2626" strokeWidth={2.5} dot={{ r: 4 }} name="Detected Potholes" />
                  <Line type="monotone" dataKey="repaired" stroke="#10B981" strokeWidth={2.5} dot={{ r: 4 }} name="Repairs Completed" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Section 3: Road Quality Index (RQI) by Corridor */}
        <div className="bg-white border border-[#CBD5E1] rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3.5 border-b border-[#E2E8F0] flex items-center justify-between bg-[#F8FAFC]">
            <div>
              <h3 className="text-sm font-bold text-[#1E293B]">Corridor Road Quality Index (RQI) Monitoring</h3>
              <p className="text-xs text-[#64748B]">Continuous surface condition telemetry aggregated from bus fleet multi-pass scans</p>
            </div>
            <Link
              to="/gis"
              className="inline-flex items-center gap-1 text-xs font-semibold text-[#2563EB] hover:underline"
            >
              <span>View Heatmap on GIS</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-[#1E293B]">
              <thead className="text-[11px] font-bold uppercase tracking-wider bg-[#F1F5F9] text-[#475569] border-b border-[#CBD5E1]">
                <tr>
                  <th className="py-3 px-4">Corridor & Highway</th>
                  <th className="py-3 px-4">City</th>
                  <th className="py-3 px-4">RQI Score (0-100)</th>
                  <th className="py-3 px-4">Condition Status</th>
                  <th className="py-3 px-4">Active Hazards</th>
                  <th className="py-3 px-4">Daily Bus Passes</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E2E8F0] text-xs sm:text-sm">
                {filteredCorridors.map((c, i) => {
                  const rqiColor =
                    c.rqi >= 85 ? "text-[#15803D]" :
                    c.rqi >= 70 ? "text-[#2563EB]" :
                    c.rqi >= 60 ? "text-[#D97706]" : "text-[#DC2626]";
                  const barColor =
                    c.rqi >= 85 ? "bg-[#10B981]" :
                    c.rqi >= 70 ? "bg-[#2563EB]" :
                    c.rqi >= 60 ? "bg-[#F59E0B]" : "bg-[#DC2626]";

                  return (
                    <tr key={i} className="hover:bg-[#F8FAFC] transition">
                      <td className="py-3.5 px-4 font-semibold text-[#1E293B]">
                        <div className="flex items-center gap-1.5">
                          <MapPin className="w-3.5 h-3.5 text-[#DC2626]" />
                          <span>{c.corridor}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-[#64748B] font-medium">{c.city}</td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <span className={`font-black text-sm ${rqiColor}`}>{c.rqi}</span>
                          <div className="w-20 bg-[#E2E8F0] rounded-full h-2 overflow-hidden">
                            <div className={`h-full rounded-full ${barColor}`} style={{ width: `${c.rqi}%` }} />
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="font-medium text-[#1E293B]">{c.status}</span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="font-bold text-[#DC2626]">{c.activeDefects} defects</span>
                      </td>
                      <td className="py-3.5 px-4 text-[#475569]">{c.busTripsDaily} scans/day</td>
                      <td className="py-3.5 px-4 text-right">
                        <Link
                          to="/hazards"
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border border-[#CBD5E1] bg-white hover:bg-[#F1F5F9] text-[#1E293B] transition"
                        >
                          <span>View Defects</span>
                          <ChevronRight className="w-3 h-3 text-[#64748B]" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FleetAnalytics;
