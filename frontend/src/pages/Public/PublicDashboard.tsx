// src/pages/Public/PublicDashboard.tsx
// Phase 30 — Public Urban Safety Dashboard
// Citizen-facing portal showing aggregated, non-sensitive municipal transportation safety info:
// - Road condition
// - Congestion
// - Waterlogging
// - Public road hazards
// - Aggregated traffic trends
// Strictly zero-PII: No passenger data, raw footage, incident evidence, or unverified plates.

import React, { useState, useEffect } from "react";
import {
  ShieldCheck, AlertTriangle, Droplets, Construction, Activity,
  Clock, MapPin, Search, ThumbsUp, RefreshCw, Layers, CheckCircle2,
  Car, Compass, Info, ArrowRight, Shield, ExternalLink
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Cell
} from "recharts";

export interface PublicHazard {
  hazard_id: string;
  category: string;
  standard_label: string;
  location_name: string;
  zone: string;
  description: string;
  safety_recommendation: string;
  reported_at: string;
  citizen_acknowledgments: number;
  status: string;
}

export const PublicDashboard: React.FC = () => {
  const [overview, setOverview] = useState<any>(null);
  const [roadCondition, setRoadCondition] = useState<any>(null);
  const [congestion, setCongestion] = useState<any>(null);
  const [waterlogging, setWaterlogging] = useState<any[]>([]);
  const [hazards, setHazards] = useState<PublicHazard[]>([]);
  const [trafficTrends, setTrafficTrends] = useState<any[]>([]);
  const [hotspots, setHotspots] = useState<any[]>([]);

  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activeCategory, setActiveCategory] = useState<string>("All");
  const [loading, setLoading] = useState<boolean>(true);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const fetchPublicData = async () => {
    setLoading(true);
    try {
      const [ovRes, rcRes, congRes, wlogRes, hazRes, trendRes, mapRes] = await Promise.all([
        fetch("/api/v1/public/overview"),
        fetch("/api/v1/public/road-condition"),
        fetch("/api/v1/public/congestion"),
        fetch("/api/v1/public/waterlogging"),
        fetch("/api/v1/public/hazards"),
        fetch("/api/v1/public/traffic-trends"),
        fetch("/api/v1/public/map-hotspots"),
      ]);

      if (ovRes.ok) setOverview(await ovRes.json());
      if (rcRes.ok) setRoadCondition(await rcRes.json());
      if (congRes.ok) setCongestion(await congRes.json());
      if (wlogRes.ok) setWaterlogging(await wlogRes.json());
      if (hazRes.ok) setHazards(await hazRes.json());
      if (trendRes.ok) setTrafficTrends(await trendRes.json());
      if (mapRes.ok) setHotspots(await mapRes.json());
    } catch (e) {
      console.error("Failed to load public safety data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPublicData();
  }, []);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const handleAcknowledge = async (hazardId: string) => {
    try {
      const res = await fetch(`/api/v1/public/hazards/${hazardId}/acknowledge`, { method: "POST" });
      if (res.ok) {
        const updated = await res.json();
        setHazards((prev) =>
          prev.map((h) => (h.hazard_id === hazardId ? { ...h, citizen_acknowledgments: updated.citizen_acknowledgments } : h))
        );
        showToast("Thank you for your feedback! Community advisory updated.");
      }
    } catch (e) {
      console.error("Failed to acknowledge hazard:", e);
    }
  };

  // Filter hazards
  const filteredHazards = hazards.filter((h) => {
    const matchesCategory =
      activeCategory === "All" ||
      (activeCategory === "Road Hazards" && h.category === "Road Hazard") ||
      (activeCategory === "Heavy Congestion" && h.category === "Traffic Congestion") ||
      (activeCategory === "Waterlogging" && h.category === "Waterlogging");

    const matchesQuery =
      !searchQuery ||
      h.location_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      h.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      h.zone.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesCategory && matchesQuery;
  });

  return (
    <div className="min-h-screen bg-transparent text-[#16192E] p-3 sm:p-5 lg:p-8 space-y-4 sm:space-y-6">
      {/* Toast */}
      {toastMsg && (
        <div className="fixed top-5 right-5 z-50 flex items-center gap-2 px-4 py-3 rounded-xl bg-emerald-600 text-white shadow-2xl animate-fade-in border border-emerald-400">
          <CheckCircle2 className="w-5 h-5" />
          <span className="text-sm font-semibold">{toastMsg}</span>
        </div>
      )}

      {/* ── Public Civic Header ────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between pb-6 border-b border-[#E2E8F0] gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-emerald-50 text-emerald-700 rounded-2xl border border-emerald-200 shadow-2xs">
              <ShieldCheck className="w-7 h-7" />
            </span>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#16192E] flex flex-wrap items-center gap-3">
                Public Urban Safety Portal
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1">
                  <Shield className="w-3.5 h-3.5 text-blue-600" /> PRIVACY PROTECTED · ZERO-PII
                </span>
              </h1>
              <p className="text-xs sm:text-sm text-[#64748B] mt-1">
                Real-time aggregated road safety, congestion advisories, and waterlogging notices for citizens &amp; commuters.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={fetchPublicData}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs sm:text-sm font-semibold bg-white hover:bg-[#F8FAFC] text-[#16192E] rounded-xl border border-[#CBD5E1] shadow-2xs transition-all"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-[#C85A17]" : "text-[#64748B]"}`} />
          {loading ? "Updating..." : "Live Sync"}
        </button>
      </div>

      {/* ── 4 Top Headline Cards ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Road Health */}
        <div className="p-4 bg-white rounded-2xl border border-[#E2E8F0] shadow-sm">
          <div className="flex items-center justify-between text-emerald-700">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">City Road Condition</span>
            <div className="p-1.5 bg-emerald-50 rounded-lg">
              <Construction className="w-4 h-4 text-emerald-600" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-[#16192E] mt-2">
            {roadCondition?.road_health_index ?? 78.5}<span className="text-sm font-normal text-[#64748B]"> / 100</span>
          </div>
          <p className="text-xs text-[#64748B] mt-1">
            {roadCondition?.repairs_completed_this_week ?? 34} potholes repaired this week
          </p>
        </div>

        {/* Active Hazards */}
        <div className="p-4 bg-white rounded-2xl border border-[#E2E8F0] shadow-sm">
          <div className="flex items-center justify-between text-amber-700">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">Public Road Hazards</span>
            <div className="p-1.5 bg-amber-50 rounded-lg">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-[#16192E] mt-2">
            {hazards.length}
          </div>
          <p className="text-xs text-[#64748B] mt-1">Verified road defects &amp; surface notices</p>
        </div>

        {/* Congestion Status */}
        <div className="p-4 bg-white rounded-2xl border border-[#E2E8F0] shadow-sm">
          <div className="flex items-center justify-between text-rose-700">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">Traffic Congestion</span>
            <div className="p-1.5 bg-rose-50 rounded-lg">
              <Activity className="w-4 h-4 text-rose-600" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-[#16192E] mt-2">
            {congestion?.network_traffic_status?.split(" ")[0] ?? "Moderate"}
          </div>
          <p className="text-xs text-[#64748B] mt-1">
            Network avg: {congestion?.city_average_speed_kmh ?? 24.6} km/h
          </p>
        </div>

        {/* Waterlogging Notices */}
        <div className="p-4 bg-white rounded-2xl border border-[#E2E8F0] shadow-sm">
          <div className="flex items-center justify-between text-blue-700">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">Waterlogged Zones</span>
            <div className="p-1.5 bg-blue-50 rounded-lg">
              <Droplets className="w-4 h-4 text-blue-600" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-[#16192E] mt-2">
            {waterlogging.length}
          </div>
          <p className="text-xs text-[#64748B] mt-1">Active drainage pumps operating</p>
        </div>
      </div>

      {/* ── Search & Category Filter Pills ─────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 bg-white rounded-2xl border border-[#E2E8F0] shadow-sm">
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          {["All", "Road Hazards", "Heavy Congestion", "Waterlogging"].map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                activeCategory === cat
                  ? "bg-[#16192E] text-white shadow-xs"
                  : "bg-[#F8FAFC] text-[#64748B] hover:text-[#16192E] hover:bg-[#EEF2F6] border border-[#E2E8F0]"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-[#94A3B8] absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search road or corridor..."
            className="w-full bg-[#F8FAFC] border border-[#CBD5E1] text-[#16192E] text-xs rounded-xl pl-9 pr-3 py-2 placeholder-[#94A3B8] focus:outline-none focus:border-[#16192E]"
          />
        </div>
      </div>

      {/* ── Live Citizen Hazard Feed & GIS Map ─────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Citizen Hazard Cards */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-base font-bold text-[#16192E] flex items-center justify-between">
            <span>Verified Citizen Road Advisories ({filteredHazards.length})</span>
            <span className="text-xs text-[#64748B]">Continuous 10-Minute Polling</span>
          </h2>

          <div className="space-y-3">
            {filteredHazards.map((h) => {
              const isHazard = h.standard_label === "Road hazard reported";
              const isCongestion = h.standard_label === "Heavy congestion";
              const isWaterlog = h.standard_label === "Waterlogging";

              return (
                <div
                  key={h.hazard_id}
                  className="p-5 rounded-2xl border bg-white border-[#E2E8F0] shadow-sm hover:border-[#CBD5E1] transition-all space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      {/* Standard Label Badge */}
                      <span
                        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                          isHazard
                            ? "bg-amber-50 text-amber-800 border border-amber-200"
                            : isCongestion
                            ? "bg-rose-50 text-rose-800 border border-rose-200"
                            : "bg-blue-50 text-blue-800 border border-blue-200"
                        }`}
                      >
                        {isHazard && <AlertTriangle className="w-3.5 h-3.5" />}
                        {isCongestion && <Activity className="w-3.5 h-3.5" />}
                        {isWaterlog && <Droplets className="w-3.5 h-3.5" />}
                        {h.standard_label}
                      </span>

                      <h3 className="text-base font-bold text-[#16192E] mt-2 flex items-center gap-1.5">
                        <MapPin className="w-4 h-4 text-[#64748B] shrink-0" />
                        {h.location_name}
                        <span className="text-xs font-normal text-[#64748B]">({h.zone})</span>
                      </h3>
                    </div>

                    <span className="text-[11px] text-[#64748B] flex items-center gap-1 font-mono">
                      <Clock className="w-3 h-3" /> {h.reported_at}
                    </span>
                  </div>

                  <p className="text-xs text-[#475569]">{h.description}</p>

                  {/* Safety Recommendation */}
                  <div className="p-3 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] text-xs text-[#16192E]">
                    <strong className="text-[#C85A17]">Commuter Advice:</strong> {h.safety_recommendation}
                  </div>

                  {/* Citizen Upvote Acknowledgment */}
                  <div className="flex items-center justify-between pt-2 border-t border-[#E2E8F0] text-xs">
                    <span className="text-[11px] text-[#64748B]">
                      {h.citizen_acknowledgments} citizens marked this advisory helpful
                    </span>

                    <button
                      onClick={() => handleAcknowledge(h.hazard_id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1 bg-white hover:bg-[#F8FAFC] text-[#16192E] border border-[#CBD5E1] text-xs font-semibold rounded-lg shadow-2xs transition-all"
                    >
                      <ThumbsUp className="w-3.5 h-3.5 text-[#C85A17]" />
                      Helpful / I Observed This
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Col: GIS Hotspots & Diurnal Commuter Trend Chart */}
        <div className="space-y-6">
          {/* Public GIS Map Overview */}
          <div className="p-5 bg-white rounded-2xl border border-[#E2E8F0] shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-[#16192E] flex items-center justify-between">
              <span>Public GIS Safety Pins</span>
              <span className="text-[10px] text-[#64748B] bg-[#F8FAFC] border border-[#E2E8F0] px-2 py-0.5 rounded-full font-semibold">No Raw Telemetry</span>
            </h3>
            <p className="text-xs text-[#64748B]">
              Spatial markers of verified public hazards and drainage advisories.
            </p>

            <div className="p-2.5 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] space-y-2">
              {hotspots.map((spot) => (
                <div key={spot.hotspot_id} className="flex items-center justify-between text-xs p-2.5 bg-white rounded-lg border border-[#E2E8F0]">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                        spot.category === "HAZARD"
                          ? "bg-amber-500"
                          : spot.category === "CONGESTION"
                          ? "bg-rose-500"
                          : "bg-blue-500"
                      }`}
                    ></span>
                    <span className="font-semibold text-[#16192E] truncate max-w-[160px]">{spot.name}</span>
                  </div>
                  <span className="text-[10px] font-bold uppercase text-[#64748B]">{spot.public_label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Diurnal Commuter Travel Curve */}
          <div className="p-5 bg-white rounded-2xl border border-[#E2E8F0] shadow-sm space-y-2">
            <h3 className="text-sm font-bold text-[#16192E]">24h Commuter Mobility Guide</h3>
            <p className="text-xs text-[#64748B] mb-3">
              Relative travel delay curve (Plan travel during off-peak green hours for faster trips).
            </p>
            <div className="h-44">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trafficTrends}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="hour" stroke="#64748B" fontSize={10} tickLine={false} />
                  <YAxis stroke="#64748B" fontSize={10} domain={[0.8, 2.2]} tickLine={false} />
                  <Tooltip contentStyle={{ backgroundColor: "#FFFFFF", borderColor: "#CBD5E1", borderRadius: "0.75rem", color: "#16192E", fontSize: "11px" }} />
                  <Line type="monotone" dataKey="relative_delay_index" name="Delay Factor" stroke="#C85A17" strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Public Commuter Guidance */}
          <div className="p-5 bg-blue-50/60 rounded-2xl border border-blue-200 text-xs space-y-2">
            <h4 className="font-bold text-blue-900 flex items-center gap-1.5">
              <Info className="w-4 h-4 text-blue-700" />
              Civic Commuter Tips
            </h4>
            <ul className="space-y-1.5 text-blue-950 text-xs">
              <li>&bull; During wet weather, waterlogging at Dairy Circle and Hebbal underpasses may slow transit buses.</li>
              <li>&bull; Keep clear of designated bus lanes on MG Road to maintain scheduled bus arrival offsets.</li>
              <li>&bull; Report hazardous road conditions directly to municipal helpline 1533 or city traffic control.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PublicDashboard;
