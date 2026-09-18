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
    <div className="min-h-screen bg-transparent text-[#16192E] p-4 sm:p-6 lg:p-8 space-y-6">
      {/* ── Header & Navigation ────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700">
              <Car className="w-5 h-5" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-[#16192E] flex items-center gap-2">
                Automatic Number Plate Recognition (ANPR)
              </h1>
              <p className="text-xs text-[#64748B] mt-0.5">
                Indian vehicle registration recognition, planar perspective rectification, and human verification gate
              </p>
            </div>
          </div>
        </div>

        {/* Global Navigation Links */}
        <div className="flex flex-wrap items-center gap-2">
          <nav className="flex items-center space-x-1 text-xs bg-white border border-[#CBD5E1] rounded-xl p-1 shadow-2xs">
            <a href="/" className="px-2.5 py-1 text-[#64748B] hover:text-[#16192E] rounded-lg hover:bg-[#F8FAFC] transition-colors">Home</a>
            <a href="/fleet" className="px-2.5 py-1 text-[#64748B] hover:text-[#16192E] rounded-lg hover:bg-[#F8FAFC] transition-colors">Fleet</a>
            <a href="/road-defects" className="px-2.5 py-1 text-[#64748B] hover:text-[#16192E] rounded-lg hover:bg-[#F8FAFC] transition-colors">Defects</a>
            <a href="/traffic" className="px-2.5 py-1 text-[#64748B] hover:text-[#16192E] rounded-lg hover:bg-[#F8FAFC] transition-colors">Traffic</a>
            <a href="/congestion" className="px-2.5 py-1 text-[#64748B] hover:text-[#16192E] rounded-lg hover:bg-[#F8FAFC] transition-colors">Congestion</a>
            <a href="/pedestrian-safety" className="px-2.5 py-1 text-[#64748B] hover:text-[#16192E] rounded-lg hover:bg-[#F8FAFC] transition-colors">Pedestrian</a>
            <a href="/incidents" className="px-2.5 py-1 text-[#64748B] hover:text-[#16192E] rounded-lg hover:bg-[#F8FAFC] transition-colors">Incidents</a>
            <span className="px-2.5 py-1 bg-[#16192E] text-white rounded-lg font-semibold shadow-xs">ANPR</span>
          </nav>

          <button
            onClick={fetchRecords}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3 py-1.5 bg-white border border-[#CBD5E1] hover:bg-[#F8FAFC] text-[#16192E] text-xs rounded-xl font-medium shadow-2xs transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-[#C85A17]" : "text-[#64748B]"}`} />
            <span>{isRefreshing ? "Syncing..." : "Sync Live"}</span>
          </button>
        </div>
      </div>

      {/* ── Strict Quarantine Guardrail Banner ───────────────────────────────── */}
      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-start gap-3 text-xs text-amber-900 shadow-sm">
        <ShieldAlert className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-bold text-amber-950 block">
            Strict Publication Guardrail — Never Automatically Publish Low-Confidence Plates
          </span>
          <p className="text-amber-800 leading-relaxed text-[11px]">
            In strict compliance with evidentiary standards, plates with confidence below threshold (&lt;0.85), character ambiguity, or severe blur are quarantined. They are designated as <strong>LOW_CONFIDENCE</strong> or <strong>NOT_READABLE</strong> with an immutable requirement: <strong>"Human verification required"</strong>. These records remain blocked from external dissemination or enforcement actions until an authorized officer reviews the raw frame, confirms the transcription, and manually signs off.
          </p>
        </div>
      </div>

      {/* ── 4 Primary KPI Cards ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Scanned */}
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#64748B] font-semibold">Total Plates Scanned</span>
            <span className="p-1.5 bg-blue-50 border border-blue-200 text-blue-700 rounded-lg">
              <Car className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-[#16192E]">{totalScanned}</span>
            <span className="text-[11px] text-[#64748B] font-medium">Total Analyzed</span>
          </div>
          <p className="text-[10px] text-[#64748B] mt-1">Multi-frame sharpest candidate selection</p>
        </div>

        {/* Verified Readable */}
        <div className="bg-white border border-emerald-200 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs text-emerald-800 font-semibold">Verified Readable</span>
            <span className="p-1.5 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg">
              <CheckCircle2 className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-700">{readableCount}</span>
            <span className="text-[11px] text-emerald-800/80 font-medium">
              {((readableCount / Math.max(1, totalScanned)) * 100).toFixed(1)}% auto-published
            </span>
          </div>
          <p className="text-[10px] text-emerald-700 mt-1">Confidence &ge; 0.85 + Indian RTO validated</p>
        </div>

        {/* Quarantined Low-Confidence */}
        <div className="bg-white border border-amber-200 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs text-amber-800 font-semibold">Quarantined Plates</span>
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-amber-700">{quarantinedCount}</span>
            <span className="text-[11px] text-amber-800/80 font-medium">Human verification required</span>
          </div>
          <p className="text-[10px] text-amber-700 mt-1">Automated publishing blocked</p>
        </div>

        {/* Unreadable / Missing */}
        <div className="bg-white border border-rose-200 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs text-rose-800 font-semibold">Unreadable / Not Present</span>
            <span className="p-1.5 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg">
              <XCircle className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-rose-700">{unreadableCount}</span>
            <span className="text-[11px] text-rose-800/80 font-medium">Severely obscured</span>
          </div>
          <p className="text-[10px] text-rose-700 mt-1">Plate missing or blur index &lt; 30</p>
        </div>
      </div>

      {/* ── Interactive 8-Stage Pipeline Flow Visualizer ─────────────────────── */}
      <div className="bg-white border border-[#E2E8F0] rounded-2xl p-4 space-y-3 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-[#16192E] flex items-center gap-2">
            <Layers className="w-4 h-4 text-[#C85A17]" />
            Autonomous Vehicle Registration Recognition Pipeline
          </span>
          <span className="text-[10px] text-[#64748B]">
            Edge-native execution on onboard bus compute
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
          {PIPELINE_STAGES.map((st, i) => (
            <div
              key={st.id}
              className="p-2.5 rounded-xl border bg-[#F8FAFC] border-[#E2E8F0] flex flex-col justify-between hover:border-[#CBD5E1] transition-colors"
            >
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[9px] font-bold text-[#C85A17]">STAGE {st.id}</span>
                  {i < 7 && <ArrowRight className="w-2.5 h-2.5 text-[#94A3B8] hidden lg:block" />}
                </div>
                <div className="text-[11px] font-bold text-[#16192E]">{st.name}</div>
              </div>
              <p className="text-[9px] text-[#64748B] mt-1 leading-tight">{st.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Main Workspace: Records Feed & Verification Inspector Pane ───────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* ── Left Column: Records Feed & Filters (5 cols) ───────────────────── */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white border border-[#E2E8F0] rounded-2xl p-3.5 space-y-3 shadow-sm">
            {/* Search Input */}
            <div className="flex items-center gap-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl px-3 py-1.5">
              <Search className="w-4 h-4 text-[#94A3B8]" />
              <input
                type="text"
                placeholder="Search plate (e.g. DL 01), record ID, or bus..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-transparent text-xs text-[#16192E] placeholder-[#94A3B8] focus:outline-none w-full"
              />
              {searchTerm && (
                <button onClick={() => setSearchTerm("")} className="text-[#94A3B8] hover:text-[#16192E]">
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
                      ? "bg-[#16192E] text-white shadow-xs font-semibold"
                      : "bg-[#F8FAFC] text-[#64748B] hover:text-[#16192E] hover:bg-[#EEF2F6] border border-[#E2E8F0]"
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
              <div className="p-8 text-center bg-white border border-[#E2E8F0] rounded-2xl shadow-sm">
                <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2 opacity-60" />
                <p className="text-xs text-[#64748B]">No ANPR records match your filter</p>
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
                        ? "bg-orange-50/50 border-[#C85A17] shadow-sm ring-1 ring-[#C85A17]/40"
                        : "bg-white border-[#E2E8F0] hover:bg-[#F8FAFC] shadow-sm"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider ${
                            isReadable
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : isLow
                              ? "bg-amber-50 text-amber-800 border border-amber-200"
                              : isUnreadable
                              ? "bg-rose-50 text-rose-700 border border-rose-200"
                              : "bg-slate-100 text-[#64748B] border border-slate-200"
                          }`}
                        >
                          {rec.state.replace(/_/g, " ")}
                        </span>

                        {rec.quarantined && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-1">
                            <Lock className="w-2.5 h-2.5" /> Quarantined
                          </span>
                        )}
                      </div>

                      <span className="text-[10px] text-[#64748B] flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(rec.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>

                    <div className="mt-2.5 flex items-center justify-between">
                      <div>
                        <div className="font-mono text-sm font-bold text-[#16192E] tracking-wide">
                          {rec.registration_number}
                        </div>
                        <div className="text-[11px] text-[#64748B] mt-0.5">
                          Bus {rec.bus_id} ({rec.camera_id}) • {rec.format_details?.state_name || "Regional Authority"}
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-xs font-bold text-[#C85A17]">
                          {(rec.confidence * 100).toFixed(0)}% Conf
                        </div>
                        <div className="text-[9px] text-[#64748B] font-mono">
                          {rec.evidence_reference.slice(0, 14)}...
                        </div>
                      </div>
                    </div>

                    {rec.human_verification_required && (
                      <div className="mt-2 pt-2 border-t border-[#E2E8F0] flex items-center gap-1 text-[10px] text-amber-700 font-medium">
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
            <div className="bg-white border border-[#E2E8F0] rounded-2xl p-5 space-y-5 shadow-sm">
              {/* Header Info */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E2E8F0] pb-3.5">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-[#16192E]">
                      ANPR Evidence Inspector — {selectedRecord.record_id}
                    </h2>
                    <span
                      className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase ${
                        selectedRecord.state === "READABLE"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : selectedRecord.state === "LOW_CONFIDENCE"
                          ? "bg-amber-50 text-amber-800 border border-amber-200"
                          : "bg-rose-50 text-rose-700 border border-rose-200"
                      }`}
                    >
                      {selectedRecord.state.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="text-xs text-[#64748B] mt-0.5 flex items-center gap-1">
                    <MapPin className="w-3 h-3 text-[#64748B]" />
                    {selectedRecord.gps.address || "Road Segment"} • GPS: {selectedRecord.gps.lat.toFixed(4)}, {selectedRecord.gps.lon.toFixed(4)}
                  </p>
                </div>

                <div className="text-right">
                  <div className="text-xs text-[#64748B] font-medium">Overall Confidence</div>
                  <div className="text-lg font-extrabold text-[#C85A17]">
                    {(selectedRecord.confidence * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* ── Perspective-Corrected Plate Crop ──────────────────────────── */}
              <div className="space-y-2">
                <span className="text-xs font-bold text-[#16192E] flex items-center justify-between">
                  <span>Perspective-Rectified Plate Crop (Standard 320×80 Planar Projection)</span>
                  <span className="text-[10px] font-mono text-[#64748B]">
                    Laplacian Sharpness: {selectedRecord.sharpness_score?.toFixed(1) || "120.0"}
                  </span>
                </span>

                <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div className="w-full max-w-[320px] rounded-lg overflow-hidden border border-[#CBD5E1] shadow-sm">
                    <img
                      src={selectedRecord.perspective_crop_b64}
                      alt="Perspective Rectified Plate"
                      className="w-full h-auto"
                    />
                  </div>

                  <div className="text-xs space-y-1.5 w-full">
                    <div className="flex justify-between border-b border-[#E2E8F0] pb-1">
                      <span className="text-[#64748B]">State / Authority:</span>
                      <span className="text-[#16192E] font-semibold">{selectedRecord.format_details?.state_name || "Official State"}</span>
                    </div>
                    <div className="flex justify-between border-b border-[#E2E8F0] pb-1">
                      <span className="text-[#64748B]">Format Standard:</span>
                      <span className="text-emerald-700 font-mono text-[11px] font-semibold">{selectedRecord.format_details?.format_type || "STANDARD_RTO"}</span>
                    </div>
                    <div className="flex justify-between border-b border-[#E2E8F0] pb-1">
                      <span className="text-[#64748B]">Evidence Hash:</span>
                      <span className="text-[#16192E] font-mono text-[10px]">{selectedRecord.evidence_reference}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#64748B]">Camera / Bus:</span>
                      <span className="text-[#16192E] font-medium">{selectedRecord.camera_id} CAM • {selectedRecord.bus_id}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* ── Character-Level Confidence Breakdown ──────────────────────── */}
              {selectedRecord.character_confs && selectedRecord.character_confs.length > 0 && (
                <div className="space-y-2">
                  <span className="text-xs font-bold text-[#16192E] block">
                    Optical Character Recognition (OCR) Confidence Breakdown
                  </span>
                  <div className="grid grid-cols-5 sm:grid-cols-10 gap-1.5">
                    {selectedRecord.character_confs.map((c, idx) => (
                      <div
                        key={idx}
                        className={`p-2 rounded-lg border text-center ${
                          c.confidence >= 0.85
                            ? "bg-emerald-50 border-emerald-200 text-emerald-800 font-bold"
                            : "bg-amber-50 border-amber-200 text-amber-800 ring-1 ring-amber-400 font-bold"
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
              <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#16192E] flex items-center gap-1.5">
                    <FileCheck2 className="w-4 h-4 text-[#C85A17]" />
                    Human Verification &amp; Manual Correction Gate
                  </span>
                  <span className="text-[10px] text-[#64748B]">
                    Mandatory for quarantined plates
                  </span>
                </div>

                {selectedRecord.verified_by && (
                  <div className="p-3 bg-white border border-[#E2E8F0] rounded-lg text-xs space-y-1 shadow-2xs">
                    <div className="text-[10px] text-[#64748B] flex items-center justify-between">
                      <span>Verified by: <strong>{selectedRecord.verified_by}</strong></span>
                      <span>{selectedRecord.verified_at ? new Date(selectedRecord.verified_at).toLocaleString() : ""}</span>
                    </div>
                    <p className="text-[#16192E] text-[11px] italic">"{selectedRecord.officer_notes}"</p>
                  </div>
                )}

                <div className="space-y-2.5">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] font-semibold text-[#64748B] block mb-1">
                        Verified Registration Number (Indian Standard Format)
                      </label>
                      <input
                        type="text"
                        value={editedPlate}
                        onChange={(e) => setEditedPlate(e.target.value.toUpperCase())}
                        placeholder="e.g. DL 01 AB 1234"
                        className="w-full bg-white border border-[#CBD5E1] rounded-lg px-2.5 py-1.5 text-xs font-mono font-bold text-[#16192E] focus:outline-none focus:border-[#16192E] uppercase tracking-wider"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-semibold text-[#64748B] block mb-1">Safety Officer ID</label>
                      <input
                        type="text"
                        value={officerId}
                        onChange={(e) => setOfficerId(e.target.value)}
                        placeholder="e.g. officer_delhi_01"
                        className="w-full bg-white border border-[#CBD5E1] rounded-lg px-2.5 py-1.5 text-xs text-[#16192E] focus:outline-none focus:border-[#16192E]"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-[10px] font-semibold text-[#64748B] block mb-1">Officer Observations &amp; Evidentiary Notes</label>
                    <textarea
                      rows={2}
                      value={officerNotes}
                      onChange={(e) => setOfficerNotes(e.target.value)}
                      placeholder="Add inspection notes (e.g. verified plate visually against raw video frame, resolved optical ambiguity between 8 and B...)"
                      className="w-full bg-white border border-[#CBD5E1] rounded-lg p-2 text-xs text-[#16192E] placeholder-[#94A3B8] focus:outline-none focus:border-[#16192E]"
                    />
                  </div>
                </div>

                {/* Verification Actions */}
                <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
                  <button
                    onClick={() => handleVerify("REJECT")}
                    disabled={isSubmitting}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-[#CBD5E1] hover:bg-[#F8FAFC] text-[#64748B] hover:text-[#16192E] rounded-xl text-xs font-semibold shadow-2xs transition-all disabled:opacity-50"
                  >
                    <XCircle className="w-4 h-4 text-rose-600" />
                    <span>Mark Unreadable</span>
                  </button>

                  <button
                    onClick={() => handleVerify(editedPlate !== selectedRecord.registration_number ? "EDIT" : "APPROVE")}
                    disabled={isSubmitting}
                    className="flex items-center gap-1.5 px-4 py-1.5 bg-[#C85A17] hover:bg-[#B34F14] text-white rounded-xl text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Verify &amp; Approve Plate</span>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center bg-white border border-[#E2E8F0] rounded-2xl shadow-sm">
              <p className="text-xs text-[#64748B]">Select an ANPR record from the list to inspect</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ANPR;
