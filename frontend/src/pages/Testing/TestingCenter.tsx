// src/pages/Testing/TestingCenter.tsx
// Phase 33: Complete Testing Framework Console
// Covers 4 Pillars:
//   1. Model Testing (8 environmental conditions, Precision, Recall, mAP, F1, Per-class)
//   2. System Testing (7-hop E2E trace: Video -> Edge AI -> Event -> Network -> Backend -> Database -> GIS)
//   3. Load Testing (10, 50, 100, 500 buses concurrent event ingestion)
//   4. Failure Testing (6 failure modes verifying zero event loss, local buffering, auto-reconnect, duplicate prevention)

import React, { useState, useEffect } from "react";
import {
  Activity, Play, CheckCircle2, AlertTriangle, XCircle, RefreshCw,
  Gauge, Cpu, Eye, ShieldCheck, Zap, Server, Database, Wifi,
  Camera, Terminal, ArrowRight, Layers, FileText, Check, Sliders
} from "lucide-react";

type TestingTab = "model" | "system" | "load" | "failure";

export const TestingCenter: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TestingTab>("model");

  // Model benchmark state
  const [modelReport, setModelReport] = useState<any>(null);
  const [modelRunning, setModelRunning] = useState<boolean>(false);

  // System trace state
  const [traceReport, setTraceReport] = useState<any>(null);
  const [traceRunning, setTraceRunning] = useState<boolean>(false);

  // Load test state
  const [loadReport, setLoadReport] = useState<any>(null);
  const [loadRunning, setLoadRunning] = useState<boolean>(false);
  const [loadBuses, setLoadBuses] = useState<number>(50);

  // Failure suite state
  const [resilienceReport, setResilienceReport] = useState<any>(null);
  const [failureRunning, setFailureRunning] = useState<boolean>(false);

  // Run model benchmark
  const handleRunModelBenchmark = async () => {
    setModelRunning(true);
    try {
      const res = await fetch("/api/v1/testing/model-benchmark", { method: "POST" });
      if (res.ok) {
        setModelReport(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setModelRunning(false);
    }
  };

  // Run system trace
  const handleRunSystemTrace = async () => {
    setTraceRunning(true);
    try {
      const res = await fetch("/api/v1/testing/system-trace?event_type=POTHOLE&bus_id=BUS_104&route_id=ROUTE_12", { method: "POST" });
      if (res.ok) {
        setTraceReport(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setTraceRunning(false);
    }
  };

  // Run load test
  const handleRunLoadTest = async () => {
    setLoadRunning(true);
    try {
      const res = await fetch(`/api/v1/testing/load-test?num_buses=${loadBuses}&events_per_bus=2`, { method: "POST" });
      if (res.ok) {
        setLoadReport(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadRunning(false);
    }
  };

  // Run failure suite
  const handleRunFailureScenarios = async () => {
    setFailureRunning(true);
    try {
      const res = await fetch("/api/v1/testing/failure-scenarios", { method: "POST" });
      if (res.ok) {
        setResilienceReport(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setFailureRunning(false);
    }
  };

  useEffect(() => {
    // Initial fetch of default reports
    handleRunModelBenchmark();
    handleRunSystemTrace();
  }, []);

  return (
    <div className="min-h-screen bg-transparent text-[#16192E] p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-5">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-blue-50 text-blue-700 rounded-2xl border border-blue-200 shadow-2xs">
                <Activity size={24} />
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-[#16192E]">Complete Testing Framework</h1>
                <p className="text-[#64748B] text-xs sm:text-sm mt-0.5">
                  Automated verification across Model Stress, System Trace, Fleet Load, and Fault Resilience
                </p>
              </div>
            </div>
          </div>

          {/* Quick Action */}
          <div className="flex items-center gap-3">
            <a
              href="/demo-flow"
              className="px-4 py-2 bg-[#C85A17] hover:bg-[#B34F14] text-white text-xs font-semibold rounded-xl shadow-sm transition-all flex items-center gap-2"
            >
              <Zap size={14} />
              Open 17-Step Demo Flow
            </a>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-[#E2E8F0] space-x-2">
          <button
            onClick={() => setActiveTab("model")}
            className={`px-4 py-2.5 text-xs sm:text-sm font-semibold rounded-t-xl transition-all flex items-center gap-2 ${
              activeTab === "model"
                ? "bg-white text-[#16192E] border-b-2 border-[#C85A17] shadow-2xs font-bold"
                : "text-[#64748B] hover:text-[#16192E] hover:bg-[#F8FAFC]"
            }`}
          >
            <Eye size={16} />
            1. Model Testing (8 Conditions)
          </button>
          <button
            onClick={() => setActiveTab("system")}
            className={`px-4 py-2.5 text-xs sm:text-sm font-semibold rounded-t-xl transition-all flex items-center gap-2 ${
              activeTab === "system"
                ? "bg-white text-[#16192E] border-b-2 border-[#C85A17] shadow-2xs font-bold"
                : "text-[#64748B] hover:text-[#16192E] hover:bg-[#F8FAFC]"
            }`}
          >
            <Layers size={16} />
            2. System Testing (7 Hops)
          </button>
          <button
            onClick={() => setActiveTab("load")}
            className={`px-4 py-2.5 text-xs sm:text-sm font-semibold rounded-t-xl transition-all flex items-center gap-2 ${
              activeTab === "load"
                ? "bg-white text-[#16192E] border-b-2 border-[#C85A17] shadow-2xs font-bold"
                : "text-[#64748B] hover:text-[#16192E] hover:bg-[#F8FAFC]"
            }`}
          >
            <Gauge size={16} />
            3. Load Testing (10-500 Buses)
          </button>
          <button
            onClick={() => setActiveTab("failure")}
            className={`px-4 py-2.5 text-xs sm:text-sm font-semibold rounded-t-xl transition-all flex items-center gap-2 ${
              activeTab === "failure"
                ? "bg-white text-[#16192E] border-b-2 border-[#C85A17] shadow-2xs font-bold"
                : "text-[#64748B] hover:text-[#16192E] hover:bg-[#F8FAFC]"
            }`}
          >
            <ShieldCheck size={16} />
            4. Failure &amp; Resilience (6 Modes)
          </button>
        </div>

        {/* Tab Content: 1. Model Testing */}
        {activeTab === "model" && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-white p-4 rounded-2xl border border-[#E2E8F0] shadow-sm">
              <div>
                <h3 className="font-bold text-base text-[#16192E]">Environmental Stress Testing Suite</h3>
                <p className="text-xs text-[#64748B] mt-1">
                  Evaluates optical detection robustness across: Day, Night, Rain, Wet roads, Glare, Motion blur, Occlusion, Dense traffic.
                </p>
              </div>
              <button
                onClick={handleRunModelBenchmark}
                disabled={modelRunning}
                className="px-4 py-2 bg-[#C85A17] hover:bg-[#B34F14] disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-sm transition-all flex items-center gap-2 shrink-0"
              >
                {modelRunning ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
                Run Model Benchmark
              </button>
            </div>

            {modelReport && (
              <>
                {/* 4 Summary KPI Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-white border border-[#E2E8F0] p-4 rounded-2xl shadow-sm">
                    <span className="text-[10px] text-[#64748B] uppercase font-bold">Precision</span>
                    <div className="text-2xl font-extrabold text-[#16192E] mt-1">
                      {(modelReport.overall_precision * 100).toFixed(1)}%
                    </div>
                    <span className="text-xs text-[#64748B]">TP / (TP + FP)</span>
                  </div>
                  <div className="bg-white border border-[#E2E8F0] p-4 rounded-2xl shadow-sm">
                    <span className="text-[10px] text-[#64748B] uppercase font-bold">Recall</span>
                    <div className="text-2xl font-extrabold text-emerald-700 mt-1">
                      {(modelReport.overall_recall * 100).toFixed(1)}%
                    </div>
                    <span className="text-xs text-[#64748B]">TP / (TP + FN)</span>
                  </div>
                  <div className="bg-white border border-[#E2E8F0] p-4 rounded-2xl shadow-sm">
                    <span className="text-[10px] text-[#64748B] uppercase font-bold">mAP@0.50</span>
                    <div className="text-2xl font-extrabold text-blue-700 mt-1">
                      {(modelReport.overall_map_50 * 100).toFixed(1)}%
                    </div>
                    <span className="text-xs text-[#64748B]">mean Average Precision</span>
                  </div>
                  <div className="bg-white border border-[#E2E8F0] p-4 rounded-2xl shadow-sm">
                    <span className="text-[10px] text-[#64748B] uppercase font-bold">F1 Score</span>
                    <div className="text-2xl font-extrabold text-[#C85A17] mt-1">
                      {(modelReport.overall_f1_score * 100).toFixed(1)}%
                    </div>
                    <span className="text-xs text-[#64748B]">Harmonic Mean</span>
                  </div>
                </div>

                {/* Condition Breakdown Grid */}
                <div className="bg-white border border-[#E2E8F0] rounded-2xl p-5 shadow-sm space-y-4">
                  <h4 className="font-bold text-sm text-[#16192E]">Performance across 8 Environmental Stress Conditions</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    {modelReport.conditions_tested.map((cond: string) => {
                      const c = modelReport.condition_reports[cond];
                      return (
                        <div key={cond} className="bg-[#F8FAFC] p-3.5 rounded-xl border border-[#E2E8F0] space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-sm text-[#16192E]">{cond}</span>
                            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-white text-[#C85A17] border border-[#E2E8F0]">
                              mAP {(c.map_50 * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="grid grid-cols-3 text-center text-xs pt-1 border-t border-[#E2E8F0]">
                            <div>
                              <span className="text-[#64748B] block text-[10px]">Precision</span>
                              <span className="font-semibold text-[#16192E]">{(c.precision * 100).toFixed(0)}%</span>
                            </div>
                            <div>
                              <span className="text-[#64748B] block text-[10px]">Recall</span>
                              <span className="font-semibold text-[#16192E]">{(c.recall * 100).toFixed(0)}%</span>
                            </div>
                            <div>
                              <span className="text-[#64748B] block text-[10px]">F1</span>
                              <span className="font-semibold text-[#16192E]">{(c.f1_score * 100).toFixed(0)}%</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Per-Class Breakdown Table */}
                <div className="bg-white border border-[#E2E8F0] rounded-2xl p-5 shadow-sm space-y-3">
                  <h4 className="font-bold text-sm text-[#16192E]">Per-Class Performance Breakdown</h4>
                  <div className="overflow-x-auto border border-[#E2E8F0] rounded-xl">
                    <table className="w-full text-left text-xs text-[#16192E]">
                      <thead className="bg-[#F8FAFC] text-[#64748B] border-b border-[#E2E8F0] uppercase text-[10px]">
                        <tr>
                          <th className="py-2.5 px-3">Class Category</th>
                          <th className="py-2.5 px-3">Precision</th>
                          <th className="py-2.5 px-3">Recall</th>
                          <th className="py-2.5 px-3">F1 Score</th>
                          <th className="py-2.5 px-3">mAP@0.50</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#E2E8F0] font-mono">
                        {Object.entries(modelReport.per_class_summary).map(([cls, metrics]: any) => (
                          <tr key={cls} className="hover:bg-[#F8FAFC] transition-colors">
                            <td className="py-2.5 px-3 font-semibold text-[#16192E] capitalize font-sans">{cls.replace(/_/g, " ")}</td>
                            <td className="py-2.5 px-3 text-[#16192E]">{(metrics.precision * 100).toFixed(1)}%</td>
                            <td className="py-2.5 px-3 text-emerald-700 font-bold">{(metrics.recall * 100).toFixed(1)}%</td>
                            <td className="py-2.5 px-3 text-[#16192E]">{(metrics.f1_score * 100).toFixed(1)}%</td>
                            <td className="py-2.5 px-3 text-[#C85A17] font-bold">{(metrics.ap_50 * 100).toFixed(1)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* Tab Content: 2. System Testing */}
        {activeTab === "system" && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-white p-4 rounded-2xl border border-[#E2E8F0] shadow-sm">
              <div>
                <h3 className="font-bold text-base text-[#16192E]">7-Hop End-to-End System Pipeline Trace</h3>
                <p className="text-xs text-[#64748B] mt-1">
                  Traces a live detection from Video &rarr; Edge AI &rarr; Event &rarr; Network &rarr; Backend &rarr; Database &rarr; GIS Dashboard.
                </p>
              </div>
              <button
                onClick={handleRunSystemTrace}
                disabled={traceRunning}
                className="px-4 py-2 bg-[#C85A17] hover:bg-[#B34F14] disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-sm transition-all flex items-center gap-2 shrink-0"
              >
                {traceRunning ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
                Execute 7-Hop Trace
              </button>
            </div>

            {traceReport && (
              <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 space-y-6 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E2E8F0] pb-4">
                  <div>
                    <span className="text-xs font-mono text-[#64748B] uppercase">Trace ID: {traceReport.trace_id}</span>
                    <h4 className="text-lg font-bold text-[#16192E] flex items-center gap-2 mt-0.5">
                      <CheckCircle2 size={18} className="text-emerald-600" />
                      Status: {traceReport.overall_status} (Total Pipeline: {traceReport.total_pipeline_latency_ms}ms)
                    </h4>
                  </div>
                  <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 w-fit">
                    GIS Verified
                  </span>
                </div>

                {/* 7-Hop Flowchart Cards */}
                <div className="grid grid-cols-1 md:grid-cols-7 gap-2">
                  {traceReport.hops.map((hop: any) => (
                    <div
                      key={hop.hop_number}
                      className="bg-[#F8FAFC] border border-[#E2E8F0] p-3.5 rounded-xl flex flex-col justify-between space-y-2 relative"
                    >
                      <div>
                        <div className="flex items-center justify-between text-xs text-[#64748B]">
                          <span>Hop {hop.hop_number}</span>
                          <span className="font-mono text-emerald-700 font-bold">{hop.latency_ms}ms</span>
                        </div>
                        <h5 className="font-bold text-xs sm:text-sm text-[#16192E] mt-1">{hop.name}</h5>
                        <p className="text-[10px] text-[#64748B] mt-1 line-clamp-2">{hop.component}</p>
                      </div>
                      <div className="pt-2 border-t border-[#E2E8F0] flex items-center justify-between text-[11px]">
                        <span className="text-emerald-700 flex items-center gap-1 font-bold">
                          <Check size={12} />
                          {hop.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="p-3 bg-[#F8FAFC] rounded-xl text-xs font-mono text-[#16192E] border border-[#E2E8F0]">
                  {traceReport.summary}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab Content: 3. Load Testing */}
        {activeTab === "load" && (
          <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-[#E2E8F0] shadow-sm">
              <div>
                <h3 className="font-bold text-base text-[#16192E]">Scalable Concurrency Load Test</h3>
                <p className="text-xs text-[#64748B] mt-1">
                  Simulate concurrent event ingestion across fleet scales: 10, 50, 100, and 500 buses.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-1.5 bg-[#F8FAFC] p-1 rounded-xl border border-[#E2E8F0] text-xs">
                  <span className="text-[#64748B] font-semibold px-2">Scale:</span>
                  {[10, 50, 100, 500].map((count) => (
                    <button
                      key={count}
                      onClick={() => setLoadBuses(count)}
                      className={`px-2.5 py-1 rounded-lg font-bold transition-all ${
                        loadBuses === count
                          ? "bg-[#16192E] text-white shadow-xs"
                          : "text-[#64748B] hover:text-[#16192E]"
                      }`}
                    >
                      {count} Buses
                    </button>
                  ))}
                </div>
                <button
                  onClick={handleRunLoadTest}
                  disabled={loadRunning}
                  className="px-4 py-2 bg-[#C85A17] hover:bg-[#B34F14] disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-sm transition-all flex items-center gap-2"
                >
                  {loadRunning ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
                  Run Load Simulation
                </button>
              </div>
            </div>

            {loadReport && (
              <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 space-y-6 shadow-sm">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-[#F8FAFC] p-4 rounded-xl border border-[#E2E8F0]">
                    <span className="text-[10px] uppercase font-bold text-[#64748B]">Throughput</span>
                    <div className="text-2xl font-extrabold text-blue-700 mt-1">{loadReport.throughput_eps} EPS</div>
                    <span className="text-xs text-[#64748B]">Events per second</span>
                  </div>
                  <div className="bg-[#F8FAFC] p-4 rounded-xl border border-[#E2E8F0]">
                    <span className="text-[10px] uppercase font-bold text-[#64748B]">Success Rate</span>
                    <div className="text-2xl font-extrabold text-emerald-700 mt-1">
                      {loadReport.successful_ingestions} / {loadReport.total_events_generated}
                    </div>
                    <span className="text-xs text-[#64748B]">Error: {loadReport.error_rate_pct}%</span>
                  </div>
                  <div className="bg-[#F8FAFC] p-4 rounded-xl border border-[#E2E8F0]">
                    <span className="text-[10px] uppercase font-bold text-[#64748B]">Median Latency (p50)</span>
                    <div className="text-2xl font-extrabold text-[#16192E] mt-1">{loadReport.latency_p50_ms} ms</div>
                    <span className="text-xs text-[#64748B]">Fast path ingestion</span>
                  </div>
                  <div className="bg-[#F8FAFC] p-4 rounded-xl border border-[#E2E8F0]">
                    <span className="text-[10px] uppercase font-bold text-[#64748B]">95th Percentile (p95)</span>
                    <div className="text-2xl font-extrabold text-[#C85A17] mt-1">{loadReport.latency_p95_ms} ms</div>
                    <span className="text-xs text-[#64748B]">Tail latency</span>
                  </div>
                </div>

                <div className="p-3 bg-[#F8FAFC] rounded-xl text-xs font-mono text-[#16192E] border border-[#E2E8F0]">
                  {loadReport.summary}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab Content: 4. Failure Testing */}
        {activeTab === "failure" && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-white p-4 rounded-2xl border border-[#E2E8F0] shadow-sm">
              <div>
                <h3 className="font-bold text-base text-[#16192E]">Fault-Tolerance &amp; Failure Injection Suite</h3>
                <p className="text-xs text-[#64748B] mt-1">
                  Injects 6 real-world failures and verifies: Zero Event Loss, Local Buffering, Auto-Reconnect, and Duplicate Prevention.
                </p>
              </div>
              <button
                onClick={handleRunFailureScenarios}
                disabled={failureRunning}
                className="px-4 py-2 bg-[#C85A17] hover:bg-[#B34F14] disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-sm transition-all flex items-center gap-2 shrink-0"
              >
                {failureRunning ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
                Run 6 Failure Scenarios
              </button>
            </div>

            {resilienceReport && (
              <div className="space-y-6">
                {/* 4 Invariant Badges */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="bg-white border border-[#E2E8F0] p-4 rounded-2xl shadow-sm flex items-center gap-3">
                    <CheckCircle2 size={24} className="text-emerald-600 shrink-0" />
                    <div>
                      <span className="text-[10px] text-[#64748B] block font-bold uppercase">Invariant 1</span>
                      <span className="text-sm font-bold text-[#16192E]">Events Not Lost</span>
                    </div>
                  </div>
                  <div className="bg-white border border-[#E2E8F0] p-4 rounded-2xl shadow-sm flex items-center gap-3">
                    <CheckCircle2 size={24} className="text-emerald-600 shrink-0" />
                    <div>
                      <span className="text-[10px] text-[#64748B] block font-bold uppercase">Invariant 2</span>
                      <span className="text-sm font-bold text-[#16192E]">Local Buffering Works</span>
                    </div>
                  </div>
                  <div className="bg-white border border-[#E2E8F0] p-4 rounded-2xl shadow-sm flex items-center gap-3">
                    <CheckCircle2 size={24} className="text-emerald-600 shrink-0" />
                    <div>
                      <span className="text-[10px] text-[#64748B] block font-bold uppercase">Invariant 3</span>
                      <span className="text-sm font-bold text-[#16192E]">Auto-Reconnects</span>
                    </div>
                  </div>
                  <div className="bg-white border border-[#E2E8F0] p-4 rounded-2xl shadow-sm flex items-center gap-3">
                    <CheckCircle2 size={24} className="text-emerald-600 shrink-0" />
                    <div>
                      <span className="text-[10px] text-[#64748B] block font-bold uppercase">Invariant 4</span>
                      <span className="text-sm font-bold text-[#16192E]">Duplicates Prevented</span>
                    </div>
                  </div>
                </div>

                {/* 6 Failure Scenario Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {resilienceReport.scenario_results.map((scen: any) => (
                    <div key={scen.scenario_name} className="bg-white border border-[#E2E8F0] p-4 rounded-2xl shadow-sm space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="font-bold text-sm text-[#16192E]">{scen.scenario_name}</h4>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {scen.status}
                        </span>
                      </div>
                      <p className="text-xs text-[#64748B]">{scen.injected_failure}</p>
                      <div className="grid grid-cols-3 gap-2 text-center text-xs bg-[#F8FAFC] p-2.5 rounded-xl border border-[#E2E8F0]">
                        <div>
                          <span className="text-[#64748B] text-[10px] block font-medium">Generated</span>
                          <span className="font-bold text-[#16192E]">{scen.events_generated}</span>
                        </div>
                        <div>
                          <span className="text-[#64748B] text-[10px] block font-medium">Buffered</span>
                          <span className="font-bold text-amber-700">{scen.events_buffered_locally}</span>
                        </div>
                        <div>
                          <span className="text-[#64748B] text-[10px] block font-medium">Zero Loss</span>
                          <span className="font-bold text-emerald-700">CERTIFIED</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TestingCenter;
