// src/components/LiveGisMap.tsx
import React, { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { 
  Compass, Layers, RefreshCw, Key, Bus, AlertTriangle, 
  Droplet, ShieldAlert, CheckCircle2, Sliders, ExternalLink, MapPin, Globe, Check
} from "lucide-react";
import nationwideData from "../data/nationwide_gis_data.json";

export interface BusItem {
  bus_id: string;
  route_id: string;
  name: string;
  lat: number;
  lon: number;
  bearing_deg: number;
  speed_kmh: number;
  status: string;
  passenger_occupancy_pct?: number;
}

export interface GisFeature {
  type: string;
  geometry: {
    type: string;
    coordinates: [number, number] | [number, number][];
  };
  properties: {
    event_id?: string;
    event_type?: string;
    layer?: string;
    confidence?: number;
    severity?: string;
    status?: string;
    address?: string;
    road_segment?: string;
    bus_id?: string;
    timestamp?: string;
    name?: string;
    color?: string;
    details?: Record<string, any>;
  };
}

export const CITIES: Record<string, { name: string; lat: number; lon: number; zoom: number }> = {
  DELHI: { name: "New Delhi (NCT of Delhi)", lat: 28.6139, lon: 77.2090, zoom: 13 },
  MUMBAI: { name: "Mumbai (Maharashtra)", lat: 19.1136, lon: 72.8697, zoom: 13 },
  BANGALORE: { name: "Bengaluru (Karnataka)", lat: 12.9716, lon: 77.5946, zoom: 13 },
  ...((nationwideData as any).CITIES || {}),
};

// Pure Google Maps and clean public tiles with ZERO "API KEY REQUIRED" watermarks
const BASEMAP_PRESETS = [
  { 
    id: "google_streets", 
    name: "Google Maps (Roadmap)", 
    url: "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", 
    attribution: "&copy; Google Maps" 
  },
  { 
    id: "google_hybrid", 
    name: "Google Maps (Satellite + Streets)", 
    url: "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", 
    attribution: "&copy; Google Maps Imagery" 
  },
  { 
    id: "google_satellite", 
    name: "Google Maps (Satellite Only)", 
    url: "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", 
    attribution: "&copy; Google Maps Satellite" 
  },
  { 
    id: "google_terrain", 
    name: "Google Maps (Terrain)", 
    url: "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}", 
    attribution: "&copy; Google Maps Terrain" 
  },
  { 
    id: "esri_dark", 
    name: "Clean Dark Canvas (No Watermark)", 
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}", 
    attribution: "&copy; Esri &copy; OpenStreetMap" 
  },
  { 
    id: "osm", 
    name: "OpenStreetMap Standard", 
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", 
    attribution: "&copy; OpenStreetMap contributors" 
  },
];

// Fallback seed buses from nationwide GIS data for immediate rendering across all Indian states
const FALLBACK_BUSES: BusItem[] = ((nationwideData as any).FALLBACK_BUSES as BusItem[]) || [];

// Fallback seed hazards from nationwide GIS data across all Indian states
const FALLBACK_HAZARDS = ((nationwideData as any).FALLBACK_HAZARDS as any[]) || [];

export interface LiveGisMapProps {
  height?: string;
  initialCity?: keyof typeof CITIES;
  showControls?: boolean;
  flyToLocation?: { lat: number; lon: number; zoom?: number; label?: string } | null;
  onSelectEvent?: (event: any) => void;
  onSelectBus?: (bus: BusItem) => void;
}

