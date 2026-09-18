// src/pages/DemoFlow/DemoFlowTheater.tsx
// Phase 35: The Complete End-to-End Demonstration Scenario & Theater
// Demonstrates Bus 104 on Route 12 through all 17 canonical steps:
// Video -> Detection -> Tracking -> Traffic Bottleneck -> Pothole Detection -> GPS
// -> Offline Local Buffering -> Reconnection -> Central Ingestion -> Deduplication
// -> GIS Map -> Alert -> Verification -> Maintenance Ticket -> Second Bus Confirmation
// -> Analytics Update -> Post-Repair Resolution.
// Also includes the Vehicle Incident Investigation pipeline.

import React, { useState, useEffect } from "react";
import {
  Play, Pause, RotateCcw, ChevronRight, ChevronLeft, CheckCircle2,
  AlertTriangle, Shield, Wifi, WifiOff, Car, Camera, MapPin,
  FileText, ArrowRight, Activity, Zap, Check, Eye, Clock, Tool,
  ExternalLink, Wrench
} from "lucide-react";

export const DemoFlowTheater: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [scenarioState, setScenarioState] = useState<any>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [historyLogs, setHistoryLogs] = useState<any[]>([]);
  const [incidentModalOpen, setIncidentModalOpen] = useState<boolean>(false);
  const [incidentResult, setIncidentResult] = useState<any>(null);

  const fetchState = async () => {
    try {
      const res = await fetch("/api/v1/demo-flow/state");
      if (res.ok) {
        const data = await res.json();
        setScenarioState(data.scenario_state);
        setCurrentStep(data.current_step || 1);
        setHistoryLogs(data.scenario_state.history_log || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleStep = async (stepNum: number) => {
    try {
      const res = await fetch(`/api/v1/demo-flow/step/${stepNum}`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setCurrentStep(data.current_step);
        setScenarioState(data.scenario_state);
        setHistoryLogs(data.scenario_state.history_log || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleReset = async () => {
    setIsPlaying(false);
    try {
      const res = await fetch("/api/v1/demo-flow/reset", { method: "POST" });
      if (res.ok) {
        await handleStep(1);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Autonomous auto-play through 17 steps
  useEffect(() => {
    let timer: any;
    if (isPlaying) {
      if (currentStep < 17) {
        timer = setTimeout(() => {
          handleStep(currentStep + 1);
        }, 1800);
      } else {
        setIsPlaying(false);
      }
    }
    return () => clearTimeout(timer);
  }, [isPlaying, currentStep]);

  useEffect(() => {
    fetchState();
  }, []);

  const handleRunIncident = async () => {
    try {
      const res = await fetch("/api/v1/demo-flow/incident-run?vehicle_id=TRACK_VEH_842&plate_text=DL+01+AB+1234", { method: "POST" });
      if (res.ok) {
        setIncidentResult(await res.json());
        setIncidentModalOpen(true);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const STEP_TITLES = [
    "1. Video Processing",
    "2. Vehicle Detection",
    "3. Traffic Tracking",
    "4. Bottleneck Detection",
    "5. Pothole Detection",
    "6. GPS Attachment",
    "7. Network Loss & Local Buffer",
    "8. Reconnect & Transmit",
    "9. Backend Ingestion",
    "10. Deduplication Check",
    "11. GIS Map Appearance",
    "12. Authority Alert",
    "13. Authority Verification",
    "14. Ticket Creation",
    "15. Bus 109 Reinforcement",
    "16. Analytics Update",
    "17. Repair & Resolution",
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-3 sm:p-5 lg:p-8">
      <div className="max-w-7xl mx-auto space-y-4 sm:space-y-6">
        {/* Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-xl shadow-lg">
                <Zap size={24} />
              </div>
              <div>
                <h1 className="text-xl sm:text-2xl md:text-3xl font-extrabold tracking-tight">
                  End-to-End Demo Flow Theater
                </h1>
                <p className="text-slate-400 text-sm mt-0.5">
                  Live Demonstration: Bus 104 on Route 12 through complete 17-step lifecycle & Incident Pipeline
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRunIncident}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold rounded-lg transition shadow flex items-center gap-2"
            >
              <AlertTriangle size={14} />
              Demonstrate Incident Flow
            </button>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className={`px-4 py-2 text-white text-xs font-bold rounded-lg transition shadow flex items-center gap-2 ${
                isPlaying ? "bg-amber-600 hover:bg-amber-500" : "bg-emerald-600 hover:bg-emerald-500"
              }`}
            >
              {isPlaying ? <Pause size={14} /> : <Play size={14} />}
              {isPlaying ? "Pause Flow" : "Run Autonomous 17-Step Demo"}
            </button>
            <button
              onClick={handleReset}
              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold rounded-lg transition flex items-center gap-1.5"
            >
              <RotateCcw size={14} />
              Reset
            </button>
          </div>
        </div>

        {/* 17-Step Horizontal Stepper Bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 overflow-x-auto">
          <div className="flex items-center min-w-max space-x-1.5">
            {STEP_TITLES.map((title, idx) => {
              const sNum = idx + 1;
              const isPast = sNum < currentStep;
              const isCurr = sNum === currentStep;
              return (
                <button
                  key={sNum}
                  onClick={() => {
                    setIsPlaying(false);
                    handleStep(sNum);
                  }}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                    isCurr
                      ? "bg-indigo-600 text-white shadow-lg ring-2 ring-indigo-400/50"
                      : isPast
                      ? "bg-emerald-950/60 text-emerald-300 border border-emerald-800/60"
                      : "bg-slate-950 text-slate-400 hover:bg-slate-800 border border-slate-800"
                  }`}
                >
                  {isPast ? <Check size={12} className="text-emerald-400" /> : <span className="font-mono">{sNum}</span>}
                  <span className="hidden lg:inline">{title.split(". ")[1]}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Stage Visualization Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Simulated Video / Optical Detection View */}
          <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-slate-200 font-bold text-sm">
                <Camera size={18} className="text-indigo-400" />
                Bus 104 Road-Facing Camera &bull; Route 12
              </div>
              <span className="flex items-center gap-1.5 text-xs font-mono text-emerald-400 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                LIVE STREAM 30 FPS
              </span>
            </div>

            {/* Simulated Frame Canvas */}
            <div className="relative aspect-video bg-gradient-to-b from-slate-900 via-slate-950 to-slate-900 rounded-xl overflow-hidden border border-slate-800 flex flex-col justify-between p-4">
              {/* Overlay HUD */}
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 bg-black/60 px-3 py-1.5 rounded-lg border border-white/10 backdrop-blur-sm">
                <span>VEHICLE: BUS-104 (Tata JanBus)</span>
                <span>SPEED: {scenarioState?.traffic_telemetry?.average_speed_kmh || 8.5} km/h</span>
                <span>GPS: 28.6322° N, 77.2198° E</span>
              </div>

              {/* Bounding Boxes Simulation based on current step */}
              <div className="relative w-full h-48 flex items-center justify-center">
                {currentStep >= 2 && currentStep <= 4 && (
                  <div className="absolute inset-0 flex items-center justify-center gap-6">
                    <div className="border-2 border-indigo-400 bg-indigo-500/20 text-indigo-200 text-[10px] font-mono px-2 py-1 rounded shadow-lg">
                      Car #01 (0.96)
                    </div>
                    <div className="border-2 border-cyan-400 bg-cyan-500/20 text-cyan-200 text-[10px] font-mono px-2 py-1 rounded shadow-lg">
                      Bus #02 (0.94)
                    </div>
                    <div className="border-2 border-amber-400 bg-amber-500/20 text-amber-200 text-[10px] font-mono px-2 py-1 rounded shadow-lg">
                      Motorcycle #03 (0.91)
                    </div>
                  </div>
                )}

                {currentStep >= 5 && currentStep <= 16 && (
                  <div className="border-2 border-rose-500 bg-rose-500/20 text-rose-200 px-4 py-2 rounded-xl text-center shadow-xl animate-pulse">
                    <div className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5">
                      <AlertTriangle size={14} />
                      ROAD DEFECT: POTHOLE DETECTED
                    </div>
                    <div className="text-[11px] font-mono mt-1 opacity-90">
                      Depth: 7.4 cm &bull; Diam: 45 cm &bull; Conf: {(scenarioState?.cluster_confidence * 100 || 84).toFixed(0)}%
                    </div>
                    {scenarioState?.observation_count > 1 && (
                      <div className="text-[10px] font-bold text-amber-300 mt-1 bg-black/40 py-0.5 px-2 rounded">
                        Reinforced by Bus 109 &bull; Observations: {scenarioState.observation_count}
                      </div>
                    )}
                  </div>
                )}

                {currentStep === 17 && (
                  <div className="border-2 border-emerald-500 bg-emerald-500/20 text-emerald-200 px-5 py-3 rounded-xl text-center shadow-xl">
                    <div className="text-sm font-bold uppercase tracking-wider flex items-center justify-center gap-1.5">
                      <CheckCircle2 size={16} />
                      ROAD RESURFACING COMPLETED
                    </div>
                    <div className="text-xs font-mono mt-1 opacity-90">
                      Authority Status: RESOLVED &bull; Verification Confirmed
                    </div>
                  </div>
                )}
              </div>

              {/* Bottom Telemetry HUD */}
              <div className="flex items-center justify-between text-xs font-mono bg-black/60 px-3 py-2 rounded-lg border border-white/10 backdrop-blur-sm">
                <span className="text-indigo-300">
                  Step {currentStep}: {STEP_TITLES[currentStep - 1]}
                </span>
                <span className="flex items-center gap-1.5">
                  {scenarioState?.network_state === "ONLINE" ? (
                    <span className="text-emerald-400 flex items-center gap-1 font-bold">
                      <Wifi size={14} /> ONLINE
                    </span>
                  ) : (
                    <span className="text-amber-400 flex items-center gap-1 font-bold animate-pulse">
                      <WifiOff size={14} /> OFFLINE (1 BUFFERED)
                    </span>
                  )}
                </span>
              </div>
            </div>

            {/* Stepper Controls */}
            <div className="flex items-center justify-between pt-2">
              <button
                onClick={() => handleStep(Math.max(1, currentStep - 1))}
                disabled={currentStep <= 1}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 text-xs font-bold rounded-lg transition flex items-center gap-1"
              >
                <ChevronLeft size={14} /> Previous Step
              </button>

              <div className="text-xs font-mono text-slate-400">
                Step <span className="text-indigo-400 font-bold">{currentStep}</span> of 17
              </div>

              <button
                onClick={() => handleStep(Math.min(17, currentStep + 1))}
                disabled={currentStep >= 17}
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-xs font-bold rounded-lg transition flex items-center gap-1"
              >
                Next Step <ChevronRight size={14} />
              </button>
            </div>
          </div>

          {/* Right Column: Live Telemetry, Authority Actions & Audit Timeline */}
          <div className="lg:col-span-5 space-y-4">
            {/* Context & Authority Action Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2 border-b border-slate-800 pb-3">
                <Shield size={16} className="text-amber-400" />
                Operational State & Authority Actions
              </h3>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-500 text-[10px] block font-semibold uppercase">Defect Status</span>
                  <span className="font-bold text-indigo-300 text-sm">{scenarioState?.defect_status || "PENDING"}</span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-500 text-[10px] block font-semibold uppercase">Cluster Confidence</span>
                  <span className="font-bold text-emerald-400 text-sm">
                    {(scenarioState?.cluster_confidence * 100 || 84).toFixed(0)}% (Obs: {scenarioState?.observation_count || 1})
                  </span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-500 text-[10px] block font-semibold uppercase">Network State</span>
                  <span className={`font-bold text-sm ${scenarioState?.network_state === "ONLINE" ? "text-emerald-400" : "text-amber-400"}`}>
                    {scenarioState?.network_state || "ONLINE"}
                  </span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-500 text-[10px] block font-semibold uppercase">Maintenance Ticket</span>
                  <span className="font-bold text-amber-300 text-sm">
                    {scenarioState?.maintenance_ticket_id || "NOT ISSUED"}
                  </span>
                </div>
              </div>

              {/* Contextual Action Trigger for Steps 13, 14, 17 */}
              {currentStep === 13 && (
                <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl space-y-2">
                  <span className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                    <CheckCircle2 size={14} /> Authority Verification Required
                  </span>
                  <p className="text-[11px] text-slate-300">
                    Pothole alert received from Bus 104. Review optical evidence crop and confirm defect.
                  </p>
                  <button
                    onClick={() => handleStep(14)}
                    className="w-full py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold rounded-lg transition"
                  >
                    Verify Pothole & Create Maintenance Ticket
                  </button>
                </div>
              )}

              {currentStep === 16 && (
                <div className="p-3 bg-indigo-500/10 border border-indigo-500/30 rounded-xl space-y-2">
                  <span className="text-xs font-bold text-indigo-400 flex items-center gap-1.5">
                    <Wrench size={14} /> Road Repair Dispatched
                  </span>
                  <p className="text-[11px] text-slate-300">
                    Works crew has resurfaced Section 4 of Route 12. Buses will stop detecting the defect.
                  </p>
                  <button
                    onClick={() => handleStep(17)}
                    className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-lg transition"
                  >
                    Mark Defect as RESOLVED
                  </button>
                </div>
              )}
            </div>

            {/* Audit History Timeline Log */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2 border-b border-slate-800 pb-2">
                <Clock size={16} className="text-cyan-400" />
                Live Scenario Audit Log
              </h3>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1 text-xs font-mono">
                {historyLogs.slice().reverse().map((log: any, i: number) => (
                  <div key={i} className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                    <div className="flex items-center justify-between text-[10px] text-slate-500">
                      <span>{log.title}</span>
                      <span>{log.timestamp.slice(11, 19)}Z</span>
                    </div>
                    <pre className="text-[10px] text-slate-400 overflow-x-auto">
                      {JSON.stringify(log.details, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Incident Investigation Pipeline Modal */}
        {incidentModalOpen && incidentResult && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 w-full max-w-2xl rounded-2xl p-6 space-y-5 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 bg-rose-500/20 text-rose-400 rounded-lg">
                    <AlertTriangle size={20} />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-slate-100">Vehicle Incident Investigation Flow</h3>
                    <p className="text-xs text-slate-400 font-mono">Incident ID: {incidentResult.incident_id}</p>
                  </div>
                </div>
                <button
                  onClick={() => setIncidentModalOpen(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800"
                >
                  ✕
                </button>
              </div>

              {/* 8-Stage Pipeline Flowchart */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                {incidentResult.stages.map((stg: any) => (
                  <div key={stg.stage} className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 space-y-1">
                    <span className="text-[10px] text-slate-500 block">Stage {stg.stage}</span>
                    <span className="font-bold text-indigo-300 block">{stg.name}</span>
                    <span className="text-[10px] text-emerald-400 font-semibold">{stg.status}</span>
                  </div>
                ))}
              </div>

              {/* Certified Incident Report Preview */}
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className="font-bold text-xs text-slate-200 flex items-center gap-1.5">
                    <FileText size={14} className="text-indigo-400" />
                    Official Municipal Incident Dossier
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Chain of Custody: VERIFIED
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono text-slate-300">
                  <div>Vehicle Track: {incidentResult.report.vehicle_track_id}</div>
                  <div>Plate Text: <span className="text-amber-400 font-bold">{incidentResult.report.license_plate}</span></div>
                  <div>Confidence: {(incidentResult.report.confidence * 100).toFixed(0)}%</div>
                  <div>Clip: {incidentResult.report.evidence_clip}</div>
                  <div className="col-span-2 text-[11px] text-slate-400 truncate">
                    SHA-256: {incidentResult.report.clip_sha256}
                  </div>
                </div>
              </div>

              <div className="flex justify-end">
                <button
                  onClick={() => setIncidentModalOpen(false)}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-lg transition"
                >
                  Close Dossier
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DemoFlowTheater;
