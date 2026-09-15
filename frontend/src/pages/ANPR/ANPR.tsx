// src/pages/ANPR/ANPR.tsx
// Vehicle Registration Recognition (ANPR) Command Center

import React, { useState, useEffect } from "react";
import {
  Car, ShieldAlert, CheckCircle2, AlertTriangle, XCircle,
  Eye, RefreshCw, Search, Clock, MapPin, ArrowRight,
  Sliders, FileCheck2, AlertOctagon, Check, X, Edit3,
  Layers, Lock, ExternalLink
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface CharacterConfidence {
  char: string;
  confidence: number;
}

export interface FormatDetails {
  is_valid: boolean;
  format_type: string;
  formatted_plate?: string;
  state_code?: string;
  state_name?: string;
  district_code?: string;
  series?: string;
  unique_number?: string;
  format_score?: number;
  issues?: string[];
  corrected_from_ambiguity?: boolean;
}

export interface AnprRecord {
  record_id: string;
  registration_number: string;
  confidence: number;
  timestamp: string;
  gps: {
    lat: number;
    lon: number;
    bearing_deg?: number;
    road_segment?: string;
    address?: string;
  };
  bus_id: string;
  camera_id: string;
  evidence_reference: string;
  state: "READABLE" | "LOW_CONFIDENCE" | "NOT_READABLE" | "NOT_PRESENT" | string;
  human_verification_required: boolean;
  verification_notice: string;
  perspective_crop_b64: string;
  raw_frame_b64: string;
  auto_publish: boolean;
  quarantined: boolean;
  character_confs?: CharacterConfidence[];
  format_details?: FormatDetails;
  sharpness_score?: number;
  detection_score?: number;
  ocr_score?: number;
  verified_by?: string | null;
  verified_at?: string | null;
  officer_notes?: string | null;
}

// ── Fallback SVG Badges ───────────────────────────────────────────────────────

const makePlateSvg = (text: string) => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 80" width="320" height="80"><rect x="2" y="2" width="316" height="76" rx="8" fill="#ffffff" stroke="#1f2937" stroke-width="4"/><rect x="2" y="2" width="36" height="76" rx="6" fill="#1e3a8a"/><circle cx="20" cy="30" r="10" fill="#3b82f6" opacity="0.6"/><text x="20" y="55" font-family="Arial" font-size="11" font-weight="900" fill="#ffffff" text-anchor="middle">IND</text><text x="175" y="52" font-family="monospace" font-size="32" font-weight="900" fill="#111827" letter-spacing="4" text-anchor="middle">${text}</text></svg>`;
  return `data:image/svg+xml;base64,${btoa(svg)}`;
};

// ── Seed Fallback Records ─────────────────────────────────────────────────────

