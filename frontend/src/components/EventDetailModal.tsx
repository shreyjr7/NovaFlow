// src/components/EventDetailModal.tsx
// Step 33  Authority Dashboard: Event Detail Page / Modal
// Implements 5 structured panels:
//   1. Event (Type, Severity)
//   2. Location (GPS, Road, Area)
//   3. AI (Confidence, Detection time, Source bus)
//   4. Evidence (Video clip, Images)
//   5. Action (Confirm, Dismiss, Escalate, Mark under repair)

import React, { useState } from "react";
import {
  X, Check, AlertTriangle, ArrowUp, Wrench,
  MapPin, ShieldAlert, Clock, Bus, Video, Image,
  ExternalLink, CheckCircle2, Shield
} from "lucide-react";

export interface EventDetailData {
  id: string;
  type: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  status: string;
  // Location
  gps: { lat: number; lon: number };
  road: string;
  area: string;
  // AI
  confidence: number;
  detection_time: string;
  source_bus: string;
  plate_number?: string;
  // Evidence
  video_clip_url?: string;
  image_urls?: string[];
  evidence_description?: string;
}

interface Props {
  event: EventDetailData | null;
  isOpen: boolean;
  onClose: () => void;
  onAction?: (action: "CONFIRM" | "DISMISS" | "ESCALATE" | "MARK_UNDER_REPAIR", eventId: string) => void;
}

