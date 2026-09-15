// src/pages/Reports/ReportGenerator.tsx
// Phase 29 — Urban Intelligence Report Generator
// Allows users to configure:
// - Date range, City, Zone, Route, Event types
// Generates:
// - 1. Executive Summary
// - 2. Traffic Overview
// - 3. Road Condition
// - 4. Infrastructure Deficiencies
// - 5. Incident Summary
// - 6. Pedestrian Safety
// - 7. Route Delays (with Route 12 benchmark)
// - 8. Congestion Analysis
// - 9. Top Priority Locations
// - 10. Recommended Actions
// Includes charts, GIS map, and explicit data sources.
// Allows: Preview, Download PDF, Save Report, Share with authorized users.

import React, { useState, useEffect } from "react";
import {
  FileText, Download, Share2, Save, Eye, CheckCircle2,
  AlertTriangle, Calendar, MapPin, Route as RouteIcon,
  Sliders, RefreshCw, Check, Copy, Shield, Users, Clock,
  Layers, Construction, Activity, ShieldCheck, ChevronRight,
  ExternalLink, FileCheck, X
} from "lucide-react";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from "recharts";
import RouteDelayMap, { RouteSectionData } from "../../components/RouteDelayMap";

// ── Types ───────────────────────────────────────────────────────────────────

export interface ReportConfigForm {
  date_range: string;
  city: string;
  zone: string;
  route: string;
  event_types: string[];
  title: string;
}

const ALL_EVENT_TYPES = [
  { id: "pothole", label: "Potholes" },
  { id: "road_damage", label: "Road Damage" },
  { id: "waterlogging", label: "Waterlogging" },
  { id: "missing_infrastructure", label: "Missing Infrastructure" },
  { id: "traffic_congestion", label: "Traffic Congestion" },
  { id: "pedestrian_risk", label: "Pedestrian Risks" },
  { id: "collision_incident", label: "Collision Incidents" },
];

const ROUTE_12_SECTIONS: RouteSectionData[] = [
  {
    section_id: "SEC-12-1",
    name: "Majestic City Bus Stand to Richmond Circle",
    length_km: 4.8,
    scheduled_time_minutes: 12.0,
    observed_time_minutes: 14.0,
    delay_minutes: 2.0,
    is_delayed_section: false,
    delay_severity: "NORMAL",
    contributing_factor: "Normal Flow",
    polyline: [
      { lat: 12.9780, lon: 77.5724 },
      { lat: 12.9730, lon: 77.5850 },
      { lat: 12.9660, lon: 77.5980 }
    ],
  },
  {
    section_id: "SEC-12-2",
    name: "Road Segment A — MG Road Radial (Pothole Persistence Corridor)",
    length_km: 3.6,
    scheduled_time_minutes: 10.0,
    observed_time_minutes: 18.0,
    delay_minutes: 8.0,
    is_delayed_section: true,
    delay_severity: "SEVERE",
    contributing_factor: "Road damage & Persistent Potholes",
    polyline: [
      { lat: 12.9660, lon: 77.5980 },
      { lat: 12.9550, lon: 77.6040 },
      { lat: 12.9420, lon: 77.6110 }
    ],
  },
  {
    section_id: "SEC-12-3",
    name: "Dairy Circle to Silk Board Terminal Approach",
    length_km: 4.2,
    scheduled_time_minutes: 20.0,
    observed_time_minutes: 25.0,
    delay_minutes: 5.0,
    is_delayed_section: true,
    delay_severity: "MODERATE",
    contributing_factor: "Severe Congestion & Waterlogging",
    polyline: [
      { lat: 12.9420, lon: 77.6110 },
      { lat: 12.9280, lon: 77.6180 },
      { lat: 12.9172, lon: 77.6229 }
    ],
  },
];

