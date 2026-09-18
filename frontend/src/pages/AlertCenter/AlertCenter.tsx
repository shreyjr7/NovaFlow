import { EventDetailModal, EventDetailData } from "../../components/EventDetailModal";
// src/pages/AlertCenter/AlertCenter.tsx
// Phase 24 — Centralized Alert Center with Real-Time WebSockets

import React, { useState, useEffect, useRef } from "react";
import {
  Bell, AlertTriangle, ShieldAlert, CheckCircle2,
  Clock, MapPin, Bus, Check, X, Filter, Radio,
  ArrowUpRight, AlertOctagon, RefreshCw, UserPlus,
  Video, Camera, Cpu, Waves, ShieldCheck
} from "lucide-react";

export interface AuditAction {
  timestamp: string;
  action: string;
  actor: string;
  notes?: string;
}

export interface AlertCardData {
  alert_id: string;
  type: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  location: string;
  lat: number;
  lon: number;
  road_segment?: string;
  bus: string;
  timestamp: string;
  confidence: number;
  evidence: string;
  evidence_snapshot_url?: string;
  evidence_video_clip?: string;
  status: "NEW" | "ACKNOWLEDGED" | "VERIFIED" | "ESCALATED" | "ASSIGNED" | "RESOLVED";
  assigned_to?: string;
  audit_trail: AuditAction[];
}

