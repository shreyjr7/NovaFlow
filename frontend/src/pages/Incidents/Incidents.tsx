// src/pages/Incidents/Incidents.tsx
// Incident & Hit-and-Run Anomaly Detection Command Center

import React, { useState, useEffect } from "react";
import {
  AlertTriangle, ShieldAlert, CheckCircle2, XCircle,
  Eye, RefreshCw, Filter, Search, Clock, MapPin,
  Car, Play, Pause, ChevronRight, FileText, Check,
  X, AlertOctagon, Info, ArrowUpRight, Gauge
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend
} from "recharts";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface InvolvedTrack {
  track_id: number;
  class_name: string;
  speed_kmh: number;
  heading_deg: number;
  bbox: number[];
  role: string; // primary | secondary | departing | disappeared
}

export interface NearbyVehicle {
  track_id: number;
  class_name: string;
  speed_kmh: number;
  distance_m: number;
}

export interface SignalDetail {
  name: string;
  triggered: boolean;
  value: number;
  threshold: number;
  unit: string;
  description: string;
}

export interface AnprDetail {
  plate_number: string;
  confidence: number;
  vehicle_class: string;
  plate_crop_b64: string;
  detected: boolean;
  state_code: string;
}

export interface EvidenceFrame {
  phase: string; // PRE_IMPACT | IMPACT | POST_IMPACT
  frame_idx: number;
  timestamp_s?: number;
  frame_b64: string;
}

export interface EvidenceClipDetail {
  clip_id: string;
  frame_count: number;
  duration_s: number;
  fps: number;
  frames: EvidenceFrame[];
  key_frame_b64: string;
}

export interface IncidentEvent {
  event_id: string;
  event_type: string;
  incident_category: "HIT_AND_RUN_SIGNATURE" | "COLLISION_RISK" | "TRAJECTORY_ANOMALY" | string;
  verification_status: "PENDING_REVIEW" | "VERIFIED_INCIDENT" | "DISMISSED" | string;
  legal_disclaimer?: string;
  requires_human_verification?: boolean;
  confidence: number;
  timestamp: string;
  location: {
    lat: number;
    lon: number;
    bearing_deg?: number;
    road_segment?: string;
    address?: string;
  };
  bus_id: string;
  camera_id: string;
  involved_tracks: InvolvedTrack[];
  nearby_vehicles: NearbyVehicle[];
  explainable_signals: Record<string, SignalDetail>;
  anpr?: AnprDetail;
  evidence_clip?: EvidenceClipDetail;
  is_hit_and_run: boolean;
  reviewed_at?: string | null;
  reviewer_id?: string | null;
  human_notes?: string | null;
}

// ── Visual SVGs for Resilient Fallback ────────────────────────────────────────

const makeSvgPlate = (plate: string) => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 80" width="320" height="80"><rect x="2" y="2" width="316" height="76" rx="8" fill="#ffffff" stroke="#1f2937" stroke-width="4"/><rect x="2" y="2" width="36" height="76" rx="6" fill="#1e3a8a"/><circle cx="20" cy="30" r="10" fill="#3b82f6" opacity="0.6"/><text x="20" y="55" font-family="Arial" font-size="11" font-weight="900" fill="#ffffff" text-anchor="middle">IND</text><text x="175" y="52" font-family="monospace" font-size="32" font-weight="900" fill="#111827" letter-spacing="4" text-anchor="middle">${plate}</text></svg>`;
  return `data:image/svg+xml;base64,${btoa(svg)}`;
};

const makeSvgFrame = (title: string, subtitle: string, color: string = "#dc2626") => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360" width="640" height="360"><rect width="640" height="360" fill="#0f172a"/><path d="M120 360 L280 180 L360 180 L520 360 Z" fill="#1e293b"/><line x1="320" y1="180" x2="320" y2="360" stroke="#f59e0b" stroke-width="3" stroke-dasharray="12 10"/><rect x="240" y="160" width="160" height="110" rx="6" fill="none" stroke="${color}" stroke-width="3"/><rect x="240" y="140" width="160" height="20" fill="${color}"/><text x="245" y="154" font-family="Arial" font-size="11" font-weight="bold" fill="#ffffff">${title}</text><rect x="16" y="16" width="220" height="42" rx="4" fill="#000000" fill-opacity="0.7"/><text x="26" y="34" font-family="Arial" font-size="12" font-weight="bold" fill="#ffffff">CAMERA SENSOR: ${subtitle}</text><text x="26" y="48" font-family="Arial" font-size="10" fill="#94a3b8">INCIDENT ANOMALY CLIP</text></svg>`;
  return `data:image/svg+xml;base64,${btoa(svg)}`;
};

// ── Initial Mock Fallback State ───────────────────────────────────────────────

