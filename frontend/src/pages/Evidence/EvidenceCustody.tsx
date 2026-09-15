// src/pages/Evidence/EvidenceCustody.tsx
// Phase 27 — Evidence Chain of Custody & Cryptographic Verification

import React, { useState, useEffect } from "react";
import {
  ShieldCheck, ShieldAlert, Lock, CheckCircle2,
  XCircle, Clock, MapPin, Bus, Camera, FileText,
  RefreshCw, AlertTriangle, Download, Eye, Share2,
  Check, X, ShieldX, Copy
} from "lucide-react";

export interface CustodyAuditEvent {
  audit_id: string;
  stage: "Created" | "Accessed" | "Downloaded" | "Reviewed" | "Exported";
  timestamp: string;
  actor: string;
  actor_role: string;
  ip_address: string;
  notes?: string;
}

export interface EvidenceRecord {
  evidence_id: string;
  sha256_hash: string;
  timestamp: string;
  bus_id: string;
  camera_id: string;
  event_id: string;
  file_name: string;
  file_size_bytes: number;
  binary_payload: string;
  is_immutable: boolean;
  integrity_status: "VERIFIED" | "INTEGRITY CHECK FAILED";
  audit_history: CustodyAuditEvent[];
}

export const EvidenceCustody: React.FC = () => {
  const [evidenceList, setEvidenceList] = useState<EvidenceRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string>("EV_BUF_102_987");
  const [loading, setLoading] = useState<boolean>(true);
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState<boolean>(false);

  const fetchEvidence = async () => {
    try {
      const res = await fetch("/api/v1/evidence");
      if (res.ok) {
        const data = await res.json();
        setEvidenceList(data);
      }
    } catch (err) {
      console.error("Failed to load evidence records:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvidence();
  }, []);

  const selectedRecord = evidenceList.find((e) => e.evidence_id === selectedId) || evidenceList[0];

  const handleVerifyIntegrity = async (evidenceId: string) => {
    try {
      const res = await fetch(`/api/v1/evidence/${evidenceId}/verify-integrity`);
      if (res.ok) {
        const result = await res.json();
        setEvidenceList((prev) =>
          prev.map((e) => (e.evidence_id === evidenceId ? { ...e, integrity_status: result.evidence_integrity } : e))
        );
        setToastMsg(`Evidence Integrity: ${result.evidence_integrity}`);
        setTimeout(() => setToastMsg(null), 4000);
      }
    } catch (err) {
      console.error("Verification failed:", err);
    }
  };

  const handleSimulateTamper = async (evidenceId: string) => {
    try {
      const res = await fetch(`/api/v1/evidence/${evidenceId}/simulate-tamper`, { method: "POST" });
      if (res.ok) {
        const result = await res.json();
        setEvidenceList((prev) =>
          prev.map((e) => (e.evidence_id === evidenceId ? { ...e, integrity_status: result.evidence_integrity } : e))
        );
        setToastMsg(`TAMPER DETECTED! Evidence Integrity: ${result.evidence_integrity}`);
        setTimeout(() => setToastMsg(null), 5000);
      }
    } catch (err) {
      console.error("Tamper simulation failed:", err);
    }
  };

  const handleRecordCustodyStage = async (evidenceId: string, stage: "Accessed" | "Downloaded" | "Reviewed" | "Exported") => {
    try {
      const res = await fetch(`/api/v1/evidence/${evidenceId}/custody-action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          stage,
          actor: "Officer Miller",
          actor_role: "SAFETY_OFFICER",
          notes: `Action ${stage} performed from Chain of Custody dashboard.`,
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        setEvidenceList((prev) => prev.map((e) => (e.evidence_id === evidenceId ? updated : e)));
        setToastMsg(`Custody stage '${stage}' recorded in immutable audit ledger!`);
        setTimeout(() => setToastMsg(null), 3500);
      }
    } catch (err) {
      console.error("Custody action failed:", err);
    }
  };

  const handleTestAntiOverwrite = async () => {
    try {
      const duplicatePayload = {
        evidence_id: selectedRecord.evidence_id, // duplicate
        bus_id: selectedRecord.bus_id,
        camera_id: selectedRecord.camera_id,
        event_id: selectedRecord.event_id,
        file_name: "overwrite_attempt.mp4",
        file_size_bytes: 500,
        binary_payload: "TAMPERED_FORGERY_ATTEMPT",
      };

      const res = await fetch("/api/v1/evidence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(duplicatePayload),
      });

      if (res.status === 409) {
        const errData = await res.json();
        setToastMsg(`Anti-Overwrite Guardrail Active! 409 Conflict: ${errData.detail}`);
        setTimeout(() => setToastMsg(null), 5000);
      }
    } catch (err) {
      console.error("Overwrite test failed:", err);
    }
  };

  const copyHashToClipboard = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-400">
              <Lock size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
                Evidence Chain of Custody
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  Phase 27
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Cryptographic SHA-256 provenance manifests, immutable lifecycle audit stages & anti-overwrite integrity assurance.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchEvidence}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-sm font-medium transition"
          >
            <RefreshCw size={15} />
            Refresh Records
          </button>
          <a
            href="/privacy"
            className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium transition"
          >
            Privacy Dashboard
          </a>
          <a
            href="/"
            className="px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition"
          >
            &larr; Main Hub
          </a>
        </div>
      </div>

      {/* Toast popup */}
      {toastMsg && (
        <div className="p-3 bg-indigo-600 text-white text-sm rounded-lg flex items-center justify-between shadow-lg animate-fade-in">
          <span className="font-semibold flex items-center gap-2">
            <CheckCircle2 size={18} />
            {toastMsg}
          </span>
          <button onClick={() => setToastMsg(null)}>
            <X size={16} />
          </button>
        </div>
      )}

      {/* Main Grid: Selector & Evidence Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Evidence Records List */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/90 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Stored Incident Clips ({evidenceList.length})
            </span>
            <span className="text-xs text-slate-500 font-mono">AES-256 ENCRYPTED</span>
          </div>

          <div className="space-y-2.5">
            {evidenceList.map((rec) => {
              const isSelected = selectedRecord?.evidence_id === rec.evidence_id;
              const isVerified = rec.integrity_status === "VERIFIED";

              return (
                <div
                  key={rec.evidence_id}
                  onClick={() => setSelectedId(rec.evidence_id)}
                  className={`p-3.5 rounded-lg border cursor-pointer transition ${
                    isSelected
                      ? "border-amber-500/60 bg-slate-800/80 shadow-md"
                      : "border-slate-800/80 bg-slate-950/60 hover:bg-slate-850"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-sm text-indigo-400">
                      {rec.evidence_id}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded font-bold ${
                        isVerified
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          : "bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse"
                      }`}
                    >
                      {rec.integrity_status}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 mt-1 flex items-center gap-2">
                    <span className="font-bold text-slate-200">{rec.bus_id}</span>
                    <span>•</span>
                    <span>Event: {rec.event_id}</span>
                  </div>
                  <div className="text-xs text-slate-500 font-mono mt-1 truncate">
                    SHA256: {rec.sha256_hash.slice(0, 16)}...
                  </div>
                </div>
              );
            })}
          </div>

          <div className="pt-3 border-t border-slate-800">
            <button
              onClick={handleTestAntiOverwrite}
              className="w-full py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-rose-500/30 text-rose-300 font-semibold text-xs transition"
            >
              Test Anti-Overwrite Protection (409 Guardrail)
            </button>
          </div>
        </div>

        {/* Right Column: Selected Evidence Deep Inspector */}
        {selectedRecord && (
          <div className="lg:col-span-2 space-y-6">
            {/* Primary Cryptographic Manifest Card */}
            <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/90 space-y-5">
              {/* Status Header */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-slate-800 pb-4">
                <div>
                  <div className="text-xs font-mono text-slate-400">EVIDENCE MANIFEST</div>
                  <h2 className="text-xl font-bold text-white mt-0.5">{selectedRecord.evidence_id}</h2>
                  <div className="text-xs text-slate-400 mt-0.5">
                    File: <strong className="text-slate-200">{selectedRecord.file_name}</strong> ({(selectedRecord.file_size_bytes / 1024 / 1024).toFixed(1)} MB)
                  </div>
                </div>

                {/* Exact Prompt Display: Evidence Integrity: VERIFIED / INTEGRITY CHECK FAILED */}
                <div className="text-right">
                  <div className="text-xs text-slate-400 font-medium mb-1">Evidence Integrity:</div>
                  <div
                    className={`text-sm font-extrabold px-4 py-1.5 rounded-lg border font-mono tracking-wide ${
                      selectedRecord.integrity_status === "VERIFIED"
                        ? "bg-emerald-950/60 text-emerald-300 border-emerald-500/50 shadow-emerald-950/40 shadow-lg"
                        : "bg-rose-950/70 text-rose-300 border-rose-500/60 shadow-rose-950/40 shadow-lg animate-pulse"
                    }`}
                  >
                    {selectedRecord.integrity_status === "VERIFIED" ? "VERIFIED" : "INTEGRITY CHECK FAILED"}
                  </div>
                </div>
              </div>

              {/* Cryptographic Manifest Fields: SHA-256, Timestamp, Bus ID, Camera ID, Event ID */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
                  <div className="text-xs text-slate-400 flex items-center gap-1">
                    <Bus size={12} /> Bus ID
                  </div>
                  <div className="font-bold text-white text-sm mt-0.5">{selectedRecord.bus_id}</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
                  <div className="text-xs text-slate-400 flex items-center gap-1">
                    <Camera size={12} /> Camera ID
                  </div>
                  <div className="font-bold text-white text-sm mt-0.5">{selectedRecord.camera_id}</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
                  <div className="text-xs text-slate-400 flex items-center gap-1">
                    <FileText size={12} /> Event ID
                  </div>
                  <div className="font-bold text-white text-sm mt-0.5">{selectedRecord.event_id}</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
                  <div className="text-xs text-slate-400 flex items-center gap-1">
                    <Clock size={12} /> Timestamp
                  </div>
                  <div className="font-mono text-white text-xs mt-0.5">
                    {selectedRecord.timestamp.slice(11, 19)} UTC
                  </div>
                </div>
              </div>

              {/* Full SHA-256 Cryptographic Hash Banner */}
              <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-amber-400 flex items-center gap-1">
                    <Lock size={12} /> SHA-256 Cryptographic Hash Digest:
                  </span>
                  <button
                    onClick={() => copyHashToClipboard(selectedRecord.sha256_hash)}
                    className="text-slate-400 hover:text-white flex items-center gap-1 font-mono text-xs"
                  >
                    <Copy size={12} />
                    {copiedHash ? "Copied!" : "Copy Hash"}
                  </button>
                </div>
                <div className="font-mono text-xs text-slate-200 break-all select-all pt-1">
                  {selectedRecord.sha256_hash}
                </div>
              </div>

              {/* Action Toolbar */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleVerifyIntegrity(selectedRecord.evidence_id)}
                    className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition flex items-center gap-1.5"
                  >
                    <ShieldCheck size={14} />
                    Verify Integrity Now
                  </button>
                  <button
                    onClick={() => handleSimulateTamper(selectedRecord.evidence_id)}
                    className="px-3 py-2 rounded-lg bg-rose-950 hover:bg-rose-900 border border-rose-500/40 text-rose-300 text-xs font-semibold transition flex items-center gap-1.5"
                  >
                    <ShieldAlert size={14} />
                    Simulate Tamper / Bit Rot
                  </button>
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-slate-400 mr-1">Record Stage:</span>
                  <button
                    onClick={() => handleRecordCustodyStage(selectedRecord.evidence_id, "Accessed")}
                    className="px-2.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200"
                  >
                    Accessed
                  </button>
                  <button
                    onClick={() => handleRecordCustodyStage(selectedRecord.evidence_id, "Downloaded")}
                    className="px-2.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200"
                  >
                    Downloaded
                  </button>
                  <button
                    onClick={() => handleRecordCustodyStage(selectedRecord.evidence_id, "Reviewed")}
                    className="px-2.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200"
                  >
                    Reviewed
                  </button>
                  <button
                    onClick={() => handleRecordCustodyStage(selectedRecord.evidence_id, "Exported")}
                    className="px-2.5 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white"
                  >
                    Exported
                  </button>
                </div>
              </div>
            </div>

            {/* Immutable Chain-of-Custody Timeline: Created, Accessed, Downloaded, Reviewed, Exported */}
            <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/90 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <FileText size={18} className="text-amber-400" />
                  Immutable Chain-of-Custody Timeline ({selectedRecord.audit_history.length} Stages)
                </h3>
                <span className="text-xs font-mono text-emerald-400">APPEND-ONLY SECURE LEDGER</span>
              </div>

              <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
                {selectedRecord.audit_history.map((evt, idx) => (
                  <div key={idx} className="relative">
                    <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-amber-400 border-2 border-slate-900" />
                    <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800">
                      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-white">{evt.stage}</span>
                          <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                            {evt.actor} ({evt.actor_role})
                          </span>
                        </div>
                        <div className="text-xs font-mono text-slate-400">
                          {evt.timestamp.slice(0, 19).replace("T", " ")} UTC
                        </div>
                      </div>
                      {evt.notes && (
                        <p className="text-xs text-slate-300 mt-1.5">{evt.notes}</p>
                      )}
                      <div className="text-xs text-slate-500 font-mono mt-1">IP: {evt.ip_address}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default EvidenceCustody;
