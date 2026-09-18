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
        return "bg-emerald-50 text-emerald-700 border border-emerald-200";
      case "WARNING":
        return "bg-amber-50 text-amber-700 border border-amber-200";
      case "DEGRADED":
        return "bg-rose-50 text-rose-700 border border-rose-200 animate-pulse";
      case "OFFLINE":
        return "bg-gray-100 text-gray-600 border border-gray-200";
      default:
        return "bg-gray-100 text-gray-500 border border-gray-200";
    }
  };

  const healthyCount = cameras.filter((c) => c.camera_status === "HEALTHY").length;
  const degradedCount = cameras.filter((c) => c.camera_status === "DEGRADED").length;
  const haltedCount = cameras.filter((c) => c.unreliable_detections_halted).length;

  return (
    <div className="min-h-screen bg-transparent text-[#16192E] p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-[#E2E8F0] pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-50 border border-blue-200 rounded-2xl text-blue-700 shadow-2xs">
              <Camera size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-[#16192E] flex items-center gap-3">
                Camera &amp; Edge Device Health
              </h1>
              <p className="text-xs sm:text-sm text-[#64748B]">
                Continuous diagnostics for optical lens quality, frame rate, thermal metrics, and automatic fail-safe ticketing.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchHealthData}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white hover:bg-[#F8FAFC] border border-[#CBD5E1] text-xs font-semibold text-[#16192E] shadow-2xs transition-all"
          >
            <RefreshCw size={14} className="text-[#C85A17]" />
            Refresh Telemetry
          </button>
          <a
            href="/"
            className="px-3.5 py-2 rounded-xl bg-[#C85A17] hover:bg-[#B34F14] text-white text-xs font-semibold shadow-sm transition-all"
          >
            &larr; Main Hub
          </a>
        </div>
      </div>

      {/* Critical Rule Banner */}
      <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-rose-900">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-xl bg-rose-100 text-rose-700 shrink-0 mt-0.5">
            <ShieldAlert size={20} />
          </div>
          <div>
            <h4 className="text-sm font-bold text-rose-950">
              Critical Fail-Safe: Dirty or Obstructed Lens Guardrail
            </h4>
            <p className="text-xs text-rose-800 mt-0.5 leading-relaxed">
              If an edge camera is dirty or obstructed: <strong>Do NOT silently continue producing unreliable detections</strong>. The system immediately marks <strong>CAMERA DEGRADED</strong>, halts downstream inference, and spawns an automated maintenance ticket.
            </p>
          </div>
        </div>
        <span className="text-[10px] font-mono font-bold text-rose-700 bg-white px-3 py-1 rounded-full border border-rose-200 shrink-0">
          FAIL-SAFE ARMED
        </span>
      </div>

      {/* Toast Notification */}
      {toastMsg && (
        <div className="p-3 bg-rose-600 text-white text-sm rounded-xl flex items-center justify-between shadow-lg animate-fade-in">
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
        <div className="p-4 rounded-2xl bg-white border border-[#E2E8F0] shadow-sm">
          <div className="text-xs font-semibold text-[#64748B]">Total Monitored Nodes</div>
          <div className="text-2xl font-extrabold text-[#16192E] mt-1">{cameras.length}</div>
          <div className="text-xs text-emerald-700 mt-1 flex items-center gap-1 font-medium">
            <CheckCircle2 size={12} /> {healthyCount} Healthy &amp; Operational
          </div>
        </div>
        <div className="p-4 rounded-2xl bg-white border border-[#E2E8F0] shadow-sm">
          <div className="text-xs font-semibold text-rose-700">Degraded Optical Sensors</div>
          <div className="text-2xl font-extrabold text-rose-700 mt-1">{degradedCount}</div>
          <div className="text-xs text-[#64748B] mt-1">Obstructed or severe blur</div>
        </div>
        <div className="p-4 rounded-2xl bg-white border border-[#E2E8F0] shadow-sm">
          <div className="text-xs font-semibold text-amber-700">Detections Halted (Fail-Safe)</div>
          <div className="text-2xl font-extrabold text-amber-700 mt-1">{haltedCount}</div>
          <div className="text-xs text-[#64748B] mt-1">Protecting AI data integrity</div>
        </div>
        <div className="p-4 rounded-2xl bg-white border border-[#E2E8F0] shadow-sm">
          <div className="text-xs font-semibold text-blue-700">Auto Maintenance Tickets</div>
          <div className="text-2xl font-extrabold text-blue-700 mt-1">{tickets.length}</div>
          <div className="text-xs text-[#64748B] mt-1 flex items-center gap-1">
            <Wrench size={12} /> Cleaning &amp; realignment
          </div>
        </div>
      </div>

      {/* Status Filter Buttons */}
      <div className="flex flex-wrap items-center gap-2 bg-white p-3 rounded-2xl border border-[#E2E8F0] shadow-sm">
        <span className="text-xs text-[#64748B] font-semibold px-2">Filter State:</span>
        {["ALL", "HEALTHY", "WARNING", "DEGRADED", "OFFLINE"].map((st) => (
          <button
            key={st}
            onClick={() => setStatusFilter(st)}
            className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all ${
              statusFilter === st
                ? "bg-[#16192E] text-white shadow-xs"
                : "bg-[#F8FAFC] text-[#64748B] hover:text-[#16192E] hover:bg-[#EEF2F6] border border-[#E2E8F0]"
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

          return (
            <div
              key={cam.camera_id}
              className={`p-5 rounded-2xl border bg-white shadow-sm transition-all space-y-4 ${
                isDegraded
                  ? "border-rose-300 ring-1 ring-rose-200"
                  : isWarning
                  ? "border-amber-300 ring-1 ring-amber-200"
                  : "border-[#E2E8F0]"
              }`}
            >
              {/* Card Header */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-[#E2E8F0] pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[#16192E] text-base">{cam.camera_id}</span>
                    <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase ${getStatusBadge(cam.camera_status)}`}>
                      {cam.camera_status}
                    </span>
                  </div>
                  <div className="text-xs text-[#64748B] mt-0.5">
                    {cam.camera_name} &bull; Bus: <strong className="text-[#C85A17]">{cam.bus_id}</strong>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-xs text-[#64748B] font-mono">
                    Heartbeat: {cam.last_heartbeat.slice(11, 19)} UTC
                  </div>
                  <div className="text-xs text-[#64748B]">{cam.network_status} ({cam.network_latency_ms} ms)</div>
                </div>
              </div>

              {/* Optical Diagnostics Strip */}
              <div className="space-y-2">
                <div className="text-xs font-bold text-[#64748B] uppercase tracking-wider flex items-center gap-1.5">
                  <Camera size={13} className="text-[#C85A17]" /> Optical Sensor Health
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="p-2.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                    <div className="text-[10px] uppercase font-bold text-[#64748B]">Stream FPS</div>
                    <div className="text-sm font-bold text-[#16192E] mt-0.5">
                      {cam.fps} <span className="text-xs font-normal text-[#64748B]">/ {cam.target_fps}</span>
                    </div>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                    <div className="text-[10px] uppercase font-bold text-[#64748B]">Blur Score</div>
                    <div className="text-sm font-bold text-[#16192E] mt-0.5">
                      {cam.blur_score} <span className="text-xs font-normal text-[#64748B]">var(∇²)</span>
                    </div>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                    <div className="text-[10px] uppercase font-bold text-[#64748B]">Brightness</div>
                    <div className="text-sm font-bold text-[#16192E] mt-0.5">{cam.brightness} / 255</div>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                    <div className="text-[10px] uppercase font-bold text-[#64748B]">Lens Obstruction</div>
                    <div className={`text-sm font-bold mt-0.5 ${cam.lens_obstruction_pct >= 25 ? "text-rose-700" : "text-[#16192E]"}`}>
                      {cam.lens_obstruction_pct}%
                    </div>
                  </div>
                </div>
              </div>

              {/* Edge Node Hardware Telemetry */}
              <div className="space-y-2">
                <div className="text-xs font-bold text-[#64748B] uppercase tracking-wider flex items-center gap-1.5">
                  <Cpu size={13} className="text-blue-600" /> Edge Computing Diagnostics
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
                  <div className="p-2 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                    <div className="text-[#64748B] text-[10px]">CPU Usage</div>
                    <div className="font-mono font-bold text-[#16192E] mt-0.5">{cam.cpu_usage_pct}%</div>
                  </div>
                  <div className="p-2 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                    <div className="text-[#64748B] text-[10px]">GPU Usage</div>
                    <div className="font-mono font-bold text-[#16192E] mt-0.5">{cam.gpu_usage_pct}%</div>
                  </div>
                  <div className="p-2 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                    <div className="text-[#64748B] text-[10px]">RAM Usage</div>
                    <div className="font-mono font-bold text-[#16192E] mt-0.5">{cam.ram_usage_pct}%</div>
                  </div>
                  <div className="p-2 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                    <div className="text-[#64748B] text-[10px]">Storage</div>
                    <div className="font-mono font-bold text-[#16192E] mt-0.5">{cam.storage_usage_pct}%</div>
                  </div>
                  <div className="p-2 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                    <div className="text-[#64748B] text-[10px]">Temperature</div>
                    <div className={`font-mono font-bold mt-0.5 ${cam.temperature_celsius > 65 ? "text-amber-700" : "text-[#16192E]"}`}>
                      {cam.temperature_celsius}°C
                    </div>
                  </div>
                </div>
              </div>

              {/* Fail-Safe Guardrail Status Badge */}
              {cam.unreliable_detections_halted && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <EyeOff size={16} className="text-rose-700 flex-shrink-0" />
                    <span>
                      <strong>CAMERA DEGRADED:</strong> Unreliable detections halted to protect platform data integrity.
                    </span>
                  </div>
                  {cam.active_maintenance_ticket_id && (
                    <span className="font-mono text-xs bg-rose-100 text-rose-800 px-2 py-0.5 rounded border border-rose-200">
                      {cam.active_maintenance_ticket_id}
                    </span>
                  )}
                </div>
              )}

              {/* Interactive Simulation Action */}
              <div className="pt-2 border-t border-[#E2E8F0] flex items-center justify-between">
                <span className="text-xs text-[#64748B]">
                  {cam.camera_status === "HEALTHY" ? "Optical feed verified healthy" : "Requires maintenance bay review"}
                </span>
                {cam.camera_status !== "DEGRADED" && (
                  <button
                    onClick={() => handleSimulateObstruction(cam.camera_id)}
                    className="px-3 py-1.5 rounded-xl bg-white hover:bg-rose-50 text-xs font-semibold text-rose-700 border border-rose-200 shadow-2xs transition-all flex items-center gap-1.5"
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
      <div className="p-5 rounded-2xl border border-[#E2E8F0] bg-white shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
          <div className="flex items-center gap-2 font-bold text-[#16192E] text-base">
            <Wrench size={18} className="text-[#C85A17]" />
            Automatic Optical Maintenance Tickets ({tickets.length})
          </div>
          <span className="text-xs text-[#64748B]">Triggered automatically by dirty/obstructed lens fail-safe</span>
        </div>

        <div className="overflow-x-auto border border-[#E2E8F0] rounded-xl">
          <table className="w-full text-left text-xs text-[#16192E]">
            <thead className="bg-[#F8FAFC] text-[#64748B] border-b border-[#E2E8F0] uppercase text-[10px]">
              <tr>
                <th className="py-2.5 px-3">Ticket ID</th>
                <th className="py-2.5 px-3">Camera</th>
                <th className="py-2.5 px-3">Bus</th>
                <th className="py-2.5 px-3">Issue</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">Reason</th>
                <th className="py-2.5 px-3">Detections</th>
                <th className="py-2.5 px-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2E8F0] font-medium">
              {tickets.map((t) => (
                <tr key={t.ticket_id} className="hover:bg-[#F8FAFC] transition-colors">
                  <td className="py-2.5 px-3 font-mono text-[#C85A17] font-semibold">{t.ticket_id}</td>
                  <td className="py-2.5 px-3">{t.camera_id}</td>
                  <td className="py-2.5 px-3 font-bold">{t.bus_id}</td>
                  <td className="py-2.5 px-3">{t.issue_type}</td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] bg-rose-50 text-rose-700 border border-rose-200 font-bold">
                      {t.severity}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-[#64748B] max-w-xs truncate">{t.reason}</td>
                  <td className="py-2.5 px-3">
                    <span className="text-rose-700 font-semibold">HALTED</span>
                  </td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] bg-blue-50 text-blue-700 border border-blue-200 font-bold">
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
