// src/pages/OfflineBuffer/OfflineBuffer.tsx
// Onboard Local Buffer & Store-and-Forward Dashboard

import React, { useState, useEffect } from "react";
import {
  Wifi,
  WifiOff,
  RefreshCw,
  HardDrive,
  Database,
  ArrowRight,
  ShieldCheck,
  AlertTriangle,
  PlusCircle,
  Trash2,
  Clock,
  MapPin,
  CheckCircle2,
  XCircle,
  AlertOctagon,
  Layers,
  Activity,
} from "lucide-react";
import { Header } from "../../components/Header";
import NetworkStatusIndicator, { NetworkMode } from "../../components/NetworkStatusIndicator";

export interface BufferedEventRecord {
  id: number;
  event_id: string;
  event_type: string;
  gps: {
    lat: number;
    lon: number;
    bearing_deg?: number;
    road_segment?: string;
  };
  timestamp: string;
  confidence: number;
  evidence_reference?: string;
  retry_count: number;
  max_retries: number;
  status: "PENDING" | "IN_FLIGHT" | "ACKNOWLEDGED" | "DEAD_LETTER";
  created_at?: string;
  error_message?: string;
}

export interface QueueMetrics {
  pending_count: number;
  in_flight_count: number;
  dead_letter_count: number;
  max_events: number;
  db_size_bytes: number;
  db_path: string;
  oldest_pending_timestamp?: string;
}

const INITIAL_MOCK_EVENTS: BufferedEventRecord[] = [
  {
    id: 101,
    event_id: "evt_pothole_9021a",
    event_type: "ROAD_DEFECT_POTHOLE",
    gps: { lat: 12.9716, lon: 77.5946, bearing_deg: 42.0, road_segment: "MG_ROAD_SEG_1" },
    timestamp: new Date(Date.now() - 140000).toISOString(),
    confidence: 0.93,
    evidence_reference: "sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
    retry_count: 0,
    max_retries: 5,
    status: "PENDING",
  },
  {
    id: 102,
    event_id: "evt_ped_risk_3342b",
    event_type: "PEDESTRIAN_RISK",
    gps: { lat: 12.9725, lon: 77.5955, bearing_deg: 44.5, road_segment: "MG_ROAD_SEG_2" },
    timestamp: new Date(Date.now() - 110000).toISOString(),
    confidence: 0.88,
    evidence_reference: "sha256:cb436b7b16d93f6bda406141496a3c9228464cd979e73d6eb9f8542152c8f9ae",
    retry_count: 0,
    max_retries: 5,
    status: "PENDING",
  },
  {
    id: 103,
    event_id: "evt_incident_7781c",
    event_type: "POSSIBLE_INCIDENT",
    gps: { lat: 12.9738, lon: 77.5968, bearing_deg: 40.0, road_segment: "MG_ROAD_SEG_3" },
    timestamp: new Date(Date.now() - 75000).toISOString(),
    confidence: 0.85,
    evidence_reference: "sha256:a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e",
    retry_count: 1,
    max_retries: 5,
    status: "PENDING",
    error_message: "Connection timeout to Central API",
  },
  {
    id: 104,
    event_id: "evt_traffic_bot_1209d",
    event_type: "CONGESTION_EVENT",
    gps: { lat: 12.9749, lon: 77.598, bearing_deg: 41.2, road_segment: "MG_ROAD_SEG_4" },
    timestamp: new Date(Date.now() - 32000).toISOString(),
    confidence: 0.91,
    evidence_reference: "sha256:5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5",
    retry_count: 0,
    max_retries: 5,
    status: "PENDING",
  },
];