const INITIAL_INCIDENTS: IncidentEvent[] = [
  {
    event_id: "inc_del_001",
    event_type: "POSSIBLE_INCIDENT",
    incident_category: "HIT_AND_RUN_SIGNATURE",
    verification_status: "PENDING_REVIEW",
    legal_disclaimer: "Preliminary automated sensor anomaly alert. Does not determine legal fault. Human verification required before enforcement action.",
    confidence: 0.93,
    timestamp: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
    location: {
      lat: 28.6315,
      lon: 77.2167,
      bearing_deg: 142.0,
      road_segment: "DEL_CP_01",
      address: "Connaught Place Radial Rd 3, New Delhi",
    },
    bus_id: "BUS_101",
    camera_id: "FRONT",
    involved_tracks: [
      { track_id: 412, class_name: "car", speed_kmh: 46.5, heading_deg: 145.0, bbox: [210, 140, 390, 270], role: "departing" },
      { track_id: 415, class_name: "motorcycle", speed_kmh: 0.0, heading_deg: 110.0, bbox: [180, 220, 240, 290], role: "disappeared" },
    ],
    nearby_vehicles: [
      { track_id: 409, class_name: "bus", speed_kmh: 22.0, distance_m: 14.5 },
      { track_id: 418, class_name: "auto-rickshaw", speed_kmh: 28.0, distance_m: 8.2 },
    ],
    explainable_signals: {
      sudden_deceleration: { name: "sudden_deceleration", triggered: true, value: -5.2, threshold: -4.5, unit: "m/s^2", description: "Sharp braking before impact (a=-5.2 m/s²)" },
      abrupt_heading_change: { name: "abrupt_heading_change", triggered: true, value: 41.2, threshold: 35.0, unit: "deg", description: "Abrupt yaw deviation (41.2 deg)" },
      trajectory_discontinuity: { name: "trajectory_discontinuity", triggered: false, value: 28.5, threshold: 75.0, unit: "px", description: "Within continuous tracking bounds" },
      nearby_vehicle_interaction: { name: "nearby_vehicle_interaction", triggered: true, value: 34.0, threshold: 70.0, unit: "px", description: "Close proximity contact with motorcycle #415" },
      object_disappearance_after_interaction: { name: "object_disappearance_after_interaction", triggered: true, value: 1.0, threshold: 1.0, unit: "binary", description: "Interacting motorcycle track #415 vanished post-impact" },
      unusual_acceleration: { name: "unusual_acceleration", triggered: true, value: 4.8, threshold: 4.0, unit: "m/s^2", description: "Rapid acceleration spike leaving scene" },
      vehicle_leaving_scene: { name: "vehicle_leaving_scene", triggered: true, value: 46.5, threshold: 28.0, unit: "km/h", description: "Car #412 rapidly accelerated away at 46.5 km/h" },
    },
    anpr: {
      plate_number: "DL 01 AB 1234",
      confidence: 0.942,
      vehicle_class: "car",
      plate_crop_b64: makeSvgPlate("DL 01 AB 1234"),
      detected: true,
      state_code: "DL",
    },
    evidence_clip: {
      clip_id: "clip_del_001",
      frame_count: 3,
      duration_s: 2.4,
      fps: 10.0,
      frames: [
        { phase: "PRE_IMPACT", frame_idx: 101, frame_b64: makeSvgFrame("PRE-IMPACT APPROACH", "FRONT - T-0.8s", "#3b82f6") },
        { phase: "IMPACT", frame_idx: 105, frame_b64: makeSvgFrame("ANOMALOUS INTERACTION", "FRONT - IMPACT T=0", "#ef4444") },
        { phase: "POST_IMPACT", frame_idx: 110, frame_b64: makeSvgFrame("VEHICLE DEPARTING SCENE", "FRONT - T+0.8s", "#f59e0b") },
      ],
      key_frame_b64: makeSvgFrame("ANOMALOUS INTERACTION", "FRONT - IMPACT T=0", "#ef4444"),
    },
    is_hit_and_run: true,
  },
  {
    event_id: "inc_del_002",
    event_type: "POSSIBLE_INCIDENT",
    incident_category: "COLLISION_RISK",
    verification_status: "PENDING_REVIEW",
    legal_disclaimer: "Preliminary automated sensor anomaly alert. Does not determine legal fault. Human verification required before enforcement action.",
    confidence: 0.875,
    timestamp: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
    location: {
      lat: 28.5672,
      lon: 77.2100,
      bearing_deg: 88.0,
      road_segment: "DEL_RING_04",
      address: "Ring Road near AIIMS Flyover, New Delhi",
    },
    bus_id: "BUS_204",
    camera_id: "REAR",
    involved_tracks: [
      { track_id: 512, class_name: "truck", speed_kmh: 12.0, heading_deg: 90.0, bbox: [150, 100, 480, 310], role: "primary" },
      { track_id: 516, class_name: "car", speed_kmh: 0.0, heading_deg: 85.0, bbox: [190, 180, 340, 280], role: "secondary" },
    ],
    nearby_vehicles: [
      { track_id: 520, class_name: "motorcycle", speed_kmh: 35.0, distance_m: 12.0 },
    ],
    explainable_signals: {
      sudden_deceleration: { name: "sudden_deceleration", triggered: true, value: -4.8, threshold: -4.5, unit: "m/s^2", description: "Sharp braking before contact (a=-4.8 m/s²)" },
      abrupt_heading_change: { name: "abrupt_heading_change", triggered: false, value: 12.0, threshold: 35.0, unit: "deg", description: "Minimal yaw deviation" },
      trajectory_discontinuity: { name: "trajectory_discontinuity", triggered: true, value: 82.0, threshold: 75.0, unit: "px", description: "Positional displacement during impact (82 px)" },
      nearby_vehicle_interaction: { name: "nearby_vehicle_interaction", triggered: true, value: 18.0, threshold: 70.0, unit: "px", description: "Bounding box contact with car #516" },
      object_disappearance_after_interaction: { name: "object_disappearance_after_interaction", triggered: false, value: 0.0, threshold: 1.0, unit: "binary", description: "Vehicles remained in frame" },
      unusual_acceleration: { name: "unusual_acceleration", triggered: false, value: 0.0, threshold: 4.0, unit: "m/s^2", description: "No subsequent acceleration" },
      vehicle_leaving_scene: { name: "vehicle_leaving_scene", triggered: false, value: 12.0, threshold: 28.0, unit: "km/h", description: "Truck stopped at scene" },
    },
    anpr: {
      plate_number: "HR 26 BC 3456",
      confidence: 0.912,
      vehicle_class: "truck",
      plate_crop_b64: makeSvgPlate("HR 26 BC 3456"),
      detected: true,
      state_code: "HR",
    },
    evidence_clip: {
      clip_id: "clip_del_002",
      frame_count: 3,
      duration_s: 2.0,
      fps: 10.0,
      frames: [
        { phase: "PRE_IMPACT", frame_idx: 201, frame_b64: makeSvgFrame("TRUCK APPROACHING", "REAR - T-0.6s", "#3b82f6") },
        { phase: "IMPACT", frame_idx: 204, frame_b64: makeSvgFrame("BUMPER CONTACT", "REAR - CONTACT", "#ef4444") },
        { phase: "POST_IMPACT", frame_idx: 208, frame_b64: makeSvgFrame("VEHICLES AT REST", "REAR - REST", "#10b981") },
      ],
      key_frame_b64: makeSvgFrame("BUMPER CONTACT", "REAR - CONTACT", "#ef4444"),
    },
    is_hit_and_run: false,
  },
  {
    event_id: "inc_blr_003",
    event_type: "POSSIBLE_INCIDENT",
    incident_category: "COLLISION_RISK",
    verification_status: "VERIFIED_INCIDENT",
    legal_disclaimer: "Preliminary automated sensor anomaly alert. Does not determine legal fault. Human verification required before enforcement action.",
    confidence: 0.945,
    timestamp: new Date(Date.now() - 1000 * 60 * 65).toISOString(),
    location: {
      lat: 12.9716,
      lon: 77.5946,
      bearing_deg: 210.0,
      road_segment: "BLR_MG_01",
      address: "MG Road & Brigade Rd Junction, Bengaluru",
    },
    bus_id: "BUS_305",
    camera_id: "FRONT",
    involved_tracks: [
      { track_id: 601, class_name: "auto-rickshaw", speed_kmh: 0.0, heading_deg: 220.0, bbox: [180, 160, 310, 290], role: "primary" },
    ],
    nearby_vehicles: [],
    explainable_signals: {
      sudden_deceleration: { name: "sudden_deceleration", triggered: true, value: -5.6, threshold: -4.5, unit: "m/s^2", description: "Abrupt stop" },
      abrupt_heading_change: { name: "abrupt_heading_change", triggered: true, value: 52.0, threshold: 35.0, unit: "deg", description: "Overturned heading" },
      trajectory_discontinuity: { name: "trajectory_discontinuity", triggered: true, value: 90.0, threshold: 75.0, unit: "px", description: "Lateral roll jump" },
      nearby_vehicle_interaction: { name: "nearby_vehicle_interaction", triggered: true, value: 20.0, threshold: 70.0, unit: "px", description: "Impact with curb barrier" },
      object_disappearance_after_interaction: { name: "object_disappearance_after_interaction", triggered: false, value: 0.0, threshold: 1.0, unit: "binary", description: "Object retained" },
      unusual_acceleration: { name: "unusual_acceleration", triggered: false, value: 0.0, threshold: 4.0, unit: "m/s^2", description: "Stationary" },
      vehicle_leaving_scene: { name: "vehicle_leaving_scene", triggered: false, value: 0.0, threshold: 28.0, unit: "km/h", description: "No departure" },
    },
    anpr: {
      plate_number: "KA 05 EF 9012",
      confidence: 0.955,
      vehicle_class: "auto-rickshaw",
      plate_crop_b64: makeSvgPlate("KA 05 EF 9012"),
      detected: true,
      state_code: "KA",
    },
    evidence_clip: {
      clip_id: "clip_blr_003",
      frame_count: 3,
      duration_s: 2.2,
      fps: 10.0,
      frames: [
        { phase: "PRE_IMPACT", frame_idx: 301, frame_b64: makeSvgFrame("AUTO SWERVING", "FRONT - T-0.6s", "#f59e0b") },
        { phase: "IMPACT", frame_idx: 304, frame_b64: makeSvgFrame("BARRIER IMPACT", "FRONT - CONTACT", "#ef4444") },
        { phase: "POST_IMPACT", frame_idx: 308, frame_b64: makeSvgFrame("REST AT CURB", "FRONT - REST", "#3b82f6") },
      ],
      key_frame_b64: makeSvgFrame("BARRIER IMPACT", "FRONT - CONTACT", "#ef4444"),
    },
    is_hit_and_run: false,
    reviewed_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    reviewer_id: "officer_blr_04",
    human_notes: "Reviewed camera footage. Auto tipped after swerving to avoid construction debris. Ambulance dispatched.",
  },
  {
    event_id: "inc_mum_004",
    event_type: "POSSIBLE_INCIDENT",
    incident_category: "TRAJECTORY_ANOMALY",
    verification_status: "DISMISSED",
    legal_disclaimer: "Preliminary automated sensor anomaly alert. Does not determine legal fault. Human verification required before enforcement action.",
    confidence: 0.68,
    timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    location: {
      lat: 19.0760,
      lon: 72.8777,
      bearing_deg: 18.0,
      road_segment: "MUM_WEH_02",
      address: "Western Express Highway near Bandra, Mumbai",
    },
    bus_id: "BUS_402",
    camera_id: "LEFT",
    involved_tracks: [
      { track_id: 702, class_name: "car", speed_kmh: 38.0, heading_deg: 25.0, bbox: [120, 150, 280, 270], role: "primary" },
    ],
    nearby_vehicles: [],
    explainable_signals: {
      sudden_deceleration: { name: "sudden_deceleration", triggered: false, value: -2.1, threshold: -4.5, unit: "m/s^2", description: "Moderate braking" },
      abrupt_heading_change: { name: "abrupt_heading_change", triggered: true, value: 37.5, threshold: 35.0, unit: "deg", description: "Rapid lane switch" },
      trajectory_discontinuity: { name: "trajectory_discontinuity", triggered: true, value: 78.0, threshold: 75.0, unit: "px", description: "Lane transition displacement" },
      nearby_vehicle_interaction: { name: "nearby_vehicle_interaction", triggered: false, value: 110.0, threshold: 70.0, unit: "px", description: "No vehicle contact" },
      object_disappearance_after_interaction: { name: "object_disappearance_after_interaction", triggered: false, value: 0.0, threshold: 1.0, unit: "binary", description: "Normal track continuation" },
      unusual_acceleration: { name: "unusual_acceleration", triggered: false, value: 1.8, threshold: 4.0, unit: "m/s^2", description: "Steady cruise" },
      vehicle_leaving_scene: { name: "vehicle_leaving_scene", triggered: false, value: 38.0, threshold: 28.0, unit: "km/h", description: "Normal progression" },
    },
    anpr: {
      plate_number: "MH 02 CD 5678",
      confidence: 0.865,
      vehicle_class: "car",
      plate_crop_b64: makeSvgPlate("MH 02 CD 5678"),
      detected: true,
      state_code: "MH",
    },
    evidence_clip: {
      clip_id: "clip_mum_004",
      frame_count: 3,
      duration_s: 1.8,
      fps: 10.0,
      frames: [
        { phase: "PRE_IMPACT", frame_idx: 401, frame_b64: makeSvgFrame("LANE CHANGE", "LEFT - T-0.5s", "#3b82f6") },
        { phase: "IMPACT", frame_idx: 404, frame_b64: makeSvgFrame("SHARP SWERVE", "LEFT - APEX", "#f59e0b") },
        { phase: "POST_IMPACT", frame_idx: 407, frame_b64: makeSvgFrame("LANE RECOVERY", "LEFT - RECOVERY", "#10b981") },
      ],
      key_frame_b64: makeSvgFrame("SHARP SWERVE", "LEFT - APEX", "#f59e0b"),
    },
    is_hit_and_run: false,
    reviewed_at: new Date(Date.now() - 1000 * 60 * 90).toISOString(),
    reviewer_id: "officer_mum_02",
    human_notes: "False positive: vehicle performed rapid evasive lane change around plastic road barricade with no contact.",
  },
];

