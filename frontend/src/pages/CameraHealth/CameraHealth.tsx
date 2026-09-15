// src/pages/CameraHealth/CameraHealth.tsx
// Phase 25 — Camera & Edge Device Health Dashboard

import React, { useState, useEffect } from "react";
import {
  Camera, Cpu, Activity, AlertTriangle, ShieldCheck,
  ShieldAlert, Wrench, RefreshCw, HardDrive, Wifi,
  Thermometer, Zap, CheckCircle2, XCircle, Droplets,
  EyeOff, AlertOctagon, Clock, Check, X, Layers
} from "lucide-react";

export interface MaintenanceTicket {
  ticket_id: string;
  camera_id: string;
  bus_id: string;
  issue_type: string;
  severity: string;
  status: string;
  created_at: string;
  reason: string;
  halted_detections: boolean;
  assigned_technician?: string;
}

export interface CameraTelemetry {
  camera_id: string;
  bus_id: string;
  camera_name: string;
  camera_status: "HEALTHY" | "WARNING" | "DEGRADED" | "OFFLINE";
  fps: number;
  target_fps: number;
  blur_score: number;
  brightness: number;
  lens_obstruction_pct: number;
  is_lens_obstructed: boolean;
  unreliable_detections_halted: boolean;
  temperature_celsius: number;
  cpu_usage_pct: number;
  gpu_usage_pct: number;
  ram_usage_pct: number;
  storage_usage_pct: number;
  network_status: string;
  network_latency_ms: number;
  last_heartbeat: string;
  active_maintenance_ticket_id?: string;
}

