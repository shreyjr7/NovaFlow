// src/components/NetworkStatusIndicator.tsx
import React from "react";
import { Wifi, WifiOff, RefreshCw, HardDrive, ShieldCheck } from "lucide-react";

export type NetworkMode = "ONLINE" | "OFFLINE" | "RECONNECTING";

export interface NetworkStatusIndicatorProps {
  state: NetworkMode | string;
  bufferedCount?: number;
  compact?: boolean;
  onModeChange?: (mode: NetworkMode) => void;
  onFlush?: () => void;
  className?: string;
}

export const NetworkStatusIndicator: React.FC<NetworkStatusIndicatorProps> = ({
  state,
  bufferedCount = 0,
  compact = false,
  onModeChange,
  onFlush,
  className = "",
}) => {
  const normState = (state || "ONLINE").toUpperCase() as NetworkMode;

  if (compact) {
    if (normState === "ONLINE") {
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 ${className}`}
          title="Network: ONLINE"
        >
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <Wifi size={13} />
          <span>Network: ONLINE</span>
        </span>
      );
    }
    if (normState === "RECONNECTING") {
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30 ${className}`}
          title={`NETWORK: RECONNECTING (${bufferedCount} EVENTS BUFFERED)`}
        >
          <RefreshCw size={13} className="animate-spin text-amber-400" />
          <span>NETWORK: RECONNECTING ({bufferedCount} BUFFERED)</span>
        </span>
      );
    }
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30 ${className}`}
        title={`NETWORK: OFFLINE (${bufferedCount} EVENTS BUFFERED)`}
      >
        <WifiOff size={13} />
        <span>NETWORK: OFFLINE ({bufferedCount} BUFFERED)</span>
      </span>
    );
  }

  // Exact Block Display matching prompt specification:
  // "Network:\nONLINE" or "NETWORK:\nOFFLINE\n17 EVENTS BUFFERED"
  return (
    <div
      className={`rounded-xl border p-4 transition-all duration-300 ${
        normState === "ONLINE"
          ? "bg-gradient-to-b from-gray-900 to-emerald-950/30 border-emerald-500/40 shadow-lg shadow-emerald-950/30 text-gray-100"
          : normState === "RECONNECTING"
          ? "bg-gradient-to-b from-gray-900 to-amber-950/30 border-amber-500/40 shadow-lg shadow-amber-950/30 text-gray-100"
          : "bg-gradient-to-b from-gray-900 to-rose-950/30 border-rose-500/40 shadow-lg shadow-rose-950/30 text-gray-100"
      } ${className}`}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          {normState === "ONLINE" ? (
            <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400">
              <Wifi size={20} />
            </div>
          ) : normState === "RECONNECTING" ? (
            <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400">
              <RefreshCw size={20} className="animate-spin" />
            </div>
          ) : (
            <div className="p-2 rounded-lg bg-rose-500/20 text-rose-400">
              <WifiOff size={20} />
            </div>
          )}
          <div>
            <div className="text-[11px] font-mono uppercase tracking-widest text-gray-400">
              Onboard Store & Forward
            </div>
            <div className="text-xs text-gray-300 font-medium">Edge Connection Engine</div>
          </div>
        </div>

        <div className="flex items-center gap-1.5 font-mono text-[11px] px-2 py-1 rounded bg-black/40 border border-gray-800 text-gray-300">
          <HardDrive size={13} className="text-gray-400" />
          <span>SQLite Store</span>
        </div>
      </div>

      {/* Prompt-mandated verbatim indicator block */}
      <div
        className={`my-3 p-3.5 rounded-lg font-mono text-center select-all border ${
          normState === "ONLINE"
            ? "bg-black/70 border-emerald-500/50 text-emerald-400 shadow-inner shadow-emerald-900/40"
            : normState === "RECONNECTING"
            ? "bg-black/70 border-amber-500/50 text-amber-400 shadow-inner shadow-amber-900/40"
            : "bg-black/70 border-rose-500/50 text-rose-400 shadow-inner shadow-rose-900/40"
        }`}
      >
        {normState === "ONLINE" ? (
          <div>
            <div className="text-xs text-gray-400 font-bold uppercase tracking-wider">Network:</div>
            <div className="text-xl font-black tracking-wide text-emerald-400 mt-0.5">ONLINE</div>
            <div className="text-[11px] text-emerald-500/70 mt-1 flex items-center justify-center gap-1">
              <ShieldCheck size={12} />
              <span>Direct Central Streaming Active</span>
            </div>
          </div>
        ) : normState === "RECONNECTING" ? (
          <div>
            <div className="text-xs text-amber-400 font-bold uppercase tracking-wider">NETWORK:</div>
            <div className="text-xl font-black tracking-wide text-amber-400 mt-0.5">RECONNECTING</div>
            <div className="text-xs font-black text-amber-300 mt-1 bg-amber-500/10 py-0.5 px-2 rounded inline-block">
              {bufferedCount} EVENTS BUFFERED
            </div>
          </div>
        ) : (
          <div>
            <div className="text-xs text-rose-400 font-bold uppercase tracking-wider">NETWORK:</div>
            <div className="text-xl font-black tracking-wide text-rose-400 mt-0.5">OFFLINE</div>
            <div className="text-xs font-black text-rose-300 mt-1 bg-rose-500/10 py-0.5 px-2 rounded inline-block">
              {bufferedCount} EVENTS BUFFERED
            </div>
          </div>
        )}
      </div>

      {/* Simulation Mode Toggle Bar */}
      {onModeChange && (
        <div className="mt-3 pt-3 border-t border-gray-800">
          <div className="text-[10px] uppercase font-mono text-gray-400 mb-1.5 flex justify-between">
            <span>Simulate Network State</span>
            <span className="text-gray-500">Live Hardware Override</span>
          </div>
          <div className="grid grid-cols-3 gap-1.5">
            <button
              onClick={() => onModeChange("ONLINE")}
              className={`px-2 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                normState === "ONLINE"
                  ? "bg-emerald-600 text-white border-emerald-400 shadow-sm shadow-emerald-500/50"
                  : "bg-gray-800/80 hover:bg-gray-700 text-gray-300 border-gray-700"
              }`}
            >
              ONLINE
            </button>
            <button
              onClick={() => onModeChange("OFFLINE")}
              className={`px-2 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                normState === "OFFLINE"
                  ? "bg-rose-600 text-white border-rose-400 shadow-sm shadow-rose-500/50"
                  : "bg-gray-800/80 hover:bg-gray-700 text-gray-300 border-gray-700"
              }`}
            >
              OFFLINE
            </button>
            <button
              onClick={() => onModeChange("RECONNECTING")}
              className={`px-2 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                normState === "RECONNECTING"
                  ? "bg-amber-600 text-white border-amber-400 shadow-sm shadow-amber-500/50"
                  : "bg-gray-800/80 hover:bg-gray-700 text-gray-300 border-gray-700"
              }`}
            >
              RECONN
            </button>
          </div>

          {onFlush && normState !== "OFFLINE" && bufferedCount > 0 && (
            <button
              onClick={onFlush}
              className="w-full mt-2 py-1.5 px-3 rounded-lg text-xs font-semibold bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 border border-indigo-500/40 transition flex items-center justify-center gap-1.5"
            >
              <RefreshCw size={13} className="text-indigo-400" />
              <span>Drain & Flush {bufferedCount} Events to Central Server</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default NetworkStatusIndicator;
