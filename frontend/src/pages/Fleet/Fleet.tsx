// src/pages/Fleet/Fleet.tsx
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bus, MapPin, Gauge, Camera, Cpu, ArrowLeft, Radio } from 'lucide-react';

export default function Fleet() {
  const [buses, setBuses] = useState<any[]>([]);

  useEffect(() => {
    fetch('/api/v1/demo/buses')
      .then(res => res.json())
      .then(data => setBuses(data))
      .catch(() => {
        // Mock fallback
        const mockBuses = Array.from({ length: 20 }, (_, i) => ({
          bus_id: `BUS_${String(i + 1).padStart(3, '0')}`,
          name: `BUS_${String(i + 1).padStart(3, '0')} (Tata Ultra EV)`,
          route_id: `ROUTE_0${(i % 5) + 1}`,
          speed_kmh: Math.floor(Math.random() * 40) + 18,
          status: i % 7 === 0 ? 'MAINTENANCE' : 'IN_SERVICE',
          lat: 28.6139 + (Math.random() - 0.5) * 0.08,
          lon: 77.2090 + (Math.random() - 0.5) * 0.08,
          camera_status: 'HEALTHY',
          edge_device: 'NVIDIA Jetson AGX Orin 64GB'
        }));
        setBuses(mockBuses);
      });
  }, []);

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-[#16192E]">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <Link to="/" className="inline-flex items-center text-xs font-semibold text-[#64748B] hover:text-[#16192E] mb-2 transition">
            <ArrowLeft className="w-3.5 h-3.5 mr-1" /> Back to Dashboard
          </Link>
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#C85A17] mb-1">
            MUNICIPAL TRANSIT GRID ── ACTIVE SENSOR FLEET
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-[#16192E] tracking-tight flex items-center gap-2">
            <span>🚌 Fleet Command</span>
            <span className="text-slate-400">──</span>
            <span>{buses.length || 144} Connected Buses</span>
          </h1>
          <p className="text-xs sm:text-sm text-[#64748B] mt-1">
            Real-time multi-bus kinematic telemetry, edge AI inference status, and camera health monitoring.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold px-3 py-1 rounded-full flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>98.2% Telemetry Online</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {buses.map(bus => (
          <Link
            key={bus.bus_id}
            to={`/fleet/${bus.bus_id}`}
            className="bg-white border border-[#E2E8F0] hover:border-[#CBD5E1] shadow-[0_1px_3px_rgba(0,0,0,0.05)] rounded-xl p-4 transition-all block group hover:shadow-md"
          >
            <div className="flex justify-between items-start mb-3">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-[#F1F5F9] text-[#16192E] flex items-center justify-center font-bold text-xs shrink-0 group-hover:bg-[#C85A17] group-hover:text-white transition">
                  <Bus className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <h3 className="font-bold text-sm text-[#16192E] truncate group-hover:text-[#C85A17] transition">{bus.name}</h3>
                  <div className="text-[10px] text-[#64748B] font-mono">{bus.bus_id}</div>
                </div>
              </div>
              {bus.status === 'IN_SERVICE' ? (
                <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0">
                  IN_SERVICE
                </span>
              ) : (
                <span className="bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0">
                  {bus.status}
                </span>
              )}
            </div>
            
            <div className="space-y-1.5 text-xs text-[#64748B] pt-2 border-t border-[#F1F5F9]">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-[#94A3B8]"><Radio className="w-3.5 h-3.5" /> Route</span>
                <span className="font-semibold text-[#16192E]">{bus.route_id}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-[#94A3B8]"><Gauge className="w-3.5 h-3.5" /> Speed</span>
                <span className="font-mono font-semibold text-[#16192E]">{bus.speed_kmh} km/h</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-[#94A3B8]"><MapPin className="w-3.5 h-3.5" /> GPS</span>
                <span className="font-mono text-[#64748B] text-[11px]">{Number(bus.lat).toFixed(4)}, {Number(bus.lon).toFixed(4)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-[#94A3B8]"><Camera className="w-3.5 h-3.5" /> Cameras</span>
                <span className="text-emerald-700 font-semibold text-[11px]">{bus.camera_status}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-[#94A3B8]"><Cpu className="w-3.5 h-3.5" /> Edge</span>
                <span className="text-[#16192E] text-[10px] font-medium truncate max-w-[130px]">{bus.edge_device}</span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
