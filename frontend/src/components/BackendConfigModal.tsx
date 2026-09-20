// src/components/BackendConfigModal.tsx
// Backend Server Configuration Modal for NovaFlow Platform
// Allows connecting Vercel frontend to local tunnel (localtunnel / ngrok) or cloud backend (Render / Railway)

import React, { useState, useEffect } from "react";
import {
  Server,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  X,
  Zap,
  Copy,
  Check,
  Globe,
  Terminal,
} from "lucide-react";
import {
  getBackendBaseUrl,
  setBackendBaseUrl,
  roadScanApi,
} from "../services/roadScanApi";

interface BackendConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnected?: () => void;
}

export const BackendConfigModal: React.FC<BackendConfigModalProps> = ({
  isOpen,
  onClose,
  onConnected,
}) => {
  const [currentUrl, setCurrentUrl] = useState<string>("");
  const [inputUrl, setInputUrl] = useState<string>("");
  const [isTesting, setIsTesting] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<{
    tested: boolean;
    success: boolean;
    message: string;
    modelWeights?: string;
  }>({
    tested: false,
    success: false,
    message: "",
  });
  const [copiedCmd, setCopiedCmd] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen) {
      const active = getBackendBaseUrl();
      setCurrentUrl(active);
      setInputUrl(active || "");
      setTestResult({ tested: false, success: false, message: "" });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTestAndSave = async (urlToSave?: string) => {
    const target = urlToSave !== undefined ? urlToSave : inputUrl;
    setIsTesting(true);
    setTestResult({ tested: false, success: false, message: "" });

    try {
      // Save temporarily to test
      setBackendBaseUrl(target);
      const health = await roadScanApi.checkBackendHealth();

      setTestResult({
        tested: true,
        success: health.online,
        message: health.message,
        modelWeights: health.modelWeights,
      });

      if (health.online) {
        setCurrentUrl(getBackendBaseUrl());
        if (onConnected) onConnected();
      }
    } catch (err: any) {
      setTestResult({
        tested: true,
        success: false,
        message: err.message || "Failed to reach backend endpoint",
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleReset = async () => {
    setBackendBaseUrl("");
    setInputUrl("");
    setCurrentUrl("");
    await handleTestAndSave("");
  };

  const handleCopyLocaltunnel = () => {
    navigator.clipboard.writeText("npx localtunnel --port 8000");
    setCopiedCmd(true);
    setTimeout(() => setCopiedCmd(false), 2500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/75 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[#1A1F36] border border-[#2E3656] text-white w-full max-w-xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#282F50] flex items-center justify-between bg-[#15192E]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
              <Server size={18} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>AI Backend Server Endpoint</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30 font-mono">
                  FastAPI YOLOv8
                </span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Connect your Vercel frontend to the NovaFlow AI engine
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5 overflow-y-auto">
          {/* Current Status Pill */}
          <div className="p-3.5 rounded-xl bg-[#202642] border border-[#2B345A] flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  testResult.tested
                    ? testResult.success
                      ? "bg-emerald-400 ring-2 ring-emerald-500/30"
                      : "bg-rose-500 ring-2 ring-rose-500/30"
                    : currentUrl
                    ? "bg-emerald-400"
                    : "bg-amber-400"
                }`}
              />
              <span className="text-xs text-slate-300 font-medium">
                Active Backend:{" "}
                <span className="font-mono text-white font-semibold">
                  {currentUrl || "(Default relative /api/v1)"}
                </span>
              </span>
            </div>
            {testResult.modelWeights && (
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-mono">
                Weights Active
              </span>
            )}
          </div>

          {/* Test Feedback Notice */}
          {testResult.tested && (
            <div
              className={`p-3.5 rounded-xl text-xs flex items-start gap-2.5 border ${
                testResult.success
                  ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-200"
                  : "bg-rose-950/40 border-rose-500/40 text-rose-200"
              }`}
            >
              {testResult.success ? (
                <CheckCircle2 size={16} className="text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle size={16} className="text-rose-400 shrink-0 mt-0.5" />
              )}
              <div className="space-y-0.5">
                <div className="font-bold">
                  {testResult.success ? "Successfully Connected!" : "Connection Failed"}
                </div>
                <div>{testResult.message}</div>
              </div>
            </div>
          )}

          {/* Input Form */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-300">
              Backend Endpoint URL
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={inputUrl}
                onChange={(e) => setInputUrl(e.target.value)}
                placeholder="e.g. https://novaflow-api.loca.lt or https://novaflow.onrender.com"
                className="flex-1 bg-[#121626] border border-[#2E3656] focus:border-blue-500 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono transition"
              />
              <button
                onClick={() => handleTestAndSave()}
                disabled={isTesting}
                className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-bold transition flex items-center gap-1.5 shrink-0 shadow-md"
              >
                <RefreshCw size={14} className={isTesting ? "animate-spin" : ""} />
                <span>{isTesting ? "Testing..." : "Save & Connect"}</span>
              </button>
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
              <span>Saved in your browser for seamless sessions.</span>
              <button
                onClick={handleReset}
                className="text-slate-400 hover:text-white underline transition"
              >
                Reset to default
              </button>
            </div>
          </div>

          {/* Quick Setup Instructions */}
          <div className="p-4 rounded-xl bg-[#141829] border border-[#252B47] space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-amber-300">
              <Zap size={14} />
              <span>How to connect your backend:</span>
            </div>

            {/* Option 1: Localtunnel */}
            <div className="space-y-1.5 text-xs text-slate-300">
              <div className="font-semibold text-slate-200 flex items-center gap-1.5">
                <Terminal size={13} className="text-blue-400" />
                <span>Option 1: Instant 30-Second Tunnel (Local PC)</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                If your backend is running locally on port 8000, open a terminal and run:
              </p>
              <div className="flex items-center justify-between bg-[#0A0D18] border border-[#232942] rounded-lg px-3 py-1.5 font-mono text-[11px] text-emerald-400">
                <span>npx localtunnel --port 8000</span>
                <button
                  onClick={handleCopyLocaltunnel}
                  className="p-1 rounded text-slate-400 hover:text-white transition flex items-center gap-1 text-[10px]"
                >
                  {copiedCmd ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                  <span>{copiedCmd ? "Copied" : "Copy"}</span>
                </button>
              </div>
              <p className="text-[11px] text-slate-400">
                Copy the generated HTTPS URL, paste it into the box above, and click <strong>Save & Connect</strong>.
              </p>
            </div>

            {/* Option 2: Cloud */}
            <div className="pt-2 border-t border-[#20263E] space-y-1 text-xs text-slate-300">
              <div className="font-semibold text-slate-200 flex items-center gap-1.5">
                <Globe size={13} className="text-purple-400" />
                <span>Option 2: 24/7 Cloud Host (Render / Railway / Hugging Face)</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Deploy the <code className="text-white font-mono">backend/</code> directory to Render or Railway. Then add <code className="text-amber-300 font-mono">VITE_API_URL</code> to your Vercel Project Settings &gt; Environment Variables.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-[#282F50] bg-[#15192E] flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-[#252C4A] hover:bg-[#313A61] text-xs font-semibold text-slate-200 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default BackendConfigModal;
