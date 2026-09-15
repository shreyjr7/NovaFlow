// src/pages/AIModels/AIModelManagement.tsx
// Phase 32 — AI Model Management
// Manages the 6 core vision & ML models:
// 1. Road Defect Detection, 2. Vehicle Detection, 3. Vehicle Tracking,
// 4. Pedestrian Detection, 5. Plate Detection, 6. OCR.
// Displays: Model Name, Version, Task, Dataset, Accuracy Metrics, Deployment Status, Last Updated.
// Allows administrators to:
// - View model version
// - Activate model (with unvalidated deployment guardrail)
// - Deactivate model
// - Compare versions side-by-side

import React, { useState, useEffect } from "react";
import {
  Boxes, Cpu, CheckCircle2, AlertTriangle, Activity,
  ArrowRight, RefreshCw, X, ShieldAlert, Sliders, Layers,
  ChevronRight, Gauge, Check, Power, GitCompare
} from "lucide-react";

export interface AIModelSummary {
  model_id: string;
  name: string;
  current_active_version: string;
  task: string;
  dataset: string;
  accuracy_metrics: Record<string, any>;
  deployment_status: string;
  last_updated: string;
  versions_count: number;
}

export const AIModelManagement: React.FC = () => {
  const [models, setModels] = useState<AIModelSummary[]>([]);
  const [selectedModel, setSelectedModel] = useState<any>(null);
  const [comparison, setComparison] = useState<any>(null);
  const [compareModalOpen, setCompareModalOpen] = useState<boolean>(false);
  const [versionModalOpen, setVersionModalOpen] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(true);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const fetchModels = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/ai-models");
      if (res.ok) {
        setModels(await res.json());
      }
    } catch (e) {
      console.error("Failed to load AI models:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3500);
  };

  // Inspect Model Versions
  const handleViewModel = async (modelId: string) => {
    try {
      const res = await fetch(`/api/v1/ai-models/${modelId}`);
      if (res.ok) {
        setSelectedModel(await res.json());
        setVersionModalOpen(true);
      }
    } catch (e) {
      console.error("Failed to load model details:", e);
    }
  };

  // Activate Version with Guardrail check
  const handleActivateVersion = async (modelId: string, version: string) => {
    try {
      const res = await fetch(`/api/v1/ai-models/${modelId}/versions/${version}/activate`, {
        method: "POST",
      });
      if (res.ok) {
        showToast(`Model ${modelId} (${version}) activated successfully.`);
        fetchModels();
        if (selectedModel && selectedModel.model_id === modelId) {
          handleViewModel(modelId);
        }
      } else {
        const err = await res.json();
        showToast(`Deployment Blocked: ${err.detail}`);
      }
    } catch (e) {
      console.error("Failed to activate model:", e);
      showToast("Activation request failed.");
    }
  };

  // Deactivate Version
  const handleDeactivateVersion = async (modelId: string, version: string) => {
    try {
      const res = await fetch(`/api/v1/ai-models/${modelId}/versions/${version}/deactivate`, {
        method: "POST",
      });
      if (res.ok) {
        showToast(`Model ${modelId} (${version}) deactivated.`);
        fetchModels();
        if (selectedModel && selectedModel.model_id === modelId) {
          handleViewModel(modelId);
        }
      }
    } catch (e) {
      console.error("Failed to deactivate model:", e);
    }
  };

  // Compare Versions
  const handleOpenCompare = async (modelId: string) => {
    try {
      const res = await fetch(`/api/v1/ai-models/${modelId}`);
      if (res.ok) {
        const detail = await res.json();
        const v1 = detail.versions[0]?.version;
        const v2 = detail.versions[1]?.version;
        if (v1 && v2) {
          const compRes = await fetch(`/api/v1/ai-models/${modelId}/compare?v1=${v1}&v2=${v2}`);
          if (compRes.ok) {
            setComparison(await compRes.json());
            setCompareModalOpen(true);
          }
        }
      }
    } catch (e) {
      console.error("Failed to load comparison:", e);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      {/* Toast */}
      {toastMsg && (
        <div className="fixed top-5 right-5 z-50 flex items-center gap-2 px-4 py-3 rounded-xl bg-indigo-600 text-white shadow-2xl animate-fade-in border border-indigo-400">
          <CheckCircle2 className="w-5 h-5" />
          <span className="text-sm font-semibold">{toastMsg}</span>
        </div>
      )}

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between pb-6 border-b border-gray-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-purple-600/20 text-purple-400 rounded-2xl border border-purple-500/30">
              <Boxes className="w-7 h-7" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                AI Model Management Console
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> GUARDRAIL ACTIVE
                </span>
              </h1>
              <p className="text-xs text-gray-400 mt-0.5">
                Lifecycle governance for the 6 core vision & tracking models. Unvalidated candidate deployments are strictly prohibited.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={fetchModels}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl border border-gray-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-purple-400 ${loading ? "animate-spin" : ""}`} />
          Sync Models
        </button>
      </div>

      {/* ── KPI Summary Cards ───────────────────────────────────────────── */}
      <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 bg-gray-900 rounded-2xl border border-gray-800">
          <span className="text-2xs font-bold uppercase text-gray-400">Registered Models</span>
          <div className="text-3xl font-extrabold text-white mt-1">6</div>
          <span className="text-2xs text-gray-500">Core vision & OCR modules</span>
        </div>

        <div className="p-4 bg-gray-900 rounded-2xl border border-gray-800">
          <span className="text-2xs font-bold uppercase text-emerald-400">Active Deployments</span>
          <div className="text-3xl font-extrabold text-emerald-400 mt-1">6 / 6</div>
          <span className="text-2xs text-gray-500">Running on 112 active buses</span>
        </div>

        <div className="p-4 bg-gray-900 rounded-2xl border border-gray-800">
          <span className="text-2xs font-bold uppercase text-amber-400">Validating Candidates</span>
          <div className="text-3xl font-extrabold text-amber-400 mt-1">3</div>
          <span className="text-2xs text-gray-500">Testbed hardware benchmarking</span>
        </div>

        <div className="p-4 bg-gray-900 rounded-2xl border border-gray-800">
          <span className="text-2xs font-bold uppercase text-purple-400">Fleet Inference Speed</span>
          <div className="text-3xl font-extrabold text-purple-400 mt-1">28.4 <span className="text-sm font-normal text-gray-400">FPS</span></div>
          <span className="text-2xs text-gray-500">Jetson Orin TensorRT FP16</span>
        </div>
      </div>

      {/* ── 6 Core AI Model Cards Grid ───────────────────────────────────── */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {models.map((m) => (
          <div
            key={m.model_id}
            className="p-5 bg-gray-900 rounded-2xl border border-gray-800 hover:border-gray-700 transition shadow-xl space-y-4 flex flex-col justify-between"
          >
            <div className="space-y-3">
              {/* Card Header */}
              <div className="flex items-start justify-between">
                <div>
                  <span className="px-2 py-0.5 rounded text-2xs font-mono font-bold uppercase bg-purple-500/20 text-purple-300">
                    {m.current_active_version}
                  </span>
                  <h3 className="text-base font-bold text-white mt-1">{m.name}</h3>
                </div>

                <span className="px-2.5 py-0.5 rounded-full text-2xs font-bold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  {m.deployment_status}
                </span>
              </div>

              {/* Task & Dataset */}
              <div className="space-y-1 text-xs">
                <div className="text-gray-400">
                  Task: <strong className="text-gray-200">{m.task}</strong>
                </div>
                <div className="text-gray-400">
                  Dataset: <strong className="text-gray-200">{m.dataset}</strong>
                </div>
              </div>

              {/* Accuracy Metrics Grid */}
              <div className="p-3 bg-gray-950 rounded-xl border border-gray-850">
                <div className="text-2xs font-bold uppercase text-gray-400 mb-1.5">Live Accuracy Metrics:</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(m.accuracy_metrics).map(([k, v]: [string, any]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-gray-500 font-mono text-2xs uppercase">{k.replace("_", "@")}</span>
                      <span className="font-bold text-emerald-400">
                        {typeof v === "number" && v < 1 ? (v * 100).toFixed(1) + "%" : v}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="text-2xs text-gray-500">Updated: {m.last_updated}</div>
            </div>

            {/* Action Buttons */}
            <div className="pt-3 border-t border-gray-800 flex items-center justify-between gap-2">
              <button
                onClick={() => handleViewModel(m.model_id)}
                className="px-3 py-1.5 text-xs font-semibold bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition"
              >
                View Versions ({m.versions_count})
              </button>

              <button
                onClick={() => handleOpenCompare(m.model_id)}
                className="px-3 py-1.5 text-xs font-semibold bg-purple-950/60 hover:bg-purple-900/60 text-purple-300 border border-purple-800/40 rounded-lg transition flex items-center gap-1"
              >
                <GitCompare className="w-3.5 h-3.5" />
                Compare
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* ── Version Detail Modal ────────────────────────────────────────── */}
      {versionModalOpen && selectedModel && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Boxes className="w-5 h-5 text-purple-400" />
                  {selectedModel.name} — Version History
                </h3>
                <p className="text-xs text-gray-400">Inspect versions, benchmarks, and deployment states.</p>
              </div>
              <button
                onClick={() => setVersionModalOpen(false)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
              {selectedModel.versions.map((ver: any) => {
                const isActive = ver.deployment_status === "ACTIVE";
                const isValidating = ver.deployment_status === "VALIDATING";

                return (
                  <div
                    key={ver.version}
                    className={`p-4 rounded-xl border transition space-y-2 ${
                      isActive
                        ? "bg-purple-950/20 border-purple-800/50"
                        : isValidating
                        ? "bg-amber-950/10 border-amber-800/40"
                        : "bg-gray-950 border-gray-800"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-bold text-white">{ver.version}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-2xs font-bold uppercase ${
                            isActive
                              ? "bg-emerald-500/20 text-emerald-400"
                              : isValidating
                              ? "bg-amber-500/20 text-amber-400"
                              : "bg-gray-700 text-gray-300"
                          }`}
                        >
                          {ver.deployment_status}
                        </span>

                        {!ver.is_validated && (
                          <span className="px-2 py-0.5 rounded text-2xs font-bold uppercase bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-1">
                            <ShieldAlert className="w-3 h-3" /> UNVALIDATED
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {isActive ? (
                          <button
                            onClick={() => handleDeactivateVersion(selectedModel.model_id, ver.version)}
                            className="px-2.5 py-1 text-xs font-semibold bg-gray-800 hover:bg-gray-700 text-gray-300 rounded transition"
                          >
                            Deactivate
                          </button>
                        ) : (
                          <button
                            onClick={() => handleActivateVersion(selectedModel.model_id, ver.version)}
                            className={`px-3 py-1 text-xs font-bold rounded transition flex items-center gap-1 ${
                              ver.is_validated
                                ? "bg-emerald-700 hover:bg-emerald-600 text-white"
                                : "bg-gray-800 text-gray-500 cursor-not-allowed"
                            }`}
                          >
                            <Power className="w-3 h-3" />
                            {ver.is_validated ? "Deploy & Activate" : "Unvalidated (Blocked)"}
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-2xs text-gray-300 pt-1 border-t border-gray-850">
                      <div>Dataset: <strong>{ver.dataset}</strong></div>
                      <div>Params: <strong>{ver.parameters_millions}M</strong></div>
                      <div>Released: <strong>{ver.release_date}</strong></div>
                      <div>FPS: <strong>{ver.accuracy_metrics?.fps ?? "N/A"}</strong></div>
                    </div>

                    {ver.validation_notes && (
                      <div className="text-2xs text-gray-400 italic">
                        Benchmark: {ver.validation_notes}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="flex justify-end pt-2 border-t border-gray-800">
              <button
                onClick={() => setVersionModalOpen(false)}
                className="px-4 py-1.5 text-xs font-semibold bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Version Comparison Modal ────────────────────────────────────── */}
      {compareModalOpen && comparison && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <GitCompare className="w-5 h-5 text-purple-400" />
                  Compare Versions: {comparison.version_a.version} vs {comparison.version_b.version}
                </h3>
                <p className="text-xs text-gray-400">{comparison.model_name}</p>
              </div>
              <button
                onClick={() => setCompareModalOpen(false)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Side-by-side Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-gray-300">
                <thead className="bg-gray-950 uppercase text-gray-400 border-b border-gray-800">
                  <tr>
                    <th className="py-2.5 px-3">Metric / Property</th>
                    <th className="py-2.5 px-3">{comparison.version_a.version} (Active)</th>
                    <th className="py-2.5 px-3">{comparison.version_b.version} (Candidate)</th>
                    <th className="py-2.5 px-3">Diff</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  <tr>
                    <td className="py-2 px-3 font-semibold text-white">Status</td>
                    <td className="py-2 px-3">{comparison.version_a.deployment_status}</td>
                    <td className="py-2 px-3">{comparison.version_b.deployment_status}</td>
                    <td className="py-2 px-3 text-gray-400">-</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold text-white">Validation Gate</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">PASSED</td>
                    <td className="py-2 px-3 font-bold text-emerald-400">
                      {comparison.version_b.is_validated ? "PASSED" : "PENDING"}
                    </td>
                    <td className="py-2 px-3 text-gray-400">-</td>
                  </tr>
                  {Object.entries(comparison.metric_differences).map(([k, diff]: [string, any]) => {
                    const valA = comparison.version_a.accuracy_metrics?.[k] ?? "-";
                    const valB = comparison.version_b.accuracy_metrics?.[k] ?? "-";
                    return (
                      <tr key={k}>
                        <td className="py-2 px-3 font-semibold text-white uppercase">{k.replace("_", "@")}</td>
                        <td className="py-2 px-3">{valA}</td>
                        <td className="py-2 px-3">{valB}</td>
                        <td className={`py-2 px-3 font-bold ${diff > 0 ? "text-emerald-400" : diff < 0 ? "text-rose-400" : "text-gray-400"}`}>
                          {diff > 0 ? `+${diff}` : diff}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Recommendation Box */}
            <div className="p-3.5 bg-gray-950 rounded-xl border border-gray-800 text-xs">
              <strong className="text-purple-300">Deployment Recommendation:</strong>
              <p className="text-gray-300 mt-1">{comparison.recommendation}</p>
            </div>

            <div className="flex justify-end pt-2 border-t border-gray-800">
              <button
                onClick={() => setCompareModalOpen(false)}
                className="px-4 py-1.5 text-xs font-semibold bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AIModelManagement;
