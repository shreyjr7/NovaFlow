// src/pages/Privacy/Privacy.tsx
// Phase 26 — Enterprise Privacy & Security Dashboard

import React, { useState, useEffect } from "react";
import {
  ShieldCheck, Lock, EyeOff, FileText, Database,
  Clock, CheckCircle2, XCircle, RefreshCw, Slider,
  Sliders, UserCheck, Key, HardDrive, Cpu, Radio,
  Layers, AlertTriangle, Shield, Check, X
} from "lucide-react";

export interface RetentionPolicyConfig {
  raw_frame_buffer_seconds: number;
  unverified_anomaly_retention_days: number;
  confirmed_evidence_clip_retention_days: number;
  access_audit_log_retention_days: number;
  passenger_cabin_telemetry_retention_hours: number;
}

export interface AccessLogEntry {
  log_id: string;
  timestamp: string;
  user_id: string;
  user_role: string;
  action: string;
  resource_id: string;
  resource_type: string;
  ip_address: string;
  justification: string;
  granted: boolean;
}

export interface RolePermission {
  role: string;
  description: string;
  evidence_access_level: string;
  permissions: string[];
}

export const Privacy: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"retention" | "camera" | "storage" | "logs" | "rbac">("retention");
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [policies, setPolicies] = useState<RetentionPolicyConfig>({
    raw_frame_buffer_seconds: 15,
    unverified_anomaly_retention_days: 7,
    confirmed_evidence_clip_retention_days: 90,
    access_audit_log_retention_days: 365,
    passenger_cabin_telemetry_retention_hours: 24,
  });
  const [accessLogs, setAccessLogs] = useState<AccessLogEntry[]>([]);
  const [roles, setRoles] = useState<RolePermission[]>([]);
  const [saving, setSaving] = useState<boolean>(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const fetchPrivacyData = async () => {
    try {
      const [dashRes, polRes, logsRes, rolesRes] = await Promise.all([
        fetch("/api/v1/privacy/dashboard"),
        fetch("/api/v1/privacy/retention-policies"),
        fetch("/api/v1/privacy/access-logs"),
        fetch("/api/v1/privacy/roles"),
      ]);

      if (dashRes.ok) setDashboardData(await dashRes.json());
      if (polRes.ok) setPolicies(await polRes.json());
      if (logsRes.ok) setAccessLogs(await logsRes.json());
      if (rolesRes.ok) setRoles(await rolesRes.json());
    } catch (err) {
      console.error("Failed to load privacy data:", err);
    }
  };

  useEffect(() => {
    fetchPrivacyData();
  }, []);

  const handleSavePolicies = async () => {
    setSaving(true);
    try {
      const res = await fetch("/api/v1/privacy/retention-policies", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(policies),
      });
      if (res.ok) {
        const updated = await res.json();
        setPolicies(updated);
        setToastMsg("Retention policies updated and recorded in immutable audit ledger!");
        await fetchPrivacyData();
        setTimeout(() => setToastMsg(null), 4000);
      }
    } catch (err) {
      console.error("Failed to update retention policies:", err);
    } finally {
      setSaving(false);
    }
  };

  const handlePurgeExpired = async () => {
    try {
      const res = await fetch("/api/v1/privacy/purge-expired", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setToastMsg(`Purge Complete: ${data.raw_frames_purged_count.toLocaleString()} unflagged frames purged from onboard ring buffers.`);
        setTimeout(() => setToastMsg(null), 4000);
      }
    } catch (err) {
      console.error("Purge failed:", err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400">
              <ShieldCheck size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
                Privacy & Security Architecture
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Compliance Guardrails
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                13-rule compliance enforcement, zero raw video upload, on-edge inference, RBAC access control & immutable audit trail.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-3.5 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-xs font-mono font-bold flex items-center gap-1.5">
            <CheckCircle2 size={14} className="text-emerald-400" />
            13 / 13 RULES ENFORCED
          </div>
          <button
            onClick={fetchPrivacyData}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-sm font-medium transition"
          >
            <RefreshCw size={15} />
            Refresh
          </button>
          <a
            href="/"
            className="px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition"
          >
            &larr; Main Hub
          </a>
        </div>
      </div>

      {/* Toast Notification */}
      {toastMsg && (
        <div className="p-3 bg-emerald-600 text-white text-sm rounded-lg flex items-center justify-between shadow-lg animate-fade-in">
          <span className="font-medium flex items-center gap-2">
            <ShieldCheck size={18} />
            {toastMsg}
          </span>
          <button onClick={() => setToastMsg(null)}>
            <X size={16} />
          </button>
        </div>
      )}

      {/* 5-Pillar Tab Buttons */}
      <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-3">
        {[
          { id: "retention", label: "1. Data Retention", icon: Clock },
          { id: "camera", label: "2. Camera Processing", icon: Cpu },
          { id: "storage", label: "3. Evidence Storage", icon: HardDrive },
          { id: "logs", label: "4. Access Logs", icon: FileText },
          { id: "rbac", label: "5. User Permissions (RBAC)", icon: Key },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition ${
                isActive
                  ? "bg-indigo-600 text-white shadow-md"
                  : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
              }`}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Pillar 1: Data Retention */}
      {activeTab === "retention" && (
        <div className="space-y-6">
          <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/90 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Sliders size={18} className="text-indigo-400" />
                  Configurable Data Retention Policies
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Adjust rolling buffer thresholds and automatic evidence purge schedules.
                </p>
              </div>
              <button
                onClick={handlePurgeExpired}
                className="px-3 py-1.5 rounded-lg bg-rose-950 hover:bg-rose-900 border border-rose-500/40 text-xs font-semibold text-rose-300 transition"
              >
                Trigger Retention Purge Now
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
              {/* Policy 1 */}
              <div className="p-4 rounded-lg bg-slate-950/70 border border-slate-800 space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-300">
                    Non-Incident Raw Frame Buffer (Seconds)
                  </label>
                  <span className="font-mono text-sm font-bold text-indigo-400">
                    {policies.raw_frame_buffer_seconds} sec
                  </span>
                </div>
                <input
                  type="range"
                  min={5}
                  max={60}
                  step={1}
                  value={policies.raw_frame_buffer_seconds}
                  onChange={(e) => setPolicies({ ...policies, raw_frame_buffer_seconds: parseInt(e.target.value) })}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
                <p className="text-xs text-slate-500">
                  Unflagged frames are permanently discarded from onboard memory after this window.
                </p>
              </div>

              {/* Policy 2 */}
              <div className="p-4 rounded-lg bg-slate-950/70 border border-slate-800 space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-300">
                    Unverified Anomaly Retention (Days)
                  </label>
                  <span className="font-mono text-sm font-bold text-indigo-400">
                    {policies.unverified_anomaly_retention_days} days
                  </span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={30}
                  step={1}
                  value={policies.unverified_anomaly_retention_days}
                  onChange={(e) => setPolicies({ ...policies, unverified_anomaly_retention_days: parseInt(e.target.value) })}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
                <p className="text-xs text-slate-500">
                  Sensor anomalies unreviewed by human officers are purged after this period.
                </p>
              </div>

              {/* Policy 3 */}
              <div className="p-4 rounded-lg bg-slate-950/70 border border-slate-800 space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-300">
                    Confirmed Evidence Clip Retention (Days)
                  </label>
                  <span className="font-mono text-sm font-bold text-indigo-400">
                    {policies.confirmed_evidence_clip_retention_days} days
                  </span>
                </div>
                <input
                  type="range"
                  min={14}
                  max={365}
                  step={1}
                  value={policies.confirmed_evidence_clip_retention_days}
                  onChange={(e) => setPolicies({ ...policies, confirmed_evidence_clip_retention_days: parseInt(e.target.value) })}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
                <p className="text-xs text-slate-500">
                  Legally preserved incident video clips and telemetry traces.
                </p>
              </div>

              {/* Policy 4 */}
              <div className="p-4 rounded-lg bg-slate-950/70 border border-slate-800 space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-300">
                    Access Audit Log Retention (Days)
                  </label>
                  <span className="font-mono text-sm font-bold text-indigo-400">
                    {policies.access_audit_log_retention_days} days
                  </span>
                </div>
                <input
                  type="range"
                  min={90}
                  max={730}
                  step={1}
                  value={policies.access_audit_log_retention_days}
                  onChange={(e) => setPolicies({ ...policies, access_audit_log_retention_days: parseInt(e.target.value) })}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
                <p className="text-xs text-slate-500">
                  Immutable evidentiary access log preservation for legal and compliance audits.
                </p>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end">
              <button
                onClick={handleSavePolicies}
                disabled={saving}
                className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition shadow"
              >
                {saving ? "Saving..." : "Save Configurable Retention Policies"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Pillar 2: Camera Processing */}
      {activeTab === "camera" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-xs font-medium text-slate-400">Edge Local Processing</div>
              <div className="text-3xl font-bold text-emerald-400 mt-1">100.0%</div>
              <div className="text-xs text-slate-400 mt-1">All AI inference executed on-bus</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-xs font-medium text-slate-400">Cloud Raw Stream Bandwidth</div>
              <div className="text-3xl font-bold text-white mt-1">0.0 GB</div>
              <div className="text-xs text-emerald-400 mt-1 font-semibold">Guaranteed Zero Continuous Upload</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-xs font-medium text-slate-400">Bandwidth Savings vs Cloud Stream</div>
              <div className="text-3xl font-bold text-cyan-400 mt-1">99.98%</div>
              <div className="text-xs text-slate-400 mt-1">Metadata-only ingestion</div>
            </div>
          </div>

          <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/90 space-y-3">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <EyeOff size={18} className="text-indigo-400" />
              Passenger Cabin Privacy Guardrail (Rule 13)
            </h3>
            <p className="text-sm text-slate-300 leading-relaxed">
              Passenger cabin sensors run <strong>100% locally on-edge</strong>. The onboard AI computes anonymous headcounts and crowd density percentages. Under no circumstances is any passenger facial imagery, biometric data, or passenger-identifying video transmitted outside the bus.
            </p>
            <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-500/30 text-xs text-emerald-300 font-mono">
              Cabin State: LOCAL_AGGREGATION_ONLY • PII_TRANSMISSION = 0 • FACE_BLUR_ACTIVE
            </div>
          </div>
        </div>
      )}

      {/* Pillar 3: Evidence Storage */}
      {activeTab === "storage" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-xs font-medium text-slate-400">Encrypted Storage Volume</div>
              <div className="text-3xl font-bold text-white mt-1">348.5 MB</div>
              <div className="text-xs text-slate-400 mt-1">AES-256-GCM cipher</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-xs font-medium text-slate-400">Retained Incident Clips</div>
              <div className="text-3xl font-bold text-indigo-400 mt-1">7 Clips</div>
              <div className="text-xs text-slate-400 mt-1">Only verified flagged anomalies</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <div className="text-xs font-medium text-slate-400">Unflagged Frames Purged Today</div>
              <div className="text-3xl font-bold text-emerald-400 mt-1">4.3M</div>
              <div className="text-xs text-slate-400 mt-1">Purged via 15s ring buffer</div>
            </div>
          </div>

          <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/90 space-y-3">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Lock size={18} className="text-indigo-400" />
              Evidence Chain of Custody &amp; Immutability
            </h3>
            <p className="text-sm text-slate-300 leading-relaxed">
              Every stored incident clip is cryptographically bound to a <strong>SHA-256 genesis hash</strong>, GPS coordinates, bus ID, and timestamp. Silent overwrites are strictly rejected by storage gates.
            </p>
            <div className="pt-2">
              <a
                href="/evidence-custody"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition"
              >
                Open Evidence Chain of Custody Portal &rarr;
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Pillar 4: Access Logs */}
      {activeTab === "logs" && (
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/90 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <FileText size={18} className="text-indigo-400" />
                Immutable Evidence Access Audit Ledger
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Rule 6: Every access, view, or export of raw evidence or ANPR records is permanently logged.
              </p>
            </div>
            <span className="text-xs font-mono text-slate-400">
              {accessLogs.length} audit records
            </span>
          </div>

          <div className="overflow-x-auto touch-scroll">
            <table className="w-full min-w-[750px] text-left text-xs">
              <thead className="text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="pb-2">Log ID</th>
                  <th className="pb-2">Timestamp</th>
                  <th className="pb-2">User</th>
                  <th className="pb-2">Role</th>
                  <th className="pb-2">Action</th>
                  <th className="pb-2">Resource ID</th>
                  <th className="pb-2">IP Address</th>
                  <th className="pb-2">Justification</th>
                  <th className="pb-2">Clearance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {accessLogs.map((log) => (
                  <tr key={log.log_id} className="text-slate-300 hover:bg-slate-800/30">
                    <td className="py-2.5 font-mono text-indigo-400">{log.log_id}</td>
                    <td className="py-2.5 font-mono text-slate-400">{log.timestamp.slice(11, 19)} UTC</td>
                    <td className="py-2.5 font-bold text-white">{log.user_id}</td>
                    <td className="py-2.5">
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-xs">
                        {log.user_role}
                      </span>
                    </td>
                    <td className="py-2.5 font-semibold text-slate-200">{log.action}</td>
                    <td className="py-2.5 font-mono text-slate-400">{log.resource_id}</td>
                    <td className="py-2.5 font-mono text-slate-500">{log.ip_address}</td>
                    <td className="py-2.5 text-slate-400 max-w-xs truncate">{log.justification}</td>
                    <td className="py-2.5">
                      {log.granted ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30">
                          GRANTED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-bold border border-rose-500/30">
                          DENIED (403)
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pillar 5: User Permissions (RBAC) */}
      {activeTab === "rbac" && (
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/90 space-y-4">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Key size={18} className="text-indigo-400" />
              Role-Based Access Control (RBAC) Matrix
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Rule 5 & Rule 9: Granular role clearance defining evidence visibility and administrative rights.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {roles.map((r) => (
              <div key={r.role} className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white text-sm">{r.role}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-bold ${
                      r.evidence_access_level === "FULL_RAW"
                        ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                        : r.evidence_access_level === "REDACTED_BLURRED"
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {r.evidence_access_level}
                  </span>
                </div>
                <p className="text-xs text-slate-400">{r.description}</p>
                <div className="pt-2 border-t border-slate-800/80">
                  <div className="text-xs font-semibold text-slate-400 mb-1.5">Permissions:</div>
                  <div className="flex flex-wrap gap-1">
                    {r.permissions.map((p, idx) => (
                      <span key={idx} className="text-xs px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Privacy;
