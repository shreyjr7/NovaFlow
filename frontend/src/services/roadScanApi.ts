// src/services/roadScanApi.ts
// Frontend Service Abstraction for NovaFlow AI Road Intelligence Pipeline
// Bharat Electronics Limited (BEL) • Smart Automation

export type DefectCategory =
  | "POTHOLE"
  | "DAMAGED_ROAD"
  | "ROAD_CRACK"
  | "WATERLOGGING"
  | "DEBRIS"
  | "ROAD_DEBRIS"
  | "MISSING_SIGN"
  | "TRAFFIC_SIGN"
  | "ROAD_DIVIDER"
  | "MISSING_DIVIDER"
  | "DAMAGED_ZEBRA"
  | "DAMAGED_ZEBRA_CROSSING"
  | "BUS"
  | "CAR"
  | "TRUCK"
  | "MOTORCYCLE"
  | "PEDESTRIAN"
  | string;

export type SeverityLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type JobStatus = "IDLE" | "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED" | "CANCELLED";

export interface ScanDetection {
  id: string;
  trackId: number;
  type: DefectCategory;
  label: string;
  confidence: number; // 0.0 to 1.0
  severity: SeverityLevel;
  timestamp: string;
  frameNumber: number;
  location: {
    lat: number;
    lon: number;
    accuracyM?: number;
    roadSegment?: string;
  };
  sourceBusId?: string;
  sourceRouteId?: string;
  boundingBox?: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  };
  evidenceImagePath?: string;      // Main evidence image
  originalImagePath?: string;      // Clean unannotated frame
  annotatedImagePath?: string;     // Frame with bounding box & tags
  thumbnailPath?: string;          // Cropped thumbnail
  storageProvider?: string;        // "supabase_storage" or "local_disk"
  status: "DETECTED" | "CONFIRMED" | "DISMISSED" | "TICKET_CREATED";
  associatedTicketId?: string;
  conditionType?: "DIRECT" | "POTENTIAL";
  isMultimodalVerified?: boolean;
  verificationNotes?: string;
  ticketId?: string;
  ticketStatus?: string;
  persistentHazardId?: string;
  independentBusesCount?: number;
  contributingBuses?: string | string[];
  persistenceBadge?: string;
  lastDetectedAt?: string;
  observationCount?: number;
}

export interface HazardObservation {
  id: string;
  hazard_id: string;
  detection_id?: string;
  bus_id: string;
  route_id?: string;
  road_segment?: string;
  model_confidence: number;
  severity: string;
  latitude: number;
  longitude: number;
  evidence_path?: string;
  thumbnail_path?: string;
  observed_at: string;
}

export interface PersistentHazard {
  id: string;
  hazard_code: string;
  hazard_type: string;
  severity: string;
  latitude: number;
  longitude: number;
  road_segment?: string;
  city?: string;
  initial_confidence: number;
  persistence_score: number;
  persistence_status: string; // e.g. "CONFIRMED BY 3 BUSES"
  total_observations: number;
  independent_buses_count: number;
  contributing_buses: string[];
  first_detected_at: string;
  last_detected_at: string;
  ticket_id?: string;
  status: string;
  observations?: HazardObservation[];
}

export interface DerivedIntelligence {
  traffic_congestion?: {
    level: "LOW" | "MEDIUM" | "HIGH";
    vehicle_count?: number;
    road_occupancy_pct?: number;
    occupancy_ratio?: number;
    avg_speed_kmh?: number | null;
    score?: number;
    recommendation?: string;
  };
  pedestrian_risk?: any;
  incidents?: any;
}

export interface VideoJobProgress {
  jobId: string;
  status: JobStatus;
  progressPct: number;
  framesProcessed: number;
  totalEstimatedFrames: number;
  detectionsCount: number;
  confirmedCount: number;
  summaryBySeverity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  summaryByType: Record<string, number>;
  videoMetadata?: {
    width: number;
    height: number;
    nativeFps: number;
    durationSec: number;
  };
  detections: ScanDetection[];
  derivedIntelligence?: DerivedIntelligence;
  ticketsSpawned?: any[];
  errorMessage?: string;
  startedAt?: string;
  completedAt?: string;
}

export interface ScanConfig {
  sampleFps: number; // 1, 2, or 5
  busId: string;
  routeId: string;
  confidenceThreshold: number; // e.g. 0.70
  city: string;
}