export const ReportGenerator: React.FC = () => {
  // Page Navigation State: "generator" | "archive"
  const [activeView, setActiveView] = useState<"generator" | "archive">("generator");

  // Filter & Form State
  const [config, setConfig] = useState<ReportConfigForm>({
    date_range: "today",
    city: "Bengaluru",
    zone: "all_zones",
    route: "all_routes",
    event_types: ["pothole", "road_damage", "waterlogging", "missing_infrastructure", "traffic_congestion", "pedestrian_risk", "collision_incident"],
    title: "City-Wide Daily Urban Transit Diagnostic & Action Report",
  });

  // Current Generated Report State
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  // Saved Reports List State
  const [savedReports, setSavedReports] = useState<any[]>([]);

  // Share Dialog Modal State
  const [shareModalOpen, setShareModalOpen] = useState<boolean>(false);
  const [shareEmails, setShareEmails] = useState<string>("transit.planner@bmtc.gov.in, police.commissioner@bcp.gov.in");
  const [shareRole, setShareRole] = useState<string>("TRANSIT_PLANNER");
  const [sharePermission, setSharePermission] = useState<string>("VIEW");
  const [shareLink, setShareLink] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState<boolean>(false);

  // Fetch initial pre-seeded report on mount
  useEffect(() => {
    fetchInitialReport();
    fetchSavedReports();
  }, []);

  const fetchInitialReport = async () => {
    try {
      const res = await fetch("/api/v1/reports/REP-BLR-2026-001");
      if (res.ok) {
        setReport(await res.json());
      }
    } catch (e) {
      console.error("Failed to load initial report:", e);
    }
  };

  const fetchSavedReports = async () => {
    try {
      const res = await fetch("/api/v1/reports");
      if (res.ok) {
        setSavedReports(await res.json());
      }
    } catch (e) {
      console.error("Failed to list saved reports:", e);
    }
  };

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3500);
  };

  // Trigger Report Generation
  const handleGenerateReport = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/reports/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (res.ok) {
        const data = await res.json();
        setReport(data);
        showToast("Report generated successfully!");
      } else {
        showToast("Failed to generate report.");
      }
    } catch (err) {
      console.error("Error generating report:", err);
      showToast("Error communicating with server.");
    } finally {
      setLoading(false);
    }
  };

  // Action: Save Report
  const handleSaveReport = async () => {
    if (!report) return;
    try {
      const res = await fetch(`/api/v1/reports/${report.report_id}/save`, {
        method: "POST",
      });
      if (res.ok) {
        const updated = await res.json();
        setReport(updated);
        fetchSavedReports();
        showToast(`Report ${report.report_id} saved to municipal archive.`);
      }
    } catch (e) {
      console.error("Failed to save report:", e);
      showToast("Failed to save report.");
    }
  };

  // Action: Download PDF
  const handleDownloadPdf = () => {
    if (!report) return;
    window.location.href = `/api/v1/reports/${report.report_id}/download-pdf`;
    showToast("PDF document download started.");
  };

  // Action: Share Report
  const handleShareSubmit = async () => {
    if (!report) return;
    try {
      const emails = shareEmails.split(",").map((s) => s.trim()).filter(Boolean);
      const payload = {
        recipients: emails.map((e) => ({
          email: e,
          role: shareRole,
          permission_level: sharePermission,
        })),
        role_restrictions: [shareRole, "TRANSIT_PLANNER", "MUNICIPAL_OFFICER"],
        permission_level: sharePermission,
        notes: `Shared report: ${report.title}`,
      };

      const res = await fetch(`/api/v1/reports/${report.report_id}/share`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        setShareLink(`${window.location.origin}${data.share_link}`);
        showToast("Report shared with authorized users.");
      }
    } catch (e) {
      console.error("Failed to share report:", e);
      showToast("Failed to share report.");
    }
  };

  const handleCopyShareLink = () => {
    if (shareLink) {
      navigator.clipboard.writeText(shareLink);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
      showToast("Share link copied to clipboard.");
    }
  };

  const toggleEventType = (et: string) => {
    setConfig((prev) => {
      const exists = prev.event_types.includes(et);
      const nextTypes = exists ? prev.event_types.filter((x) => x !== et) : [...prev.event_types, et];
      return { ...prev, event_types: nextTypes };
    });
  };

  // Modal split chart data
  const modalChartData = report?.charts_data?.modal_split || [];
  // Severity chart data
  const severityChartData = report?.charts_data?.severity_distribution || [];

  const PIE_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6"];

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      {/* ── Toast Notification ────────────────────────────────────────── */}
      {toastMsg && (
        <div className="fixed top-5 right-5 z-50 flex items-center gap-2 px-4 py-3 rounded-xl bg-emerald-600 text-white shadow-2xl animate-fade-in border border-emerald-400">
          <CheckCircle2 className="w-5 h-5" />
          <span className="text-sm font-semibold">{toastMsg}</span>
        </div>
      )}

      {/* ── Page Header & View Toggle ─────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between pb-6 border-b border-gray-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-indigo-600/20 text-indigo-400 rounded-xl border border-indigo-500/30">
              <FileText className="w-7 h-7" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                Urban Intelligence Report Generator
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                  PHASE 29
                </span>
              </h1>
              <p className="text-sm text-gray-400">
                Automated municipal diagnostics across 10 intelligence domains with embedded charts, GIS maps, and data provenance.
              </p>
            </div>
          </div>
        </div>

        {/* View Switcher: Generator vs Archive */}
        <div className="flex items-center gap-2 bg-gray-800 p-1 rounded-xl border border-gray-700">
          <button
            onClick={() => setActiveView("generator")}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
              activeView === "generator" ? "bg-blue-600 text-white shadow" : "text-gray-400 hover:text-white"
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            Report Generator & Preview
          </button>
          <button
            onClick={() => setActiveView("archive")}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
              activeView === "archive" ? "bg-blue-600 text-white shadow" : "text-gray-400 hover:text-white"
            }`}
          >
            <FileCheck className="w-3.5 h-3.5" />
            Saved Reports Archive ({savedReports.length})
          </button>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────────
          VIEW 1: REPORT GENERATOR & PREVIEW
      ───────────────────────────────────────────────────────────────── */}
      {activeView === "generator" && (
        <div className="mt-6 space-y-6">
          {/* Configuration Selection Form Box */}
          <div className="p-5 bg-gray-800/90 rounded-2xl border border-gray-700 shadow-xl">
            <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-blue-400" />
              Configure Report Generation Criteria
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Date Range Selector */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">
                  Date Range
                </label>
                <select
                  value={config.date_range}
                  onChange={(e) => setConfig({ ...config, date_range: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="today">Today</option>
                  <option value="yesterday">Yesterday</option>
                  <option value="last_7_days">Last 7 Days</option>
                  <option value="last_30_days">Last 30 Days</option>
                </select>
              </div>

              {/* City Selector */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">
                  City
                </label>
                <select
                  value={config.city}
                  onChange={(e) => setConfig({ ...config, city: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="Bengaluru">Bengaluru</option>
                  <option value="Delhi">Delhi</option>
                  <option value="Mumbai">Mumbai</option>
                </select>
              </div>

              {/* Zone Selector */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">
                  Zone
                </label>
                <select
                  value={config.zone}
                  onChange={(e) => setConfig({ ...config, zone: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="all_zones">All Zones (City-Wide)</option>
                  <option value="zone_a">Zone A (Central CBD)</option>
                  <option value="zone_b">Zone B (North Corridor)</option>
                  <option value="zone_c">Zone C (Tech Park East)</option>
                  <option value="zone_d">Zone D (South Residential)</option>
                </select>
              </div>

              {/* Route Selector */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">
                  Route
                </label>
                <select
                  value={config.route}
                  onChange={(e) => setConfig({ ...config, route: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="all_routes">All Routes</option>
                  <option value="ROUTE-12">Route 12 (Majestic ↔ Silk Board)</option>
                  <option value="ROUTE-543">Route 543 (Hebbal ↔ Electronic City)</option>
                  <option value="ROUTE-403">Route 403 (Majestic ↔ ITPL Whitefield)</option>
                  <option value="ROUTE-305">Route 305 (Shivajinagar ↔ Kadugodi)</option>
                  <option value="ROUTE-813">Route 813 (Banashankari ↔ Jayanagar)</option>
                </select>
              </div>
            </div>

            {/* Event Types Multi-Selector */}
            <div className="mt-4">
              <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
                Event Types to Include
              </label>
              <div className="flex flex-wrap gap-2">
                {ALL_EVENT_TYPES.map((et) => {
                  const isChecked = config.event_types.includes(et.id);
                  return (
                    <button
                      key={et.id}
                      type="button"
                      onClick={() => toggleEventType(et.id)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition flex items-center gap-1.5 ${
                        isChecked
                          ? "bg-blue-600/30 border-blue-500 text-blue-200 font-semibold"
                          : "bg-gray-900/60 border-gray-700 text-gray-400 hover:text-gray-200"
                      }`}
                    >
                      <span className={`w-2 h-2 rounded-full ${isChecked ? "bg-blue-400" : "bg-gray-600"}`}></span>
                      {et.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Title & Generate Action Button */}
            <div className="mt-5 flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-gray-700/80">
              <input
                type="text"
                value={config.title}
                onChange={(e) => setConfig({ ...config, title: e.target.value })}
                placeholder="Enter report title..."
                className="w-full sm:w-2/3 bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-lg px-3.5 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />

              <button
                onClick={handleGenerateReport}
                disabled={loading}
                className="w-full sm:w-auto px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm rounded-lg shadow-lg flex items-center justify-center gap-2 transition"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                {loading ? "Synthesizing Report..." : "Generate Intelligence Report"}
              </button>
            </div>
          </div>

          {/* ── Document Actions Toolbar ─────────────────────────────────── */}
          {report && (
            <div className="flex flex-wrap items-center justify-between p-4 bg-gray-800 rounded-xl border border-gray-700 gap-4">
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold uppercase tracking-wider text-gray-400">Report Status:</span>
                <span className={`px-2.5 py-0.5 rounded text-xs font-bold ${
                  report.status === "SAVED" || report.status === "PUBLISHED"
                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                    : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                }`}>
                  {report.status}
                </span>
                <span className="text-xs text-gray-400 font-mono">ID: {report.report_id}</span>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {/* 1. Save Report */}
                <button
                  onClick={handleSaveReport}
                  className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition"
                >
                  <Save className="w-3.5 h-3.5 text-blue-400" />
                  Save Report
                </button>

                {/* 2. Download PDF */}
                <button
                  onClick={handleDownloadPdf}
                  className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold bg-emerald-700 hover:bg-emerald-600 text-white rounded-lg transition shadow"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download PDF
                </button>

                {/* 3. Share Report */}
                <button
                  onClick={() => setShareModalOpen(true)}
                  className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition shadow"
                >
                  <Share2 className="w-3.5 h-3.5" />
                  Share with Authorized Users
                </button>
              </div>
            </div>
          )}

          {/* ───────────────────────────────────────────────────────────────
              REPORT PREVIEW DOCUMENT (ALL 10 SECTIONS)
          ─────────────────────────────────────────────────────────────── */}
          {report && (
            <div className="bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl overflow-hidden p-8 space-y-8">
              {/* Document Banner */}
              <div className="border-b border-gray-800 pb-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <div className="text-xs font-mono uppercase tracking-widest text-blue-400 mb-1">
                      MUNICIPAL TRANSIT DIAGNOSTIC INTELLIGENCE
                    </div>
                    <h2 className="text-2xl font-extrabold text-white">{report.title}</h2>
                    <p className="text-xs text-gray-400 mt-1">
                      City: <strong className="text-gray-200">{report.city}</strong> · Zone: <strong className="text-gray-200 uppercase">{report.config.zone}</strong> · Generated: <strong className="text-gray-200">{new Date(report.generated_at).toLocaleString()}</strong>
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-gray-400">Municipal Health Index</div>
                    <div className="text-3xl font-extrabold text-emerald-400">
                      {report.executive_summary.municipal_health_score}<span className="text-base text-gray-400">/100</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 1. EXECUTIVE SUMMARY */}
              <section className="space-y-3">
                <h3 className="text-lg font-bold text-white border-l-4 border-blue-500 pl-3">
                  1. Executive Summary
                </h3>
                <div className="p-4 bg-gray-800/80 rounded-xl border border-gray-700">
                  <p className="text-sm font-semibold text-gray-200">{report.executive_summary.headline}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Analysis based on <strong className="text-white">{report.executive_summary.total_events_analyzed.toLocaleString()}</strong> raw edge detections synthesized across <strong className="text-white">{report.executive_summary.active_buses_contributing}</strong> active fleet buses.
                  </p>
                  <div className="mt-3">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400 mb-1">Key Operational Takeaways:</h4>
                    <ul className="space-y-1 text-xs text-gray-300">
                      {report.executive_summary.key_takeaways.map((t: string, idx: number) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-blue-400 font-bold">•</span>
                          {t}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </section>

              {/* 2. TRAFFIC OVERVIEW */}
              <section className="space-y-3">
                <h3 className="text-lg font-bold text-white border-l-4 border-blue-500 pl-3">
                  2. Traffic Overview
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                  <div className="p-4 bg-gray-800 rounded-xl border border-gray-700">
                    <div className="text-xs text-gray-400">Total Vehicle Volume</div>
                    <div className="text-2xl font-bold text-white mt-1">{report.traffic_overview.total_vehicle_count.toLocaleString()}</div>
                  </div>
                  <div className="p-4 bg-gray-800 rounded-xl border border-gray-700">
                    <div className="text-xs text-gray-400">Network Average Speed</div>
                    <div className="text-2xl font-bold text-emerald-400 mt-1">{report.traffic_overview.average_speed_kmh} km/h</div>
                  </div>
                  <div className="p-4 bg-gray-800 rounded-xl border border-gray-700">
                    <div className="text-xs text-gray-400">Network Congestion Score</div>
                    <div className="text-2xl font-bold text-rose-400 mt-1">{report.traffic_overview.network_congestion_score}/100</div>
                  </div>
                  <div className="p-4 bg-gray-800 rounded-xl border border-gray-700">
                    <div className="text-xs text-gray-400">Active Bottlenecks</div>
                    <div className="text-2xl font-bold text-amber-400 mt-1">{report.traffic_overview.active_bottlenecks} choke points</div>
                  </div>
                </div>

                {/* Traffic Diurnal Line Chart */}
                <div className="p-4 bg-gray-800 rounded-xl border border-gray-700">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
                    24-Hour Diurnal Speed & Volume Curve
                  </h4>
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={report.charts_data?.diurnal_curve || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="hour" stroke="#9ca3af" fontSize={10} />
                        <YAxis yAxisId="vol" stroke="#3b82f6" fontSize={10} />
                        <YAxis yAxisId="spd" orientation="right" stroke="#ef4444" fontSize={10} unit=" km/h" />
                        <Tooltip contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151" }} />
                        <Line yAxisId="vol" type="monotone" dataKey="vehicles" name="Volume" stroke="#3b82f6" strokeWidth={2} dot={false} />
                        <Line yAxisId="spd" type="monotone" dataKey="speed" name="Speed (km/h)" stroke="#ef4444" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </section>

              {/* 3. ROAD CONDITION & DEFECTS */}
              <section className="space-y-3">
                <h3 className="text-lg font-bold text-white border-l-4 border-amber-500 pl-3">
                  3. Road Condition & Defect Analysis
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                  <div className="p-4 bg-gray-800 rounded-xl border border-gray-700 text-amber-400">
                    <div className="text-xs text-gray-400">Potholes</div>
                    <div className="text-2xl font-bold mt-1">{report.road_condition.potholes}</div>
                  </div>
                  <div className="p-4 bg-gray-800 rounded-xl border border-gray-700 text-orange-400">
                    <div className="text-xs text-gray-400">Road Damage</div>
                    <div className="text-2xl font-bold mt-1">{report.road_condition.road_damage}</div>
                  </div>
                  <div className="p-4 bg-gray-800 rounded-xl border border-gray-700 text-cyan-400">
                    <div className="text-xs text-gray-400">Waterlogging</div>
                    <div className="text-2xl font-bold mt-1">{report.road_condition.waterlogging}</div>
                  </div>
                  <div className="p-4 bg-gray-800 rounded-xl border border-gray-700 text-rose-400">
                    <div className="text-xs text-gray-400">Missing Infrastructure</div>
                    <div className="text-2xl font-bold mt-1">{report.road_condition.missing_infrastructure}</div>
                  </div>
                </div>
              </section>

              {/* 4. INFRASTRUCTURE DEFICIENCIES */}
              <section className="space-y-3">
                <h3 className="text-lg font-bold text-white border-l-4 border-purple-500 pl-3">
                  4. Infrastructure Deficiencies
                </h3>
                <div className="p-4 bg-gray-800 rounded-xl border border-gray-700">
                  <table className="w-full text-left text-xs text-gray-300">
                    <thead className="text-gray-400 uppercase border-b border-gray-700">
                      <tr>
                        <th className="py-2 px-3">Deficient Asset</th>
                        <th className="py-2 px-3">Corridor</th>
                        <th className="py-2 px-2">Zone</th>
                        <th className="py-2 px-2">Urgency</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                      {report.infrastructure_deficiencies.priority_deficiency_list.map((item: any, i: number) => (
                        <tr key={i}>
                          <td className="py-2 px-3 font-semibold text-white">{item.asset}</td>
                          <td className="py-2 px-3">{item.corridor}</td>
                          <td className="py-2 px-2 uppercase">{item.zone}</td>
                          <td className="py-2 px-2 font-bold text-amber-400">{item.urgency}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* 5. INCIDENT SUMMARY & 6. PEDESTRIAN SAFETY */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <section className="space-y-3">
                  <h3 className="text-lg font-bold text-white border-l-4 border-rose-500 pl-3">
                    5. Incident Summary
                  </h3>
                  <div className="p-4 bg-gray-800 rounded-xl border border-gray-700 space-y-2 text-xs">
                    <div className="flex justify-between py-1 border-b border-gray-700">
                      <span className="text-gray-400">Total Recorded Incidents</span>
                      <strong className="text-white">{report.incident_summary.total_incidents}</strong>
                    </div>
                    <div className="flex justify-between py-1 border-b border-gray-700">
                      <span className="text-gray-400">Collision Near-Misses</span>
                      <strong className="text-amber-400">{report.incident_summary.collision_near_misses}</strong>
                    </div>
                    <div className="flex justify-between py-1 border-b border-gray-700">
                      <span className="text-gray-400">Sudden Deceleration Events</span>
                      <strong className="text-purple-400">{report.incident_summary.sudden_heavy_braking}</strong>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-gray-400">Severity Assessment</span>
                      <strong className="text-emerald-400">{report.incident_summary.severity_index}</strong>
                    </div>
                  </div>
                </section>

                <section className="space-y-3">
                  <h3 className="text-lg font-bold text-white border-l-4 border-emerald-500 pl-3">
                    6. Pedestrian Safety
                  </h3>
                  <div className="p-4 bg-gray-800 rounded-xl border border-gray-700 space-y-2 text-xs">
                    <div className="flex justify-between py-1 border-b border-gray-700">
                      <span className="text-gray-400">Total Pedestrian Conflicts</span>
                      <strong className="text-rose-400">{report.pedestrian_safety.pedestrian_conflicts}</strong>
                    </div>
                    <div className="flex justify-between py-1 border-b border-gray-700">
                      <span className="text-gray-400">School Zone Conflicts</span>
                      <strong className="text-amber-400">{report.pedestrian_safety.school_zone_conflicts}</strong>
                    </div>
                    <div className="mt-2">
                      <span className="text-gray-400 font-semibold block mb-1">Top Conflict Hotspot:</span>
                      <div className="p-2 bg-gray-900 rounded border border-gray-700 text-gray-200">
                        <strong>{report.pedestrian_safety.vulnerable_hotspots[0]?.location}</strong> ({report.pedestrian_safety.vulnerable_hotspots[0]?.zone}) — {report.pedestrian_safety.vulnerable_hotspots[0]?.reason}
                      </div>
                    </div>
                  </div>
                </section>
              </div>

              {/* 7. ROUTE DELAYS & ROUTE 12 BENCHMARK */}
              <section className="space-y-3">
                <h3 className="text-lg font-bold text-white border-l-4 border-indigo-500 pl-3">
                  7. Route Delays & Route 12 Benchmark
                </h3>
                <div className="p-5 bg-gradient-to-r from-blue-950/40 to-gray-800 rounded-xl border border-blue-800/40">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <span className="px-2 py-0.5 rounded text-2xs font-bold uppercase bg-blue-500/20 text-blue-300">
                        Canonical Target Route Benchmark
                      </span>
                      <h4 className="text-base font-bold text-white mt-1">
                        {report.route_delays.canonical_route_12.name}
                      </h4>
                      <p className="text-xs text-gray-300 mt-1">
                        Scheduled: <strong>{report.route_delays.canonical_route_12.scheduled_travel_time_minutes} min</strong> | Observed: <strong>{report.route_delays.canonical_route_12.observed_travel_time_minutes} min</strong> | Average Delay: <strong className="text-rose-400">+{report.route_delays.canonical_route_12.average_delay_minutes} min</strong>
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-400">Attributed Factors:</div>
                      <div className="text-xs font-semibold text-gray-200 mt-1">
                        Congestion: 54% · Road damage: 28% · Waterlogging: 18%
                      </div>
                    </div>
                  </div>
                </div>

                {/* Worst Delayed Routes Table */}
                <div className="p-4 bg-gray-800 rounded-xl border border-gray-700 overflow-x-auto">
                  <table className="w-full text-left text-xs text-gray-300">
                    <thead className="uppercase text-gray-400 border-b border-gray-700">
                      <tr>
                        <th className="py-2 px-3">Route</th>
                        <th className="py-2 px-2">Scheduled</th>
                        <th className="py-2 px-2">Observed</th>
                        <th className="py-2 px-2">Avg Delay</th>
                        <th className="py-2 px-3">Primary Factor</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                      {report.route_delays.worst_delayed_routes.map((r: any, idx: number) => (
                        <tr key={idx} className={r.route_id === "ROUTE-12" ? "bg-blue-950/30" : ""}>
                          <td className="py-2 px-3 font-semibold text-white">{r.name}</td>
                          <td className="py-2 px-2 text-gray-400">{r.scheduled_min}m</td>
                          <td className="py-2 px-2 font-bold text-white">{r.observed_min}m</td>
                          <td className="py-2 px-2 font-extrabold text-rose-400">+{r.avg_delay_min}m</td>
                          <td className="py-2 px-3 text-amber-300">{r.primary_factor}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* 8. CONGESTION ANALYSIS */}
              <section className="space-y-3">
                <h3 className="text-lg font-bold text-white border-l-4 border-amber-500 pl-3">
                  8. Congestion Analysis
                </h3>
                <div className="p-4 bg-gray-800 rounded-xl border border-gray-700">
                  <div className="text-xs text-gray-400 mb-2">Top 5 Bottlenecks:</div>
                  <div className="space-y-2 text-xs">
                    {report.congestion_analysis.top_congested_corridors.map((c: any, i: number) => (
                      <div key={i} className="flex items-center justify-between p-2 bg-gray-900/60 rounded border border-gray-700">
                        <span className="font-semibold text-white">{c.name}</span>
                        <div className="flex items-center gap-3">
                          <span className="text-gray-400">Speed: {c.avg_speed} km/h (Free flow {c.free_flow})</span>
                          <span className="font-bold text-rose-400">Score: {c.score}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>

              {/* 9. TOP PRIORITY LOCATIONS & GIS MAP */}
              <section className="space-y-3">
                <h3 className="text-lg font-bold text-white border-l-4 border-rose-500 pl-3">
                  9. Top Priority Locations & GIS Map Visualization
                </h3>
                <div className="p-4 bg-gray-800 rounded-xl border border-gray-700 overflow-x-auto">
                  <table className="w-full text-left text-xs text-gray-300">
                    <thead className="uppercase text-gray-400 border-b border-gray-700">
                      <tr>
                        <th className="py-2.5 px-3">#</th>
                        <th className="py-2.5 px-3">Location</th>
                        <th className="py-2.5 px-2">Zone</th>
                        <th className="py-2.5 px-2">Severity</th>
                        <th className="py-2.5 px-3">Primary Issue</th>
                        <th className="py-2.5 px-3">Lead Agency</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                      {report.top_priority_locations.map((loc: any) => (
                        <tr key={loc.rank} className="hover:bg-gray-750">
                          <td className="py-2.5 px-3 font-bold text-gray-400">{loc.rank}</td>
                          <td className="py-2.5 px-3 font-bold text-white flex items-center gap-1.5">
                            <MapPin className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                            {loc.location_name}
                          </td>
                          <td className="py-2.5 px-2 uppercase">{loc.zone}</td>
                          <td className="py-2.5 px-2">
                            <span className="px-2 py-0.5 rounded text-2xs font-extrabold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                              {loc.severity}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-gray-200">{loc.primary_issue}</td>
                          <td className="py-2.5 px-3 text-blue-300">{loc.lead_agency}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Embedded GIS Map */}
                <div className="p-4 bg-gray-800 rounded-xl border border-gray-700">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
                    GIS Spatial Corridor Map — Route 12 Delayed Sections & Pothole Clusters
                  </h4>
                  <div className="border border-gray-700 rounded-lg overflow-hidden">
                    <RouteDelayMap
                      routeName="Route 12 Corridor & Spatial Defect Map"
                      sections={ROUTE_12_SECTIONS}
                      height="280px"
                    />
                  </div>
                </div>
              </section>

              {/* 10. RECOMMENDED OPERATIONAL ACTIONS */}
              <section className="space-y-3">
                <h3 className="text-lg font-bold text-white border-l-4 border-emerald-500 pl-3">
                  10. Recommended Operational Actions
                </h3>
                <div className="space-y-3">
                  {report.recommended_actions.map((act: any, idx: number) => (
                    <div key={idx} className="p-4 bg-gray-800 rounded-xl border border-gray-700 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm text-white flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-2xs font-extrabold ${
                            act.priority === "IMMEDIATE" ? "bg-rose-500/20 text-rose-300 border border-rose-500/30" : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                          }`}>
                            {act.priority}
                          </span>
                          {act.title}
                        </span>
                        <span className="text-xs text-gray-400">Target: {act.target_completion_days} days</span>
                      </div>
                      <p className="text-xs text-gray-300"><strong className="text-white">Action:</strong> {act.recommended_action}</p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-2xs text-gray-400 pt-1 border-t border-gray-700">
                        <div><strong>Evidence:</strong> {act.evidence}</div>
                        <div><strong>Impact:</strong> {act.estimated_impact}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* DATA SOURCES & PROVENANCE */}
              <section className="p-4 bg-gray-800/60 rounded-xl border border-gray-700 text-xs space-y-2">
                <h4 className="font-bold uppercase tracking-wider text-gray-400">
                  Data Sources & Algorithmic Provenance
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {report.data_sources.map((src: any, i: number) => (
                    <div key={i} className="p-2.5 bg-gray-900/60 rounded border border-gray-700">
                      <div className="font-bold text-blue-300">{src.source_name}</div>
                      <div className="text-gray-400 text-2xs mt-0.5">Type: {src.type}</div>
                      <div className="text-gray-300 text-2xs mt-0.5">Coverage: {src.coverage}</div>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          )}
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────
          VIEW 2: SAVED REPORTS ARCHIVE
      ───────────────────────────────────────────────────────────────── */}
      {activeView === "archive" && (
        <div className="mt-6 space-y-4">
          <div className="p-5 bg-gray-800 rounded-2xl border border-gray-700 shadow-xl">
            <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
              <FileCheck className="w-4 h-4 text-emerald-400" />
              Municipal Intelligence Report Archive
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-gray-300">
                <thead className="bg-gray-900/60 text-xs uppercase text-gray-400 border-b border-gray-700">
                  <tr>
                    <th className="py-3 px-4">Report ID</th>
                    <th className="py-3 px-4">Title</th>
                    <th className="py-3 px-3">City</th>
                    <th className="py-3 px-3">Date Range</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-3">Generated At</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {savedReports.map((r: any) => (
                    <tr key={r.report_id} className="hover:bg-gray-750">
                      <td className="py-3 px-4 font-mono text-xs font-bold text-blue-400">{r.report_id}</td>
                      <td className="py-3 px-4 font-semibold text-white">{r.title}</td>
                      <td className="py-3 px-3">{r.city}</td>
                      <td className="py-3 px-3 uppercase text-xs text-gray-400">{r.config.date_range}</td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          {r.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-xs text-gray-400">{new Date(r.generated_at).toLocaleDateString()}</td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => {
                              setReport(r);
                              setActiveView("generator");
                            }}
                            className="px-2.5 py-1 text-xs font-semibold bg-gray-700 hover:bg-gray-600 text-white rounded transition"
                          >
                            View
                          </button>
                          <a
                            href={`/api/v1/reports/${r.report_id}/download-pdf`}
                            className="px-2.5 py-1 text-xs font-semibold bg-emerald-700 hover:bg-emerald-600 text-white rounded transition"
                          >
                            PDF
                          </a>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── Share Modal Dialog ────────────────────────────────────────── */}
      {shareModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-gray-800 border border-gray-700 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-700 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Share2 className="w-5 h-5 text-indigo-400" />
                Share Report with Authorized Users
              </h3>
              <button
                onClick={() => {
                  setShareModalOpen(false);
                  setShareLink(null);
                }}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase text-gray-400 mb-1">
                Authorized Recipient Emails (comma-separated)
              </label>
              <textarea
                rows={2}
                value={shareEmails}
                onChange={(e) => setShareEmails(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 text-gray-200 text-xs rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold uppercase text-gray-400 mb-1">
                  Role Restriction
                </label>
                <select
                  value={shareRole}
                  onChange={(e) => setShareRole(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 text-gray-200 text-xs rounded-lg px-2.5 py-2 focus:ring-2 focus:ring-blue-500"
                >
                  <option value="TRANSIT_PLANNER">Transit Planner</option>
                  <option value="MUNICIPAL_OFFICER">Municipal Officer</option>
                  <option value="TRAFFIC_POLICE_CHIEF">Traffic Police Chief</option>
                  <option value="FLEET_OPERATOR">Fleet Operator</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-400 mb-1">
                  Permission Level
                </label>
                <select
                  value={sharePermission}
                  onChange={(e) => setSharePermission(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 text-gray-200 text-xs rounded-lg px-2.5 py-2 focus:ring-2 focus:ring-blue-500"
                >
                  <option value="VIEW">View Only</option>
                  <option value="EXPORT">View & Export PDF</option>
                  <option value="EDIT">Collaborative Review</option>
                </select>
              </div>
            </div>

            {shareLink && (
              <div className="p-3 bg-gray-900 rounded-lg border border-gray-700 space-y-1.5">
                <span className="text-2xs font-bold uppercase text-emerald-400">Secure Access Link Generated:</span>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={shareLink}
                    className="w-full bg-gray-950 border border-gray-800 text-xs text-gray-300 rounded px-2 py-1.5 font-mono"
                  />
                  <button
                    onClick={handleCopyShareLink}
                    className="px-3 py-1.5 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white rounded flex items-center gap-1 shrink-0"
                  >
                    {copiedLink ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedLink ? "Copied" : "Copy"}
                  </button>
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-3 border-t border-gray-700">
              <button
                onClick={() => {
                  setShareModalOpen(false);
                  setShareLink(null);
                }}
                className="px-4 py-2 text-xs font-semibold bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition"
              >
                Close
              </button>
              <button
                onClick={handleShareSubmit}
                className="px-4 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
              >
                Send & Generate Link
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportGenerator;