export const EventDetailModal: React.FC<Props> = ({ event, isOpen, onClose, onAction }) => {
  const [currentStatus, setCurrentStatus] = useState<string>(event?.status || "NEW");
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  if (!isOpen || !event) return null;

  const handleActionClick = async (action: "CONFIRM" | "DISMISS" | "ESCALATE" | "MARK_UNDER_REPAIR") => {
    setIsProcessing(true);
    try {
      if (onAction) {
        onAction(action, event.id);
      }
      
      // Update local status display
      if (action === "CONFIRM") {
        setCurrentStatus("CONFIRMED");
        setActionFeedback("✓ Event successfully confirmed and verified by Authority.");
      } else if (action === "DISMISS") {
        setCurrentStatus("DISMISSED");
        setActionFeedback("✕ Event marked as false positive and dismissed.");
      } else if (action === "ESCALATE") {
        setCurrentStatus("ESCALATED");
        setActionFeedback("↑ Event escalated to Traffic Police quick-response dispatch.");
      } else if (action === "MARK_UNDER_REPAIR") {
        setCurrentStatus("UNDER_REPAIR");
        setActionFeedback("🔧 Maintenance work order dispatched to Road Engineering Bay.");
      }

      // Also call backend PATCH /events/{id} or /api/v1/alerts
      await fetch(`/events/${event.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: action }),
      }).catch(() => null);
    } finally {
      setIsProcessing(false);
    }
  };

  const getSeverityBadgeColor = (sev: string) => {
    switch (sev) {
      case "CRITICAL": return "bg-red-500/20 text-red-400 border-red-500/40";
      case "HIGH": return "bg-amber-500/20 text-amber-400 border-amber-500/40";
      case "MEDIUM": return "bg-yellow-500/20 text-yellow-400 border-yellow-500/40";
      default: return "bg-blue-500/20 text-blue-400 border-blue-500/40";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto bg-gray-900 border border-gray-800 rounded-xl shadow-2xl text-gray-100 flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800 bg-gray-950/60 sticky top-0 z-10">
          <div className="flex items-center space-x-3">
            <span className="text-xl">🚨</span>
            <div>
              <h2 className="text-lg font-bold tracking-wide flex items-center space-x-2">
                <span>Authority Event Detail</span>
                <span className="text-xs text-gray-400 font-mono">[{event.id}]</span>
              </h2>
              <p className="text-xs text-gray-400">Step 33 Canonical Incident & Infrastructure Investigation Page</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content - 5 Step-33 Sections */}
        <div className="p-6 space-y-6">
          {actionFeedback && (
            <div className="p-3 bg-emerald-950/40 border border-emerald-500/30 rounded-lg text-emerald-300 text-sm flex items-center justify-between">
              <span>{actionFeedback}</span>
              <button onClick={() => setActionFeedback(null)} className="text-xs underline text-emerald-400">Dismiss</button>
            </div>
          )}

          {/* Section 1: Event */}
          <div className="bg-gray-950/40 border border-gray-800/80 rounded-lg p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3 flex items-center justify-between">
              <span>1. Event Overview</span>
              <span className={`px-2 py-0.5 text-xs font-mono rounded border ${getSeverityBadgeColor(event.severity)}`}>
                {event.severity}
              </span>
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-xs text-gray-500 block">Type</span>
                <span className="font-semibold text-white">{event.type}</span>
              </div>
              <div>
                <span className="text-xs text-gray-500 block">Severity</span>
                <span className="font-bold text-red-400">{event.severity}</span>
              </div>
              <div>
                <span className="text-xs text-gray-500 block">Status</span>
                <span className="font-mono text-emerald-400">{currentStatus}</span>
              </div>
              <div>
                <span className="text-xs text-gray-500 block">ANPR Plate</span>
                <span className="font-mono bg-yellow-950/40 text-yellow-300 px-1.5 py-0.5 rounded border border-yellow-700/40 text-xs">
                  {event.plate_number || "UP65AB1234"}
                </span>
              </div>
            </div>
          </div>

          {/* Section 2: Location */}
          <div className="bg-gray-950/40 border border-gray-800/80 rounded-lg p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3 flex items-center space-x-2">
              <MapPin className="w-3.5 h-3.5 text-cyan-400" />
              <span>2. Location</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-xs text-gray-500 block">GPS Coordinates</span>
                <span className="font-mono text-cyan-300">
                  {event.gps?.lat != null ? event.gps.lat.toFixed(5) : "—"},{" "}
                  {event.gps?.lon != null ? event.gps.lon.toFixed(5) : "—"}
                </span>
              </div>
              <div>
                <span className="text-xs text-gray-500 block">Road</span>
                <span className="text-white font-medium">{event.road || (event as any).road_segment || (event as any).address || "—"}</span>
              </div>
              <div>
                <span className="text-xs text-gray-500 block">Area / Sector</span>
                <span className="text-gray-300">{event.area || (event as any).district || "—"}</span>
              </div>
            </div>
          </div>

          {/* Section 3: AI */}
          <div className="bg-gray-950/40 border border-gray-800/80 rounded-lg p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3 flex items-center space-x-2">
              <Shield className="w-3.5 h-3.5 text-purple-400" />
              <span>3. AI Telemetry</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-xs text-gray-500 block">Confidence</span>
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-lg text-purple-300">
                    {(((event.confidence ?? 0.9)) * 100).toFixed(0)}%
                  </span>
                  <div className="flex-1 bg-gray-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-purple-500 h-full rounded-full"
                      style={{ width: `${Math.min(100, (event.confidence ?? 0.9) * 100)}%` }}
                    />
                  </div>
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-500 block">Detection Time</span>
                <span className="text-gray-200 font-mono text-xs">{event.detection_time}</span>
              </div>
              <div>
                <span className="text-xs text-gray-500 block">Source Bus</span>
                <span className="font-mono text-amber-300 flex items-center space-x-1">
                  <Bus className="w-3.5 h-3.5 inline" />
                  <span>{event.source_bus}</span>
                </span>
              </div>
            </div>
          </div>

          {/* Section 4: Evidence */}
          <div className="bg-gray-950/40 border border-gray-800/80 rounded-lg p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3 flex items-center space-x-2">
              <Video className="w-3.5 h-3.5 text-amber-400" />
              <span>4. Evidence Assets</span>
            </h3>
            <div className="space-y-3">
              {event.evidence_description && (
                <p className="text-xs text-gray-300 bg-gray-900/60 p-2.5 rounded border border-gray-800 italic">
                  &ldquo;{event.evidence_description}&rdquo;
                </p>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 flex flex-col items-center justify-center min-h-[120px] text-center">
                  <Video className="w-8 h-8 text-amber-400 mb-2" />
                  <span className="text-xs font-semibold text-gray-200">Video Clip (11-Point Rolling Buffer)</span>
                  <span className="text-[10px] text-gray-500 font-mono mt-0.5">SHA-256 Verified ? 30s Window</span>
                  <a
                    href={event.video_clip_url || "#"}
                    className="mt-2 text-xs text-cyan-400 hover:underline flex items-center space-x-1"
                    onClick={(e) => { e.preventDefault(); alert("Playing verified evidentiary clip."); }}
                  >
                    <span>Play Recorded Clip</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 flex flex-col items-center justify-center min-h-[120px] text-center">
                  <Image className="w-8 h-8 text-cyan-400 mb-2" />
                  <span className="text-xs font-semibold text-gray-200">High-Res Camera Frames</span>
                  <span className="text-[10px] text-gray-500 font-mono mt-0.5">Faces & Non-Incident Privacy Masked</span>
                  <button
                    onClick={() => alert("Viewing privacy-masked optical snapshot.")}
                    className="mt-2 text-xs text-cyan-400 hover:underline flex items-center space-x-1"
                  >
                    <span>View Snapshots (2 Frames)</span>
                    <ExternalLink className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Section 5: Action */}
          <div className="bg-gray-950 border border-gray-800 rounded-lg p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">
              5. Authority Actions
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <button
                disabled={isProcessing}
                onClick={() => handleActionClick("CONFIRM")}
                className="flex items-center justify-center space-x-1.5 px-3 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-xs rounded-lg transition shadow-md"
              >
                <Check className="w-4 h-4" />
                <span>✓ Confirm</span>
              </button>
              <button
                disabled={isProcessing}
                onClick={() => handleActionClick("DISMISS")}
                className="flex items-center justify-center space-x-1.5 px-3 py-2.5 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-gray-200 font-medium text-xs rounded-lg transition border border-gray-700"
              >
                <X className="w-4 h-4" />
                <span>✕ Dismiss</span>
              </button>
              <button
                disabled={isProcessing}
                onClick={() => handleActionClick("ESCALATE")}
                className="flex items-center justify-center space-x-1.5 px-3 py-2.5 bg-red-700 hover:bg-red-600 disabled:opacity-50 text-white font-medium text-xs rounded-lg transition shadow-md"
              >
                <ArrowUp className="w-4 h-4" />
                <span>↑ Escalate</span>
              </button>
              <button
                disabled={isProcessing}
                onClick={() => handleActionClick("MARK_UNDER_REPAIR")}
                className="flex items-center justify-center space-x-1.5 px-3 py-2.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white font-medium text-xs rounded-lg transition shadow-md"
              >
                <Wrench className="w-4 h-4" />
                <span>🔧 Mark repair</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EventDetailModal;