export const OfflineBuffer: React.FC = () => {
  const [networkMode, setNetworkMode] = useState<NetworkMode>("OFFLINE");
  const [events, setEvents] = useState<BufferedEventRecord[]>(INITIAL_MOCK_EVENTS);
  const [isDraining, setIsDraining] = useState(false);
  const [activeTab, setActiveTab] = useState<"ALL" | "PENDING" | "DEAD_LETTER">("ALL");

  const pendingCount = events.filter((e) => e.status === "PENDING").length;
  const deadLetterCount = events.filter((e) => e.status === "DEAD_LETTER").length;
  const maxEvents = 2000;
  const dbSizeBytes = 1024 * (32 + pendingCount * 4);

  // Poll simulator edge API if available, fallback to mock state
  useEffect(() => {
    let isMounted = true;
    const checkEdgeApi = async () => {
      try {
        const res = await fetch("http://localhost:7000/api/simulator/network/status");
        if (res.ok && isMounted) {
          const data = await res.json();
          if (data.state) {
            setNetworkMode(data.state as NetworkMode);
          }
        }
      } catch {
        // Edge simulator offline or standalone frontend demo mode
      }
    };
    checkEdgeApi();
    const timer = setInterval(checkEdgeApi, 4000);
    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, []);

  const handleModeChange = async (newMode: NetworkMode) => {
    setNetworkMode(newMode);
    try {
      await fetch("http://localhost:7000/api/simulator/network/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: newMode }),
      });
    } catch {
      // Standalone simulation mode
    }

    if (newMode === "RECONNECTING") {
      triggerDrainProcess();
    }
  };

  const triggerDrainProcess = async () => {
    if (isDraining) return;
    setIsDraining(true);

    try {
      await fetch("http://localhost:7000/api/simulator/network/flush", {
        method: "POST",
      });
    } catch {
      // Standalone simulation
    }

    // Step-by-step simulated drain
    let currentEvents = [...events];
    const pendingItems = currentEvents.filter((e) => e.status === "PENDING");

    for (const item of pendingItems) {
      await new Promise((r) => setTimeout(r, 600));
      currentEvents = currentEvents.map((e) =>
        e.id === item.id ? { ...e, status: "ACKNOWLEDGED", retry_count: e.retry_count + 1 } : e
      );
      setEvents([...currentEvents]);
    }

    setIsDraining(false);
    setNetworkMode("ONLINE");
  };

  const handleInjectTestEvent = async () => {
    const newId = Date.now();
    const eventTypes = [
      "ROAD_DEFECT_POTHOLE",
      "PEDESTRIAN_RISK",
      "POSSIBLE_INCIDENT",
      "CONGESTION_EVENT",
      "ROAD_DEFECT_DAMAGED_SIGN",
    ];
    const chosenType = eventTypes[Math.floor(Math.random() * eventTypes.length)];

    const newEvt: BufferedEventRecord = {
      id: newId,
      event_id: `evt_sim_${newId.toString(36)}`,
      event_type: chosenType,
      gps: {
        lat: Number((12.9716 + (Math.random() - 0.5) * 0.01).toFixed(5)),
        lon: Number((77.5946 + (Math.random() - 0.5) * 0.01).toFixed(5)),
        bearing_deg: Math.floor(Math.random() * 360),
        road_segment: `SEG_${Math.floor(Math.random() * 8) + 1}`,
      },
      timestamp: new Date().toISOString(),
      confidence: Number((0.82 + Math.random() * 0.16).toFixed(2)),
      evidence_reference: `sha256:${Math.random().toString(36).substring(2)}${Math.random().toString(36).substring(2)}`,
      retry_count: 0,
      max_retries: 5,
      status: networkMode === "OFFLINE" ? "PENDING" : "ACKNOWLEDGED",
    };

    setEvents((prev) => [newEvt, ...prev]);

    try {
      await fetch("http://localhost:7000/api/simulator/network/test-event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: chosenType,
          confidence: newEvt.confidence,
          details: { injected: true },
        }),
      });
    } catch {
      // Standalone simulation
    }
  };

  const handleClearBuffer = () => {
    setEvents([]);
  };

  const filteredEvents = events.filter((e) => {
    if (activeTab === "PENDING") return e.status === "PENDING";
    if (activeTab === "DEAD_LETTER") return e.status === "DEAD_LETTER";
    return true;
  });

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6 space-y-6">
      {/* Header */}
      <Header />

      {/* Top Banner & Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-brand text-xs font-mono uppercase tracking-widest">
            <Database size={14} />
            <span>Local Store-and-Forward Engine</span>
          </div>
          <h2 className="text-2xl font-bold mt-1">Onboard Local Buffer & Offline Mode</h2>
          <p className="text-sm text-gray-400 mt-0.5">
            Guaranteed edge delivery with transactional SQLite storage, retry backoff, and FIFO eviction.
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleInjectTestEvent}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 text-xs font-semibold transition"
          >
            <PlusCircle size={14} className="text-brand" />
            <span>Generate Test Event</span>
          </button>
          <button
            onClick={triggerDrainProcess}
            disabled={isDraining || pendingCount === 0}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-indigo-900/40 transition"
          >
            <RefreshCw size={14} className={isDraining ? "animate-spin" : ""} />
            <span>{isDraining ? "Draining Queue…" : "Drain & Retransmit"}</span>
          </button>
          <button
            onClick={handleClearBuffer}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-gray-900 hover:bg-rose-950/40 text-gray-400 hover:text-rose-400 border border-gray-800 hover:border-rose-900/50 text-xs font-semibold transition"
            title="Clear Queue"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Main Grid: Status Indicator & KPI Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Prompt-Mandated UI Indicator */}
        <div className="lg:col-span-1">
          <NetworkStatusIndicator
            state={networkMode}
            bufferedCount={pendingCount}
            onModeChange={handleModeChange}
            onFlush={triggerDrainProcess}
          />
        </div>

        {/* Right Column: Queue Metrics & Capacity */}
        <div className="lg:col-span-2 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="text-xs text-gray-400 font-medium">Pending Delivery</div>
              <div className="text-2xl font-black text-rose-400 mt-1">{pendingCount}</div>
            </div>
            <div className="text-[11px] text-gray-500 flex items-center gap-1 mt-2">
              <Clock size={12} />
              <span>Awaiting Central Ack</span>
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="text-xs text-gray-400 font-medium">Dead Letter Isolated</div>
              <div className="text-2xl font-black text-amber-400 mt-1">{deadLetterCount}</div>
            </div>
            <div className="text-[11px] text-gray-500 flex items-center gap-1 mt-2">
              <AlertTriangle size={12} />
              <span>Exceeded 5 retries</span>
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="text-xs text-gray-400 font-medium">SQLite Storage</div>
              <div className="text-2xl font-black text-cyan-400 mt-1">
                {(dbSizeBytes / 1024).toFixed(1)} <span className="text-xs text-gray-400 font-normal">KB</span>
              </div>
            </div>
            <div className="text-[11px] text-gray-500 flex items-center gap-1 mt-2 font-mono truncate">
              <Database size={12} />
              <span>event_buffer.db</span>
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="text-xs text-gray-400 font-medium">FIFO Capacity Quota</div>
              <div className="text-2xl font-black text-emerald-400 mt-1">
                {pendingCount} <span className="text-xs text-gray-400 font-normal">/ {maxEvents}</span>
              </div>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-1.5 mt-2">
              <div
                className="bg-emerald-500 h-1.5 rounded-full transition-all"
                style={{ width: `${Math.min(100, (pendingCount / maxEvents) * 100)}%` }}
              />
            </div>
          </div>

          {/* Architecture Summary Card */}
          <div className="col-span-2 sm:col-span-4 bg-gray-900/60 border border-gray-800 rounded-xl p-4">
            <div className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Layers size={14} className="text-indigo-400" />
              <span>Store-and-Forward Reconnection Protocol</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-gray-400">
              <div className="p-2.5 rounded-lg bg-gray-950/70 border border-gray-800">
                <span className="font-bold text-emerald-400">1. Online Mode</span>
                <p className="mt-1 text-[11px] leading-relaxed">
                  Real-time events stream immediately to Central REST endpoints. Zero local queue delay.
                </p>
              </div>
              <div className="p-2.5 rounded-lg bg-gray-950/70 border border-gray-800">
                <span className="font-bold text-rose-400">2. Offline Mode</span>
                <p className="mt-1 text-[11px] leading-relaxed">
                  Outages divert payloads directly to SQLite queue. Metadata, GPS, timestamp & evidence preserved.
                </p>
              </div>
              <div className="p-2.5 rounded-lg bg-gray-950/70 border border-gray-800">
                <span className="font-bold text-amber-400">3. Reconnection & Drain</span>
                <p className="mt-1 text-[11px] leading-relaxed">
                  Batches retransmit with backoff. Upon 200/201 Acknowledgment, events are safely deleted from disk.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Events Table Section */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {/* Table Header Controls */}
        <div className="p-4 border-b border-gray-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Activity size={16} className="text-brand" />
            <h3 className="font-semibold text-sm">Local Queue Event Registry</h3>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-gray-800 text-gray-400">
              {filteredEvents.length} records
            </span>
          </div>

          <div className="flex items-center gap-2">
            {(["ALL", "PENDING", "DEAD_LETTER"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                  activeTab === tab
                    ? "bg-brand text-white"
                    : "bg-gray-800 text-gray-400 hover:text-gray-200"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Table Body */}
        <div className="overflow-x-auto touch-scroll">
          <table className="w-full min-w-[700px] text-left text-xs font-mono">
            <thead className="bg-gray-950/80 text-gray-400 border-b border-gray-800 text-[11px]">
              <tr>
                <th className="py-3 px-4">Event ID</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">GPS / Segment</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Confidence</th>
                <th className="py-3 px-4">Evidence Hash</th>
                <th className="py-3 px-4">Retries</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-gray-500 italic">
                    No buffered events in this view.
                  </td>
                </tr>
              ) : (
                filteredEvents.map((evt) => (
                  <tr key={evt.id} className="hover:bg-gray-800/40 transition">
                    <td className="py-3 px-4 font-bold text-gray-200">{evt.event_id}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          evt.event_type.includes("POTHOLE")
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                            : evt.event_type.includes("INCIDENT")
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                            : evt.event_type.includes("PEDESTRIAN")
                            ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                            : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                        }`}
                      >
                        {evt.event_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-300">
                      <div className="flex items-center gap-1">
                        <MapPin size={11} className="text-gray-500" />
                        <span>
                          {evt.gps.lat.toFixed(4)}, {evt.gps.lon.toFixed(4)}
                        </span>
                      </div>
                      <div className="text-[10px] text-gray-500">{evt.gps.road_segment}</div>
                    </td>
                    <td className="py-3 px-4 text-gray-400">{evt.timestamp.slice(11, 19)}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`font-semibold ${
                          evt.confidence >= 0.9
                            ? "text-emerald-400"
                            : evt.confidence >= 0.75
                            ? "text-yellow-400"
                            : "text-rose-400"
                        }`}
                      >
                        {(evt.confidence * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-400 text-[10px]" title={evt.evidence_reference}>
                      {evt.evidence_reference ? `${evt.evidence_reference.slice(0, 15)}…` : "—"}
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-gray-300">
                        {evt.retry_count} / {evt.max_retries}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {evt.status === "ACKNOWLEDGED" ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold text-[11px]">
                          <CheckCircle2 size={12} />
                          <span>DELIVERED</span>
                        </span>
                      ) : evt.status === "PENDING" ? (
                        <span className="inline-flex items-center gap-1 text-rose-400 font-semibold text-[11px]">
                          <Clock size={12} />
                          <span>BUFFERED</span>
                        </span>
                      ) : evt.status === "IN_FLIGHT" ? (
                        <span className="inline-flex items-center gap-1 text-amber-400 font-semibold text-[11px]">
                          <RefreshCw size={12} className="animate-spin" />
                          <span>DRAINING</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-red-500 font-semibold text-[11px]">
                          <AlertOctagon size={12} />
                          <span>DEAD LETTER</span>
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default OfflineBuffer;