export const Incidents: React.FC = () => {
  const [incidents, setIncidents] = useState<IncidentEvent[]>(INITIAL_INCIDENTS);
  const [selectedIncident, setSelectedIncident] = useState<IncidentEvent | null>(INITIAL_INCIDENTS[0]);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [lastRefreshed, setLastRefreshed] = useState<string>("");

  // Review modal state
  const [reviewerNotes, setReviewerNotes] = useState<string>("");
  const [reviewerId, setReviewerId] = useState<string>("safety_officer_01");
  const [isSubmittingReview, setIsSubmittingReview] = useState<boolean>(false);
  const [activeFrameIdx, setActiveFrameIdx] = useState<number>(1);
  const [isPlayingClip, setIsPlayingClip] = useState<boolean>(false);

  // Sync with backend API
  const fetchIncidents = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch("/api/v1/incidents/events?limit=100");
      if (res.ok) {
        const data = await res.json();
        if (data.items && data.items.length > 0) {
          setIncidents(data.items);
          if (selectedIncident) {
            const updated = data.items.find((i: IncidentEvent) => i.event_id === selectedIncident.event_id);
            if (updated) setSelectedIncident(updated);
          }
        }
      }
      setLastRefreshed(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    } catch (e) {
      console.warn("Backend API not reachable; maintaining resilient mock view", e);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 20000);
    return () => clearInterval(interval);
  }, []);

  // Frame player playback timer
  useEffect(() => {
    let timer: any = null;
    if (isPlayingClip && selectedIncident?.evidence_clip?.frames?.length) {
      timer = setInterval(() => {
        setActiveFrameIdx((prev) => {
          const total = selectedIncident.evidence_clip?.frames.length || 3;
          return (prev + 1) % total;
        });
      }, 700);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isPlayingClip, selectedIncident]);

  // Handle Human Review Submission
  const handleReviewAction = async (newStatus: "VERIFIED_INCIDENT" | "DISMISSED") => {
    if (!selectedIncident) return;
    setIsSubmittingReview(true);
    try {
      const res = await fetch(`/api/v1/incidents/events/${selectedIncident.event_id}/review`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: newStatus,
          reviewer_id: reviewerId || "safety_officer_01",
          notes: reviewerNotes || (newStatus === "VERIFIED_INCIDENT" ? "Verified anomalous vehicle interaction" : "Dismissed as false positive"),
        }),
      });

      const updatedDoc: IncidentEvent = {
        ...selectedIncident,
        verification_status: newStatus,
        reviewed_at: new Date().toISOString(),
        reviewer_id: reviewerId,
        human_notes: reviewerNotes,
      };

      setIncidents((prev) =>
        prev.map((it) => (it.event_id === selectedIncident.event_id ? updatedDoc : it))
      );
      setSelectedIncident(updatedDoc);
      setReviewerNotes("");
    } catch (e) {
      console.error("Failed to update status on backend", e);
    } finally {
      setIsSubmittingReview(false);
    }
  };

  // Filtered items
  const displayedIncidents = incidents.filter((item) => {
    const matchesStatus =
      statusFilter === "ALL" || item.verification_status === statusFilter;
    const matchesCategory =
      categoryFilter === "ALL" || item.incident_category === categoryFilter;
    const matchesSearch =
      searchTerm === "" ||
      item.event_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.bus_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.anpr?.plate_number || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.location.address || "").toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesCategory && matchesSearch;
  });

  // KPIs
  const totalAnomalies = incidents.length;
  const pendingReview = incidents.filter((i) => i.verification_status === "PENDING_REVIEW").length;
  const verifiedCount = incidents.filter((i) => i.verification_status === "VERIFIED_INCIDENT").length;
  const hitAndRunCount = incidents.filter((i) => i.is_hit_and_run).length;

  const categoryPieData = [
    { name: "Hit & Run Signatures", value: incidents.filter((i) => i.incident_category === "HIT_AND_RUN_SIGNATURE").length, color: "#ef4444" },
    { name: "Collision Risk", value: incidents.filter((i) => i.incident_category === "COLLISION_RISK").length, color: "#f59e0b" },
    { name: "Trajectory Anomaly", value: incidents.filter((i) => i.incident_category === "TRAJECTORY_ANOMALY").length, color: "#3b82f6" },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-4 sm:p-6 lg:p-8 space-y-6">
      {/* ── Top Header & Navigation ────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-rose-950/60 border border-rose-800/50 rounded-xl text-rose-400">
              <AlertOctagon className="w-5 h-5" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                Incident & Hit-and-Run Anomaly Intelligence
              </h1>
              <p className="text-xs text-gray-400 mt-0.5">
                Compound physical trajectory analysis, rolling evidentiary buffer, ANPR, and human-in-the-loop review
              </p>
            </div>
          </div>
        </div>

        {/* Global Navigation Links */}
        <div className="flex flex-wrap items-center gap-2">
          <nav className="flex items-center space-x-1 text-xs bg-gray-900 border border-gray-800 rounded-xl p-1">
            <a href="/" className="px-2.5 py-1 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors">Home</a>
            <a href="/fleet" className="px-2.5 py-1 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors">Fleet</a>
            <a href="/road-defects" className="px-2.5 py-1 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors">Defects</a>
            <a href="/traffic" className="px-2.5 py-1 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors">Traffic</a>
            <a href="/congestion" className="px-2.5 py-1 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors">Congestion</a>
            <a href="/pedestrian-safety" className="px-2.5 py-1 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors">Pedestrian</a>
            <span className="px-2.5 py-1 bg-rose-600 text-white rounded-lg font-semibold">Incidents</span>
          </nav>

          <button
            onClick={fetchIncidents}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3 py-1.5 bg-gray-900 border border-gray-800 hover:bg-gray-800 text-gray-300 text-xs rounded-xl font-medium transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-rose-400" : ""}`} />
            <span>{isRefreshing ? "Syncing..." : "Sync Live"}</span>
          </button>
        </div>
      </div>

      {/* ── Strict Legal & Ethical AI Compliance Notice ──────────────────────── */}
      <div className="bg-rose-950/30 border border-rose-800/40 rounded-2xl p-4 flex items-start gap-3 text-xs text-rose-200">
        <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-semibold text-white block">
            Legal & Ethical Guardrails — Non-Fault Sensor Proxy Architecture
          </span>
          <p className="text-rose-300 leading-relaxed text-[11px]">
            In strict compliance with statutory jurisprudence and ethical AI standards, this system <strong>does not determine legal fault, assert criminal culpability, or confirm crimes</strong>. Every event emitted by edge camera nodes is strictly designated as a <strong>POSSIBLE INCIDENT</strong> based on explainable physical sensor signals (sudden deceleration, heading deviation, trajectory discontinuity, vehicle interaction, and departure signatures). Solitary hard braking is explicitly suppressed. <strong>Human verification is strictly mandatory before any enforcement or legal action can be initiated.</strong>
          </p>
        </div>
      </div>

      {/* ── KPI Summary Cards ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Anomalies */}
        <div className="bg-gray-900/80 border border-gray-800/80 rounded-2xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 font-medium">Total Sensor Anomalies</span>
            <span className="p-1.5 bg-blue-950/60 border border-blue-800/40 text-blue-400 rounded-lg">
              <AlertTriangle className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">{totalAnomalies}</span>
            <span className="text-[11px] text-gray-400">POSSIBLE INCIDENTS</span>
          </div>
          <p className="text-[10px] text-gray-500 mt-1">Multi-signal compound triggers</p>
        </div>

        {/* Pending Human Review */}
        <div className="bg-amber-950/20 border border-amber-800/40 rounded-2xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-amber-300 font-medium">Pending Human Review</span>
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-amber-300">{pendingReview}</span>
            <span className="text-[11px] text-amber-400/80">Require verification</span>
          </div>
          <p className="text-[10px] text-amber-400/70 mt-1">Enforcement blocked until signed</p>
        </div>

        {/* Verified Incidents */}
        <div className="bg-emerald-950/20 border border-emerald-800/40 rounded-2xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-emerald-300 font-medium">Verified Incidents</span>
            <span className="p-1.5 bg-emerald-950/60 border border-emerald-800/40 text-emerald-400 rounded-lg">
              <CheckCircle2 className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-300">{verifiedCount}</span>
            <span className="text-[11px] text-emerald-400/80">Officer validated</span>
          </div>
          <p className="text-[10px] text-emerald-400/70 mt-1">Forwarded to operations dispatch</p>
        </div>

        {/* Hit-and-Run Signatures */}
        <div className="bg-rose-950/20 border border-rose-800/40 rounded-2xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-rose-300 font-medium">Hit-and-Run Signatures</span>
            <span className="p-1.5 bg-rose-950/60 border border-rose-800/40 text-rose-400 rounded-lg">
              <AlertOctagon className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-rose-300">{hitAndRunCount}</span>
            <span className="text-[11px] text-rose-400/80">ANPR extracted</span>
          </div>
          <p className="text-[10px] text-rose-400/70 mt-1">Departure signature confirmed</p>
        </div>
      </div>

      {/* ── Main Layout: Incident Feed & Evidence Inspector Modal/Pane ────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* ── Left Column: Incident List & Filters (5 cols) ───────────────────── */}
        <div className="lg:col-span-5 space-y-4">
          {/* Filter Bar */}
          <div className="bg-gray-900/80 border border-gray-800/80 rounded-2xl p-3.5 space-y-3">
            <div className="flex items-center gap-2 bg-gray-950 border border-gray-800 rounded-xl px-3 py-1.5">
              <Search className="w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="Search by event ID, bus, plate, or road..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-transparent text-xs text-gray-200 placeholder-gray-500 focus:outline-none w-full"
              />
              {searchTerm && (
                <button onClick={() => setSearchTerm("")} className="text-gray-500 hover:text-gray-300">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Status Pills */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] text-gray-500 font-medium mr-1">Status:</span>
              {[
                { id: "ALL", label: "All" },
                { id: "PENDING_REVIEW", label: "Pending Review" },
                { id: "VERIFIED_INCIDENT", label: "Verified" },
                { id: "DISMISSED", label: "Dismissed" },
              ].map((s) => (
                <button
                  key={s.id}
                  onClick={() => setStatusFilter(s.id)}
                  className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors ${
                    statusFilter === s.id
                      ? "bg-rose-600 text-white"
                      : "bg-gray-800/60 text-gray-400 hover:text-gray-200 hover:bg-gray-800"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>

            {/* Category Pills */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] text-gray-500 font-medium mr-1">Type:</span>
              {[
                { id: "ALL", label: "All Types" },
                { id: "HIT_AND_RUN_SIGNATURE", label: "Hit & Run" },
                { id: "COLLISION_RISK", label: "Collision Risk" },
                { id: "TRAJECTORY_ANOMALY", label: "Trajectory" },
              ].map((c) => (
                <button
                  key={c.id}
                  onClick={() => setCategoryFilter(c.id)}
                  className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors ${
                    categoryFilter === c.id
                      ? "bg-indigo-600 text-white"
                      : "bg-gray-800/60 text-gray-400 hover:text-gray-200 hover:bg-gray-800"
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>

          {/* Incident List */}
          <div className="space-y-2.5 max-h-[700px] overflow-y-auto pr-1">
            {displayedIncidents.length === 0 ? (
              <div className="p-8 text-center bg-gray-900/40 border border-gray-800/60 rounded-2xl">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2 opacity-60" />
                <p className="text-xs text-gray-400">No incident alerts match your filter criteria</p>
              </div>
            ) : (
              displayedIncidents.map((inc) => {
                const isSelected = selectedIncident?.event_id === inc.event_id;
                const isPending = inc.verification_status === "PENDING_REVIEW";
                const isVerified = inc.verification_status === "VERIFIED_INCIDENT";
                const isDismissed = inc.verification_status === "DISMISSED";

                return (
                  <div
                    key={inc.event_id}
                    onClick={() => {
                      setSelectedIncident(inc);
                      setActiveFrameIdx(1);
                      setIsPlayingClip(false);
                    }}
                    className={`p-3.5 rounded-2xl border transition-all cursor-pointer ${
                      isSelected
                        ? "bg-gray-900 border-rose-500/70 shadow-lg shadow-rose-950/20 ring-1 ring-rose-500/40"
                        : "bg-gray-900/60 border-gray-800/70 hover:bg-gray-900 hover:border-gray-700"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider ${
                            inc.incident_category === "HIT_AND_RUN_SIGNATURE"
                              ? "bg-red-950/80 text-red-300 border border-red-800/60"
                              : inc.incident_category === "COLLISION_RISK"
                              ? "bg-amber-950/80 text-amber-300 border border-amber-800/60"
                              : "bg-blue-950/80 text-blue-300 border border-blue-800/60"
                          }`}
                        >
                          {inc.incident_category.replace(/_/g, " ")}
                        </span>

                        <span
                          className={`px-2 py-0.5 rounded-md text-[10px] font-medium ${
                            isPending
                              ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                              : isVerified
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                              : "bg-gray-700/40 text-gray-400 border border-gray-600/30"
                          }`}
                        >
                          {inc.verification_status.replace(/_/g, " ")}
                        </span>
                      </div>

                      <span className="text-[10px] text-gray-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(inc.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>

                    <div className="mt-2.5">
                      <div className="text-xs font-semibold text-white flex items-center justify-between">
                        <span>{inc.location.address || inc.location.road_segment || "Urban Corridor"}</span>
                        <span className="text-[11px] font-bold text-rose-400">{(inc.confidence * 100).toFixed(0)}% Conf</span>
                      </div>
                      <div className="text-[11px] text-gray-400 mt-0.5 flex items-center gap-3">
                        <span>Bus {inc.bus_id} ({inc.camera_id} CAM)</span>
                        {inc.anpr && (
                          <span className="font-mono text-gray-200 bg-gray-800 px-1.5 py-0.2 rounded text-[10px]">
                            {inc.anpr.plate_number}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Quick Trigger summary */}
                    <div className="mt-2 pt-2 border-t border-gray-800/60 flex flex-wrap gap-1 text-[10px]">
                      {Object.values(inc.explainable_signals || {})
                        .filter((s) => s.triggered)
                        .slice(0, 3)
                        .map((s) => (
                          <span key={s.name} className="bg-gray-800/80 text-gray-300 px-1.5 py-0.5 rounded">
                            {s.name.replace(/_/g, " ")}
                          </span>
                        ))}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ── Right Column: Human Reviewer & Evidence Inspector (7 cols) ──────── */}
        <div className="lg:col-span-7 space-y-4">
          {selectedIncident ? (
            <div className="bg-gray-900/80 border border-gray-800/80 rounded-2xl p-5 space-y-5">
              {/* Header Info */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-800/80 pb-3.5">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-white">
                      Evidence Inspector — {selectedIncident.event_id}
                    </h2>
                    <span
                      className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase ${
                        selectedIncident.verification_status === "PENDING_REVIEW"
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                          : selectedIncident.verification_status === "VERIFIED_INCIDENT"
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          : "bg-gray-700/30 text-gray-400 border border-gray-600/30"
                      }`}
                    >
                      {selectedIncident.verification_status.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {selectedIncident.location.address || "Urban Road Segment"} • Timestamp: {new Date(selectedIncident.timestamp).toLocaleString()}
                  </p>
                </div>

                <div className="text-right">
                  <div className="text-xs text-gray-400">Sensor Confidence</div>
                  <div className="text-lg font-extrabold text-rose-400">
                    {(selectedIncident.confidence * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* ── Multi-frame Evidence Sequence Player ───────────────────────── */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
                    <FileText className="w-4 h-4 text-indigo-400" />
                    Multi-Frame Evidence Sequence ({selectedIncident.evidence_clip?.duration_s || 2.0}s rolling window)
                  </span>
                  <button
                    onClick={() => setIsPlayingClip(!isPlayingClip)}
                    className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-800 hover:bg-gray-700 text-xs font-medium rounded-lg text-gray-200 transition-colors"
                  >
                    {isPlayingClip ? <Pause className="w-3.5 h-3.5 text-amber-400" /> : <Play className="w-3.5 h-3.5 text-emerald-400" />}
                    <span>{isPlayingClip ? "Pause Sequence" : "Play Sequence"}</span>
                  </button>
                </div>

                {/* Video Player Display */}
                <div className="relative aspect-video bg-gray-950 rounded-xl overflow-hidden border border-gray-800 flex items-center justify-center">
                  {selectedIncident.evidence_clip?.frames && selectedIncident.evidence_clip.frames.length > 0 ? (
                    <img
                      src={selectedIncident.evidence_clip.frames[activeFrameIdx]?.frame_b64 || selectedIncident.evidence_clip.key_frame_b64}
                      alt="Incident Evidence Frame"
                      className="w-full h-full object-contain"
                    />
                  ) : (
                    <div className="text-gray-500 text-xs">No video frames buffered</div>
                  )}

                  {/* Active Frame Phase Badge Overlay */}
                  <div className="absolute top-3 right-3 bg-black/70 backdrop-blur-sm border border-gray-700 px-2.5 py-1 rounded-lg text-[10px] font-bold text-white flex items-center gap-1.5">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        activeFrameIdx === 0
                          ? "bg-blue-400"
                          : activeFrameIdx === 1
                          ? "bg-red-500 animate-ping"
                          : "bg-amber-400"
                      }`}
                    />
                    <span>
                      {selectedIncident.evidence_clip?.frames[activeFrameIdx]?.phase || "IMPACT"} (Frame {activeFrameIdx + 1}/{selectedIncident.evidence_clip?.frames.length || 3})
                    </span>
                  </div>

                  {/* Camera & Bus stamp */}
                  <div className="absolute bottom-3 left-3 bg-black/70 backdrop-blur-sm border border-gray-700 px-2.5 py-1 rounded-lg text-[10px] font-mono text-gray-300">
                    BUS: {selectedIncident.bus_id} | CAM: {selectedIncident.camera_id} | GPS: {selectedIncident.location.lat.toFixed(4)}, {selectedIncident.location.lon.toFixed(4)}
                  </div>
                </div>

                {/* Frame Select Thumbnails */}
                <div className="grid grid-cols-3 gap-2 pt-1">
                  {selectedIncident.evidence_clip?.frames?.map((frm, idx) => (
                    <button
                      key={frm.phase + idx}
                      onClick={() => {
                        setActiveFrameIdx(idx);
                        setIsPlayingClip(false);
                      }}
                      className={`p-1.5 rounded-xl border text-left transition-all ${
                        activeFrameIdx === idx
                          ? "bg-indigo-950/40 border-indigo-500 ring-1 ring-indigo-500"
                          : "bg-gray-950/40 border-gray-800 hover:border-gray-700"
                      }`}
                    >
                      <div className="text-[10px] font-bold text-gray-300">{frm.phase}</div>
                      <div className="text-[9px] text-gray-500">T{idx === 0 ? "-0.8s" : idx === 1 ? "=0.0s (Apex)" : "+0.8s"}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* ── ANPR License Plate Card ────────────────────────────────────── */}
              {selectedIncident.anpr && (
                <div className="bg-gray-950 border border-gray-800 rounded-xl p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
                      <Car className="w-4 h-4 text-emerald-400" />
                      Automatic Number Plate Recognition (ANPR)
                    </span>
                    <span className="text-[11px] font-semibold text-emerald-400 bg-emerald-950/50 border border-emerald-800/40 px-2 py-0.5 rounded">
                      {(selectedIncident.anpr.confidence * 100).toFixed(1)}% OCR Match
                    </span>
                  </div>

                  <div className="flex flex-col sm:flex-row items-center gap-4">
                    {/* Visual Plate Badge */}
                    <div className="shrink-0 max-w-[240px] w-full shadow-md rounded-lg overflow-hidden border border-gray-700">
                      <img
                        src={selectedIncident.anpr.plate_crop_b64}
                        alt="ANPR Plate Crop"
                        className="w-full h-auto"
                      />
                    </div>

                    {/* Plate metadata */}
                    <div className="text-xs space-y-1 w-full">
                      <div className="flex justify-between border-b border-gray-800 pb-1">
                        <span className="text-gray-400">Registration:</span>
                        <span className="font-mono font-bold text-white text-sm">{selectedIncident.anpr.plate_number}</span>
                      </div>
                      <div className="flex justify-between border-b border-gray-800 pb-1">
                        <span className="text-gray-400">Target Vehicle:</span>
                        <span className="text-gray-200 capitalize">{selectedIncident.anpr.vehicle_class}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">RTO Jurisdiction:</span>
                        <span className="text-gray-200">{selectedIncident.anpr.state_code} State Transport Authority</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ── 7 Explainable Trajectory Signals Checklist ─────────────────── */}
              <div className="space-y-2.5">
                <h3 className="text-xs font-semibold text-gray-300 flex items-center justify-between">
                  <span>Explainable Physical Trajectory Signals</span>
                  <span className="text-[10px] text-gray-500 font-normal">Compound trigger verified</span>
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {Object.values(selectedIncident.explainable_signals || {}).map((sig) => (
                    <div
                      key={sig.name}
                      className={`p-2.5 rounded-xl border flex items-start gap-2.5 text-xs ${
                        sig.triggered
                          ? "bg-rose-950/20 border-rose-800/40 text-rose-200"
                          : "bg-gray-950/40 border-gray-800/50 text-gray-400"
                      }`}
                    >
                      <span
                        className={`p-1 rounded-md shrink-0 mt-0.5 ${
                          sig.triggered ? "bg-rose-900/60 text-rose-300" : "bg-gray-800 text-gray-500"
                        }`}
                      >
                        {sig.triggered ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
                      </span>
                      <div className="space-y-0.5">
                        <div className="font-semibold text-white text-[11px] capitalize">
                          {sig.name.replace(/_/g, " ")}
                        </div>
                        <p className="text-[10px] text-gray-400 leading-tight">
                          {sig.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* ── Human Verification & Review Form ──────────────────────────── */}
              <div className="bg-gray-950 border border-gray-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <ShieldAlert className="w-4 h-4 text-amber-400" />
                    Human Review & Legal Enforcement Sign-off
                  </span>
                  <span className="text-[10px] text-gray-400">
                    Mandatory step for legal validity
                  </span>
                </div>

                {selectedIncident.human_notes && (
                  <div className="p-3 bg-gray-900 border border-gray-800 rounded-lg text-xs space-y-1">
                    <div className="text-[10px] text-gray-400 flex items-center justify-between">
                      <span>Reviewed by: <strong>{selectedIncident.reviewer_id}</strong></span>
                      <span>{selectedIncident.reviewed_at ? new Date(selectedIncident.reviewed_at).toLocaleString() : ""}</span>
                    </div>
                    <p className="text-gray-200 text-[11px] italic">"{selectedIncident.human_notes}"</p>
                  </div>
                )}

                <div className="space-y-2">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-gray-400 block mb-1">Safety Officer ID</label>
                      <input
                        type="text"
                        value={reviewerId}
                        onChange={(e) => setReviewerId(e.target.value)}
                        placeholder="e.g. officer_delhi_09"
                        className="w-full bg-gray-900 border border-gray-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-rose-500"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-gray-400 block mb-1">Review Timestamp</label>
                      <input
                        type="text"
                        disabled
                        value={new Date().toLocaleString()}
                        className="w-full bg-gray-900/50 border border-gray-800/60 rounded-lg px-2.5 py-1.5 text-xs text-gray-500 cursor-not-allowed"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-[10px] text-gray-400 block mb-1">Reviewer Observation & Findings</label>
                    <textarea
                      rows={2}
                      value={reviewerNotes}
                      onChange={(e) => setReviewerNotes(e.target.value)}
                      placeholder="Add official verification notes (e.g. verified dashcam rolling buffer, observed physical contact between vehicles...)"
                      className="w-full bg-gray-900 border border-gray-800 rounded-lg p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-rose-500"
                    />
                  </div>
                </div>

                {/* Review Action Buttons */}
                <div className="flex flex-wrap items-center justify-end gap-2.5 pt-1">
                  <button
                    onClick={() => handleReviewAction("DISMISSED")}
                    disabled={isSubmittingReview}
                    className="flex items-center gap-1.5 px-3.5 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white rounded-xl text-xs font-semibold transition-all disabled:opacity-50"
                  >
                    <XCircle className="w-4 h-4 text-gray-400" />
                    <span>Dismiss False Alarm</span>
                  </button>

                  <button
                    onClick={() => handleReviewAction("VERIFIED_INCIDENT")}
                    disabled={isSubmittingReview}
                    className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-emerald-950/30 transition-all disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Verify Incident & Forward</span>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center bg-gray-900/40 border border-gray-800/60 rounded-2xl">
              <p className="text-xs text-gray-400">Select an incident from the feed to inspect evidence</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Incidents;