export const AlertCenter: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertCardData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [typeFilter, setTypeFilter] = useState<string>("ALL");
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [detailEvent, setDetailEvent] = useState<EventDetailData | null>(null);
  const [actionModal, setActionModal] = useState<{
    alertId: string;
    action: "Assign" | "Resolve";
  } | null>(null);
  const [modalInput, setModalInput] = useState<string>("");
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

  const fetchAlerts = async () => {
    try {
      const res = await fetch("/api/v1/alerts");
      if (res.ok) {
        const data = await res.json();
        setAlerts(data);
      }
    } catch (err) {
      console.error("Error fetching alerts:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();

    // WebSocket Connection
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/v1/alerts/ws`;

    try {
      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        setWsConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.event === "ALERT_CREATED") {
            setAlerts((prev) => [payload.alert, ...prev]);
            setToastMsg(`Live Alert: ${payload.alert.type} (${payload.alert.severity}) on ${payload.alert.bus}`);
          } else if (payload.event === "ALERT_UPDATED") {
            setAlerts((prev) =>
              prev.map((a) => (a.alert_id === payload.alert.alert_id ? payload.alert : a))
            );
          }
        } catch (e) {
          // ignore non-json ping/pong
        }
      };

      socket.onclose = () => {
        setWsConnected(false);
      };

      socket.onerror = () => {
        setWsConnected(false);
      };
    } catch (err) {
      console.warn("WebSocket could not be established; using HTTP polling fallback.");
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

    const toDetailData = (card: AlertCardData): EventDetailData => ({
    id: card.alert_id,
    type: card.type,
    severity: card.severity,
    status: card.status,
    gps: { lat: card.lat, lon: card.lon },
    road: card.road_segment || "Central City Corridor",
    area: card.location,
    confidence: card.confidence,
    detection_time: card.timestamp,
    source_bus: card.bus,
    plate_number: "UP65AB1234",
    video_clip_url: card.evidence_video_clip,
    image_urls: card.evidence_snapshot_url ? [card.evidence_snapshot_url] : [],
    evidence_description: card.evidence,
  });

const handleAction = async (alertId: string, action: "Acknowledge" | "Verify" | "Escalate" | "Assign" | "Resolve", extraParam?: string) => {
    try {
      const body: any = {
        action,
        actor: "Control Room Lead",
        notes: extraParam || `Action ${action} executed.`,
      };
      if (action === "Assign" && extraParam) {
        body.assigned_to = extraParam;
      }

      const res = await fetch(`/api/v1/alerts/${alertId}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        const updated = await res.json();
        setAlerts((prev) => prev.map((a) => (a.alert_id === alertId ? updated : a)));
        setToastMsg(`Alert ${alertId} status updated to ${updated.status}`);
        setTimeout(() => setToastMsg(null), 3500);
      }
    } catch (err) {
      console.error(`Failed to execute ${action}:`, err);
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    const matchesSev = severityFilter === "ALL" || a.severity === severityFilter;
    const matchesType = typeFilter === "ALL" || a.type === typeFilter;
    return matchesSev && matchesType;
  });

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return "bg-rose-500/20 text-rose-300 border-rose-500/40";
      case "HIGH":
        return "bg-orange-500/20 text-orange-300 border-orange-500/40";
      case "MEDIUM":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40";
      default:
        return "bg-slate-700 text-slate-300 border-slate-600";
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "Possible Incident":
        return <ShieldAlert size={16} className="text-rose-400" />;
      case "Severe Congestion":
        return <AlertTriangle size={16} className="text-orange-400" />;
      case "Pedestrian Risk":
        return <AlertOctagon size={16} className="text-rose-400" />;
      case "Major Waterlogging":
        return <Waves size={16} className="text-cyan-400" />;
      case "Camera Failure":
        return <Camera size={16} className="text-amber-400" />;
      case "Edge Device Failure":
        return <Cpu size={16} className="text-purple-400" />;
      default:
        return <AlertTriangle size={16} className="text-amber-400" />;
    }
  };

  const criticalCount = alerts.filter((a) => a.severity === "CRITICAL").length;
  const highCount = alerts.filter((a) => a.severity === "HIGH").length;
  const unresolvedCount = alerts.filter((a) => a.status !== "RESOLVED").length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Top Nav Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400">
              <Bell size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
                Centralized Alert Center
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                  Live Dispatch
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Live multi-tier alert stream powered by real-time WebSockets with 5-stage operational dispatch actions.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-semibold ${
              wsConnected
                ? "bg-emerald-950/40 text-emerald-300 border-emerald-500/40"
                : "bg-amber-950/40 text-amber-300 border-amber-500/40"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                wsConnected ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
              }`}
            />
            {wsConnected ? "LIVE WEBSOCKET STREAM ACTIVE" : "WEBSOCKET RECONNECTING (POLLING)"}
          </div>
          <button
            onClick={fetchAlerts}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs font-medium transition"
          >
            <RefreshCw size={13} />
            Refresh
          </button>
          <a
            href="/"
            className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
          >
            &larr; Main Hub
          </a>
        </div>
      </div>

      {/* Toast popup */}
      {toastMsg && (
        <div className="p-3 bg-rose-600 text-white text-sm rounded-lg flex items-center justify-between shadow-lg animate-fade-in">
          <span className="flex items-center gap-2 font-medium">
            <Radio size={16} className="animate-pulse" />
            {toastMsg}
          </span>
          <button onClick={() => setToastMsg(null)}>
            <X size={16} />
          </button>
        </div>
      )}

      {/* KPI Ticker */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs font-medium text-slate-400">Total Alerts Today</div>
          <div className="text-2xl font-bold text-white mt-1">{alerts.length}</div>
          <div className="text-xs text-slate-500 mt-1">Across entire transit network</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs font-medium text-slate-400">Critical Alerts</div>
          <div className="text-2xl font-bold text-rose-400 mt-1">{criticalCount}</div>
          <div className="text-xs text-rose-400/80 mt-1">Immediate intervention required</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs font-medium text-slate-400">High Priority</div>
          <div className="text-2xl font-bold text-orange-400 mt-1">{highCount}</div>
          <div className="text-xs text-orange-400/80 mt-1">Bottlenecks & Waterlogging</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs font-medium text-slate-400">Unresolved Queue</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">{unresolvedCount}</div>
          <div className="text-xs text-amber-400/80 mt-1">Under investigation / assigned</div>
        </div>
      </div>

      {/* Severity & Type Filter Strip */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/70 p-3 rounded-xl border border-slate-800">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-slate-400 font-medium mr-2 flex items-center gap-1">
            <Filter size={13} /> Severity:
          </span>
          {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                severityFilter === sev
                  ? "bg-slate-700 text-white shadow-sm border border-slate-600"
                  : "bg-slate-800/80 text-slate-400 hover:text-slate-200"
              }`}
            >
              {sev}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-slate-400 font-medium mr-2">Type:</span>
          {[
            { id: "ALL", label: "All Types" },
            { id: "Possible Incident", label: "Possible Incident" },
            { id: "Severe Congestion", label: "Congestion" },
            { id: "Pedestrian Risk", label: "Pedestrian Risk" },
            { id: "Major Waterlogging", label: "Waterlogging" },
            { id: "Camera Failure", label: "Camera Failure" },
            { id: "Edge Device Failure", label: "Edge Device Failure" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTypeFilter(t.id)}
              className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                typeFilter === t.id
                  ? "bg-indigo-600 text-white font-semibold"
                  : "bg-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Alert Cards Stream */}
      <div className="space-y-4">
        {filteredAlerts.map((card) => {
          const isCritical = card.severity === "CRITICAL";
          const isHigh = card.severity === "HIGH";

          return (
            <div
              key={card.alert_id}
              className={`p-5 rounded-xl border bg-slate-900/90 transition shadow-lg ${
                isCritical
                  ? "border-rose-500/50 shadow-rose-950/20"
                  : isHigh
                  ? "border-orange-500/40 shadow-orange-950/20"
                  : "border-slate-800"
              }`}
            >
              {/* Alert Card Header */}
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3 pb-3 border-b border-slate-800/80">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-slate-800 flex-shrink-0">
                    {getTypeIcon(card.type)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-base font-bold text-white">{card.type}</span>
                      <span className={`text-xs px-2.5 py-0.5 rounded border font-bold uppercase ${getSeverityBadge(card.severity)}`}>
                        {card.severity}
                      </span>
                      <span className="text-xs font-mono text-slate-500">{card.alert_id}</span>
                    </div>
                    <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                      <span className="flex items-center gap-1">
                        <MapPin size={12} className="text-slate-500" />
                        {card.location}
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1 font-mono text-indigo-400">
                        <Bus size={12} />
                        {card.bus}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="text-xs font-mono text-emerald-400 font-semibold">
                      {Math.round(card.confidence * 100)}% Confidence
                    </div>
                    <div className="text-xs text-slate-500 flex items-center gap-1">
                      <Clock size={11} />
                      {card.timestamp.slice(11, 19)} UTC
                    </div>
                  </div>
                  <span
                    className={`text-xs px-2.5 py-1 rounded font-semibold ${
                      card.status === "RESOLVED"
                        ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/30"
                        : card.status === "ASSIGNED"
                        ? "bg-blue-500/10 text-blue-300 border border-blue-500/30"
                        : card.status === "ESCALATED"
                        ? "bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse"
                        : "bg-slate-800 text-slate-300 border border-slate-700"
                    }`}
                  >
                    {card.status}
                  </span>
                </div>
              </div>

              {/* Alert Card Body: Evidence & Assigned Authority */}
              <div className="py-3.5 space-y-2.5">
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                    <Video size={13} className="text-indigo-400" />
                    Sensory Evidence & Diagnostic Data:
                  </div>
                  <p className="text-sm text-slate-200 leading-relaxed">
                    {card.evidence}
                  </p>
                </div>

                {card.assigned_to && (
                  <div className="text-xs text-blue-300 bg-blue-950/30 border border-blue-500/30 px-3 py-1.5 rounded flex items-center gap-2">
                    <UserPlus size={13} />
                    <span>Assigned To: <strong>{card.assigned_to}</strong></span>
                  </div>
                )}
              </div>

              {/* Alert Card Footer: Actions Toolbar */}
              <div className="pt-3 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3">
                <div className="text-xs text-slate-500">
                  Audit: {card.audit_trail.length} events recorded
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {/* Action 1: Acknowledge */}
                  {card.status === "NEW" && (
                    <button
                      onClick={() => handleAction(card.alert_id, "Acknowledge")}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 transition"
                    >
                      Acknowledge
                    </button>
                  )}

                  {/* Action 2: Verify */}
                  {card.status !== "VERIFIED" && card.status !== "RESOLVED" && (
                    <button
                      onClick={() => handleAction(card.alert_id, "Verify")}
                      className="px-3 py-1.5 rounded-lg bg-cyan-950 hover:bg-cyan-900 border border-cyan-500/40 text-xs font-semibold text-cyan-200 transition"
                    >
                      Verify
                    </button>
                  )}

                  {/* Action 3: Escalate */}
                  {card.status !== "ESCALATED" && card.status !== "RESOLVED" && (
                    <button
                      onClick={() => handleAction(card.alert_id, "Escalate")}
                      className="px-3 py-1.5 rounded-lg bg-rose-950 hover:bg-rose-900 border border-rose-500/40 text-xs font-semibold text-rose-200 transition"
                    >
                      Escalate
                    </button>
                  )}

                  {/* Action 4: Assign */}
                  {card.status !== "RESOLVED" && (
                    <button
                      onClick={() => setActionModal({ alertId: card.alert_id, action: "Assign" })}
                      className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition"
                    >
                      Assign
                    </button>
                  )}

                  {/* Action 5: Resolve */}
                  {card.status !== "RESOLVED" && (
                    <button
                      onClick={() => setActionModal({ alertId: card.alert_id, action: "Resolve" })}
                      className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition"
                    >
                      Resolve
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Action Modal for Assign / Resolve */}
      {actionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-3 sm:p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full max-h-[90vh] overflow-y-auto p-4 sm:p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-white">
                {actionModal.action === "Assign" ? "Assign Alert Authority" : "Resolve Fleet Alert"}
              </h3>
              <button onClick={() => setActionModal(null)} className="text-slate-400 hover:text-white">
                <X size={20} />
              </button>
            </div>
            <p className="text-xs text-slate-400">
              {actionModal.action === "Assign"
                ? "Enter the field response unit, depot bay, or municipal department name."
                : "Provide a resolution summary or corrective action confirmation."}
            </p>
            <input
              type="text"
              value={modalInput}
              onChange={(e) => setModalInput(e.target.value)}
              placeholder={actionModal.action === "Assign" ? "e.g. Field Team Delta-4" : "e.g. Site cleared, lanes reopened"}
              className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
            />
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setActionModal(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  handleAction(actionModal.alertId, actionModal.action, modalInput);
                  setActionModal(null);
                  setModalInput("");
                }}
                className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white"
              >
                Confirm {actionModal.action}
              </button>
            </div>
          </div>
        </div>
      )}
    
      {/* Step 33 Canonical Event Detail Modal */}
      <EventDetailModal
        event={detailEvent}
        isOpen={!!detailEvent}
        onClose={() => setDetailEvent(null)}
        onAction={(action, id) => {
          if (action === "CONFIRM") handleAction(id, "Verify" as any);
          else if (action === "DISMISS") handleAction(id, "Resolve" as any, "Dismissed as false positive");
          else if (action === "ESCALATE") handleAction(id, "Escalate" as any);
          else if (action === "MARK_UNDER_REPAIR") handleAction(id, "Assign" as any, "Road Maintenance Engineering");
        }}
      />
</div>
  );
};

export default AlertCenter;