const INITIAL_RECORDS: AnprRecord[] = [
  {
    record_id: "anpr_rec_001",
    registration_number: "DL 01 AB 1234",
    confidence: 0.942,
    timestamp: new Date(Date.now() - 1000 * 60 * 8).toISOString(),
    gps: { lat: 28.6315, lon: 77.2167, road_segment: "DEL_CP_01", address: "Connaught Place Radial Rd 3, New Delhi" },
    bus_id: "BUS_101",
    camera_id: "FRONT",
    evidence_reference: "ev_sha256_8f2d4e1b9a7c3e5d0a1b2c3d",
    state: "READABLE",
    human_verification_required: false,
    verification_notice: "Automated verification passed",
    perspective_crop_b64: makePlateSvg("DL 01 AB 1234"),
    raw_frame_b64: "",
    auto_publish: true,
    quarantined: false,
    character_confs: [
      {"char": "D", "confidence": 0.98}, {"char": "L", "confidence": 0.97},
      {"char": "0", "confidence": 0.94}, {"char": "1", "confidence": 0.95},
      {"char": "A", "confidence": 0.93}, {"char": "B", "confidence": 0.94},
      {"char": "1", "confidence": 0.96}, {"char": "2", "confidence": 0.93},
      {"char": "3", "confidence": 0.92}, {"char": "4", "confidence": 0.95},
    ],
    format_details: { is_valid: true, format_type: "STANDARD_RTO", state_code: "DL", state_name: "Delhi", district_code: "01", series: "AB", unique_number: "1234" },
    sharpness_score: 142.5,
    detection_score: 0.95,
    ocr_score: 0.94,
  },
  {
    record_id: "anpr_rec_002",
    registration_number: "HR 26 BC 3456",
    confidence: 0.778,
    timestamp: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
    gps: { lat: 28.5672, lon: 77.2100, road_segment: "DEL_RING_04", address: "Ring Road near AIIMS Flyover, New Delhi" },
    bus_id: "BUS_204",
    camera_id: "REAR",
    evidence_reference: "ev_sha256_1c3e5d7f9a2b4c6e8d0a1b2c",
    state: "LOW_CONFIDENCE",
    human_verification_required: true,
    verification_notice: "Human verification required",
    perspective_crop_b64: makePlateSvg("HR 26 BC 3456"),
    raw_frame_b64: "",
    auto_publish: false,
    quarantined: true,
    character_confs: [
      {"char": "H", "confidence": 0.91}, {"char": "R", "confidence": 0.90},
      {"char": "2", "confidence": 0.88}, {"char": "6", "confidence": 0.82},
      {"char": "B", "confidence": 0.64}, {"char": "C", "confidence": 0.68},
      {"char": "3", "confidence": 0.85}, {"char": "4", "confidence": 0.89},
      {"char": "5", "confidence": 0.84}, {"char": "6", "confidence": 0.87},
    ],
    format_details: { is_valid: true, format_type: "STANDARD_RTO", state_code: "HR", state_name: "Haryana", district_code: "26", series: "BC", unique_number: "3456" },
    sharpness_score: 78.4,
    detection_score: 0.82,
    ocr_score: 0.76,
  },
  {
    record_id: "anpr_rec_003",
    registration_number: "NOT_READABLE",
    confidence: 0.412,
    timestamp: new Date(Date.now() - 1000 * 60 * 42).toISOString(),
    gps: { lat: 28.6100, lon: 77.2300, road_segment: "DEL_MATH_02", address: "Mathura Road Corridor, New Delhi" },
    bus_id: "BUS_108",
    camera_id: "FRONT",
    evidence_reference: "ev_sha256_4a6c8e0b2d4f6a8c0e2b4d6f",
    state: "NOT_READABLE",
    human_verification_required: true,
    verification_notice: "Human verification required",
    perspective_crop_b64: makePlateSvg("UNREADABLE"),
    raw_frame_b64: "",
    auto_publish: false,
    quarantined: true,
    character_confs: [],
    format_details: { is_valid: false, format_type: "INVALID", issues: ["Severe motion blur and dirt occlusion"] },
    sharpness_score: 24.1,
    detection_score: 0.55,
    ocr_score: 0.38,
  },
  {
    record_id: "anpr_rec_004",
    registration_number: "NOT_PRESENT",
    confidence: 0.0,
    timestamp: new Date(Date.now() - 1000 * 60 * 75).toISOString(),
    gps: { lat: 28.6500, lon: 77.1900, road_segment: "DEL_KAROL_01", address: "Karol Bagh Junction, New Delhi" },
    bus_id: "BUS_112",
    camera_id: "LEFT",
    evidence_reference: "ev_sha256_7b9d1f3a5c7e9b1d3f5a7c9e",
    state: "NOT_PRESENT",
    human_verification_required: false,
    verification_notice: "No license plate identified on vehicle",
    perspective_crop_b64: makePlateSvg("NO PLATE"),
    raw_frame_b64: "",
    auto_publish: false,
    quarantined: false,
    character_confs: [],
    format_details: { is_valid: false, format_type: "NONE", issues: ["Plate missing from vehicle bumper"] },
    sharpness_score: 0.0,
    detection_score: 0.0,
    ocr_score: 0.0,
  },
  {
    record_id: "anpr_rec_005",
    registration_number: "KA 05 MN 9012",
    confidence: 0.955,
    timestamp: new Date(Date.now() - 1000 * 60 * 95).toISOString(),
    gps: { lat: 12.9716, lon: 77.5946, road_segment: "BLR_MG_01", address: "MG Road & Brigade Rd, Bengaluru" },
    bus_id: "BUS_305",
    camera_id: "FRONT",
    evidence_reference: "ev_sha256_2e4a6c8e0b2d4f6a8c0e2b4d",
    state: "READABLE",
    human_verification_required: false,
    verification_notice: "Automated verification passed",
    perspective_crop_b64: makePlateSvg("KA 05 MN 9012"),
    raw_frame_b64: "",
    auto_publish: true,
    quarantined: false,
    character_confs: [
      {"char": "K", "confidence": 0.98}, {"char": "A", "confidence": 0.97},
      {"char": "0", "confidence": 0.95}, {"char": "5", "confidence": 0.96},
      {"char": "M", "confidence": 0.94}, {"char": "N", "confidence": 0.95},
      {"char": "9", "confidence": 0.97}, {"char": "0", "confidence": 0.94},
      {"char": "1", "confidence": 0.96}, {"char": "2", "confidence": 0.95},
    ],
    format_details: { is_valid: true, format_type: "STANDARD_RTO", state_code: "KA", state_name: "Karnataka", district_code: "05", series: "MN", unique_number: "9012" },
    sharpness_score: 155.0,
    detection_score: 0.96,
    ocr_score: 0.95,
  },
  {
    record_id: "anpr_rec_006",
    registration_number: "22 BH 1234 AA",
    confidence: 0.925,
    timestamp: new Date(Date.now() - 1000 * 60 * 130).toISOString(),
    gps: { lat: 19.0760, lon: 72.8777, road_segment: "MUM_WEH_02", address: "Bandra Kurla Complex, Mumbai" },
    bus_id: "BUS_402",
    camera_id: "FRONT",
    evidence_reference: "ev_sha256_9d1f3a5c7e9b1d3f5a7c9e1b",
    state: "READABLE",
    human_verification_required: false,
    verification_notice: "Automated verification passed",
    perspective_crop_b64: makePlateSvg("22 BH 1234 AA"),
    raw_frame_b64: "",
    auto_publish: true,
    quarantined: false,
    character_confs: [
      {"char": "2", "confidence": 0.95}, {"char": "2", "confidence": 0.94},
      {"char": "B", "confidence": 0.92}, {"char": "H", "confidence": 0.93},
      {"char": "1", "confidence": 0.94}, {"char": "2", "confidence": 0.93},
      {"char": "3", "confidence": 0.91}, {"char": "4", "confidence": 0.92},
      {"char": "A", "confidence": 0.93}, {"char": "A", "confidence": 0.92},
    ],
    format_details: { is_valid: true, format_type: "BHARAT_SERIES", state_code: "BH", state_name: "Bharat Central Series", district_code: "22", series: "AA", unique_number: "1234" },
    sharpness_score: 138.0,
    detection_score: 0.93,
    ocr_score: 0.92,
  },
];

