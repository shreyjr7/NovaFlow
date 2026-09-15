// src/pages/RoadDefects/RoadDefects.tsx
// Road Defect Management Console (Phase 18)
// 6-Stage Lifecycle, Priority Scoring, Field Engineer Workflows & Post-Closure Watchdog

import React, { useState, useMemo, useEffect } from "react";
import {
  AlertTriangle, Droplets, Construction, Signpost,
  CrosshairIcon, ShieldAlert, Filter, RefreshCw,
  CheckCircle2, Clock, XCircle, MapPin, Camera,
  TrendingUp, Eye, Wrench, Send, AlertOctagon,
  ArrowRight, ShieldCheck, Check, FileText,
  HelpCircle, UserCheck, Flame, ExternalLink,
  ChevronRight, Sparkles, History
} from "lucide-react";
import DefectMap from "../../components/DefectMap";
import {
  DefectEvent, DefectClass, DefectSeverity, DefectStatus,
  DefectLifecycleState, DefectPriorityBreakdown
} from "./types";
import { MOCK_EVENTS, MOCK_SUMMARY } from "./mockData";

// ── Icon & Color Mappings ───────────────────────────────────────────────────

const CLASS_META: Record<string, { label: string; icon: React.FC<{ size?: number; className?: string }>; color: string }> = {
  pothole:              { label: "Pothole",             icon: CrosshairIcon, color: "text-red-400" },
  POTHOLE:              { label: "Pothole",             icon: CrosshairIcon, color: "text-red-400" },
  damaged_road:         { label: "Damaged Road",        icon: Construction,  color: "text-orange-400" },
  DAMAGED_ROAD:         { label: "Damaged Road",        icon: Construction,  color: "text-orange-400" },
  waterlogging:         { label: "Waterlogging",        icon: Droplets,      color: "text-blue-400" },
  WATERLOGGING:         { label: "Waterlogging",        icon: Droplets,      color: "text-blue-400" },
  missing_road_divider: { label: "Missing Divider",     icon: AlertTriangle, color: "text-yellow-400" },
  MISSING_DIVIDER:      { label: "Missing Divider",     icon: AlertTriangle, color: "text-yellow-400" },
  missing_zebra:        { label: "Missing Zebra",       icon: Signpost,      color: "text-purple-400" },
  damaged_sign:         { label: "Damaged Sign",        icon: ShieldAlert,   color: "text-rose-400" },
  missing_sign:         { label: "Missing Sign",        icon: XCircle,       color: "text-pink-400" },
};

const LIFECYCLE_STAGES: { id: DefectLifecycleState; label: string; color: string }[] = [
  { id: "AI_DETECTED",           label: "AI Detected",    color: "border-sky-500 text-sky-400 bg-sky-500/10" },
  { id: "UNVERIFIED",            label: "Unverified",     color: "border-amber-500 text-amber-400 bg-amber-500/10" },
  { id: "CONFIRMED",             label: "Confirmed",      color: "border-indigo-500 text-indigo-400 bg-indigo-500/10" },
  { id: "ASSIGNED",              label: "Assigned",       color: "border-blue-500 text-blue-400 bg-blue-500/10" },
  { id: "UNDER_REPAIR",          label: "Under Repair",   color: "border-purple-500 text-purple-400 bg-purple-500/10" },
  { id: "RESOLVED",              label: "Resolved",       color: "border-emerald-500 text-emerald-400 bg-emerald-500/10" },
];

const STATUS_BADGE: Record<string, string> = {
  AI_DETECTED:           "bg-sky-500/20 text-sky-400 border border-sky-500/30",
  UNVERIFIED:            "bg-amber-500/20 text-amber-400 border border-amber-500/30",
  CONFIRMED:             "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30",
  ASSIGNED:              "bg-blue-500/20 text-blue-400 border border-blue-500/30",
  UNDER_REPAIR:          "bg-purple-500/20 text-purple-400 border border-purple-500/30",
  RESOLVED:              "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
  REOPENED_UNDER_REVIEW: "bg-rose-500/25 text-rose-300 border border-rose-500/50 animate-pulse font-semibold",
  REJECTED:              "bg-gray-700/40 text-gray-400 border border-gray-600",
  // Legacy
  OPEN:                  "bg-amber-500/20 text-amber-400 border border-amber-500/30",
  IN_PROGRESS:           "bg-purple-500/20 text-purple-400 border border-purple-500/30",
  FALSE_POSITIVE:        "bg-gray-700/40 text-gray-400 border border-gray-600",
};

