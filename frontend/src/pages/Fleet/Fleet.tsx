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
          bus_id: `bus-${i + 1}`,
          name: `Bus ${i + 1}`,
          route_id: `route-${Math.floor(Math.random() * 5) + 1}`,
          speed_kmh: Math.floor(Math.random() * 60) + 10,
          status: i % 5 === 0 ? 'MAINTENANCE' : 'IN_SERVICE',
          lat: 40.7128 + (Math.random() - 0.5) * 0.1,
          lon: -74.0060 + (Math.random() - 0.5) * 0.1,
          camera_status: 'ONLINE',
          edge_device: 'Active'
        }));
        setBuses(mockBuses);
      });
  }, []);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto">
        <Link to="/" className="inline-flex items-center text-indigo-400 hover:text-indigo-300 mb-6">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Home
        </Link>
        <h1 className="text-3xl font-bold mb-8">🚌 Fleet Command — {buses.length} Connected Buses</h1>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {buses.map(bus => (
            <Link key={bus.bus_id} to={`/fleet/${bus.bus_id}`} className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-indigo-500 transition-colors block">
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-2">
                  <Bus className="w-5 h-5 text-indigo-400" />
                  <h3 className="font-semibold text-lg">{bus.name}</h3>
                </div>
                {bus.status === 'IN_SERVICE' ? (
                  <span className="bg-emerald-500/20 text-emerald-400 text-xs px-2 py-1 rounded-full border border-emerald-500/30">
                    IN_SERVICE
                  </span>
                ) : (
                  <span className="bg-amber-500/20 text-amber-400 text-xs px-2 py-1 rounded-full border border-amber-500/30">
                    {bus.status}
                  </span>
                )}
              </div>
              
              <div className="space-y-2 text-sm text-gray-400">
                <div className="flex items-center gap-2">
                  <Radio className="w-4 h-4" /> Route: {bus.route_id}
                </div>
                <div className="flex items-center gap-2">
                  <Gauge className="w-4 h-4" /> Speed: {bus.speed_kmh} km/h
                </div>
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4" /> GPS: {bus.lat.toFixed(4)}, {bus.lon.toFixed(4)}
                </div>
                <div className="flex items-center gap-2">
                  <Camera className="w-4 h-4" /> Cameras: {bus.camera_status}
                </div>
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4" /> Edge: {bus.edge_device}
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
