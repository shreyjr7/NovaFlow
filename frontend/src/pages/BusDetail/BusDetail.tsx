import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Bus, MapPin, Gauge, Camera, Cpu, Navigation, Battery } from 'lucide-react';

export default function BusDetail() {
  const { busId } = useParams();
  const [bus, setBus] = useState<any>(null);

  useEffect(() => {
    fetch('/api/v1/demo/buses')
      .then(res => res.json())
      .then(data => {
        const found = data.find((b: any) => b.bus_id === busId);
        setBus(found);
      })
      .catch(() => {
        // Mock fallback
        setBus({
          bus_id: busId,
          name: `Mock ${busId}`,
          model: 'Electric City Bus',
          propulsion: 'Battery Electric',
          route_name: 'Downtown Loop',
          speed_kmh: 42,
          lat: 40.7128,
          lon: -74.0060,
          bearing: 180,
          camera_status: 'ONLINE',
          edge_device: 'Active',
          battery_level: 85
        });
      });
  }, [busId]);

  if (!bus) return <div className="p-8 text-white">Loading...</div>;

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto">
        <Link to="/fleet" className="inline-flex items-center text-indigo-400 hover:text-indigo-300 mb-6">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Fleet
        </Link>
        
        <div className="flex items-center gap-4 mb-8">
          <div className="p-3 bg-indigo-500/20 rounded-xl border border-indigo-500/30">
            <Bus className="w-8 h-8 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">{bus.name}</h1>
            <p className="text-gray-400">{bus.model} • {bus.propulsion}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-gray-900 border border-gray-800 p-4 rounded-xl">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <Navigation className="w-4 h-4" /> Route
            </div>
            <div className="text-xl font-semibold">{bus.route_name || bus.route_id}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 p-4 rounded-xl">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <Gauge className="w-4 h-4" /> Speed
            </div>
            <div className="text-xl font-semibold">{bus.speed_kmh} km/h</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 p-4 rounded-xl">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <MapPin className="w-4 h-4" /> Location
            </div>
            <div className="text-sm font-semibold truncate">{bus.lat.toFixed(4)}, {bus.lon.toFixed(4)}</div>
            <div className="text-xs text-gray-500 mt-1">Bearing: {bus.bearing}°</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 p-4 rounded-xl">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <Battery className="w-4 h-4" /> Battery
            </div>
            <div className="text-xl font-semibold">{bus.battery_level || 100}%</div>
          </div>
        </div>

        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <Camera className="w-6 h-6" /> Camera Feeds
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
          {['FRONT', 'REAR', 'LEFT', 'RIGHT'].map(pos => (
            <div key={pos} className="aspect-video bg-gray-900 border border-gray-800 rounded-xl flex items-center justify-center relative overflow-hidden group">
              <div className="absolute top-2 left-2 bg-black/60 px-2 py-1 rounded text-xs font-mono z-10 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                {pos} CAM
              </div>
              <Camera className="w-8 h-8 text-gray-700 group-hover:scale-110 transition-transform" />
            </div>
          ))}
        </div>

        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <Cpu className="w-6 h-6" /> Edge Device Telemetry
        </h2>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4 border-b border-gray-800 pb-4">
            <div className="font-semibold">NVIDIA Jetson Orin Nano</div>
            <div className="text-emerald-400 text-sm flex items-center gap-1">
               <div className="w-2 h-2 rounded-full bg-emerald-400"></div> Online
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <div className="text-gray-400">CPU Usage</div>
              <div className="font-mono">42%</div>
            </div>
            <div>
              <div className="text-gray-400">GPU Usage</div>
              <div className="font-mono">78%</div>
            </div>
            <div>
              <div className="text-gray-400">Memory</div>
              <div className="font-mono">5.2 / 8 GB</div>
            </div>
            <div>
              <div className="text-gray-400">Temperature</div>
              <div className="font-mono">48°C</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