export interface LiveFramePayload {
  frameBase64: string;
  timestamp?: string;
  busId: string;
  routeId: string;
  gps: {
    lat: number;
    lon: number;
    speedKmh?: number | null;
    headingDeg?: number | null;
    accuracyM?: number | null;
  };
  confidenceThreshold?: number;
  persistDetections?: boolean;
}

export interface LiveFrameResponse {
  busId: string;
  routeId: string;
  timestamp: string;
  latencyMs: number;
  detectionsCount: number;
  detections: ScanDetection[];
  speedKmh?: number;
  headingDeg?: number;
  annotatedFrameB64?: string;
  derivedIntelligence?: DerivedIntelligence;
  ticketsSpawned?: any[];
  geminiVerificationEnabled?: boolean;
}

export interface LiveFrameBatchPayload {
  frames: { frameBase64: string; frameIdx?: number; timestamp?: string }[];
  busId: string;
  routeId: string;
  gps: {
    lat: number;
    lon: number;
    speedKmh?: number | null;
    headingDeg?: number | null;
    accuracyM?: number | null;
  };
  confidenceThreshold?: number;
  persistDetections?: boolean;
}

export interface LiveFrameBatchResponse {
  busId: string;
  routeId: string;
  framesProcessed: number;
  totalDetectionsCount: number;
  latencyMs: number;
  detections: ScanDetection[];
  derivedIntelligence?: DerivedIntelligence;
  ticketsSpawned?: any[];
  geminiVerificationEnabled?: boolean;
}

/**
 * Resolves the backend base URL dynamically:
 * 1. User runtime override saved in localStorage ("novaflow_backend_url")
 * 2. Vite environment variable (VITE_API_URL or VITE_BACKEND_URL)
 * 3. Default relative path (for local dev proxy or same-domain deployment)
 */
export function getBackendBaseUrl(): string {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("novaflow_backend_url");
    if (stored && stored.trim()) {
      const trimmed = stored.trim().replace(/\/+$/, "");
      // Discard invalid terminal commands stored by mistake
      if (trimmed.toLowerCase().includes("npx") || trimmed.toLowerCase().includes("localtunnel --port")) {
        localStorage.removeItem("novaflow_backend_url");
        return "";
      }
      return trimmed;
    }
  }
  const envUrl = (import.meta as any).env?.VITE_API_URL || (import.meta as any).env?.VITE_BACKEND_URL;
  if (envUrl && typeof envUrl === "string" && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, "");
  }
  return "";
}

export function setBackendBaseUrl(url: string): void {
  if (typeof window !== "undefined") {
    const trimmed = (url || "").trim().replace(/\/+$/, "");
    if (!trimmed || trimmed.toLowerCase().includes("npx") || trimmed.toLowerCase().includes("localtunnel --port")) {
      localStorage.removeItem("novaflow_backend_url");
    } else {
      const validUrl = trimmed.startsWith("http://") || trimmed.startsWith("https://") ? trimmed : `https://${trimmed}`;
      localStorage.setItem("novaflow_backend_url", validUrl);
    }
  }
}

export function getApiBaseUrl(): string {
  const base = getBackendBaseUrl();
  return base ? `${base}/api/v1` : "/api/v1";
}

export function resolveEvidenceUrl(url?: string): string {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("data:")) {
    return url;
  }
  const base = getBackendBaseUrl();
  return base ? `${base}${url.startsWith("/") ? "" : "/"}${url}` : url;
}

/**
 * Normalizes raw detection JSON from backend into typed ScanDetection.
 */
