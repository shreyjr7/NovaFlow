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
    <div className="min-h-screen bg-transparent text-[#16192E] p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Toast */}
      {toastMsg && (
        <div className="fixed top-5 right-5 z-50 flex items-center gap-2 px-4 py-3 rounded-xl bg-indigo-600 text-white shadow-2xl animate-fade-in border border-indigo-400">
          <CheckCircle2 className="w-5 h-5" />
          <span className="text-sm font-semibold">{toastMsg}</span>
        </div>
      )}

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between pb-6 border-b border-[#E2E8F0] gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-purple-50 text-purple-700 rounded-2xl border border-purple-200 shadow-2xs">
              <Boxes className="w-7 h-7" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-[#16192E] flex items-center gap-2">
                AI Model Management Console
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> GUARDRAIL ACTIVE
                </span>
              </h1>
              <p className="text-xs text-[#64748B] mt-0.5">
                Lifecycle governance for the 6 core vision &amp; tracking models. Unvalidated candidate deployments are strictly prohibited.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={fetchModels}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-white hover:bg-[#F8FAFC] text-[#16192E] rounded-xl border border-[#CBD5E1] shadow-2xs transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-[#C85A17] ${loading ? "animate-spin" : ""}`} />
          Sync Models
        </button>
      </div>

      {/* ── KPI Summary Cards ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 bg-white rounded-2xl border border-[#E2E8F0] shadow-sm">
          <span className="text-[10px] font-bold uppercase text-[#64748B]">Registered Models</span>
          <div className="text-3xl font-extrabold text-[#16192E] mt-1">6</div>
          <span className="text-xs text-[#64748B]">Core vision &amp; OCR modules</span>
        </div>

        <div className="p-4 bg-white rounded-2xl border border-[#E2E8F0] shadow-sm">
          <span className="text-[10px] font-bold uppercase text-emerald-700">Active Deployments</span>
          <div className="text-3xl font-extrabold text-emerald-700 mt-1">6 / 6</div>
          <span className="text-xs text-[#64748B]">Running on 112 active buses</span>
        </div>

        <div className="p-4 bg-white rounded-2xl border border-[#E2E8F0] shadow-sm">
          <span className="text-[10px] font-bold uppercase text-amber-700">Validating Candidates</span>
          <div className="text-3xl font-extrabold text-amber-700 mt-1">3</div>
          <span className="text-xs text-[#64748B]">Testbed hardware benchmarking</span>
        </div>

        <div className="p-4 bg-white rounded-2xl border border-[#E2E8F0] shadow-sm">
          <span className="text-[10px] font-bold uppercase text-purple-700">Fleet Inference Speed</span>
          <div className="text-3xl font-extrabold text-purple-700 mt-1">28.4 <span className="text-sm font-normal text-[#64748B]">FPS</span></div>
          <span className="text-xs text-[#64748B]">Jetson Orin TensorRT FP16</span>
        </div>
      </div>

      {/* ── 6 Core AI Model Cards Grid ───────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {models.map((m) => (
          <div
            key={m.model_id}
            className="p-5 bg-white rounded-2xl border border-[#E2E8F0] hover:border-[#CBD5E1] transition-all shadow-sm space-y-4 flex flex-col justify-between"
          >
            <div className="space-y-3">
              {/* Card Header */}
              <div className="flex items-start justify-between">
                <div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-[#F8FAFC] text-[#C85A17] border border-[#E2E8F0]">
                    {m.current_active_version}
                  </span>
                  <h3 className="text-base font-bold text-[#16192E] mt-1">{m.name}</h3>
                </div>

                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {m.deployment_status}
                </span>
              </div>

              {/* Task & Dataset */}
              <div className="space-y-1 text-xs">
                <div className="text-[#64748B]">
                  Task: <strong className="text-[#16192E]">{m.task}</strong>
                </div>
                <div className="text-[#64748B]">
                  Dataset: <strong className="text-[#16192E]">{m.dataset}</strong>
                </div>
              </div>

              {/* Accuracy Metrics Grid */}
              <div className="p-3 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0]">
                <div className="text-[10px] font-bold uppercase text-[#64748B] mb-1.5">Live Accuracy Metrics:</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(m.accuracy_metrics).map(([k, v]: [string, any]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-[#64748B] font-mono text-[10px] uppercase">{k.replace("_", "@")}</span>
                      <span className="font-bold text-emerald-700">
                        {typeof v === "number" && v < 1 ? (v * 100).toFixed(1) + "%" : v}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="text-[11px] text-[#64748B]">Updated: {m.last_updated}</div>
            </div>

            {/* Action Buttons */}
            <div className="pt-3 border-t border-[#E2E8F0] flex items-center justify-between gap-2">
              <button
                onClick={() => handleViewModel(m.model_id)}
                className="px-3 py-1.5 text-xs font-semibold bg-white hover:bg-[#F8FAFC] text-[#16192E] border border-[#CBD5E1] rounded-xl shadow-2xs transition-all"
              >
                View Versions ({m.versions_count})
              </button>

              <button
                onClick={() => handleOpenCompare(m.model_id)}
                className="px-3 py-1.5 text-xs font-semibold bg-[#C85A17] hover:bg-[#B34F14] text-white rounded-xl shadow-sm transition-all flex items-center gap-1"
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
        <div className="fixed inset-0 z-50 bg-[#16192E]/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-[#E2E8F0] rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
              <div>
                <h3 className="text-lg font-bold text-[#16192E] flex items-center gap-2">
                  <Boxes className="w-5 h-5 text-[#C85A17]" />
                  {selectedModel.name} — Version History
                </h3>
                <p className="text-xs text-[#64748B]">Inspect versions, benchmarks, and deployment states.</p>
              </div>
              <button
                onClick={() => setVersionModalOpen(false)}
                className="text-[#64748B] hover:text-[#16192E]"
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
                        ? "bg-purple-50/50 border-purple-200"
                        : isValidating
                        ? "bg-amber-50/50 border-amber-200"
                        : "bg-[#F8FAFC] border-[#E2E8F0]"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-bold text-[#16192E]">{ver.version}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            isActive
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : isValidating
                              ? "bg-amber-50 text-amber-700 border border-amber-200"
                              : "bg-gray-100 text-gray-600 border border-gray-200"
                          }`}
                        >
                          {ver.deployment_status}
                        </span>

                        {!ver.is_validated && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-rose-50 text-rose-700 border border-rose-200 flex items-center gap-1">
                            <ShieldAlert className="w-3 h-3" /> UNVALIDATED
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {isActive ? (
                          <button
                            onClick={() => handleDeactivateVersion(selectedModel.model_id, ver.version)}
                            className="px-2.5 py-1 text-xs font-semibold bg-white border border-[#CBD5E1] hover:bg-[#F8FAFC] text-[#64748B] rounded-lg transition-all"
                          >
                            Deactivate
                          </button>
                        ) : (
                          <button
                            onClick={() => handleActivateVersion(selectedModel.model_id, ver.version)}
                            className={`px-3 py-1 text-xs font-bold rounded-lg transition-all flex items-center gap-1 ${
                              ver.is_validated
                                ? "bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs"
                                : "bg-gray-100 text-gray-400 border border-gray-200 cursor-not-allowed"
                            }`}
                          >
                            <Power className="w-3 h-3" />
                            {ver.is_validated ? "Deploy & Activate" : "Unvalidated (Blocked)"}
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs text-[#64748B] pt-1 border-t border-[#E2E8F0]">
                      <div>Dataset: <strong className="text-[#16192E]">{ver.dataset}</strong></div>
                      <div>Params: <strong className="text-[#16192E]">{ver.parameters_millions}M</strong></div>
                      <div>Released: <strong className="text-[#16192E]">{ver.release_date}</strong></div>
                      <div>FPS: <strong className="text-[#16192E]">{ver.accuracy_metrics?.fps ?? "N/A"}</strong></div>
                    </div>

                    {ver.validation_notes && (
                      <div className="text-xs text-[#64748B] italic">
                        Benchmark: {ver.validation_notes}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="flex justify-end pt-2 border-t border-[#E2E8F0]">
              <button
                onClick={() => setVersionModalOpen(false)}
                className="px-4 py-1.5 text-xs font-semibold bg-white border border-[#CBD5E1] hover:bg-[#F8FAFC] text-[#16192E] rounded-xl shadow-2xs transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Version Comparison Modal ────────────────────────────────────── */}
      {compareModalOpen && comparison && (
        <div className="fixed inset-0 z-50 bg-[#16192E]/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-[#E2E8F0] rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
              <div>
                <h3 className="text-lg font-bold text-[#16192E] flex items-center gap-2">
                  <GitCompare className="w-5 h-5 text-[#C85A17]" />
                  Compare Versions: {comparison.version_a.version} vs {comparison.version_b.version}
                </h3>
                <p className="text-xs text-[#64748B]">{comparison.model_name}</p>
              </div>
              <button
                onClick={() => setCompareModalOpen(false)}
                className="text-[#64748B] hover:text-[#16192E]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Side-by-side Table */}
            <div className="overflow-x-auto border border-[#E2E8F0] rounded-xl">
              <table className="w-full text-left text-xs text-[#16192E]">
                <thead className="bg-[#F8FAFC] uppercase text-[#64748B] border-b border-[#E2E8F0] text-[10px]">
                  <tr>
                    <th className="py-2.5 px-3">Metric / Property</th>
                    <th className="py-2.5 px-3">{comparison.version_a.version} (Active)</th>
                    <th className="py-2.5 px-3">{comparison.version_b.version} (Candidate)</th>
                    <th className="py-2.5 px-3">Diff</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E2E8F0]">
                  <tr>
                    <td className="py-2 px-3 font-semibold text-[#16192E]">Status</td>
                    <td className="py-2 px-3">{comparison.version_a.deployment_status}</td>
                    <td className="py-2 px-3">{comparison.version_b.deployment_status}</td>
                    <td className="py-2 px-3 text-[#64748B]">-</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold text-[#16192E]">Validation Gate</td>
                    <td className="py-2 px-3 text-emerald-700 font-bold">PASSED</td>
                    <td className="py-2 px-3 font-bold text-emerald-700">
                      {comparison.version_b.is_validated ? "PASSED" : "PENDING"}
                    </td>
                    <td className="py-2 px-3 text-[#64748B]">-</td>
                  </tr>
                  {Object.entries(comparison.metric_differences).map(([k, diff]: [string, any]) => {
                    const valA = comparison.version_a.accuracy_metrics?.[k] ?? "-";
                    const valB = comparison.version_b.accuracy_metrics?.[k] ?? "-";
                    return (
                      <tr key={k}>
                        <td className="py-2 px-3 font-semibold text-[#16192E] uppercase">{k.replace("_", "@")}</td>
                        <td className="py-2 px-3">{valA}</td>
                        <td className="py-2 px-3">{valB}</td>
                        <td className={`py-2 px-3 font-bold ${diff > 0 ? "text-emerald-700" : diff < 0 ? "text-rose-700" : "text-[#64748B]"}`}>
                          {diff > 0 ? `+${diff}` : diff}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Recommendation Box */}
            <div className="p-3.5 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] text-xs">
              <strong className="text-[#C85A17]">Deployment Recommendation:</strong>
              <p className="text-[#334155] mt-1">{comparison.recommendation}</p>
            </div>

            <div className="flex justify-end pt-2 border-t border-[#E2E8F0]">
              <button
                onClick={() => setCompareModalOpen(false)}
                className="px-4 py-1.5 text-xs font-semibold bg-white border border-[#CBD5E1] hover:bg-[#F8FAFC] text-[#16192E] rounded-xl shadow-2xs transition-all"
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
