// src/pages/Home/Home.tsx
// Bharat Electronics Limited (BEL) • Smart Automation
// NovaFlow — Urban Fleet Intelligence Dashboard (Central Navigation & Intelligence Hub)

import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Map, AlertTriangle, Wrench, BarChart3, Bus, ShieldCheck,
  Activity, ArrowRight, ArrowUpRight, CheckCircle2, Clock,
  FileText, Download, Layers, ShieldAlert, Cpu, Radio,
  Droplet, Eye, Users, ChevronRight, X
} from "lucide-react";

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportDownloaded, setReportDownloaded] = useState(false);
  const [reportAgency, setReportAgency] = useState("ALL");
  const [reportRange, setReportRange] = useState("Last 7 Days");

  const handleDownloadCsv = () => {
    const csvContent =
      "Report Type,Date,Issuing Agency,Active Fleet,Hazards Detected,Potholes Logged,PWD Work Orders,Avg Turnaround\n" +
      `"PWD Municipal Compliance Summary","${new Date().toISOString().slice(0, 10)}","BEL Smart Automation Command Center",248,1284,847,126,"4.2 hours"\n`;

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `BEL_NovaFlow_Executive_Summary_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setReportDownloaded(true);
  };

  return (
    <div className="min-h-full pb-16 bg-[#F8FAFC]">
      {/* 1. HERO SECTION */}
      <section className="bg-gradient-to-b from-[#111C44] via-[#1B254B] to-[#1E293B] text-white border-b border-[#2D3A6E] px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        <div className="max-w-7xl mx-auto">
          {/* Government Badging & Status */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#2563EB]/20 border border-[#3B82F6]/30 text-xs font-semibold text-[#93C5FD]">
              <span className="w-2 h-2 rounded-full bg-[#22C55E] animate-pulse" />
              <span>Bharat Electronics Limited (BEL) • Smart Automation Division</span>
            </div>

            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#0F172A]/80 border border-[#334155] text-xs font-mono text-[#E2E8F0]">
              <span className="text-[#22C55E] font-bold">● SYSTEM OPERATIONAL</span>
              <span className="text-[#64748B]">|</span>
              <span>248 BUSES CONNECTED</span>
            </div>
          </div>

          {/* Main Title & Subtitle */}
          <div className="max-w-3xl">
            <h1 className="text-2xl sm:text-4xl lg:text-5xl font-black tracking-tight text-white leading-tight">
              Urban Fleet Intelligence Dashboard
            </h1>
            <p className="mt-3 text-sm sm:text-base lg:text-lg text-[#CBD5E1] leading-relaxed">
              Real-time road hazard detection, edge AI fleet intelligence, and municipal work-order automation powered by city transit networks.
            </p>
          </div>

          {/* Primary Quick Action CTAs */}
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={() => navigate("/gis")}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-bold transition shadow-lg shadow-blue-900/30"
            >
              <Map className="w-4 h-4" />
              <span>Launch Live GIS Map</span>
              <ArrowRight className="w-4 h-4 ml-0.5" />
            </button>

            <button
              onClick={() => setShowReportModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#2D3A6E] hover:bg-[#3B4C8C] text-white text-sm font-semibold transition border border-[#475569] shadow-sm"
            >
              <FileText className="w-4 h-4 text-[#93C5FD]" />
              <span>Generate PWD Report</span>
            </button>

            <button
              onClick={() => navigate("/fleet")}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#0F172A]/60 hover:bg-[#0F172A] text-[#CBD5E1] hover:text-white text-sm font-medium transition border border-[#334155]"
            >
              <Bus className="w-4 h-4 text-[#60A5FA]" />
              <span>Track Fleet Status</span>
            </button>
          </div>
        </div>
      </section>

      {/* 2. INFRASTRUCTURE & FLEET KPI STRIP */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-4">
          {/* KPI 1 */}
          <div className="bg-white border border-[#CBD5E1] rounded-xl p-4 sm:p-5 shadow-md flex items-center justify-between">
            <div>
              <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-[#64748B]">
                Active Transit Buses
              </span>
              <div className="text-2xl sm:text-3xl font-black text-[#0F172A] mt-1">248</div>
              <span className="text-[11px] text-[#059669] font-semibold flex items-center gap-1 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#059669]" />
                92.8% Fleet Utilization
              </span>
            </div>
            <div className="w-11 h-11 rounded-xl bg-[#EFF6FF] flex items-center justify-center text-[#2563EB] flex-shrink-0">
              <Bus className="w-6 h-6" />
            </div>
          </div>

          {/* KPI 2 */}
          <div className="bg-white border border-[#CBD5E1] rounded-xl p-4 sm:p-5 shadow-md flex items-center justify-between">
            <div>
              <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-[#64748B]">
                Road Hazards Detected (24h)
              </span>
              <div className="text-2xl sm:text-3xl font-black text-[#DC2626] mt-1">1,284</div>
              <span className="text-[11px] text-[#64748B] font-medium mt-0.5 block">
                Multi-pass validated
              </span>
            </div>
            <div className="w-11 h-11 rounded-xl bg-[#FEF2F2] flex items-center justify-center text-[#DC2626] flex-shrink-0">
              <AlertTriangle className="w-6 h-6" />
            </div>
          </div>

          {/* KPI 3 */}
          <div className="bg-white border border-[#CBD5E1] rounded-xl p-4 sm:p-5 shadow-md flex items-center justify-between">
            <div>
              <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-[#64748B]">
                Potholes Logged
              </span>
              <div className="text-2xl sm:text-3xl font-black text-[#D97706] mt-1">847</div>
              <span className="text-[11px] text-[#059669] font-semibold mt-0.5 block">
                721 Repaired (85.1%)
              </span>
            </div>
            <div className="w-11 h-11 rounded-xl bg-[#FFFBEB] flex items-center justify-center text-[#D97706] flex-shrink-0">
              <Droplet className="w-6 h-6" />
            </div>
          </div>

          {/* KPI 4 */}
          <div className="bg-white border border-[#CBD5E1] rounded-xl p-4 sm:p-5 shadow-md flex items-center justify-between">
            <div>
              <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-[#64748B]">
                Pending PWD Work Orders
              </span>
              <div className="text-2xl sm:text-3xl font-black text-[#2563EB] mt-1">126</div>
              <span className="text-[11px] text-[#64748B] font-medium mt-0.5 block">
                34 Dispatched Today
              </span>
            </div>
            <div className="w-11 h-11 rounded-xl bg-[#EEF2FF] flex items-center justify-center text-[#4F46E5] flex-shrink-0">
              <Wrench className="w-6 h-6" />
            </div>
          </div>
        </div>
      </section>

      {/* 3. FOUR LARGE PRIMARY ACTION / NAVIGATION CARDS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8">
        <div className="mb-4">
          <h2 className="text-lg sm:text-xl font-black text-[#0F172A] tracking-tight">
            Core Intelligence Modules
          </h2>
          <p className="text-xs sm:text-sm text-[#64748B]">
            Direct access to GIS command operations, AI hazard streams, municipal work order pipelines, and fleet analytics.
          </p>
        </div>

        {/* 2x2 Grid on desktop, 1 col on mobile */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 sm:gap-6">
          {/* CARD 1: LIVE GIS DASHBOARD */}
          <div
            onClick={() => navigate("/gis")}
            className="group bg-white border border-[#CBD5E1] hover:border-[#2563EB] rounded-xl p-6 shadow-sm hover:shadow-xl transition-all duration-200 cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="w-12 h-12 rounded-xl bg-[#EFF6FF] border border-[#BFDBFE] flex items-center justify-center text-[#2563EB] group-hover:bg-[#2563EB] group-hover:text-white transition-colors duration-200">
                  <Map className="w-6 h-6" />
                </div>
                <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-[#F1F5F9] text-[#2563EB] group-hover:bg-[#DBEAFE]">
                  /gis
                </span>
              </div>

              <h3 className="text-xl font-black text-[#0F172A] group-hover:text-[#2563EB] transition-colors">
                Live GIS Dashboard
              </h3>
              <p className="text-xs font-semibold uppercase tracking-wider text-[#2563EB] mt-0.5">
                Real-time City Transit & Hazard Map
              </p>
              <p className="text-xs sm:text-sm text-[#475569] mt-2.5 leading-relaxed">
                Track active buses in real-time across Delhi, Bengaluru, and Mumbai. View live GPS telemetry, edge AI detection pings, speed, heading, and localized road hazard clusters on an interactive GIS map.
              </p>

              {/* Key stats / metrics preview */}
              <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-[#E2E8F0] text-center">
                <div className="bg-[#F8FAFC] p-2 rounded-lg">
                  <span className="text-xs text-[#64748B] block">Connected</span>
                  <span className="text-sm font-bold text-[#0F172A]">248 Buses</span>
                </div>
                <div className="bg-[#F8FAFC] p-2 rounded-lg">
                  <span className="text-xs text-[#64748B] block">Active Routes</span>
                  <span className="text-sm font-bold text-[#0F172A]">14 Corridors</span>
                </div>
                <div className="bg-[#F8FAFC] p-2 rounded-lg">
                  <span className="text-xs text-[#64748B] block">Edge Uptime</span>
                  <span className="text-sm font-bold text-[#059669]">99.4%</span>
                </div>
              </div>
            </div>

            <div className="mt-5 pt-3 flex items-center justify-between text-[#2563EB] font-bold text-sm">
              <span className="group-hover:translate-x-1 transition-transform inline-flex items-center gap-1.5">
                Open GIS Command Center <ArrowRight className="w-4 h-4" />
              </span>
              <span className="text-xs font-normal text-[#64748B]">Leaflet / Satellite</span>
            </div>
          </div>

          {/* CARD 2: AI HAZARD DETECTIONS */}
          <div
            onClick={() => navigate("/hazards")}
            className="group bg-white border border-[#CBD5E1] hover:border-[#DC2626] rounded-xl p-6 shadow-sm hover:shadow-xl transition-all duration-200 cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="w-12 h-12 rounded-xl bg-[#FEF2F2] border border-[#FECACA] flex items-center justify-center text-[#DC2626] group-hover:bg-[#DC2626] group-hover:text-white transition-colors duration-200">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-[#F1F5F9] text-[#DC2626] group-hover:bg-[#FEE2E2]">
                  /hazards
                </span>
              </div>

              <h3 className="text-xl font-black text-[#0F172A] group-hover:text-[#DC2626] transition-colors">
                AI Hazard Detections
              </h3>
              <p className="text-xs font-semibold uppercase tracking-wider text-[#DC2626] mt-0.5">
                Edge-Identified Road Infrastructure Defects
              </p>
              <p className="text-xs sm:text-sm text-[#475569] mt-2.5 leading-relaxed">
                Review real-time detections streamed from onboard edge cameras. Automatically classifies potholes, waterlogging, damaged asphalt, missing manhole covers, and road debris with multi-pass consensus validation.
              </p>

              {/* Key stats / metrics preview */}
              <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-[#E2E8F0] text-center">
                <div className="bg-[#F8FAFC] p-2 rounded-lg">
                  <span className="text-xs text-[#64748B] block">Potholes</span>
                  <span className="text-sm font-bold text-[#DC2626]">847 Verified</span>
                </div>
                <div className="bg-[#F8FAFC] p-2 rounded-lg">
                  <span className="text-xs text-[#64748B] block">AI Confidence</span>
                  <span className="text-sm font-bold text-[#0F172A]">94.2% Avg</span>
                </div>
                <div className="bg-[#F8FAFC] p-2 rounded-lg">
                  <span className="text-xs text-[#64748B] block">Consensus</span>
                  <span className="text-sm font-bold text-[#2563EB]">3-Pass Model</span>
                </div>
              </div>
            </div>

            <div className="mt-5 pt-3 flex items-center justify-between text-[#DC2626] font-bold text-sm">
              <span className="group-hover:translate-x-1 transition-transform inline-flex items-center gap-1.5">
                Review Road Hazards <ArrowRight className="w-4 h-4" />
              </span>
              <span className="text-xs font-normal text-[#64748B]">YOLOv8s Vision</span>
            </div>
          </div>

          {/* CARD 3: PWD WORK ORDERS */}
          <div
            onClick={() => navigate("/work-orders")}
            className="group bg-white border border-[#CBD5E1] hover:border-[#D97706] rounded-xl p-6 shadow-sm hover:shadow-xl transition-all duration-200 cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="w-12 h-12 rounded-xl bg-[#FFFBEB] border border-[#FDE68A] flex items-center justify-center text-[#D97706] group-hover:bg-[#D97706] group-hover:text-white transition-colors duration-200">
                  <Wrench className="w-6 h-6" />
                </div>
                <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-[#F1F5F9] text-[#D97706] group-hover:bg-[#FEF3C7]">
                  /work-orders
                </span>
              </div>

              <h3 className="text-xl font-black text-[#0F172A] group-hover:text-[#D97706] transition-colors">
                PWD Work Orders
              </h3>
              <p className="text-xs font-semibold uppercase tracking-wider text-[#D97706] mt-0.5">
                Automated Municipal Repair Pipeline
              </p>
              <p className="text-xs sm:text-sm text-[#475569] mt-2.5 leading-relaxed">
                Streamlines handoff between transit-detected road defects and municipal repair agencies (PWD, NHAI, BBMP). Track work orders from detection to dispatch, contractor assignment, and repair completion.
              </p>

              {/* Key stats / metrics preview */}
              <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-[#E2E8F0] text-center">
                <div className="bg-[#F8FAFC] p-2 rounded-lg">
                  <span className="text-xs text-[#64748B] block">Pending Orders</span>
                  <span className="text-sm font-bold text-[#D97706]">126 Total</span>
                </div>
                <div className="bg-[#F8FAFC] p-2 rounded-lg">
                  <span className="text-xs text-[#64748B] block">Dispatched Today</span>
                  <span className="text-sm font-bold text-[#2563EB]">34 Crews</span>
                </div>
                <div className="bg-[#F8FAFC] p-2 rounded-lg">
                  <span className="text-xs text-[#64748B] block">Turnaround SLA</span>
                  <span className="text-sm font-bold text-[#059669]">4.2h Avg</span>
                </div>
              </div>
            </div>

            <div className="mt-5 pt-3 flex items-center justify-between text-[#D97706] font-bold text-sm">
              <span className="group-hover:translate-x-1 transition-transform inline-flex items-center gap-1.5">
                Manage Work Orders <ArrowRight className="w-4 h-4" />
              </span>
              <span className="text-xs font-normal text-[#64748B]">MoHUA Compliant</span>
            </div>
          </div>

          {/* CARD 4: FLEET ANALYTICS */}
          <div
            onClick={() => navigate("/analytics")}
            className="group bg-white border border-[#CBD5E1] hover:border-[#7C3AED] rounded-xl p-6 shadow-sm hover:shadow-xl transition-all duration-200 cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="w-12 h-12 rounded-xl bg-[#F5F3FF] border border-[#DDD6FE] flex items-center justify-center text-[#7C3AED] group-hover:bg-[#7C3AED] group-hover:text-white transition-colors duration-200">
                  <BarChart3 className="w-6 h-6" />
                </div>
                <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-[#F1F5F9] text-[#7C3AED] group-hover:bg-[#EDE9FE]">
                  /analytics
                </span>
              </div>

              <h3 className="text-xl font-black text-[#0F172A] group-hover:text-[#7C3AED] transition-colors">
                Fleet Analytics
              </h3>
              <p className="text-xs font-semibold uppercase tracking-wider text-[#7C3AED] mt-0.5">
                Transit Operations & Infrastructure Intelligence
              </p>
              <p className="text-xs sm:text-sm text-[#475569] mt-2.5 leading-relaxed">
                Comprehensive performance analytics across the transit network. Monitor fleet utilization, route delay patterns, road quality indices, detection density heatmaps, and municipal repair turnaround times.
              </p>

              {/* Key stats / metrics preview */}
              <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-[#E2E8F0] text-center">
                <div className="bg-[#F8FAFC] p-2 rounded-lg">
                  <span className="text-xs text-[#64748B] block">Utilization</span>
                  <span className="text-sm font-bold text-[#7C3AED]">92.8%</span>
                </div>
                <div className="bg-[#F8FAFC] p-2 rounded-lg">
                  <span className="text-xs text-[#64748B] block">Avg Speed</span>
                  <span className="text-sm font-bold text-[#0F172A]">42.1 km/h</span>
                </div>
                <div className="bg-[#F8FAFC] p-2 rounded-lg">
                  <span className="text-xs text-[#64748B] block">Delay Reduction</span>
                  <span className="text-sm font-bold text-[#059669]">18.4%</span>
                </div>
              </div>
            </div>

            <div className="mt-5 pt-3 flex items-center justify-between text-[#7C3AED] font-bold text-sm">
              <span className="group-hover:translate-x-1 transition-transform inline-flex items-center gap-1.5">
                View Fleet Analytics <ArrowRight className="w-4 h-4" />
              </span>
              <span className="text-xs font-normal text-[#64748B]">Multi-Corridor</span>
            </div>
          </div>
        </div>
      </section>

      {/* 4. RECENT ACTIVITY & SYSTEM STATUS FEED (COMPACT) */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-10">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Recent Verified Detections Feed */}
          <div className="lg:col-span-2 bg-white border border-[#CBD5E1] rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0] mb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-[#2563EB]" />
                <h3 className="text-sm font-bold text-[#0F172A]">
                  Recent Multi-Pass Verified Detections
                </h3>
              </div>
              <Link to="/hazards" className="text-xs font-semibold text-[#2563EB] hover:underline flex items-center gap-1">
                View all hazards <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="space-y-2.5">
              {[
                {
                  id: "HAZ-2026-081",
                  title: "Severe Asphalt Pothole (Depth 8.5cm)",
                  loc: "Outer Ring Road km 14.2, Near Marathahalli Flyover (BLR)",
                  bus: "Bus #04 (KA-01-F-4821)",
                  time: "12m ago",
                  conf: "96%",
                  sev: "CRITICAL"
                },
                {
                  id: "HAZ-2026-082",
                  title: "Monsoon Waterlogging Hotspot (Depth 14cm)",
                  loc: "Ring Road near AIIMS Flyover Underpass Lane 2 (DEL)",
                  bus: "Bus #01 (DL-1PB-7744)",
                  time: "24m ago",
                  conf: "92%",
                  sev: "HIGH"
                },
                {
                  id: "HAZ-2026-083",
                  title: "Structural Concrete Spalling & Exposed Rebar",
                  loc: "Western Express Highway, Andheri Ramp 3 (MUM)",
                  bus: "Bus #07 (MH-02-CL-3310)",
                  time: "38m ago",
                  conf: "91%",
                  sev: "HIGH"
                }
              ].map((h) => (
                <div key={h.id} className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg flex items-center justify-between gap-3 text-xs">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-[#0F172A]">{h.id}</span>
                      <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                        h.sev === "CRITICAL" ? "bg-[#FEE2E2] text-[#B91C1C]" : "bg-[#FFEDD5] text-[#C2410C]"
                      }`}>
                        {h.sev}
                      </span>
                      <span className="text-[#64748B]">{h.time}</span>
                    </div>
                    <p className="font-semibold text-[#1E293B] mt-0.5 truncate">{h.title}</p>
                    <p className="text-[#64748B] text-[11px] truncate">{h.loc}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <span className="text-xs font-bold text-[#059669] block">{h.conf} Conf</span>
                    <span className="text-[10px] text-[#64748B] block">{h.bus}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Edge System Telemetry & Citizen Portal Quick Link */}
          <div className="bg-white border border-[#CBD5E1] rounded-xl p-5 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0] mb-3">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-[#7C3AED]" />
                  <h3 className="text-sm font-bold text-[#0F172A]">
                    BEL Edge Hardware Telemetry
                  </h3>
                </div>
                <span className="w-2 h-2 rounded-full bg-[#22C55E]" />
              </div>

              <div className="space-y-3 text-xs">
                <div className="flex justify-between py-1 border-b border-[#F1F5F9]">
                  <span className="text-[#64748B]">Edge Computing Units</span>
                  <span className="font-bold text-[#1E293B]">248 Active Onboard</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#F1F5F9]">
                  <span className="text-[#64748B]">YOLOv8 Inference Latency</span>
                  <span className="font-bold text-[#059669]">24 ms / frame</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#F1F5F9]">
                  <span className="text-[#64748B]">Consensus Spatial Filter</span>
                  <span className="font-bold text-[#1E293B]">10m Cluster Radius</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#F1F5F9]">
                  <span className="text-[#64748B]">Data Transmission</span>
                  <span className="font-bold text-[#2563EB]">MQTT over TLS 1.3</span>
                </div>
              </div>
            </div>

            {/* Citizen Transparency Box */}
            <div className="mt-5 pt-4 border-t border-[#E2E8F0] bg-[#F1F5F9] -mx-5 -mb-5 p-4 rounded-b-xl">
              <span className="text-xs font-bold text-[#0F172A] block">
                Public Citizen Transparency Portal
              </span>
              <p className="text-[11px] text-[#64748B] mt-0.5">
                Redacted public view for citizens and transit commuters.
              </p>
              <Link
                to="/public"
                className="mt-2.5 inline-flex items-center gap-1 text-xs font-bold text-[#2563EB] hover:underline"
              >
                Access Public Road Portal <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* 5. FOOTER */}
      <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-12 pt-6 border-t border-[#CBD5E1] text-xs text-[#64748B] flex flex-col md:flex-row items-center justify-between gap-3">
        <div>
          <span className="font-bold text-[#1E293B]">Bharat Electronics Limited (BEL) • Smart Automation Division</span>
          <span className="mx-2">|</span>
          <span>Developed for Ministry of Housing and Urban Affairs (MoHUA) & Municipal Corporations</span>
        </div>
        <div className="flex items-center gap-3 text-[11px]">
          <span className="flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-[#059669]" />
            Level-3 Encrypted
          </span>
          <span>•</span>
          <span>On-Premise Edge Processing</span>
          <span>•</span>
          <span>STQC Certified</span>
        </div>
      </footer>

      {/* MODAL: Generate PWD Report */}
      {showReportModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full border border-[#CBD5E1]">
            <div className="px-6 py-4 bg-[#1B254B] text-white flex items-center justify-between rounded-t-xl">
              <div className="flex items-center gap-2.5">
                <FileText className="w-5 h-5 text-[#93C5FD]" />
                <div>
                  <h3 className="text-base font-bold">Generate PWD Compliance Report</h3>
                  <p className="text-xs text-[#93C5FD]">Ministry of Housing & Urban Affairs (MoHUA) Format</p>
                </div>
              </div>
              <button
                onClick={() => { setShowReportModal(false); setReportDownloaded(false); }}
                className="text-[#94A3B8] hover:text-white p-1 rounded transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs sm:text-sm">
              <div>
                <label className="block text-xs font-semibold text-[#475569] mb-1">
                  Target Municipal Agency / Department
                </label>
                <select
                  value={reportAgency}
                  onChange={(e) => setReportAgency(e.target.value)}
                  className="w-full px-3 py-2 border border-[#CBD5E1] rounded-md text-xs sm:text-sm text-[#1E293B] focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                >
                  <option value="ALL">All Municipal Divisions (Consolidated)</option>
                  <option value="Delhi PWD">Delhi PWD (Public Works Dept)</option>
                  <option value="BBMP">BBMP Road Infrastructure (Bengaluru)</option>
                  <option value="NHAI">NHAI Corridor Maintenance</option>
                  <option value="MCGM">MCGM Disaster & Road Dept (Mumbai)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#475569] mb-1">
                  Reporting Window
                </label>
                <select
                  value={reportRange}
                  onChange={(e) => setReportRange(e.target.value)}
                  className="w-full px-3 py-2 border border-[#CBD5E1] rounded-md text-xs sm:text-sm text-[#1E293B] focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                >
                  <option value="Last 24 Hours">Today (Last 24 Hours)</option>
                  <option value="Last 7 Days">Last 7 Days</option>
                  <option value="Last 30 Days">Last 30 Days</option>
                  <option value="Quarter Q3 2026">Quarter Q3 2026</option>
                </select>
              </div>

              <div className="bg-[#F8FAFC] border border-[#E2E8F0] p-3 rounded-lg text-xs text-[#475569] space-y-1">
                <div className="flex justify-between">
                  <span>Scope:</span>
                  <span className="font-bold text-[#1E293B]">248 Buses • 1,284 Defects • 126 Work Orders</span>
                </div>
                <div className="flex justify-between">
                  <span>Format:</span>
                  <span className="font-mono text-[11px] text-[#2563EB]">Official CSV & Government Summary</span>
                </div>
                <div className="flex justify-between">
                  <span>Authority:</span>
                  <span className="font-medium text-[#1E293B]">BEL Smart Automation Command Center</span>
                </div>
              </div>

              {reportDownloaded && (
                <div className="p-3 bg-[#DCFCE7] border border-[#86EFAC] rounded-md text-xs text-[#15803D] flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  <span>Executive summary successfully downloaded.</span>
                </div>
              )}

              <div className="pt-3 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowReportModal(false)}
                  className="px-4 py-2 border border-[#CBD5E1] rounded-md text-xs sm:text-sm font-medium text-[#475569] hover:bg-[#F1F5F9] transition"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={handleDownloadCsv}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-md text-xs sm:text-sm font-semibold transition shadow-sm"
                >
                  <Download className="w-4 h-4" />
                  <span>Download Report (CSV)</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Home;