function normalizeDetection(d: any): ScanDetection {
  const normType = (d.type || d.class_name || "UNKNOWN").toUpperCase();
  const label = d.label || d.class_name || normType.replace(/_/g, " ").toLowerCase();

  return {
    id: d.id || `DET-${Math.random().toString(36).substring(2, 8).toUpperCase()}`,
    trackId: d.track_id ?? d.trackId ?? 0,
    type: normType,
    label: label.charAt(0).toUpperCase() + label.slice(1),
    confidence: Number(d.confidence || 0),
    severity: (d.severity || "LOW").toUpperCase() as SeverityLevel,
    timestamp: d.timestamp || new Date().toISOString(),
    frameNumber: d.frame_number ?? d.frameNumber ?? 0,
    location: {
      lat: d.latitude ?? d.location?.lat ?? 12.9348,
      lon: d.longitude ?? d.location?.lon ?? 77.6101,
      accuracyM: d.location_accuracy ?? d.location?.accuracy_m ?? d.location?.accuracyM ?? 2.5,
      roadSegment: d.road_segment ?? d.location?.road_segment ?? d.location?.roadSegment,
    },
    sourceBusId: d.bus_id || d.sourceBusId,
    sourceRouteId: d.route_id || d.sourceRouteId,
    boundingBox: d.bounding_box
      ? {
          x1: d.bounding_box.x1 ?? 0,
          y1: d.bounding_box.y1 ?? 0,
          x2: d.bounding_box.x2 ?? 1,
          y2: d.bounding_box.y2 ?? 1,
        }
      : undefined,
    evidenceImagePath: resolveEvidenceUrl(d.annotated_evidence_path || d.evidence_path || d.evidenceImagePath),
    originalImagePath: resolveEvidenceUrl(d.original_evidence_path || d.evidence_path || d.originalImagePath),
    annotatedImagePath: resolveEvidenceUrl(d.annotated_evidence_path || d.evidence_path || d.annotatedImagePath),
    thumbnailPath: resolveEvidenceUrl(d.thumbnail_path || d.thumbnailPath),
    storageProvider: d.storage_provider || d.storageProvider || "local_disk",
    status: (d.status || "CONFIRMED").toUpperCase() as any,
    associatedTicketId: d.associated_ticket_id || d.associatedTicketId || d.ticket_id || d.ticketId,
    conditionType: d.condition_type || d.conditionType || "DIRECT",
    isMultimodalVerified: Boolean(d.is_multimodal_verified ?? d.isMultimodalVerified ?? false),
    verificationNotes: d.verification_notes || d.verificationNotes,
    ticketId: d.ticket_id || d.ticketId || d.associated_ticket_id || d.associatedTicketId,
    ticketStatus: d.ticket_status || d.ticketStatus,
    persistentHazardId: d.persistent_hazard_id || d.persistentHazardId,
    independentBusesCount: d.independent_buses_count ?? d.independentBusesCount,
    contributingBuses: d.contributing_buses ?? d.contributingBuses,
    persistenceBadge: d.persistence_badge || d.persistenceBadge,
    lastDetectedAt: d.last_detected_at || d.lastDetectedAt,
    observationCount: d.observation_count ?? d.observationCount ?? d.total_observations,
  };
}

/**
 * Normalizes raw job status response into strongly-typed VideoJobProgress.
 */
function normalizeJobStatus(raw: any): VideoJobProgress {
  const sev = raw.summary_by_severity || raw.summaryBySeverity || {};

  return {
    jobId: raw.job_id || raw.jobId || "",
    status: (raw.status || "IDLE").toUpperCase() as JobStatus,
    progressPct: Number(raw.progress_pct ?? raw.progressPct ?? 0),
    framesProcessed: Number(raw.frames_processed ?? raw.framesProcessed ?? 0),
    totalEstimatedFrames: Number(raw.total_frames ?? raw.totalEstimatedFrames ?? 0),
    detectionsCount: Number(raw.detections_count ?? raw.detectionsCount ?? 0),
    confirmedCount: Number(raw.confirmed_count ?? raw.confirmedCount ?? 0),
    summaryBySeverity: {
      critical: Number(sev.critical ?? 0),
      high: Number(sev.high ?? 0),
      medium: Number(sev.medium ?? 0),
      low: Number(sev.low ?? 0),
    },
    summaryByType: raw.summary_by_type || raw.summaryByType || {},
    videoMetadata: raw.video_metadata
      ? {
          width: raw.video_metadata.width,
          height: raw.video_metadata.height,
          nativeFps: raw.video_metadata.native_fps,
          durationSec: raw.video_metadata.duration_sec,
        }
      : undefined,
    detections: (raw.detections || []).map(normalizeDetection),
    derivedIntelligence: raw.derived_intelligence || raw.derivedIntelligence,
    ticketsSpawned: raw.tickets_spawned || raw.ticketsSpawned,
    errorMessage: raw.error_message || raw.errorMessage,
    startedAt: raw.started_at || raw.startedAt,
    completedAt: raw.completed_at || raw.completedAt,
  };
}

/**
 * Service client for connecting to the NovaFlow AI FastAPI Backend.
 */