const PIPELINE_STAGES = [
  { id: 1, name: "Incident Vehicle", desc: "Track bounding boxes & velocity across video stream" },
  { id: 2, name: "Track Frames", desc: "Sample 5-10 candidate frames from trajectory" },
  { id: 3, name: "Select Sharpest Frame", desc: "Laplacian blur variance metric (σ²(∇²I))" },
  { id: 4, name: "Detect License Plate", desc: "High-precision plate ROI localization" },
  { id: 5, name: "Perspective Correction", desc: "4-point planar warp to 320×80 px aspect" },
  { id: 6, name: "OCR Engine", desc: "Character segmentation & positional recognition" },
  { id: 7, name: "Format Validation", desc: "Indian RTO & Bharat BH-series syntax verification" },
  { id: 8, name: "Confidence & Gate", desc: "Quarantine low confidence (<0.85) behind human sign-off" },
];

export const ANPR: React.FC = () => {
  const [records, setRecords] = useState<AnprRecord[]>(INITIAL_RECORDS);
  const [selectedRecord, setSelectedRecord] = useState<AnprRecord | null>(INITIAL_RECORDS[1]); // select low-confidence by default
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [stateFilter, setStateFilter] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Verification Form State
  const [officerId, setOfficerId] = useState<string>("officer_delhi_01");
  const [editedPlate, setEditedPlate] = useState<string>("");
  const [officerNotes, setOfficerNotes] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Sync with Backend
  const fetchRecords = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch("/api/v1/anpr/records?limit=100");
      if (res.ok) {
        const data = await res.json();
        if (data.items && data.items.length > 0) {
          setRecords(data.items);
          if (selectedRecord) {
            const updated = data.items.find((r: AnprRecord) => r.record_id === selectedRecord.record_id);
            if (updated) setSelectedRecord(updated);
          }
        }
      }
    } catch (e) {
      console.warn("ANPR API unreachable; using resilient mock state", e);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchRecords();
    const interval = setInterval(fetchRecords, 20000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedRecord) {
      setEditedPlate(selectedRecord.registration_number === "NOT_READABLE" || selectedRecord.registration_number === "NOT_PRESENT" ? "" : selectedRecord.registration_number);
      setOfficerNotes(selectedRecord.officer_notes || "");
    }
  }, [selectedRecord]);

  // Handle Human Verification Action
  const handleVerify = async (action: "APPROVE" | "EDIT" | "REJECT") => {
    if (!selectedRecord) return;
    setIsSubmitting(true);
    try {
      const res = await fetch(`/api/v1/anpr/records/${selectedRecord.record_id}/verify`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          verified_plate: action === "EDIT" ? editedPlate : selectedRecord.registration_number,
          officer_id: officerId,
          notes: officerNotes || `Plate verified via human inspection (${action})`,
        }),
      });

      const updatedRecord: AnprRecord = {
        ...selectedRecord,
        state: action === "REJECT" ? "NOT_READABLE" : "READABLE",
        registration_number: action === "REJECT" ? "NOT_READABLE" : (editedPlate || selectedRecord.registration_number),
        quarantined: false,
        auto_publish: action !== "REJECT",
        human_verification_required: false,
        verification_notice: `Human verified by ${officerId}`,
        verified_by: officerId,
        verified_at: new Date().toISOString(),
        officer_notes: officerNotes,
        perspective_crop_b64: action === "REJECT" ? makePlateSvg("UNREADABLE") : makePlateSvg(editedPlate || selectedRecord.registration_number),
      };

      setRecords((prev) =>
        prev.map((r) => (r.record_id === selectedRecord.record_id ? updatedRecord : r))
      );
      setSelectedRecord(updatedRecord);
    } catch (e) {
      console.error("Verification error", e);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Filter records
  const displayedRecords = records.filter((r) => {
    const matchesState =
      stateFilter === "ALL" ||
      (stateFilter === "QUARANTINED" && r.quarantined) ||
      r.state === stateFilter;
    const matchesSearch =
      searchTerm === "" ||
      r.record_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.registration_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.bus_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.gps.address || "").toLowerCase().includes(searchTerm.toLowerCase());
    return matchesState && matchesSearch;
  });

  // KPIs
  const totalScanned = records.length;
  const readableCount = records.filter((r) => r.state === "READABLE").length;
  const quarantinedCount = records.filter((r) => r.quarantined).length;
  const unreadableCount = records.filter((r) => r.state === "NOT_READABLE" || r.state === "NOT_PRESENT").length;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-4 sm:p-6 lg:p-8 space-y-6">
      {/* ── Header & Navigation ────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-emerald-950/60 border border-emerald-800/50 rounded-xl text-emerald-400">
              <Car className="w-5 h-5" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                Automatic Number Plate Recognition (ANPR)
              </h1>
              <p className="text-xs text-gray-400 mt-0.5">
                Indian vehicle registration recognition, planar perspective rectification, and human verification gate
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
            <a href="/incidents" className="px-2.5 py-1 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors">Incidents</a>
            <span className="px-2.5 py-1 bg-emerald-600 text-white rounded-lg font-semibold">ANPR</span>
          </nav>

          <button
            onClick={fetchRecords}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3 py-1.5 bg-gray-900 border border-gray-800 hover:bg-gray-800 text-gray-300 text-xs rounded-xl font-medium transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-emerald-400" : ""}`} />
            <span>{isRefreshing ? "Syncing..." : "Sync Live"}</span>
          </button>
        </div>
      </div>

      {/* ── Strict Quarantine Guardrail Banner ───────────────────────────────── */}
      <div className="bg-amber-950/30 border border-amber-800/40 rounded-2xl p-4 flex items-start gap-3 text-xs text-amber-200">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-semibold text-white block">
            Strict Publication Guardrail — Never Automatically Publish Low-Confidence Plates
          </span>
          <p className="text-amber-300 leading-relaxed text-[11px]">
            In strict compliance with evidentiary standards, plates with confidence below threshold (&lt;0.85), character ambiguity, or severe blur are quarantined. They are designated as <strong>LOW_CONFIDENCE</strong> or <strong>NOT_READABLE</strong> with an immutable requirement: <strong>"Human verification required"</strong>. These records remain blocked from external dissemination or enforcement actions until an authorized officer reviews the raw frame, confirms the transcription, and manually signs off.
          </p>
        </div>
      </div>

      {/* ── 4 Primary KPI Cards ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Scanned */}
        <div className="bg-gray-900/80 border border-gray-800/80 rounded-2xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 font-medium">Total Plates Scanned</span>
            <span className="p-1.5 bg-blue-950/60 border border-blue-800/40 text-blue-400 rounded-lg">
              <Car className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">{totalScanned}</span>
            <span className="text-[11px] text-gray-400">Total Analyzed</span>
          </div>
          <p className="text-[10px] text-gray-500 mt-1">Multi-frame sharpest candidate selection</p>
        </div>

        {/* Verified Readable */}
        <div className="bg-emerald-950/20 border border-emerald-800/40 rounded-2xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-emerald-300 font-medium">Verified Readable</span>
            <span className="p-1.5 bg-emerald-950/60 border border-emerald-800/40 text-emerald-400 rounded-lg">
              <CheckCircle2 className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-300">{readableCount}</span>
            <span className="text-[11px] text-emerald-400/80">
              {((readableCount / Math.max(1, totalScanned)) * 100).toFixed(1)}% auto-published
            </span>
          </div>
          <p className="text-[10px] text-emerald-400/70 mt-1">Confidence &ge; 0.85 + Indian RTO validated</p>
        </div>

        {/* Quarantined Low-Confidence */}
        <div className="bg-amber-950/20 border border-amber-800/40 rounded-2xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-amber-300 font-medium">Quarantined Plates</span>
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-amber-300">{quarantinedCount}</span>
            <span className="text-[11px] text-amber-400/80">Human verification required</span>
          </div>
          <p className="text-[10px] text-amber-400/70 mt-1">Automated publishing blocked</p>
        </div>

        {/* Unreadable / Missing */}
        <div className="bg-rose-950/20 border border-rose-800/40 rounded-2xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-rose-300 font-medium">Unreadable / Not Present</span>
            <span className="p-1.5 bg-rose-950/60 border border-rose-800/40 text-rose-400 rounded-lg">
              <XCircle className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-rose-300">{unreadableCount}</span>
            <span className="text-[11px] text-rose-400/80">Severely obscured</span>
          </div>
          <p className="text-[10px] text-rose-400/70 mt-1">Plate missing or blur index &lt; 30</p>
        </div>
      </div>

      {/* ── Interactive 8-Stage Pipeline Flow Visualizer ─────────────────────── */}
      <div className="bg-gray-900/80 border border-gray-800/80 rounded-2xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-emerald-400" />
            Autonomous Vehicle Registration Recognition Pipeline
          </span>
          <span className="text-[10px] text-gray-400">
            Edge-native execution on onboard bus compute
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
          {PIPELINE_STAGES.map((st, i) => (
            <div
              key={st.id}
              className="p-2.5 rounded-xl border bg-gray-950/60 border-gray-800/80 flex flex-col justify-between hover:border-emerald-500/40 transition-colors"
            >
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[9px] font-bold text-emerald-400">STAGE {st.id}</span>
                  {i < 7 && <ArrowRight className="w-2.5 h-2.5 text-gray-600 hidden lg:block" />}
                </div>
                <div className="text-[11px] font-semibold text-gray-200">{st.name}</div>
              </div>
              <p className="text-[9px] text-gray-400 mt-1 leading-tight">{st.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Main Workspace: Records Feed & Verification Inspector Pane ───────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* ── Left Column: Records Feed & Filters (5 cols) ───────────────────── */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-gray-900/80 border border-gray-800/80 rounded-2xl p-3.5 space-y-3">
            {/* Search Input */}
            <div className="flex items-center gap-2 bg-gray-950 border border-gray-800 rounded-xl px-3 py-1.5">
              <Search className="w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="Search plate (e.g. DL 01), record ID, or bus..."
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

            {/* State Filter Pills */}
            <div className="flex flex-wrap items-center gap-1.5">
              {[
                { id: "ALL", label: "All Records" },
                { id: "QUARANTINED", label: "Quarantined" },
                { id: "READABLE", label: "Readable" },
                { id: "LOW_CONFIDENCE", label: "Low Conf" },
                { id: "NOT_READABLE", label: "Unreadable" },
                { id: "NOT_PRESENT", label: "No Plate" },
              ].map((pill) => (
                <button
                  key={pill.id}
                  onClick={() => setStateFilter(pill.id)}
                  className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors ${
                    stateFilter === pill.id
                      ? pill.id === "QUARANTINED"
                        ? "bg-amber-600 text-white"
                        : "bg-emerald-600 text-white"
                      : "bg-gray-800/60 text-gray-400 hover:text-gray-200 hover:bg-gray-800"
                  }`}
                >
                  {pill.label}
                </button>
              ))}
            </div>
          </div>

          {/* Records List */}
          <div className="space-y-2.5 max-h-[680px] overflow-y-auto pr-1">
            {displayedRecords.length === 0 ? (
              <div className="p-8 text-center bg-gray-900/40 border border-gray-800/60 rounded-2xl">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2 opacity-60" />
                <p className="text-xs text-gray-400">No ANPR records match your filter</p>
              </div>
            ) : (
              displayedRecords.map((rec) => {
                const isSelected = selectedRecord?.record_id === rec.record_id;
                const isReadable = rec.state === "READABLE";
                const isLow = rec.state === "LOW_CONFIDENCE";
                const isUnreadable = rec.state === "NOT_READABLE";
                const isNotPresent = rec.state === "NOT_PRESENT";

                return (
                  <div
                    key={rec.record_id}
                    onClick={() => setSelectedRecord(rec)}
                    className={`p-3.5 rounded-2xl border transition-all cursor-pointer ${
                      isSelected
                        ? "bg-gray-900 border-emerald-500/70 shadow-lg shadow-emerald-950/20 ring-1 ring-emerald-500/40"
                        : "bg-gray-900/60 border-gray-800/70 hover:bg-gray-900 hover:border-gray-700"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider ${
                            isReadable
                              ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800/60"
                              : isLow
                              ? "bg-amber-950/80 text-amber-300 border border-amber-800/60 animate-pulse"
                              : isUnreadable
                              ? "bg-rose-950/80 text-rose-300 border border-rose-800/60"
                              : "bg-gray-800 text-gray-400 border border-gray-700"
                          }`}
                        >
                          {rec.state.replace(/_/g, " ")}
                        </span>

                        {rec.quarantined && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                            <Lock className="w-2.5 h-2.5" /> Quarantined
                          </span>
                        )}
                      </div>

                      <span className="text-[10px] text-gray-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(rec.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>

                    <div className="mt-2.5 flex items-center justify-between">
                      <div>
                        <div className="font-mono text-sm font-bold text-white tracking-wide">
                          {rec.registration_number}
                        </div>
                        <div className="text-[11px] text-gray-400 mt-0.5">
                          Bus {rec.bus_id} ({rec.camera_id}) • {rec.format_details?.state_name || "Regional Authority"}
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-xs font-bold text-emerald-400">
                          {(rec.confidence * 100).toFixed(0)}% Conf
                        </div>
                        <div className="text-[9px] text-gray-500 font-mono">
                          {rec.evidence_reference.slice(0, 14)}...
                        </div>
                      </div>
                    </div>

                    {rec.human_verification_required && (
                      <div className="mt-2 pt-2 border-t border-gray-800/60 flex items-center gap-1 text-[10px] text-amber-400">
                        <AlertTriangle className="w-3 h-3 shrink-0" />
                        <span>{rec.verification_notice}</span>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ── Right Column: Verification Inspector & Evidence Detail (7 cols) ── */}
        <div className="lg:col-span-7 space-y-4">
          {selectedRecord ? (
            <div className="bg-gray-900/80 border border-gray-800/80 rounded-2xl p-5 space-y-5">
              {/* Header Info */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-800/80 pb-3.5">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-white">
                      ANPR Evidence Inspector — {selectedRecord.record_id}
                    </h2>
                    <span
                      className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase ${
                        selectedRecord.state === "READABLE"
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          : selectedRecord.state === "LOW_CONFIDENCE"
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                          : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                      }`}
                    >
                      {selectedRecord.state.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1">
                    <MapPin className="w-3 h-3 text-gray-500" />
                    {selectedRecord.gps.address || "Road Segment"} • GPS: {selectedRecord.gps.lat.toFixed(4)}, {selectedRecord.gps.lon.toFixed(4)}
                  </p>
                </div>

                <div className="text-right">
                  <div className="text-xs text-gray-400">Overall Confidence</div>
                  <div className="text-lg font-extrabold text-emerald-400">
                    {(selectedRecord.confidence * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* ── Perspective-Corrected Plate Crop ──────────────────────────── */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-gray-300 flex items-center justify-between">
                  <span>Perspective-Rectified Plate Crop (Standard 320×80 Planar Projection)</span>
                  <span className="text-[10px] font-mono text-gray-500">
                    Laplacian Sharpness: {selectedRecord.sharpness_score?.toFixed(1) || "120.0"}
                  </span>
                </span>

                <div className="bg-gray-950 border border-gray-800 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div className="w-full max-w-[320px] rounded-lg overflow-hidden border border-gray-700 shadow-md">
                    <img
                      src={selectedRecord.perspective_crop_b64}
                      alt="Perspective Rectified Plate"
                      className="w-full h-auto"
                    />
                  </div>

                  <div className="text-xs space-y-1.5 w-full">
                    <div className="flex justify-between border-b border-gray-800 pb-1">
                      <span className="text-gray-400">State / Authority:</span>
                      <span className="text-white font-medium">{selectedRecord.format_details?.state_name || "Official State"}</span>
                    </div>
                    <div className="flex justify-between border-b border-gray-800 pb-1">
                      <span className="text-gray-400">Format Standard:</span>
                      <span className="text-emerald-400 font-mono text-[11px]">{selectedRecord.format_details?.format_type || "STANDARD_RTO"}</span>
                    </div>
                    <div className="flex justify-between border-b border-gray-800 pb-1">
                      <span className="text-gray-400">Evidence Hash:</span>
                      <span className="text-gray-300 font-mono text-[10px]">{selectedRecord.evidence_reference}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Camera / Bus:</span>
                      <span className="text-gray-200">{selectedRecord.camera_id} CAM • {selectedRecord.bus_id}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* ── Character-Level Confidence Breakdown ──────────────────────── */}
              {selectedRecord.character_confs && selectedRecord.character_confs.length > 0 && (
                <div className="space-y-2">
                  <span className="text-xs font-semibold text-gray-300 block">
                    Optical Character Recognition (OCR) Confidence Breakdown
                  </span>
                  <div className="grid grid-cols-5 sm:grid-cols-10 gap-1.5">
                    {selectedRecord.character_confs.map((c, idx) => (
                      <div
                        key={idx}
                        className={`p-2 rounded-lg border text-center ${
                          c.confidence >= 0.85
                            ? "bg-emerald-950/30 border-emerald-800/40 text-emerald-300"
                            : "bg-amber-950/40 border-amber-800/50 text-amber-300 ring-1 ring-amber-500/50"
                        }`}
                      >
                        <div className="font-mono text-base font-bold">{c.char}</div>
                        <div className="text-[9px] mt-0.5">{(c.confidence * 100).toFixed(0)}%</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ── Human Verification & Sign-off Panel ───────────────────────── */}
              <div className="bg-gray-950 border border-gray-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <FileCheck2 className="w-4 h-4 text-emerald-400" />
                    Human Verification & Manual Correction Gate
                  </span>
                  <span className="text-[10px] text-gray-400">
                    Mandatory for quarantined plates
                  </span>
                </div>

                {selectedRecord.verified_by && (
                  <div className="p-3 bg-gray-900 border border-gray-800 rounded-lg text-xs space-y-1">
                    <div className="text-[10px] text-gray-400 flex items-center justify-between">
                      <span>Verified by: <strong>{selectedRecord.verified_by}</strong></span>
                      <span>{selectedRecord.verified_at ? new Date(selectedRecord.verified_at).toLocaleString() : ""}</span>
                    </div>
                    <p className="text-gray-200 text-[11px] italic">"{selectedRecord.officer_notes}"</p>
                  </div>
                )}

                <div className="space-y-2.5">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-gray-400 block mb-1">
                        Verified Registration Number (Indian Standard Format)
                      </label>
                      <input
                        type="text"
                        value={editedPlate}
                        onChange={(e) => setEditedPlate(e.target.value.toUpperCase())}
                        placeholder="e.g. DL 01 AB 1234"
                        className="w-full bg-gray-900 border border-gray-800 rounded-lg px-2.5 py-1.5 text-xs font-mono font-bold text-white focus:outline-none focus:border-emerald-500 uppercase tracking-wider"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-gray-400 block mb-1">Safety Officer ID</label>
                      <input
                        type="text"
                        value={officerId}
                        onChange={(e) => setOfficerId(e.target.value)}
                        placeholder="e.g. officer_delhi_01"
                        className="w-full bg-gray-900 border border-gray-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-[10px] text-gray-400 block mb-1">Officer Observations & Evidentiary Notes</label>
                    <textarea
                      rows={2}
                      value={officerNotes}
                      onChange={(e) => setOfficerNotes(e.target.value)}
                      placeholder="Add inspection notes (e.g. verified plate visually against raw video frame, resolved optical ambiguity between 8 and B...)"
                      className="w-full bg-gray-900 border border-gray-800 rounded-lg p-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>

                {/* Verification Actions */}
                <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
                  <button
                    onClick={() => handleVerify("REJECT")}
                    disabled={isSubmitting}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white rounded-xl text-xs font-semibold transition-all disabled:opacity-50"
                  >
                    <XCircle className="w-4 h-4 text-rose-400" />
                    <span>Mark Unreadable</span>
                  </button>

                  <button
                    onClick={() => handleVerify(editedPlate !== selectedRecord.registration_number ? "EDIT" : "APPROVE")}
                    disabled={isSubmitting}
                    className="flex items-center gap-1.5 px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-emerald-950/30 transition-all disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Verify & Approve Plate</span>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center bg-gray-900/40 border border-gray-800/60 rounded-2xl">
              <p className="text-xs text-gray-400">Select an ANPR record from the list to inspect</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ANPR;