export const CameraHealth: React.FC = () => {
  const [cameras, setCameras] = useState<CameraTelemetry[]>([]);
  const [tickets, setTickets] = useState<MaintenanceTicket[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const fetchHealthData = async () => {
    try {
      const [camsRes, tktsRes] = await Promise.all([
        fetch("/api/v1/cameras"),
        fetch("/api/v1/cameras/maintenance-tickets"),
      ]);
      if (camsRes.ok) {
        const camsData = await camsRes.json();
        setCameras(camsData);
      }
      if (tktsRes.ok) {
        const tktsData = await tktsRes.json();
        setTickets(tktsData);
      }
    } catch (err) {
      console.error("Failed to fetch camera health data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealthData();
  }, []);

  const handleSimulateObstruction = async (cameraId: string) => {
    try {
      const res = await fetch(`/api/v1/cameras/${cameraId}/simulate-obstruction`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          obstruction_pct: 74.0,
          reason: "Heavy road mud & grime coating front optical lens",
        }),
      });

      if (res.ok) {
        const updated = await res.json();
        setCameras((prev) => prev.map((c) => (c.camera_id === cameraId ? updated : c)));
        setToastMsg(`CAMERA DEGRADED: Optical obstruction detected on ${cameraId}. Unreliable detections halted & Maintenance Ticket spawned!`);
        await fetchHealthData(); // Refresh tickets
        setTimeout(() => setToastMsg(null), 5000);
      }
    } catch (err) {
      console.error("Simulation failed:", err);
    }
  };

  const filteredCameras = cameras.filter((c) => {
    return statusFilter === "ALL" || c.camera_status === statusFilter;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "HEALTHY":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
      case "WARNING":
        return "bg-amber-500/20 text-amber-300 border-amber-500/30";
      case "DEGRADED":
        return "bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse";
      case "OFFLINE":
        return "bg-slate-700 text-slate-300 border-slate-600";
      default:
        return "bg-slate-800 text-slate-400";
    }
  };

  const healthyCount = cameras.filter((c) => c.camera_status === "HEALTHY").length;
  const degradedCount = cameras.filter((c) => c.camera_status === "DEGRADED").length;
  const haltedCount = cameras.filter((c) => c.unreliable_detections_halted).length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-cyan-500/10 border border-cyan-500/30 rounded-xl text-cyan-400">
              <Camera size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
                Camera & Edge Device Health
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  Phase 25
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Continuous diagnostics for optical lens quality, frame rate, thermal metrics, and automatic fail-safe ticketing.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchHealthData}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-sm font-medium transition"
          >
            <RefreshCw size={15} />
            Refresh Telemetry
          </button>
          <a
            href="/"
            className="px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition"
          >
            &larr; Main Hub
          </a>
        </div>
      </div>

      {/* Critical Rule Banner */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-rose-950/40 via-slate-900 to-slate-900 border border-rose-500/40 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-rose-500/20 text-rose-400">
            <ShieldAlert size={22} />
          </div>
          <div>
            <h4 className="text-sm font-bold text-rose-300">
              Critical Fail-Safe: Dirty or Obstructed Lens Guardrail
            </h4>
            <p className="text-xs text-slate-300 mt-0.5">
              If an edge camera is dirty or obstructed: <strong>Do NOT silently continue producing unreliable detections</strong>. The system immediately marks <strong>CAMERA DEGRADED</strong>, halts downstream inference, and spawns an automated maintenance ticket.
            </p>
          </div>
        </div>
        <span className="text-xs font-mono text-rose-400 bg-rose-500/10 px-3 py-1 rounded border border-rose-500/30 hidden sm:inline">
          FAIL-SAFE ARMED
        </span>
      </div>

      {/* Toast Notification */}
      {toastMsg && (
        <div className="p-3 bg-rose-600 text-white text-sm rounded-lg flex items-center justify-between shadow-lg animate-fade-in">
          <span className="font-semibold flex items-center gap-2">
            <AlertOctagon size={18} />
            {toastMsg}
          </span>
          <button onClick={() => setToastMsg(null)}>
            <X size={16} />
          </button>
        </div>
      )}

      {/* KPI Diagnostic Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs font-medium text-slate-400">Total Monitored Nodes</div>
          <div className="text-2xl font-bold text-white mt-1">{cameras.length}</div>
          <div className="text-xs text-emerald-400 mt-1 flex items-center gap-1">
            <CheckCircle2 size={12} /> {healthyCount} Healthy & Operational
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs font-medium text-slate-400">Degraded Optical Sensors</div>
          <div className="text-2xl font-bold text-rose-400 mt-1">{degradedCount}</div>
          <div className="text-xs text-rose-400/80 mt-1">Obstructed or severe blur</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs font-medium text-slate-400">Detections Halted (Fail-Safe)</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">{haltedCount}</div>
          <div className="text-xs text-amber-400/80 mt-1">Protecting AI data integrity</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs font-medium text-slate-400">Auto Maintenance Tickets</div>
          <div className="text-2xl font-bold text-cyan-400 mt-1">{tickets.length}</div>
          <div className="text-xs text-cyan-400/80 mt-1 flex items-center gap-1">
            <Wrench size={12} /> Cleaning & realignment
          </div>
        </div>
      </div>

      {/* Status Filter Buttons */}
      <div className="flex items-center gap-2 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800">
        <span className="text-xs text-slate-400 font-medium px-2">Filter State:</span>
        {["ALL", "HEALTHY", "WARNING", "DEGRADED", "OFFLINE"].map((st) => (
          <button
            key={st}
            onClick={() => setStatusFilter(st)}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
              statusFilter === st
                ? "bg-slate-700 text-white border border-slate-600 shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {st}
          </button>
        ))}
      </div>

      {/* Camera Diagnostics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {filteredCameras.map((cam) => {
          const isDegraded = cam.camera_status === "DEGRADED";
          const isWarning = cam.camera_status === "WARNING";
          const isOffline = cam.camera_status === "OFFLINE";

          return (
            <div
              key={cam.camera_id}
              className={`p-5 rounded-xl border bg-slate-900/90 transition space-y-4 ${
                isDegraded
                  ? "border-rose-500/50 shadow-rose-950/20"
                  : isWarning
                  ? "border-amber-500/40 shadow-amber-950/20"
                  : "border-slate-800"
              }`}
            >
              {/* Card Header */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-800 pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white text-base">{cam.camera_id}</span>
                    <span className={`text-xs px-2.5 py-0.5 rounded border font-bold uppercase ${getStatusBadge(cam.camera_status)}`}>
                      {cam.camera_status}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {cam.camera_name} • Bus: <strong className="text-indigo-400">{cam.bus_id}</strong>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-xs text-slate-400 font-mono">
                    Heartbeat: {cam.last_heartbeat.slice(11, 19)} UTC
                  </div>
                  <div className="text-xs text-slate-500">{cam.network_status} ({cam.network_latency_ms} ms)</div>
                </div>
              </div>

              {/* Optical Diagnostics Strip */}
              <div className="space-y-2">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Camera size={13} className="text-cyan-400" /> Optical Sensor Health
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800">
                    <div className="text-xs text-slate-400">Stream FPS</div>
                    <div className="text-sm font-bold text-white mt-0.5">
                      {cam.fps} <span className="text-xs text-slate-500">/ {cam.target_fps}</span>
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800">
                    <div className="text-xs text-slate-400">Blur Score</div>
                    <div className="text-sm font-bold text-white mt-0.5">
                      {cam.blur_score} <span className="text-xs text-slate-500">var(∇²)</span>
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800">
                    <div className="text-xs text-slate-400">Brightness</div>
                    <div className="text-sm font-bold text-white mt-0.5">{cam.brightness} / 255</div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800">
                    <div className="text-xs text-slate-400">Lens Obstruction</div>
                    <div className={`text-sm font-bold mt-0.5 ${cam.lens_obstruction_pct >= 25 ? "text-rose-400" : "text-white"}`}>
                      {cam.lens_obstruction_pct}%
                    </div>
                  </div>
                </div>
              </div>

              {/* Edge Node Hardware Telemetry */}
              <div className="space-y-2">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Cpu size={13} className="text-indigo-400" /> Edge Computing Diagnostics
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
                  <div className="p-2 rounded bg-slate-950/50 border border-slate-800/80">
                    <div className="text-slate-400">CPU Usage</div>
                    <div className="font-mono font-bold text-slate-200 mt-0.5">{cam.cpu_usage_pct}%</div>
                  </div>
                  <div className="p-2 rounded bg-slate-950/50 border border-slate-800/80">
                    <div className="text-slate-400">GPU Usage</div>
                    <div className="font-mono font-bold text-slate-200 mt-0.5">{cam.gpu_usage_pct}%</div>
                  </div>
                  <div className="p-2 rounded bg-slate-950/50 border border-slate-800/80">
                    <div className="text-slate-400">RAM Usage</div>
                    <div className="font-mono font-bold text-slate-200 mt-0.5">{cam.ram_usage_pct}%</div>
                  </div>
                  <div className="p-2 rounded bg-slate-950/50 border border-slate-800/80">
                    <div className="text-slate-400">Storage</div>
                    <div className="font-mono font-bold text-slate-200 mt-0.5">{cam.storage_usage_pct}%</div>
                  </div>
                  <div className="p-2 rounded bg-slate-950/50 border border-slate-800/80">
                    <div className="text-slate-400">Temperature</div>
                    <div className={`font-mono font-bold mt-0.5 ${cam.temperature_celsius > 65 ? "text-amber-400" : "text-slate-200"}`}>
                      {cam.temperature_celsius}°C
                    </div>
                  </div>
                </div>
              </div>

              {/* Fail-Safe Guardrail Status Badge */}
              {cam.unreliable_detections_halted && (
                <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <EyeOff size={16} className="text-rose-400 flex-shrink-0" />
                    <span>
                      <strong>CAMERA DEGRADED:</strong> Unreliable detections halted to protect platform data integrity.
                    </span>
                  </div>
                  {cam.active_maintenance_ticket_id && (
                    <span className="font-mono text-xs bg-rose-500/20 px-2 py-0.5 rounded border border-rose-500/30">
                      {cam.active_maintenance_ticket_id}
                    </span>
                  )}
                </div>
              )}

              {/* Interactive Simulation Action */}
              <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
                <span className="text-xs text-slate-500">
                  {cam.camera_status === "HEALTHY" ? "Optical feed verified healthy" : "Requires maintenance bay review"}
                </span>
                {cam.camera_status !== "DEGRADED" && (
                  <button
                    onClick={() => handleSimulateObstruction(cam.camera_id)}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-rose-300 border border-rose-500/30 transition flex items-center gap-1.5"
                  >
                    <Droplets size={13} />
                    Simulate Obstructed / Dirty Lens
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Automated Maintenance Tickets Log */}
      <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/80 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2 font-bold text-white text-base">
            <Wrench size={18} className="text-indigo-400" />
            Automatic Optical Maintenance Tickets ({tickets.length})
          </div>
          <span className="text-xs text-slate-400">Triggered automatically by dirty/obstructed lens fail-safe</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-slate-400 border-b border-slate-800">
              <tr>
                <th className="pb-2">Ticket ID</th>
                <th className="pb-2">Camera</th>
                <th className="pb-2">Bus</th>
                <th className="pb-2">Issue</th>
                <th className="pb-2">Severity</th>
                <th className="pb-2">Reason</th>
                <th className="pb-2">Detections</th>
                <th className="pb-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {tickets.map((t) => (
                <tr key={t.ticket_id} className="text-slate-300 hover:bg-slate-800/30">
                  <td className="py-2.5 font-mono text-indigo-400">{t.ticket_id}</td>
                  <td className="py-2.5">{t.camera_id}</td>
                  <td className="py-2.5 font-bold">{t.bus_id}</td>
                  <td className="py-2.5">{t.issue_type}</td>
                  <td className="py-2.5">
                    <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-bold">
                      {t.severity}
                    </span>
                  </td>
                  <td className="py-2.5 text-slate-400 max-w-xs truncate">{t.reason}</td>
                  <td className="py-2.5">
                    <span className="text-rose-400 font-semibold">HALTED</span>
                  </td>
                  <td className="py-2.5">
                    <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/30">
                      {t.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default CameraHealth;