export const roadScanApi = {
  /**
   * Health probe to check if the AI backend server is active.
   */
  async checkBackendHealth(): Promise<{
    online: boolean;
    status?: string;
    modelWeights?: string;
    message: string;
  }> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 6000);

      const headers: Record<string, string> = {
        "bypass-tunnel-reminder": "true",
        "ngrok-skip-browser-warning": "true",
      };

      const res = await fetch(`${getApiBaseUrl()}/analyze/health`, {
        signal: controller.signal,
        headers,
      });
      clearTimeout(timeoutId);

      // Check if response is actually JSON and not an HTML 404/rewrite page from Vercel
      const contentType = res.headers.get("content-type") || "";
      if (res.ok && contentType.includes("application/json")) {
        const data = await res.json();
        return {
          online: true,
          status: data.status,
          modelWeights: data.model_weights,
          message: "AI Vision Backend is operational and responsive.",
        };
      }
      if (res.ok && !contentType.includes("application/json")) {
        return {
          online: false,
          message: "Backend endpoint returned HTML instead of JSON. Ensure your tunnel or backend server URL is configured.",
        };
      }
      return {
        online: false,
        message: `Backend returned HTTP ${res.status}`,
      };
    } catch (err: any) {
      return {
        online: false,
        message: err.name === "AbortError"
          ? "Connection timed out connecting to backend server."
          : `Cannot connect to NovaFlow AI Vision backend: ${err.message}`,
      };
    }
  },

  /**
   * Uploads an MP4/MOV/WebM video file for asynchronous offline frame sampling and AI detection.
   */
  async uploadRoadVideo(
    file: File,
    config: ScanConfig,
    onProgress?: (percent: number) => void,
    signal?: AbortSignal
  ): Promise<{ jobId: string; message: string }> {
    const formData = new FormData();
    formData.append("video", file);
    formData.append("sample_fps", config.sampleFps.toString());
    formData.append("bus_id", config.busId);
    formData.append("route_id", config.routeId);
    formData.append("city", config.city);
    formData.append("confidence_threshold", config.confidenceThreshold.toString());

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${getApiBaseUrl()}/analyze/video`);
      try {
        xhr.setRequestHeader("bypass-tunnel-reminder", "true");
        xhr.setRequestHeader("ngrok-skip-browser-warning", "true");
      } catch {}
      xhr.timeout = 120000; // 2 minutes for upload

      if (signal) {
        signal.addEventListener("abort", () => {
          xhr.abort();
          reject(new Error("Video upload cancelled by user."));
        });
      }

      if (xhr.upload && onProgress) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            onProgress(percent);
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText);
            resolve({
              jobId: data.job_id || `SCAN-${Date.now().toString(16).toUpperCase()}`,
              message: data.message || "Video queued for AI analysis",
            });
          } catch {
            resolve({
              jobId: `SCAN-${Date.now().toString(16).toUpperCase()}`,
              message: "Video upload completed",
            });
          }
        } else {
          let errMsg = `Upload failed with status ${xhr.status}`;
          try {
            const res = JSON.parse(xhr.responseText);
            if (res.detail) errMsg = res.detail;
          } catch {}
          reject(new Error(errMsg));
        }
      };

      xhr.onerror = () => {
        reject(
          new Error("Network error connecting to AI backend. Please verify your backend server URL in settings.")
        );
      };

      xhr.ontimeout = () => {
        reject(new Error("Video upload timed out. Please check your network connection or try a smaller video."));
      };

      xhr.send(formData);
    });
  },

  /**
   * Polls the status of an ongoing video analysis job.
   */
  async getJobStatus(jobId: string, signal?: AbortSignal): Promise<VideoJobProgress> {
    const res = await fetch(`${getApiBaseUrl()}/jobs/${jobId}`, {
      signal,
      headers: {
        "bypass-tunnel-reminder": "true",
        "ngrok-skip-browser-warning": "true",
      },
    });
    if (!res.ok) {
      if (res.status === 404) {
        throw new Error(`Job '${jobId}' not found on server.`);
      }
      let errDetail = `Status code ${res.status}`;
      try {
        const body = await res.json();
        if (body.detail) errDetail = body.detail;
      } catch {}
      throw new Error(`Failed to query job status (${errDetail})`);
    }
    const data = await res.json();
    return normalizeJobStatus(data);
  },

  /**
   * Cancels an ongoing analysis job.
   */
  async cancelJob(jobId: string): Promise<boolean> {
    try {
      const res = await fetch(`${getApiBaseUrl()}/jobs/${jobId}/cancel`, {
        method: "POST",
        headers: {
          "bypass-tunnel-reminder": "true",
          "ngrok-skip-browser-warning": "true",
        },
      });
      return res.ok;
    } catch {
      return false;
    }
  },

  /**
   * Reactive polling loop with exponential backoff for transient glitches and timeout safeguard.
   */
  async pollJobUntilFinished(
    jobId: string,
    onUpdate: (progress: VideoJobProgress) => void,
    signal?: AbortSignal,
    pollIntervalMs: number = 1000,
    maxWaitSec: number = 300
  ): Promise<VideoJobProgress> {
    const startTime = Date.now();
    let consecutiveErrors = 0;
    const maxConsecutiveErrors = 4;

    while (true) {
      if (signal?.aborted) {
        throw new Error("Polling aborted by user.");
      }

      const elapsedSec = (Date.now() - startTime) / 1000;
      if (elapsedSec > maxWaitSec) {
        throw new Error(`Analysis timed out after ${maxWaitSec} seconds.`);
      }

      try {
        const job = await this.getJobStatus(jobId, signal);
        consecutiveErrors = 0;
        onUpdate(job);

        if (job.status === "COMPLETED") {
          return job;
        }
        if (job.status === "FAILED") {
          throw new Error(job.errorMessage || "AI analysis failed during processing.");
        }
        if (job.status === "CANCELLED") {
          throw new Error("Job was cancelled.");
        }
      } catch (err: any) {
        if (err.name === "AbortError" || signal?.aborted) {
          throw new Error("Polling aborted by user.");
        }
        consecutiveErrors += 1;
        if (consecutiveErrors >= maxConsecutiveErrors) {
          throw new Error(`Connection lost while tracking job progress: ${err.message}`);
        }
      }

      await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
    }
  },

  /**
   * Ingests a single real-time frame from a connected bus dashcam or client live camera.
   */
  async sendLiveFrame(payload: LiveFramePayload, signal?: AbortSignal): Promise<LiveFrameResponse> {
    const tStart = performance.now();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);

    const onAbort = () => controller.abort();
    if (signal) signal.addEventListener("abort", onAbort);

    try {
      const res = await fetch(`${getApiBaseUrl()}/analyze/frame`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "bypass-tunnel-reminder": "true",
          "ngrok-skip-browser-warning": "true",
        },
        signal: controller.signal,
        body: JSON.stringify({
          frame_b64: payload.frameBase64,
          bus_id: payload.busId,
          route_id: payload.routeId,
          latitude: payload.gps.lat,
          longitude: payload.gps.lon,
          speed_kmh: payload.gps.speedKmh,
          heading_deg: payload.gps.headingDeg,
          timestamp: payload.timestamp || new Date().toISOString(),
          confidence_threshold: payload.confidenceThreshold ?? 0.50,
          persist_detections: payload.persistDetections ?? true,
        }),
      });

      clearTimeout(timeoutId);
      if (signal) signal.removeEventListener("abort", onAbort);

      if (!res.ok) {
        let errMsg = `Live frame analysis failed with status ${res.status}`;
        try {
          const errBody = await res.json();
          if (errBody.detail) errMsg = errBody.detail;
        } catch {}
        throw new Error(errMsg);
      }

      const data = await res.json();
      const roundtripLatency = Math.round(performance.now() - tStart);

      return {
        busId: data.bus_id,
        routeId: data.route_id,
        timestamp: data.timestamp,
        latencyMs: data.latency_ms ?? roundtripLatency,
        detectionsCount: data.detections_count || 0,
        detections: (data.detections || []).map(normalizeDetection),
        speedKmh: data.speed_kmh,
        headingDeg: data.heading_deg,
        annotatedFrameB64: data.annotated_frame_b64,
        derivedIntelligence: data.derived_intelligence,
        ticketsSpawned: data.tickets_spawned,
        geminiVerificationEnabled: data.gemini_verification_enabled,
      };
    } catch (err: any) {
      clearTimeout(timeoutId);
      if (signal) signal.removeEventListener("abort", onAbort);
      if (err.name === "AbortError" && !signal?.aborted) {
        throw new Error("Frame inference request timed out (6s).");
      }
      throw err;
    }
  },

  /**
   * Ingests a small batch of sampled frames for multi-frame road anomaly detection.
   */
  async sendLiveFrameBatch(
    payload: LiveFrameBatchPayload,
    signal?: AbortSignal
  ): Promise<LiveFrameBatchResponse> {
    const tStart = performance.now();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    const onAbort = () => controller.abort();
    if (signal) signal.addEventListener("abort", onAbort);

    try {
      const res = await fetch(`${getApiBaseUrl()}/analyze/batch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "bypass-tunnel-reminder": "true",
          "ngrok-skip-browser-warning": "true",
        },
        signal: controller.signal,
        body: JSON.stringify({
          frames: payload.frames.map((f) => ({
            frame_b64: f.frameBase64,
            frame_idx: f.frameIdx ?? 0,
            timestamp: f.timestamp || new Date().toISOString(),
          })),
          bus_id: payload.busId,
          route_id: payload.routeId,
          latitude: payload.gps.lat,
          longitude: payload.gps.lon,
          speed_kmh: payload.gps.speedKmh,
          heading_deg: payload.gps.headingDeg,
          confidence_threshold: payload.confidenceThreshold ?? 0.50,
          persist_detections: payload.persistDetections ?? true,
        }),
      });

      clearTimeout(timeoutId);
      if (signal) signal.removeEventListener("abort", onAbort);

      if (!res.ok) {
        let errMsg = `Live frame batch analysis failed with status ${res.status}`;
        try {
          const errBody = await res.json();
          if (errBody.detail) errMsg = errBody.detail;
        } catch {}
        throw new Error(errMsg);
      }

      const data = await res.json();
      const roundtripLatency = Math.round(performance.now() - tStart);

      return {
        busId: data.bus_id,
        routeId: data.route_id,
        framesProcessed: data.frames_processed || 0,
        totalDetectionsCount: data.total_detections_count || 0,
        latencyMs: data.latency_ms ?? roundtripLatency,
        detections: (data.detections || []).map(normalizeDetection),
        derivedIntelligence: data.derived_intelligence,
        ticketsSpawned: data.tickets_spawned,
        geminiVerificationEnabled: data.gemini_verification_enabled,
      };
    } catch (err: any) {
      clearTimeout(timeoutId);
      if (signal) signal.removeEventListener("abort", onAbort);
      if (err.name === "AbortError" && !signal?.aborted) {
        throw new Error("Frame batch inference request timed out (10s).");
      }
      throw err;
    }
  },

  /**
   * Fetches persistent road hazards confirmed across transit buses.
   */
  async fetchPersistentHazards(params?: {
    min_buses?: number;
    limit?: number;
  }): Promise<PersistentHazard[]> {
    const query = new URLSearchParams();
    if (params?.min_buses) query.set("min_buses", String(params.min_buses));
    if (params?.limit) query.set("limit", String(params.limit));

    const res = await fetch(`${getApiBaseUrl()}/hazards/persistent?${query.toString()}`, {
      headers: {
        "bypass-tunnel-reminder": "true",
        "ngrok-skip-browser-warning": "true",
      },
    });
    if (!res.ok) {
      throw new Error(`Failed to load persistent hazards: ${res.status}`);
    }
    const data = await res.json();
    return data.hazards || [];
  },

  /**
   * Fetches full detail for a persistent road hazard.
   */
  async fetchHazardDetail(hazardId: string): Promise<PersistentHazard> {
    const res = await fetch(`${getApiBaseUrl()}/hazards/${hazardId}`, {
      headers: {
        "bypass-tunnel-reminder": "true",
        "ngrok-skip-browser-warning": "true",
      },
    });
    if (!res.ok) {
      throw new Error(`Hazard ${hazardId} not found (${res.status})`);
    }
    return res.json();
  },

  /**
   * Fetches observation timeline for a specific hazard.
   */
  async fetchHazardObservations(hazardId: string): Promise<HazardObservation[]> {
    const res = await fetch(`${getApiBaseUrl()}/hazards/${hazardId}/observations`, {
      headers: {
        "bypass-tunnel-reminder": "true",
        "ngrok-skip-browser-warning": "true",
      },
    });
    if (!res.ok) {
      throw new Error(`Hazard observations not found (${res.status})`);
    }
    const data = await res.json();
    return Array.isArray(data) ? data : (data.observations || []);
  },

  /**
   * Fetches sample Indian road video for 1-click Judge Demo Mode.
   */
  async fetchSampleVideoBlob(): Promise<File> {
    let response: Response;
    try {
      response = await fetch(`${getApiBaseUrl()}/scan/sample-video`, {
        headers: {
          "bypass-tunnel-reminder": "true",
          "ngrok-skip-browser-warning": "true",
        },
      });
      if (!response.ok) {
        throw new Error(`Backend sample endpoint returned ${response.status}`);
      }
    } catch (backendErr) {
      // Fallback to static public copy if backend endpoint unreachable
      response = await fetch("/sample_indian_road.mp4");
      if (!response.ok) {
        throw new Error("Could not load sample road video asset.");
      }
    }

    const blob = await response.blob();
    return new File([blob], "sample_indian_road.mp4", { type: "video/mp4" });
  },
};