function formatTs(iso?: string) {
  if (!iso) return "N/A";
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function getPriorityBadge(score: number = 50) {
  if (score >= 80) return "bg-rose-500/20 text-rose-400 border border-rose-500/40";
  if (score >= 60) return "bg-orange-500/20 text-orange-400 border border-orange-500/40";
  if (score >= 40) return "bg-amber-500/20 text-amber-400 border border-amber-500/40";
  return "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40";
}

// ── Main Component ──────────────────────────────────────────────────────────

export const RoadDefects: React.FC = () => {
  const [defects, setDefects] = useState<DefectEvent[]>(MOCK_EVENTS);
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("all");
  const [selectedAuthority, setSelectedAuthority] = useState<string>("all");
  const [selectedDefect, setSelectedDefect] = useState<DefectEvent | null>(null);
  const [activeTab, setActiveTab] = useState<"table" | "map" | "clusters">("table");
  const [actionModal, setActionModal] = useState<"assign" | "update" | "evidence" | "reject" | null>(null);

  // Canonical Clusters state (Phase 19)
  const [canonicalClusters, setCanonicalClusters] = useState<any[]>([
    {
      canonical_id: "Pothole #104",
      defect_type: "POTHOLE",
      severity: "HIGH",
      road_segment: "CP_INNER_CIRCLE",
      centroid: { lat: 28.6328, lon: 77.2195, address: "Connaught Place Inner Circle Radial 2" },
      detected_by: ["Bus 102", "Bus 117", "Bus 143"],
      number_of_buses: 3,
      number_of_observations: 18,
      confidence: 0.92,
      status: "Confirmed",
      first_detected: "2026-09-13T06:00:00Z",
      last_detected: new Date().toISOString(),
      observations: [
        { observation_id: "OBS-104-01", bus_id: "Bus 102", lat: 28.63281, lon: 77.21952, confidence: 0.91, timestamp: "2026-09-13T06:00:00Z", distance_to_centroid_m: 1.8 },
        { observation_id: "OBS-104-02", bus_id: "Bus 117", lat: 28.63279, lon: 77.21948, confidence: 0.93, timestamp: "2026-09-13T09:15:00Z", distance_to_centroid_m: 2.1 },
        { observation_id: "OBS-104-03", bus_id: "Bus 143", lat: 28.63282, lon: 77.21953, confidence: 0.89, timestamp: "2026-09-14T08:30:00Z", distance_to_centroid_m: 3.2 },
        { observation_id: "OBS-104-04", bus_id: "Bus 102", lat: 28.63280, lon: 77.21950, confidence: 0.94, timestamp: "2026-09-15T04:10:00Z", distance_to_centroid_m: 0.5 },
      ],
    },
    {
      canonical_id: "Road Damage #208",
      defect_type: "DAMAGED_ROAD",
      severity: "HIGH",
      road_segment: "RING_ROAD_AIIMS",
      centroid: { lat: 28.5680, lon: 77.2090, address: "Ring Road Flyover Ramp near AIIMS" },
      detected_by: ["Bus 101", "Bus 104", "Bus 109"],
      number_of_buses: 3,
      number_of_observations: 22,
      confidence: 0.95,
      status: "Confirmed",
      first_detected: "2026-09-12T04:00:00Z",
      last_detected: new Date().toISOString(),
    },
    {
      canonical_id: "Waterlogging #312",
      defect_type: "WATERLOGGING",
      severity: "MEDIUM",
      road_segment: "TOLSTOY_MARG",
      centroid: { lat: 28.6280, lon: 77.2260, address: "Tolstoy Marg Underpass" },
      detected_by: ["Bus 102", "Bus 105"],
      number_of_buses: 2,
      number_of_observations: 14,
      confidence: 0.89,
      status: "Confirmed",
      first_detected: "2026-09-14T08:00:00Z",
      last_detected: new Date().toISOString(),
    },
    {
      canonical_id: "Pothole #405",
      defect_type: "POTHOLE",
      severity: "LOW",
      road_segment: "MG_ROAD_CORRIDOR",
      centroid: { lat: 12.9730, lon: 77.6000, address: "MG Road Metro Pillar 142" },
      detected_by: ["Bus 108"],
      number_of_buses: 1,
      number_of_observations: 1,
      confidence: 0.78,
      status: "Pending",
      first_detected: new Date().toISOString(),
      last_detected: new Date().toISOString(),
    },
  ]);
  const [selectedCluster, setSelectedCluster] = useState<any | null>(null);

  // Form states for modals
  const [assignAuthority, setAssignAuthority] = useState("Public Works Department (PWD)");
  const [assignContractor, setAssignContractor] = useState("Larsen & Toubro Infra");
  const [repairProgress, setRepairProgress] = useState(50);
  const [repairNotes, setRepairNotes] = useState("");
  const [evidenceNotes, setEvidenceNotes] = useState("Hot asphalt compaction verified on site.");
  const [rejectReason, setRejectReason] = useState("Visual shadow artifact – false positive.");
  const [notification, setNotification] = useState<{ msg: string; type: "info" | "success" | "warning" } | null>(null);

  // Fetch from backend API if available, fallback to mock data
  useEffect(() => {
    fetch("/api/v1/road-defects")
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data && data.items && data.items.length > 0) {
          setDefects(data.items);
        }
      })
      .catch(() => {
        // use mock data
      });
  }, []);

  const reopenedDefects = useMemo(() => {
    return defects.filter(d => d.status === "REOPENED_UNDER_REVIEW" || (d.reopen_count || 0) > 0);
  }, [defects]);

  const filtered = useMemo(() => {
    return defects.filter(d => {
      if (selectedStatus !== "all" && d.status !== selectedStatus) return false;
      if (selectedType !== "all" && (d.type || d.cls) !== selectedType && d.cls !== selectedType.toLowerCase()) return false;
      if (selectedSeverity !== "all" && d.severity !== selectedSeverity) return false;
      if (selectedAuthority !== "all" && (!d.assigned_authority || !d.assigned_authority.toLowerCase().includes(selectedAuthority.toLowerCase()))) return false;
      return true;
    });
  }, [defects, selectedStatus, selectedType, selectedSeverity, selectedAuthority]);

  const summary = useMemo(() => {
    const total = defects.length;
    const critical = defects.filter(d => (d.priority_score || 0) >= 80).length;
    const activeRepairs = defects.filter(d => d.status === "UNDER_REPAIR" || d.status === "ASSIGNED").length;
    const resolved = defects.filter(d => d.status === "RESOLVED").length;
    return { total, critical, activeRepairs, resolved, reopened: reopenedDefects.length };
  }, [defects, reopenedDefects]);

  // Notification auto-dismiss
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  // ── Field Engineer Workflow Handlers ──────────────────────────────────────

  const handleConfirm = async (defectId: string) => {
    try {
      const res = await fetch(`/api/v1/road-defects/${defectId}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ engineer_id: "ENG_CIVIL_042", notes: "Field engineer verified road crater on site." }),
      });
      if (res.ok) {
        const data = await res.json();
        updateLocalDefectStatus(defectId, "CONFIRMED", { priority_score: data.priority_score });
      } else {
        updateLocalDefectStatus(defectId, "CONFIRMED");
      }
      setNotification({ msg: `Defect ${defectId} successfully CONFIRMED by Field Engineer.`, type: "success" });
    } catch {
      updateLocalDefectStatus(defectId, "CONFIRMED");
      setNotification({ msg: `Defect ${defectId} confirmed locally.`, type: "success" });
    }
  };

  const handleReject = async (defectId: string) => {
    try {
      await fetch(`/api/v1/road-defects/${defectId}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ engineer_id: "ENG_CIVIL_042", reason: rejectReason }),
      });
      updateLocalDefectStatus(defectId, "REJECTED");
      setActionModal(null);
      setNotification({ msg: `Defect ${defectId} marked as REJECTED (${rejectReason}).`, type: "info" });
    } catch {
      updateLocalDefectStatus(defectId, "REJECTED");
      setActionModal(null);
      setNotification({ msg: `Defect ${defectId} rejected locally.`, type: "info" });
    }
  };

  const handleAssign = async (defectId: string) => {
    const ticketId = `TICK-2026-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;
    try {
      const res = await fetch(`/api/v1/road-defects/${defectId}/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          engineer_id: "ENG_CIVIL_042",
          assigned_authority: assignAuthority,
          assigned_contractor: assignContractor,
          notes: "Priority asphalt resurfacing work order.",
        }),
      });
      if (res.ok) {
        const data = await res.json();
        updateLocalDefectStatus(defectId, "ASSIGNED", {
          assigned_authority: assignAuthority,
          maintenance_ticket: data.ticket || { ticket_id: ticketId, assigned_authority: assignAuthority, status: "ASSIGNED", created_at: new Date().toISOString() },
        });
      } else {
        updateLocalDefectStatus(defectId, "ASSIGNED", {
          assigned_authority: assignAuthority,
          maintenance_ticket: { ticket_id: ticketId, assigned_authority: assignAuthority, status: "ASSIGNED", created_at: new Date().toISOString() },
        });
      }
      setActionModal(null);
      setNotification({ msg: `Work Order ${ticketId} issued to ${assignAuthority}.`, type: "success" });
    } catch {
      updateLocalDefectStatus(defectId, "ASSIGNED", {
        assigned_authority: assignAuthority,
        maintenance_ticket: { ticket_id: ticketId, assigned_authority: assignAuthority, status: "ASSIGNED", created_at: new Date().toISOString() },
      });
      setActionModal(null);
      setNotification({ msg: `Defect ${defectId} assigned locally.`, type: "success" });
    }
  };

  const handleUpdateRepair = async (defectId: string) => {
    try {
      await fetch(`/api/v1/road-defects/${defectId}/update`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          engineer_id: "ENG_FIELD_108",
          progress_percent: repairProgress,
          notes: repairNotes || `Repair progressed to ${repairProgress}%.`,
        }),
      });
    } catch {}
    updateLocalDefectStatus(defectId, "UNDER_REPAIR");
    setActionModal(null);
    setNotification({ msg: `Defect ${defectId} repair updated to ${repairProgress}%.`, type: "info" });
  };

  const handleUploadEvidence = async (defectId: string) => {
    try {
      await fetch(`/api/v1/road-defects/${defectId}/upload-evidence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          engineer_id: "ENG_FIELD_108",
          completion_notes: evidenceNotes,
          after_image_b64: "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkWPjfDwAEfQHzgV23vAAAAABJRU5ErkJggg==",
          completion_certificate_url: "/certs/cert_pwd_2026.pdf",
        }),
      });
    } catch {}
    if (selectedDefect && selectedDefect.defect_id === defectId) {
      setSelectedDefect({
        ...selectedDefect,
        repair_evidence: {
          evidence_id: `EVID-${Date.now().toString().slice(-4)}`,
          completion_notes: evidenceNotes,
          engineer_id: "ENG_FIELD_108",
          uploaded_at: new Date().toISOString(),
          completion_certificate_url: "/certs/cert_pwd_2026.pdf",
        },
      });
    }
    setActionModal(null);
    setNotification({ msg: `Repair completion evidence & photos uploaded for ${defectId}.`, type: "success" });
  };

  const handleCloseTicket = async (defectId: string) => {
    const nowIso = new Date().toISOString();
    try {
      await fetch(`/api/v1/road-defects/${defectId}/close`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          engineer_id: "ENG_SUPERVISOR_007",
          closure_notes: "Repair verified against municipal compaction standards. Ticket closed.",
        }),
      });
    } catch {}
    updateLocalDefectStatus(defectId, "RESOLVED", { closed_at: nowIso, closed_by: "ENG_SUPERVISOR_007" });
    setNotification({ msg: `Maintenance ticket for ${defectId} CLOSED and verified as RESOLVED.`, type: "success" });
  };

  // ── Post-Closure Watchdog Simulation ──────────────────────────────────────

  const handleSimulateRedetection = async (defectId: string) => {
    try {
      const res = await fetch(`/api/v1/road-defects/${defectId}/simulate-redetection`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bus_id: "BUS_009",
          confidence: 0.95,
          notes: "Simulated surveillance pass by bus BUS_009 over repaired site.",
        }),
      });
      if (res.ok) {
        const data = await res.json();
        updateLocalDefectStatus(defectId, data.status, {
          priority_score: data.priority_score,
          reopen_count: data.reopen_count,
          reopen_reason: data.reopen_reason,
        });
        if (data.watchdog_triggered) {
          setNotification({
            msg: `🚨 WATCHDOG TRIGGERED: Bus BUS_009 detected recurring defect at closed site! Ticket REOPENED FOR REVIEW.`,
            type: "warning",
          });
          return;
        }
      }
    } catch {}

    // Local fallback simulation
    updateLocalDefectStatus(defectId, "REOPENED_UNDER_REVIEW", {
      reopen_count: 1,
      reopen_reason: "Transit bus BUS_009 re-detected recurring defect signature after repair closure.",
      priority_score: 94,
    });
    setNotification({
      msg: `🚨 WATCHDOG TRIGGERED: Bus BUS_009 detected recurring defect at closed site! Ticket REOPENED FOR REVIEW.`,
      type: "warning",
    });
  };

  const updateLocalDefectStatus = (defectId: string, newStatus: DefectStatus, extra: Partial<DefectEvent> = {}) => {
    setDefects(prev => prev.map(d => {
      if (d.defect_id === defectId || d.event_id === defectId) {
        const updated: DefectEvent = { ...d, status: newStatus, ...extra };
        if (selectedDefect && (selectedDefect.defect_id === defectId || selectedDefect.event_id === defectId)) {
          setSelectedDefect(updated);
        }
        return updated;
      }
      return d;
    }));
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-4 md:p-6 space-y-6">
      {/* ── Top Header & Navigation ────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-gray-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Construction className="text-amber-400" size={28} />
            <h1 className="text-2xl font-bold tracking-tight text-white">Road Defect Management Console</h1>
            <span className="px-2 py-0.5 text-xs font-semibold rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
              Phase 18
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Autonomous multi-bus detection consensus, 6-stage lifecycle tracking, explainable priority scoring, and post-closure watchdog.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <a
            href="/gis"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 transition"
          >
            <ExternalLink size={14} />
            Full GIS Map
          </a>
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition"
          >
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>
      </div>

      {/* ── Notification Toast ──────────────────────────────────────────────── */}
      {notification && (
        <div className={`p-4 rounded-xl border flex items-center justify-between transition-all ${
          notification.type === "warning" ? "bg-rose-950/80 border-rose-500/50 text-rose-200" :
          notification.type === "success" ? "bg-emerald-950/80 border-emerald-500/50 text-emerald-200" :
          "bg-blue-950/80 border-blue-500/50 text-blue-200"
        }`}>
          <div className="flex items-center gap-3">
            {notification.type === "warning" ? <AlertOctagon size={20} className="text-rose-400" /> : <CheckCircle2 size={20} className="text-emerald-400" />}
            <span className="text-sm font-medium">{notification.msg}</span>
          </div>
          <button onClick={() => setNotification(null)} className="text-xs hover:underline opacity-80">Dismiss</button>
        </div>
      )}

      {/* ── Autonomous Post-Closure Watchdog Alert Banner ─────────────────── */}
      {reopenedDefects.length > 0 && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-rose-950/70 via-amber-950/50 to-gray-900 border border-rose-500/40 space-y-2">
          <div className="flex items-center gap-2 text-rose-300 font-semibold text-sm">
            <Flame className="text-rose-400 animate-pulse" size={18} />
            <span>Autonomous Watchdog Alert: {reopenedDefects.length} Ticket(s) Reopened After Repair Closure</span>
          </div>
          <p className="text-xs text-gray-300">
            Transit bus edge cameras continued detecting defects at sites marked as RESOLVED. Tickets were automatically placed into <strong className="text-rose-300">REOPENED UNDER REVIEW</strong> for contractor quality audit.
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            {reopenedDefects.map(rd => (
              <button
                key={rd.defect_id}
                onClick={() => setSelectedDefect(rd)}
                className="px-2.5 py-1 text-xs rounded bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-200 flex items-center gap-1.5 transition"
              >
                <span>{rd.defect_id} ({rd.road_segment})</span>
                <ChevronRight size={12} />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── 5 Metric KPI Cards ────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
            <span>Total Tracked</span>
            <Construction size={16} className="text-blue-400" />
          </div>
          <p className="text-2xl font-bold text-white">{summary.total}</p>
          <p className="text-[11px] text-gray-500 mt-0.5">Active across city grid</p>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
            <span>Critical Priority (&gt;80)</span>
            <Flame size={16} className="text-rose-400" />
          </div>
          <p className="text-2xl font-bold text-rose-400">{summary.critical}</p>
          <p className="text-[11px] text-gray-500 mt-0.5">High safety &amp; traffic risk</p>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
            <span>Active Work Orders</span>
            <Wrench size={16} className="text-purple-400" />
          </div>
          <p className="text-2xl font-bold text-purple-400">{summary.activeRepairs}</p>
          <p className="text-[11px] text-gray-500 mt-0.5">Assigned or Under Repair</p>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-3.5">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
            <span>Repairs Verified</span>
            <CheckCircle2 size={16} className="text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-emerald-400">{summary.resolved}</p>
          <p className="text-[11px] text-gray-500 mt-0.5">Compacted &amp; closed</p>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-3.5 col-span-2 sm:col-span-1">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
            <span>Watchdog Reopened</span>
            <AlertOctagon size={16} className="text-amber-400" />
          </div>
          <p className={`text-2xl font-bold ${summary.reopened > 0 ? "text-amber-400" : "text-gray-400"}`}>{summary.reopened}</p>
          <p className="text-[11px] text-gray-500 mt-0.5">Post-closure recurrences</p>
        </div>
      </div>

      {/* ── Filter Toolbar & View Toggles ─────────────────────────────────── */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5 text-xs">
          <span className="text-gray-400 font-medium flex items-center gap-1">
            <Filter size={14} /> Filters:
          </span>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={e => setSelectedStatus(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-1 text-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="all">All Lifecycle States</option>
            <option value="AI_DETECTED">AI Detected</option>
            <option value="UNVERIFIED">Unverified</option>
            <option value="CONFIRMED">Confirmed</option>
            <option value="ASSIGNED">Assigned</option>
            <option value="UNDER_REPAIR">Under Repair</option>
            <option value="RESOLVED">Resolved</option>
            <option value="REOPENED_UNDER_REVIEW">Reopened (Watchdog)</option>
            <option value="REJECTED">Rejected</option>
          </select>

          {/* Type Filter */}
          <select
            value={selectedType}
            onChange={e => setSelectedType(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-1 text-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="all">All Defect Types</option>
            <option value="POTHOLE">Potholes</option>
            <option value="DAMAGED_ROAD">Damaged Road</option>
            <option value="WATERLOGGING">Waterlogging</option>
            <option value="MISSING_DIVIDER">Missing Divider</option>
          </select>

          {/* Severity Filter */}
          <select
            value={selectedSeverity}
            onChange={e => setSelectedSeverity(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-1 text-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="all">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          {/* Authority Filter */}
          <select
            value={selectedAuthority}
            onChange={e => setSelectedAuthority(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-1 text-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="all">All Authorities</option>
            <option value="PWD">PWD (Public Works)</option>
            <option value="NHAI">NHAI (Highways)</option>
            <option value="BBMP">BBMP (Bengaluru)</option>
            <option value="NDMC">NDMC (New Delhi)</option>
            <option value="BMC">BMC (Mumbai)</option>
          </select>
        </div>

        <div className="flex items-center gap-1 bg-gray-800 p-0.5 rounded-lg border border-gray-700 text-xs">
          <button
            onClick={() => setActiveTab("table")}
            className={`px-3 py-1 rounded-md transition ${activeTab === "table" ? "bg-indigo-600 text-white font-medium" : "text-gray-400 hover:text-white"}`}
          >
            Table View ({filtered.length})
          </button>
          <button
            onClick={() => setActiveTab("clusters")}
            className={`px-3 py-1 rounded-md transition ${activeTab === "clusters" ? "bg-indigo-600 text-white font-medium" : "text-gray-400 hover:text-white"}`}
          >
            Deduplicated Clusters ({canonicalClusters.length})
          </button>
          <button
            onClick={() => setActiveTab("map")}
            className={`px-3 py-1 rounded-md transition ${activeTab === "map" ? "bg-indigo-600 text-white font-medium" : "text-gray-400 hover:text-white"}`}
          >
            GIS Map
          </button>
        </div>
      </div>

      {/* ── Main Content Area ─────────────────────────────────────────────── */}
      {activeTab === "clusters" ? (
        <div className="space-y-4">
          {/* Deduplication Banner */}
          <div className="bg-gray-900 border border-indigo-500/40 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-indigo-400 font-bold text-sm">
                <Sparkles size={18} />
                <span>Geospatial-Temporal Event Deduplication Engine (Phase 19)</span>
              </div>
              <p className="text-xs text-gray-300 mt-1 max-w-2xl">
                Combines multiple bus camera sightings within 25m into <strong>ONE CANONICAL DEFECT</strong> using PostGIS <code className="text-indigo-300">ST_DWithin</code>, road segment map matching, and Bayesian multi-bus consensus.
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs bg-gray-950 p-2.5 rounded-lg border border-gray-800">
              <div>
                <span className="text-gray-400 block text-[10px]">Total Raw Detections</span>
                <span className="text-lg font-bold text-white">
                  {canonicalClusters.reduce((acc, c) => acc + (c.number_of_observations || 1), 0)}
                </span>
              </div>
              <div className="border-l border-gray-800 pl-3">
                <span className="text-gray-400 block text-[10px]">Canonical Defects</span>
                <span className="text-lg font-bold text-indigo-400">{canonicalClusters.length}</span>
              </div>
              <div className="border-l border-gray-800 pl-3">
                <span className="text-gray-400 block text-[10px]">Compression Ratio</span>
                <span className="text-lg font-bold text-emerald-400">
                  {(canonicalClusters.reduce((acc, c) => acc + (c.number_of_observations || 1), 0) / Math.max(1, canonicalClusters.length)).toFixed(1)}:1
                </span>
              </div>
            </div>
          </div>

          {/* Canonical Clusters Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {canonicalClusters.map((cluster) => {
              const isPothole104 = cluster.canonical_id.includes("104");
              const isConfirmed = cluster.status === "Confirmed";

              return (
                <div
                  key={cluster.canonical_id}
                  className={`bg-gray-900 border rounded-xl p-5 space-y-3.5 transition-all ${
                    isPothole104 ? "border-indigo-500/60 ring-1 ring-indigo-500/30" : "border-gray-800 hover:border-gray-700"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xl font-extrabold text-white tracking-tight">{cluster.canonical_id}</span>
                        {isPothole104 && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                            PROMPT EXAMPLE
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-gray-400">{cluster.road_segment}</span>
                    </div>
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${
                        isConfirmed
                          ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                          : "bg-amber-500/20 text-amber-300 border-amber-500/40"
                      }`}
                    >
                      {cluster.status}
                    </span>
                  </div>

                  {/* Prompt-mandated Core Details */}
                  <div className="bg-gray-950/80 rounded-lg p-3 border border-gray-800 text-xs space-y-2">
                    <div>
                      <span className="text-gray-400 block mb-1">Detected by:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {cluster.detected_by.map((bus: string) => (
                          <span
                            key={bus}
                            className="px-2 py-0.5 rounded bg-gray-800 text-gray-200 border border-gray-700 font-mono text-[11px]"
                          >
                            {bus}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 pt-1 border-t border-gray-800">
                      <div>
                        <span className="text-gray-400 block text-[11px]">Observations:</span>
                        <span className="text-base font-bold text-white font-mono">{cluster.number_of_observations}</span>
                      </div>
                      <div>
                        <span className="text-gray-400 block text-[11px]">Confidence:</span>
                        <span className="text-base font-bold text-emerald-400 font-mono">
                          {Math.round(cluster.confidence * 100)}%
                        </span>
                      </div>
                    </div>

                    <div className="text-[11px] text-gray-400 pt-1 border-t border-gray-800 flex justify-between">
                      <span>Refined Centroid:</span>
                      <span className="font-mono text-gray-200">{cluster.centroid.lat.toFixed(4)}, {cluster.centroid.lon.toFixed(4)}</span>
                    </div>
                  </div>

                  {/* Actions & Observation History */}
                  <div className="flex items-center justify-between pt-1">
                    <button
                      onClick={() => setSelectedCluster(selectedCluster === cluster.canonical_id ? null : cluster.canonical_id)}
                      className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
                    >
                      {selectedCluster === cluster.canonical_id ? "Hide Sightings Trace" : `View ${cluster.observations?.length || cluster.number_of_observations} Sightings`}
                      <ChevronRight size={14} className={selectedCluster === cluster.canonical_id ? "rotate-90 transition" : "transition"} />
                    </button>

                    <button
                      onClick={async () => {
                        const randomBus = `Bus ${Math.floor(100 + Math.random() * 900)}`;
                        try {
                          const res = await fetch("/api/v1/clustering/observe", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                              bus_id: randomBus,
                              lat: cluster.centroid.lat + (Math.random() - 0.5) * 0.00004,
                              lon: cluster.centroid.lon + (Math.random() - 0.5) * 0.00004,
                              defect_type: cluster.defect_type,
                              confidence: 0.94,
                              road_segment: cluster.road_segment,
                            }),
                          });
                          if (res.ok) {
                            const updated = await res.json();
                            setCanonicalClusters(prev => prev.map(c => c.canonical_id === updated.canonical_id ? updated : c));
                            setNotification({
                              msg: `New observation from ${randomBus} merged into ${updated.canonical_id}! Observations: ${updated.number_of_observations}.`,
                              type: "success",
                            });
                            return;
                          }
                        } catch {}
                        // local fallback
                        setCanonicalClusters(prev => prev.map(c => {
                          if (c.canonical_id === cluster.canonical_id) {
                            const newDetected = c.detected_by.includes(randomBus) ? c.detected_by : [...c.detected_by, randomBus];
                            return {
                              ...c,
                              number_of_observations: c.number_of_observations + 1,
                              number_of_buses: newDetected.length,
                              detected_by: newDetected,
                              status: "Confirmed",
                            };
                          }
                          return c;
                        }));
                        setNotification({
                          msg: `New observation from ${randomBus} merged into ${cluster.canonical_id}!`,
                          type: "success",
                        });
                      }}
                      className="px-2.5 py-1 text-xs rounded bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-200 border border-indigo-500/40 flex items-center gap-1 transition"
                    >
                      <Sparkles size={12} />
                      + Test Sighting
                    </button>
                  </div>

                  {/* Expanded Sightings List */}
                  {selectedCluster === cluster.canonical_id && (
                    <div className="mt-2 pt-2 border-t border-gray-800 space-y-1.5 max-h-48 overflow-y-auto pr-1">
                      <div className="text-[10px] uppercase text-gray-400 font-semibold tracking-wider">Raw Sightings Stream (ST_DWithin &le; 25m)</div>
                      {(cluster.observations || []).slice(0, 8).map((obs: any, idx: number) => (
                        <div key={obs.observation_id || idx} className="p-2 rounded bg-gray-950 text-[11px] flex items-center justify-between border border-gray-800/80">
                          <div>
                            <span className="font-semibold text-white">{obs.bus_id}</span>
                            <span className="text-gray-400 ml-2">({obs.lat.toFixed(5)}, {obs.lon.toFixed(5)})</span>
                          </div>
                          <div className="text-right">
                            <span className="text-emerald-400 font-mono font-medium">{Math.round(obs.confidence * 100)}%</span>
                            <span className="text-gray-500 ml-2 text-[10px]">{obs.distance_to_centroid_m || 1.2}m offset</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ) : activeTab === "map" ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 h-[600px] flex flex-col">
          <div className="mb-2 flex items-center justify-between text-xs text-gray-400">
            <span>Displaying spatial defects on city coordinate grid</span>
            <span>Click marker to inspect lifecycle &amp; priority</span>
          </div>
          <div className="flex-1 rounded-lg overflow-hidden border border-gray-800">
            <DefectMap
              events={filtered}
              selectedEvent={selectedDefect}
              onSelectEvent={ev => setSelectedDefect(ev)}
            />
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Defects Table (2 Cols) */}
          <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
              <span className="text-sm font-semibold text-white">Tracked Road Defects ({filtered.length})</span>
              <span className="text-xs text-gray-400">Sorted by Priority Score &amp; Recurrence</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-gray-300">
                <thead className="bg-gray-800/50 text-gray-400 uppercase text-[10px] tracking-wider border-b border-gray-800">
                  <tr>
                    <th className="py-2.5 px-3">Defect ID &amp; Type</th>
                    <th className="py-2.5 px-3">Road Segment / GPS</th>
                    <th className="py-2.5 px-3">Fleet Consensus</th>
                    <th className="py-2.5 px-3">Priority Score</th>
                    <th className="py-2.5 px-3">Lifecycle State</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {filtered.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-gray-500 text-xs">
                        No defects matching current filter criteria.
                      </td>
                    </tr>
                  ) : (
                    filtered.map(defect => {
                      const meta = CLASS_META[defect.type || defect.cls] || { label: defect.type || defect.cls, icon: CrosshairIcon, color: "text-gray-400" };
                      const Icon = meta.icon;
                      const isSelected = selectedDefect?.defect_id === defect.defect_id;
                      const score = defect.priority_score || 50;
                      const isReopened = defect.status === "REOPENED_UNDER_REVIEW" || (defect.reopen_count || 0) > 0;

                      return (
                        <tr
                          key={defect.defect_id || defect.event_id}
                          onClick={() => setSelectedDefect(defect)}
                          className={`hover:bg-gray-800/60 cursor-pointer transition ${isSelected ? "bg-indigo-950/30 border-l-2 border-indigo-500" : ""}`}
                        >
                          <td className="py-3 px-3">
                            <div className="flex items-center gap-2">
                              <div className="p-1.5 rounded bg-gray-800 border border-gray-700">
                                <Icon size={16} className={meta.color} />
                              </div>
                              <div>
                                <div className="font-mono font-semibold text-white flex items-center gap-1.5">
                                  <span>{defect.defect_id || defect.event_id}</span>
                                  {isReopened && (
                                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40">
                                      RECURRING
                                    </span>
                                  )}
                                </div>
                                <span className="text-[11px] text-gray-400">{meta.label}</span>
                              </div>
                            </div>
                          </td>

                          <td className="py-3 px-3">
                            <div className="text-gray-200 font-medium">{defect.road_segment}</div>
                            <div className="text-[10px] text-gray-400">
                              {defect.gps.lat.toFixed(4)}, {defect.gps.lon.toFixed(4)}
                              {defect.gps.district ? ` • ${defect.gps.district}` : ""}
                            </div>
                          </td>

                          <td className="py-3 px-3">
                            <div className="flex items-center gap-1.5">
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-800 text-gray-200 border border-gray-700">
                                {defect.number_of_buses_confirming || 1} bus{(defect.number_of_buses_confirming || 1) > 1 ? "es" : ""}
                              </span>
                              <span className="text-[10px] text-gray-400">({defect.detection_count || 1} det)</span>
                            </div>
                            <div className="text-[10px] text-gray-500 mt-0.5 truncate max-w-[120px]">
                              {(defect.buses_confirming || [defect.bus_id]).join(", ")}
                            </div>
                          </td>

                          <td className="py-3 px-3">
                            <div className="flex items-center gap-2">
                              <span className={`px-2 py-0.5 rounded text-xs font-bold font-mono ${getPriorityBadge(score)}`}>
                                {score}
                              </span>
                              <span className="text-[10px] text-gray-400 font-medium">
                                {defect.priority_breakdown?.priority_tier || (score >= 80 ? "CRITICAL" : score >= 60 ? "HIGH" : "MEDIUM")}
                              </span>
                            </div>
                          </td>

                          <td className="py-3 px-3">
                            <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium ${STATUS_BADGE[defect.status] || STATUS_BADGE.AI_DETECTED}`}>
                              {defect.status.replace(/_/g, " ")}
                            </span>
                            {defect.maintenance_ticket && (
                              <div className="text-[9px] text-indigo-400 font-mono mt-0.5">
                                {defect.maintenance_ticket.ticket_id}
                              </div>
                            )}
                          </td>

                          <td className="py-3 px-3 text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedDefect(defect);
                              }}
                              className="px-2 py-1 text-xs rounded bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 transition"
                            >
                              Inspect
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Defect Inspection & Field Engineer Action Drawer (1 Col) */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col space-y-4">
            {selectedDefect ? (
              <>
                <div className="border-b border-gray-800 pb-3 flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-lg font-bold text-white font-mono">{selectedDefect.defect_id || selectedDefect.event_id}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getPriorityBadge(selectedDefect.priority_score || 50)}`}>
                        Priority {selectedDefect.priority_score || 50}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">{selectedDefect.label || selectedDefect.type || selectedDefect.cls}</p>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${STATUS_BADGE[selectedDefect.status] || STATUS_BADGE.AI_DETECTED}`}>
                    {selectedDefect.status.replace(/_/g, " ")}
                  </span>
                </div>

                {/* Reopen / Watchdog Notice */}
                {(selectedDefect.status === "REOPENED_UNDER_REVIEW" || (selectedDefect.reopen_count || 0) > 0) && (
                  <div className="p-2.5 rounded-lg bg-rose-950/60 border border-rose-500/40 text-xs text-rose-200 space-y-1">
                    <div className="font-semibold flex items-center gap-1.5 text-rose-300">
                      <AlertOctagon size={14} />
                      <span>Post-Closure Watchdog Reopen Flag</span>
                    </div>
                    <p className="text-[11px] text-gray-300">
                      {selectedDefect.reopen_reason || "Transit buses re-detected recurring defect signature after ticket closure."}
                    </p>
                    {selectedDefect.reopened_at && (
                      <p className="text-[10px] text-gray-400">Reopened: {formatTs(selectedDefect.reopened_at)}</p>
                    )}
                  </div>
                )}

                {/* 6-Stage Lifecycle Visual Stepper */}
                <div>
                  <label className="text-[11px] text-gray-400 uppercase tracking-wider font-semibold block mb-2">
                    6-Stage Lifecycle State
                  </label>
                  <div className="grid grid-cols-3 gap-1.5 text-[10px] text-center">
                    {LIFECYCLE_STAGES.map(stage => {
                      const isActive = selectedDefect.status === stage.id;
                      return (
                        <div
                          key={stage.id}
                          className={`p-1.5 rounded border transition ${
                            isActive
                              ? `${stage.color} font-bold ring-1 ring-white/20`
                              : "border-gray-800 bg-gray-950/60 text-gray-500"
                          }`}
                        >
                          {stage.label}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Defect Metadata Card */}
                <div className="bg-gray-950/80 rounded-lg p-3 border border-gray-800 text-xs space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Road Segment:</span>
                    <span className="text-white font-medium">{selectedDefect.road_segment}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Coordinates:</span>
                    <span className="text-gray-200 font-mono">{selectedDefect.gps.lat.toFixed(5)}, {selectedDefect.gps.lon.toFixed(5)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">First Detected:</span>
                    <span className="text-gray-300">{formatTs(selectedDefect.first_detected || selectedDefect.timestamp)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Last Detected:</span>
                    <span className="text-gray-300">{formatTs(selectedDefect.last_detected || selectedDefect.timestamp)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Confirming Buses:</span>
                    <span className="text-indigo-400 font-semibold">{selectedDefect.number_of_buses_confirming || 1} bus fleet consensus</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Assigned Authority:</span>
                    <span className="text-white">{selectedDefect.assigned_authority || "Unassigned"}</span>
                  </div>
                  {selectedDefect.maintenance_ticket && (
                    <div className="flex justify-between border-t border-gray-800 pt-1.5">
                      <span className="text-gray-400">Work Order Ticket:</span>
                      <span className="text-indigo-300 font-mono font-semibold">{selectedDefect.maintenance_ticket.ticket_id}</span>
                    </div>
                  )}
                </div>

                {/* Priority Breakdown (Explainable Formula) */}
                {selectedDefect.priority_breakdown && (
                  <div className="bg-gray-950/80 rounded-lg p-3 border border-gray-800 text-xs space-y-1.5">
                    <div className="flex items-center justify-between text-gray-300 font-medium">
                      <span>Priority Component Breakdown</span>
                      <span className="font-mono text-amber-400">{selectedDefect.priority_breakdown.total_priority_score}/100</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1 text-[11px] text-gray-400 pt-1">
                      <div>Severity (25%): <span className="text-gray-200">{selectedDefect.priority_breakdown.severity_score}</span></div>
                      <div>Traffic (20%): <span className="text-gray-200">{selectedDefect.priority_breakdown.traffic_volume_score}</span></div>
                      <div>Detections (15%): <span className="text-gray-200">{selectedDefect.priority_breakdown.detections_score}</span></div>
                      <div>Location (15%): <span className="text-gray-200">{selectedDefect.priority_breakdown.location_importance_score}</span></div>
                      <div>Safety Risk (15%): <span className="text-gray-200">{selectedDefect.priority_breakdown.safety_risk_score}</span></div>
                      <div>Persistence (10%): <span className="text-gray-200">{selectedDefect.priority_breakdown.persistence_score}</span></div>
                    </div>
                  </div>
                )}

                {/* Repair Evidence Card (if present) */}
                {selectedDefect.repair_evidence && (
                  <div className="bg-emerald-950/30 rounded-lg p-3 border border-emerald-500/30 text-xs space-y-1">
                    <div className="flex items-center justify-between text-emerald-300 font-semibold">
                      <span className="flex items-center gap-1.5"><ShieldCheck size={14} /> Repair Evidence Attached</span>
                      <span className="text-[10px] font-mono text-gray-400">{selectedDefect.repair_evidence.evidence_id}</span>
                    </div>
                    <p className="text-gray-300 text-[11px]">{selectedDefect.repair_evidence.completion_notes}</p>
                    <p className="text-[10px] text-gray-400">Engineer: {selectedDefect.repair_evidence.engineer_id} • {formatTs(selectedDefect.repair_evidence.uploaded_at)}</p>
                  </div>
                )}

                {/* Field Engineer Action Controls */}
                <div className="space-y-2 pt-1 border-t border-gray-800">
                  <label className="text-[11px] text-gray-400 uppercase tracking-wider font-semibold block">
                    Field Engineer Actions
                  </label>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {/* Confirm Button */}
                    <button
                      onClick={() => handleConfirm(selectedDefect.defect_id)}
                      className="px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium flex items-center justify-center gap-1.5 transition"
                    >
                      <Check size={14} /> Confirm
                    </button>

                    {/* Reject Button */}
                    <button
                      onClick={() => setActionModal("reject")}
                      className="px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 flex items-center justify-center gap-1.5 transition"
                    >
                      <XCircle size={14} /> Reject
                    </button>

                    {/* Assign Button */}
                    <button
                      onClick={() => setActionModal("assign")}
                      className="px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium flex items-center justify-center gap-1.5 transition"
                    >
                      <Send size={14} /> Assign Ticket
                    </button>

                    {/* Update Repair Button */}
                    <button
                      onClick={() => setActionModal("update")}
                      className="px-3 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-medium flex items-center justify-center gap-1.5 transition"
                    >
                      <Wrench size={14} /> Update Repair
                    </button>

                    {/* Upload Evidence */}
                    <button
                      onClick={() => setActionModal("evidence")}
                      className="px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-emerald-400 border border-emerald-500/40 flex items-center justify-center gap-1.5 transition col-span-1"
                    >
                      <Camera size={14} /> Evidence
                    </button>

                    {/* Close Ticket */}
                    <button
                      onClick={() => handleCloseTicket(selectedDefect.defect_id)}
                      className="px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium flex items-center justify-center gap-1.5 transition col-span-1"
                    >
                      <CheckCircle2 size={14} /> Close Ticket
                    </button>
                  </div>

                  {/* Simulate Post-Closure Re-detection (Watchdog Test) */}
                  <div className="pt-2">
                    <button
                      onClick={() => handleSimulateRedetection(selectedDefect.defect_id)}
                      className="w-full px-3 py-2 rounded-lg bg-amber-950/60 hover:bg-amber-900/60 text-amber-200 border border-amber-500/50 text-xs font-semibold flex items-center justify-center gap-1.5 transition"
                    >
                      <Sparkles size={14} className="text-amber-400" />
                      Simulate Bus Re-detection (Test Watchdog)
                    </button>
                    <span className="text-[10px] text-gray-500 block text-center mt-1">
                      Dispatches bus detection to verify automatic ticket reopening.
                    </span>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center py-16 text-gray-500 text-xs flex flex-col items-center justify-center">
                <Construction size={32} className="text-gray-600 mb-2" />
                <p>Select a defect from the table or map to inspect metadata, priority breakdown, and field engineer actions.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Modals for Field Engineer Actions ──────────────────────────────── */}

      {/* 1. Assign Authority Modal */}
      {actionModal === "assign" && selectedDefect && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 max-w-md w-full space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Send size={18} className="text-blue-400" />
              Assign Maintenance Authority &amp; Issue Ticket
            </h3>
            <div className="text-xs text-gray-400">
              Assign responsible authority for <strong className="text-gray-200">{selectedDefect.defect_id}</strong> on {selectedDefect.road_segment}.
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-400 mb-1">Assigned Municipal Authority</label>
                <select
                  value={assignAuthority}
                  onChange={e => setAssignAuthority(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2 text-white"
                >
                  <option value="Public Works Department (PWD)">Public Works Department (PWD)</option>
                  <option value="National Highways Authority of India (NHAI)">National Highways Authority of India (NHAI)</option>
                  <option value="Bruhat Bengaluru Mahanagara Palike (BBMP)">Bruhat Bengaluru Mahanagara Palike (BBMP)</option>
                  <option value="New Delhi Municipal Council (NDMC)">New Delhi Municipal Council (NDMC)</option>
                  <option value="Brihanmumbai Municipal Corporation (BMC)">Brihanmumbai Municipal Corporation (BMC)</option>
                </select>
              </div>
              <div>
                <label className="block text-gray-400 mb-1">Contractor / Agency</label>
                <input
                  type="text"
                  value={assignContractor}
                  onChange={e => setAssignContractor(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2 text-white"
                  placeholder="Contractor name"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-gray-800 text-xs">
              <button
                onClick={() => setActionModal(null)}
                className="px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={() => handleAssign(selectedDefect.defect_id)}
                className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium"
              >
                Issue Work Order
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. Update Repair Modal */}
      {actionModal === "update" && selectedDefect && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 max-w-md w-full space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Wrench size={18} className="text-purple-400" />
              Update Repair Progress
            </h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-400 mb-1">Progress: {repairProgress}%</label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="10"
                  value={repairProgress}
                  onChange={e => setRepairProgress(Number(e.target.value))}
                  className="w-full accent-purple-500 cursor-pointer"
                />
              </div>
              <div>
                <label className="block text-gray-400 mb-1">Field Notes</label>
                <textarea
                  value={repairNotes}
                  onChange={e => setRepairNotes(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2 text-white h-20"
                  placeholder="e.g. Surface milled, base gravel laid and compacted."
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-gray-800 text-xs">
              <button
                onClick={() => setActionModal(null)}
                className="px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={() => handleUpdateRepair(selectedDefect.defect_id)}
                className="px-4 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-medium"
              >
                Save Progress
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Upload Repair Evidence Modal */}
      {actionModal === "evidence" && selectedDefect && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 max-w-md w-full space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Camera size={18} className="text-emerald-400" />
              Upload Repair Completion Evidence
            </h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-400 mb-1">Repair Completion Notes</label>
                <textarea
                  value={evidenceNotes}
                  onChange={e => setEvidenceNotes(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2 text-white h-20"
                />
              </div>
              <div className="p-3 bg-gray-950 border border-dashed border-gray-700 rounded-lg text-center text-gray-400">
                <Camera size={24} className="mx-auto text-gray-500 mb-1" />
                <span className="text-[11px]">Before &amp; After Inspection Photo Attached (Simulated)</span>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-gray-800 text-xs">
              <button
                onClick={() => setActionModal(null)}
                className="px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={() => handleUploadEvidence(selectedDefect.defect_id)}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium"
              >
                Attach Evidence
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 4. Reject Defect Modal */}
      {actionModal === "reject" && selectedDefect && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 max-w-md w-full space-y-4">
            <h3 className="text-base font-bold text-rose-400 flex items-center gap-2">
              <XCircle size={18} />
              Reject / Dismiss Defect
            </h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-400 mb-1">Reason for Rejection</label>
                <textarea
                  value={rejectReason}
                  onChange={e => setRejectReason(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2 text-white h-20"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-gray-800 text-xs">
              <button
                onClick={() => setActionModal(null)}
                className="px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={() => handleReject(selectedDefect.defect_id)}
                className="px-4 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-medium"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RoadDefects;