export const LiveGisMap: React.FC<LiveGisMapProps> = ({ 
  height = "520px", 
  initialCity = "DELHI",
  showControls = true,
  flyToLocation,
  onSelectEvent,
  onSelectBus,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);

  // Layers
  const busLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const defectLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const routesLayerGroupRef = useRef<L.LayerGroup | null>(null);

  // Initial key from ENV or localStorage
  const envKey = (import.meta as any).env?.VITE_GOOGLE_MAPS_API_KEY || "";
  const storedKey = localStorage.getItem("novaflow_google_maps_key") || "";
  const initialKey = storedKey || envKey;

  // State: Default directly to Google Maps (Roadmap) - Works with 0 watermarks!
  const [selectedCity, setSelectedCity] = useState<keyof typeof CITIES>(initialCity);
  const [activeBasemap, setActiveBasemap] = useState<string>("google_streets");
  const [googleApiKey, setGoogleApiKey] = useState<string>(initialKey);
  const [showKeyModal, setShowKeyModal] = useState<boolean>(false);
  const [tempApiKey, setTempApiKey] = useState<string>(initialKey);
  
  const [layerVisibility, setLayerVisibility] = useState({
    buses: true,
    routes: true,
    potholes: true,
    congestion: true,
    incidents: true,
  });

  const [busesCount, setBusesCount] = useState<number>(FALLBACK_BUSES.length);
  const [eventsCount, setEventsCount] = useState<number>(FALLBACK_HAZARDS.length);
  const [isLive, setIsLive] = useState<boolean>(true);
  const [lastUpdated, setLastUpdated] = useState<string>("Live");

  // Save API Key
  const handleSaveApiKey = () => {
    const key = tempApiKey.trim();
    localStorage.setItem("novaflow_google_maps_key", key);
    setGoogleApiKey(key);
    setShowKeyModal(false);
    if (key) {
      setActiveBasemap("google_streets");
    }
  };

  // Helper to build tile layer
  const createTileLayer = (presetId: string, apiKey: string): L.TileLayer => {
    const preset = BASEMAP_PRESETS.find(p => p.id === presetId) || BASEMAP_PRESETS[0];
    const tileUrl = (presetId.startsWith("google") && apiKey)
      ? `${preset.url}&key=${apiKey}`
      : preset.url;

    return L.tileLayer(tileUrl, {
      maxZoom: 20,
      attribution: preset.attribution,
    });
  };

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const city = CITIES[selectedCity];
    const map = L.map(mapContainerRef.current, {
      center: [city.lat, city.lon],
      zoom: city.zoom,
      zoomControl: true,
    });

    const tiles = createTileLayer(activeBasemap, googleApiKey).addTo(map);
    tileLayerRef.current = tiles;

    // Feature Layer Groups
    routesLayerGroupRef.current = L.layerGroup().addTo(map);
    defectLayerGroupRef.current = L.layerGroup().addTo(map);
    busLayerGroupRef.current = L.layerGroup().addTo(map);

    mapRef.current = map;

    // Immediately render fallbacks so map is never empty
    renderFallbackData();

    // Invalidate size when DOM resolves
    const timer1 = setTimeout(() => map.invalidateSize(), 150);
    const timer2 = setTimeout(() => map.invalidateSize(), 500);

    const onResize = () => {
      if (mapRef.current) mapRef.current.invalidateSize();
    };
    window.addEventListener("resize", onResize);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      window.removeEventListener("resize", onResize);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update map center when initialCity prop changes
  useEffect(() => {
    if (initialCity && CITIES[initialCity] && mapRef.current) {
      jumpToCity(initialCity);
    }
  }, [initialCity]);

  // Support dynamic fly-to location (State / Capital / District / Tehsil jump)
  useEffect(() => {
    if (flyToLocation && mapRef.current && flyToLocation.lat && flyToLocation.lon) {
      const targetZoom = flyToLocation.zoom || 13;
      mapRef.current.flyTo([flyToLocation.lat, flyToLocation.lon], targetZoom, {
        duration: 1.5,
        easeLinearity: 0.25,
      });

      // Show brief marker or popup if label provided
      if (flyToLocation.label) {
        const popup = L.popup({ closeButton: true, autoClose: true })
          .setLatLng([flyToLocation.lat, flyToLocation.lon])
          .setContent(`
            <div style="font-family: sans-serif; font-size: 12px; padding: 4px;">
              <strong style="color: #2563eb;">📍 ${flyToLocation.label}</strong>
              <div style="color: #64748b; font-size: 10px; margin-top: 2px;">Coordinated Municipal Transit Node</div>
            </div>
          `)
          .openOn(mapRef.current);
      }
    }
  }, [flyToLocation]);

  // Update Basemap when activeBasemap or googleApiKey changes
  useEffect(() => {
    if (!mapRef.current) return;

    if (tileLayerRef.current) {
      mapRef.current.removeLayer(tileLayerRef.current);
    }

    const newTiles = createTileLayer(activeBasemap, googleApiKey).addTo(mapRef.current);
    newTiles.bringToBack();
    tileLayerRef.current = newTiles;
  }, [activeBasemap, googleApiKey]);

  // Jump to city
  const jumpToCity = (cityKey: keyof typeof CITIES) => {
    setSelectedCity(cityKey);
    const city = CITIES[cityKey];
    if (mapRef.current) {
      mapRef.current.flyTo([city.lat, city.lon], city.zoom, { duration: 1.2 });
    }
  };

  // Render Fallback Data Immediately
  const renderFallbackData = () => {
    if (!busLayerGroupRef.current || !defectLayerGroupRef.current) return;

    // 1. Buses
    busLayerGroupRef.current.clearLayers();
    FALLBACK_BUSES.forEach((b) => {
      const busIcon = L.divIcon({
        className: "custom-bus-marker",
        html: `
          <div class="relative flex items-center justify-center cursor-pointer group">
            <div class="w-8 h-8 rounded-full bg-blue-600 border-2 border-white shadow-xl flex items-center justify-center text-white text-xs font-bold transform transition-transform group-hover:scale-125">
              🚌
            </div>
            <div class="absolute -bottom-4 bg-gray-950/90 text-blue-300 text-[9px] px-1 rounded border border-blue-500/40 whitespace-nowrap shadow font-mono">
              ${b.bus_id} • ${b.speed_kmh}km/h
            </div>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      const marker = L.marker([b.lat, b.lon], { icon: busIcon });
      marker.on("click", () => {
        if (onSelectBus) onSelectBus(b);
      });
      busLayerGroupRef.current?.addLayer(marker);
    });

    // 2. Defects
    defectLayerGroupRef.current.clearLayers();
    FALLBACK_HAZARDS.forEach((h) => {
      let iconHtml = "🕳️";
      let pinColor = "bg-amber-600 border-amber-300 text-white";
      if (h.event_type.includes("WATERLOG")) { iconHtml = "💧"; pinColor = "bg-cyan-600 border-cyan-300 text-white"; }
      else if (h.event_type.includes("DAMAGE")) { iconHtml = "🚧"; pinColor = "bg-orange-600 border-orange-300 text-white"; }
      else if (h.event_type.includes("CONGESTION")) { iconHtml = "🚗"; pinColor = "bg-yellow-600 border-yellow-300 text-white"; }
      else if (h.event_type.includes("INCIDENT")) { iconHtml = "🚨"; pinColor = "bg-red-600 border-red-300 text-white animate-pulse"; }

      const customIcon = L.divIcon({
        className: "custom-defect-marker",
        html: `<div class="w-6 h-6 rounded-full border-2 flex items-center justify-center text-[11px] shadow-lg cursor-pointer transform hover:scale-125 transition-transform ${pinColor}">${iconHtml}</div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      const marker = L.marker([h.lat, h.lon], { icon: customIcon });
      marker.on("click", () => {
        if (onSelectEvent) onSelectEvent(h);
      });
      defectLayerGroupRef.current?.addLayer(marker);
    });
  };

  // Fetch & Render Features (Defects, Incidents, Congestion, Routes)
  const fetchFeaturesAndRoutes = async () => {
    try {
      // 1. Routes
      const routesRes = await fetch("/api/v1/gis/routes");
      if (routesRes.ok && routesLayerGroupRef.current) {
        const routesData = await routesRes.json();
        routesLayerGroupRef.current.clearLayers();

        if (routesData.features && layerVisibility.routes) {
          routesData.features.forEach((feat: GisFeature) => {
            if (feat.geometry && feat.geometry.type === "LineString") {
              const coords = (feat.geometry.coordinates as [number, number][]).map(
                ([lon, lat]) => [lat, lon] as [number, number]
              );
              const color = feat.properties.color || "#6366f1";
              
              const polyline = L.polyline(coords, {
                color: color,
                weight: 5,
                opacity: 0.8,
                lineJoin: "round",
              });

              polyline.bindPopup(`
                <div class="text-xs p-1">
                  <div class="font-bold text-white flex items-center gap-1">
                    <span style="color: ${color}">●</span> ${feat.properties.name || feat.properties.route_id}
                  </div>
                  <div class="text-gray-400 mt-1">Monitored Public Transit Corridor</div>
                </div>
              `);

              if (routesLayerGroupRef.current) {
                routesLayerGroupRef.current.addLayer(polyline);
              }
            }
          });
        }
      }

      // 2. Events & Defects
      const featuresRes = await fetch("/api/v1/gis/features");
      if (featuresRes.ok && defectLayerGroupRef.current) {
        const data = await featuresRes.json();
        if (data.features && data.features.length > 0) {
          defectLayerGroupRef.current.clearLayers();
          setEventsCount(data.features.length);

          data.features.forEach((feat: GisFeature) => {
            if (!feat.geometry || feat.geometry.type !== "Point") return;
            const [lon, lat] = feat.geometry.coordinates as [number, number];
            const p = feat.properties;
            const evType = (p.event_type || "").toUpperCase();

            // Visibility filters
            if (evType.includes("POTHOLE") || evType.includes("DAMAGE") || evType.includes("WATERLOG")) {
              if (!layerVisibility.potholes) return;
            } else if (evType.includes("CONGESTION")) {
              if (!layerVisibility.congestion) return;
            } else if (evType.includes("INCIDENT")) {
              if (!layerVisibility.incidents) return;
            }

            let iconHtml = "🕳️";
            let pinColor = "bg-amber-600 border-amber-300 text-white";
            if (evType.includes("POTHOLE")) { iconHtml = "🕳️"; pinColor = "bg-amber-600 border-amber-300 text-white"; }
            else if (evType.includes("WATERLOG")) { iconHtml = "💧"; pinColor = "bg-cyan-600 border-cyan-300 text-white"; }
            else if (evType.includes("DAMAGE")) { iconHtml = "🚧"; pinColor = "bg-orange-600 border-orange-300 text-white"; }
            else if (evType.includes("CONGESTION")) { iconHtml = "🚗"; pinColor = "bg-yellow-600 border-yellow-300 text-white"; }
            else if (evType.includes("INCIDENT")) { iconHtml = "🚨"; pinColor = "bg-red-600 border-red-300 text-white animate-pulse"; }
            else if (evType.includes("PEDESTRIAN")) { iconHtml = "🚶"; pinColor = "bg-purple-600 border-purple-300 text-white"; }

            const customIcon = L.divIcon({
              className: "custom-defect-marker",
              html: `<div class="w-6 h-6 rounded-full border-2 flex items-center justify-center text-[11px] shadow-lg cursor-pointer transform hover:scale-125 transition-transform ${pinColor}">${iconHtml}</div>`,
              iconSize: [24, 24],
              iconAnchor: [12, 12],
            });

            const marker = L.marker([lat, lon], { icon: customIcon });

            marker.on("click", () => {
              if (onSelectEvent) onSelectEvent(p);
            });

            marker.bindPopup(`
              <div class="text-xs p-1 min-w-[210px]">
                <div class="flex items-center justify-between border-b border-gray-700 pb-1.5 mb-1.5">
                  <span class="font-bold text-amber-400">${p.event_type}</span>
                  <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${p.severity === 'HIGH' || p.severity === 'SEVERE' ? 'bg-red-900 text-red-200' : 'bg-yellow-900 text-yellow-200'}">${p.severity || 'ACTIVE'}</span>
                </div>
                <div class="text-gray-300 font-medium">${p.address || p.road_segment || 'Monitored Segment'}</div>
                <div class="grid grid-cols-2 gap-1 mt-2 text-[10px] text-gray-400">
                  <div>Bus: <span class="text-white">${p.bus_id || 'N/A'}</span></div>
                  <div>Conf: <span class="text-emerald-400 font-bold">${((p.confidence || 0.9) * 100).toFixed(0)}%</span></div>
                  <div>Status: <span class="text-white">${p.status || 'UNVERIFIED'}</span></div>
                  <div>GPS: <span class="text-white">${lat.toFixed(4)}, ${lon.toFixed(4)}</span></div>
                </div>
              </div>
            `);

            if (defectLayerGroupRef.current) {
              defectLayerGroupRef.current.addLayer(marker);
            }
          });
        }
      }
    } catch (err) {
      // Keep fallbacks active
    }
  };

  // Fetch & Update Live Buses (Every 2.5 seconds)
  const fetchLiveBuses = async () => {
    try {
      const res = await fetch("/api/v1/demo/buses");
      if (!res.ok || !busLayerGroupRef.current) return;
      const buses: BusItem[] = await res.json();
      if (!buses || buses.length === 0) return;
      
      setBusesCount(buses.length);
      busLayerGroupRef.current.clearLayers();

      if (layerVisibility.buses) {
        buses.forEach((b) => {
          const busIcon = L.divIcon({
            className: "custom-bus-marker",
            html: `
              <div class="relative flex items-center justify-center cursor-pointer group">
                <div class="w-8 h-8 rounded-full bg-blue-600 border-2 border-white shadow-xl flex items-center justify-center text-white text-xs font-bold transform transition-transform group-hover:scale-125">
                  🚌
                </div>
                <div class="absolute -bottom-4 bg-gray-950/90 text-blue-300 text-[9px] px-1 rounded border border-blue-500/40 whitespace-nowrap shadow font-mono">
                  ${b.bus_id} • ${b.speed_kmh}km/h
                </div>
              </div>
            `,
            iconSize: [32, 32],
            iconAnchor: [16, 16],
          });

          const marker = L.marker([b.lat, b.lon], { icon: busIcon });

          marker.on("click", () => {
            if (onSelectBus) onSelectBus(b);
          });

          marker.bindPopup(`
            <div class="text-xs p-1 min-w-[210px]">
              <div class="flex items-center justify-between border-b border-gray-700 pb-1 mb-1.5">
                <span class="font-bold text-blue-400">🚌 ${b.bus_id}</span>
                <span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-900/80 text-emerald-300 border border-emerald-500/30">${b.status}</span>
              </div>
              <div class="text-white font-medium">${b.name}</div>
              <div class="text-gray-400 text-[11px] mt-0.5">${b.route_id} Corridor</div>
              <div class="grid grid-cols-2 gap-1 mt-2 text-[10px] text-gray-300 bg-gray-800/60 p-1.5 rounded border border-gray-700/50">
                <div>Speed: <strong class="text-white">${b.speed_kmh} km/h</strong></div>
                <div>Bearing: <strong class="text-white">${b.bearing_deg}°</strong></div>
                <div>Occupancy: <strong class="text-white">${b.passenger_occupancy_pct || 65}%</strong></div>
                <div>Cameras: <strong class="text-emerald-400">4 Online</strong></div>
              </div>
            </div>
          `);

          if (busLayerGroupRef.current) {
            busLayerGroupRef.current.addLayer(marker);
          }
        });
      }

      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      // Keep fallbacks active
    }
  };

  // Initial load and periodic polling
  useEffect(() => {
    fetchFeaturesAndRoutes();
    fetchLiveBuses();

    const interval = setInterval(() => {
      if (isLive) {
        fetchLiveBuses();
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [isLive, layerVisibility]);

  return (
    <div 
      className="relative w-full h-full overflow-hidden border border-gray-800 bg-gray-950 shadow-2xl flex flex-col"
      style={{ height, minHeight: height === "100%" ? "100%" : height }}
    >
      {/* Top Floating Control Bar */}
      {showControls && (
        <div className="absolute top-3 left-3 right-3 z-[1000] flex flex-wrap items-center justify-between gap-2 pointer-events-none">
          {/* Left: City Selector & Status */}
          <div className="flex items-center gap-1.5 bg-gray-900/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-gray-700 shadow-xl pointer-events-auto">
            <span className="flex h-2 w-2 relative mr-1">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-xs font-bold text-gray-200">GIS Feed:</span>
            
            {(Object.keys(CITIES) as (keyof typeof CITIES)[]).map((cKey) => (
              <button
                key={cKey}
                onClick={() => jumpToCity(cKey)}
                className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-all ${
                  selectedCity === cKey 
                    ? "bg-blue-600 text-white shadow-md font-bold" 
                    : "text-gray-400 hover:text-white hover:bg-gray-800"
                }`}
              >
                {cKey === "DELHI" ? "Delhi" : cKey === "MUMBAI" ? "Mumbai" : "Bengaluru"}
              </button>
            ))}
          </div>

          {/* Right: Google Maps Basemap Switcher & Key Status */}
          <div className="flex items-center gap-2 bg-gray-900/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-gray-700 shadow-xl pointer-events-auto">
            {/* Basemap Dropdown - Clean Google Maps by default */}
            <select
              value={activeBasemap}
              onChange={(e) => setActiveBasemap(e.target.value)}
              className="text-xs bg-gray-800 text-gray-200 border border-gray-600 rounded-lg px-2.5 py-1 outline-none font-medium cursor-pointer"
            >
              {BASEMAP_PRESETS.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>

            {/* Google Maps API Key Setup Button */}
            <button
              onClick={() => setShowKeyModal(true)}
              className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg font-medium border transition-all bg-emerald-950/80 text-emerald-300 border-emerald-500/50 hover:bg-emerald-900"
              title="Google Maps API Key Configuration"
            >
              <Globe size={13} />
              <span>{googleApiKey ? "Google Maps Active" : "Google Key Ready"}</span>
            </button>

            {/* Refresh Toggle */}
            <button
              onClick={() => { fetchLiveBuses(); fetchFeaturesAndRoutes(); }}
              className="p-1 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
              title="Refresh Map Layers"
            >
              <RefreshCw size={14} className={isLive ? "animate-spin-slow" : ""} />
            </button>
          </div>
        </div>
      )}

      {/* Map Container Canvas */}
      <div 
        ref={mapContainerRef} 
        style={{ height: "100%", width: "100%", minHeight: height === "100%" ? "100%" : height }} 
        className="w-full h-full flex-1 z-0 bg-gray-950"
      />

      {/* Bottom Floating Stats & Layer Toggles Bar */}
      {showControls && (
        <div className="absolute bottom-3 left-3 right-3 z-[1000] flex flex-wrap items-center justify-between gap-2 pointer-events-none">
          {/* Telemetry pill */}
          <div className="bg-gray-900/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-gray-700 shadow-xl pointer-events-auto flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1.5 text-blue-400 font-semibold">
              <Bus size={14} />
              <span>{busesCount} Live Buses</span>
            </div>
            <span className="text-gray-600">|</span>
            <div className="flex items-center gap-1.5 text-amber-400 font-semibold">
              <AlertTriangle size={14} />
              <span>{eventsCount} Detected Hazards</span>
            </div>
            {lastUpdated && (
              <>
                <span className="text-gray-600">|</span>
                <span className="text-gray-400 text-[11px]">Sync: {lastUpdated}</span>
              </>
            )}
          </div>

          {/* Quick Layer Filter Toggles */}
          <div className="bg-gray-900/90 backdrop-blur-md px-2.5 py-1.5 rounded-xl border border-gray-700 shadow-xl pointer-events-auto flex items-center gap-1 text-xs">
            <button
              onClick={() => setLayerVisibility(v => ({ ...v, buses: !v.buses }))}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-all ${
                layerVisibility.buses ? "bg-blue-600/80 text-white border border-blue-400/50" : "text-gray-500 hover:text-gray-300"
              }`}
            >
              Buses
            </button>
            <button
              onClick={() => setLayerVisibility(v => ({ ...v, routes: !v.routes }))}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-all ${
                layerVisibility.routes ? "bg-indigo-600/80 text-white border border-indigo-400/50" : "text-gray-500 hover:text-gray-300"
              }`}
            >
              Routes
            </button>
            <button
              onClick={() => setLayerVisibility(v => ({ ...v, potholes: !v.potholes }))}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-all ${
                layerVisibility.potholes ? "bg-amber-600/80 text-white border border-amber-400/50" : "text-gray-500 hover:text-gray-300"
              }`}
            >
              Defects
            </button>
            <button
              onClick={() => setLayerVisibility(v => ({ ...v, congestion: !v.congestion }))}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-all ${
                layerVisibility.congestion ? "bg-yellow-600/80 text-white border border-yellow-400/50" : "text-gray-500 hover:text-gray-300"
              }`}
            >
              Traffic
            </button>
            <button
              onClick={() => setLayerVisibility(v => ({ ...v, incidents: !v.incidents }))}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-all ${
                layerVisibility.incidents ? "bg-red-600/80 text-white border border-red-400/50" : "text-gray-500 hover:text-gray-300"
              }`}
            >
              Incidents
            </button>
          </div>
        </div>
      )}

      {/* Google Maps API Key Modal */}
      {showKeyModal && (
        <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center gap-3 border-b border-gray-800 pb-3 mb-4">
              <div className="p-2.5 rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30">
                <Globe size={22} />
              </div>
              <div>
                <h4 className="text-base font-bold text-white">Google Maps API Connection</h4>
                <p className="text-xs text-gray-400">Enable Google Maps Roadmap, Satellite, and Hybrid Layers</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  Google Maps API Key
                </label>
                <input
                  type="text"
                  value={tempApiKey}
                  onChange={(e) => setTempApiKey(e.target.value)}
                  placeholder="Paste your Google Maps API Key (AIzaSy...)"
                  className="w-full px-3 py-2 text-sm bg-gray-950 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 font-mono"
                />
                <p className="text-[11px] text-gray-400 mt-1.5">
                  NovaFlow defaults directly to Google Maps layers without any watermark. If you have an official Google Cloud key, paste it here for full high-throughput quota.
                </p>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  onClick={() => {
                    localStorage.removeItem("novaflow_google_maps_key");
                    setGoogleApiKey("");
                    setTempApiKey("");
                    setActiveBasemap("google_streets");
                    setShowKeyModal(false);
                  }}
                  className="text-xs text-rose-400 hover:underline"
                >
                  Clear Key
                </button>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowKeyModal(false)}
                    className="text-xs px-3 py-1.5 rounded-lg border border-gray-700 text-gray-300 hover:bg-gray-800"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveApiKey}
                    className="text-xs px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 font-semibold text-white shadow-lg"
                  >
                    Save & Activate
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LiveGisMap;
