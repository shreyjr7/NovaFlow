/**
 * NovaFlow Bus & Edge Node Service (Phase 8)
 * ==========================================
 * Client service for interacting with connected transit fleet edge nodes,
 * kinematics, camera health, and model inference states.
 */

export interface BusNode {
  bus_id: string;
  route_id: string;
  name: string;
  model?: string;
  latitude: number;
  longitude: number;
  speed: number;
  heading: number;
  timestamp: string;
  camera_status: "ACTIVE" | "STREAMING" | "DEGRADED" | "OFFLINE" | string;
  AI_status: "INFERENCING" | "ONLINE" | "STANDBY" | "OFFLINE" | string;
  connection_status: "CONNECTED" | "DEGRADED" | "DISCONNECTED" | string;
  status?: string;
  current_lat?: number;
  current_lon?: number;
  speed_kmh?: number;
  bearing_deg?: number;
}

export interface BusDetectionItem {
  id: string;
  scan_id?: string;
  bus_id: string;
  type: string;
  confidence: number;
  severity: string;
  latitude: number;
  longitude: number;
  timestamp: string;
  evidence_path?: string;
  annotated_evidence_path?: string;
  thumbnail_path?: string;
  ticket_id?: string;
  status: string;
  condition_type?: "DIRECT" | "POTENTIAL";
  is_multimodal_verified?: boolean;
}

export interface BusDetailNode extends BusNode {
  latest_detections: BusDetectionItem[];
  recent_hazards: BusDetectionItem[];
  total_detections_count: number;
}

export interface BusTelemetryPayload {
  bus_id: string;
  route_id?: string;
  latitude: number;
  longitude: number;
  speed?: number;
  heading?: number;
  camera_status?: string;
  AI_status?: string;
  connection_status?: string;
  timestamp?: string;
}

export async function fetchAllBuses(routeId?: string): Promise<BusNode[]> {
  try {
    const url = routeId ? `/api/v1/buses?route_id=${encodeURIComponent(routeId)}` : "/api/v1/buses";
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (err) {
    console.warn("Error fetching connected buses:", err);
    return [];
  }
}

export async function fetchBusDetail(busId: string): Promise<BusDetailNode | null> {
  try {
    const res = await fetch(`/api/v1/buses/${encodeURIComponent(busId)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`Error fetching bus detail for ${busId}:`, err);
    return null;
  }
}

export async function fetchBusDetections(busId: string, limit = 50): Promise<BusDetectionItem[]> {
  try {
    const res = await fetch(`/api/v1/buses/${encodeURIComponent(busId)}/detections?limit=${limit}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (err) {
    console.warn(`Error fetching bus detections for ${busId}:`, err);
    return [];
  }
}

export async function sendBusTelemetry(payload: BusTelemetryPayload): Promise<boolean> {
  try {
    const res = await fetch("/api/v1/buses/telemetry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return res.ok;
  } catch (err) {
    console.warn("Error transmitting bus telemetry:", err);
    return false;
  }
}
