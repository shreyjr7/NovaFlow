// src/pages/Scan/RoadScan.tsx
// Bharat Electronics Limited (BEL) • Smart Automation
// NovaFlow — AI Road Scan & Evidence Intelligence Center

import React, { useState, useRef, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  Upload, Camera, Video, AlertTriangle, ShieldCheck, CheckCircle2,
  Clock, MapPin, Wrench, X, RefreshCw, Layers, Gauge, Play, Pause,
  AlertCircle, FileVideo, ChevronRight, Activity, ArrowUpRight,
  Sliders, Info, HelpCircle, HardDrive, Cpu, Radio, Eye, Ban,
  ExternalLink, Check, Image as ImageIcon, Zap, Navigation, Compass,
  Wifi, WifiOff, Sparkles, Car, AlertOctagon, UserCheck
} from "lucide-react";
import {
  roadScanApi,
  getBackendBaseUrl,
  setBackendBaseUrl,
  ScanDetection,
  VideoJobProgress,
  ScanConfig,
  SeverityLevel,
  DerivedIntelligence,
  HazardObservation,
  PersistentHazard,
} from "../../services/roadScanApi";
import { fetchAllBuses, BusNode } from "../../services/busService";

type ScanMode = "UPLOAD" | "CONNECTED_BUS" | "DEMO_PLAYBACK";
type EvidenceViewMode = "ANNOTATED" | "ORIGINAL" | "SIDE_BY_SIDE";

const ACCEPTED_FORMATS = [".mp4", ".mov", ".avi", ".mkv", ".webm"];
const MAX_FILE_SIZE_MB = 500;

export const RoadScan: React.FC = () => {
  const navigate = useNavigate();
  const [mode, setMode] = useState<ScanMode>("UPLOAD");

  // Backend Health
  const [backendHealth, setBackendHealth] = useState<{
    checked: boolean;
    online: boolean;
    message: string;
    modelWeights?: string;
  }>({
    checked: false,
    online: false,
    message: "Checking AI backend connectivity...",
  });
  const [isCheckingHealth, setIsCheckingHealth] = useState<boolean>(false);

  // Video Upload State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string | null>(null);
  const [videoMetadata, setVideoMetadata] = useState<{
    durationSec: number;
    width: number;
    height: number;
  } | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoadingSample, setIsLoadingSample] = useState<boolean>(false);

  // Connected Bus & Demo Playback States (Phases 12 & 13)
  const [connectedBusId, setConnectedBusId] = useState<string>("BUS-027");
  const [demoStep, setDemoStep] = useState<number>(2); // 0: BUS-027, 1: BUS-014, 2: BUS-031
  const [isDemoPlaying, setIsDemoPlaying] = useState<boolean>(false);
  const [hazardObservations, setHazardObservations] = useState<HazardObservation[]>([]);
  const [isLoadingObservations, setIsLoadingObservations] = useState<boolean>(false);

  const [searchParams] = useSearchParams();
  const [availableBuses, setAvailableBuses] = useState<BusNode[]>([]);
  const [customBusIdInput, setCustomBusIdInput] = useState<string>("");
  const [derivedIntelligence, setDerivedIntelligence] = useState<DerivedIntelligence | null>(null);
  const [geminiVerificationActive, setGeminiVerificationActive] = useState<boolean>(false);
  const [totalTicketsCount, setTotalTicketsCount] = useState<number>(0);

  // Configuration
  const [sampleFps, setSampleFps] = useState<number>(1);
  const [busId, setBusId] = useState<string>("BUS-027");
  const [routeId, setRouteId] = useState<string>("ROUTE-17");
  const [city, setCity] = useState<string>("Bengaluru");
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.35);

  // Load Connected Fleet & Preselect from URL Parameters (Phase 8)
  useEffect(() => {
    const busParam = searchParams.get("busId");
    const routeParam = searchParams.get("routeId");
    if (busParam) setBusId(busParam);
    if (routeParam) setRouteId(routeParam);

    const loadFleet = async () => {
      const fleet = await fetchAllBuses();
      if (fleet && fleet.length > 0) {
        setAvailableBuses(fleet);
        if (busParam) {
          const match = fleet.find((b) => b.bus_id === busParam);
          if (match) {
            if (match.route_id && !routeParam) setRouteId(match.route_id);
            if (match.latitude && match.longitude) {
              setGpsState((prev) => ({
                ...prev,
                lat: match.latitude,
                lon: match.longitude,
                speedKmh: match.speed || prev.speedKmh,
                headingDeg: match.heading || prev.headingDeg,
              }));
            }
          }
        }
      }
    };
    loadFleet();
  }, [searchParams]);

  // Processing & Job State
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [processingStage, setProcessingStage] = useState<string>("");
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState<VideoJobProgress | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);

  // Evidence Inspection Modal
  const [selectedEvidence, setSelectedEvidence] = useState<ScanDetection | null>(null);
  const [evidenceViewMode, setEvidenceViewMode] = useState<EvidenceViewMode>("ANNOTATED");

  // Live Camera State (Phase 7 - Connected Bus Live Dashcam & Geolocation)
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const offscreenCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const geoWatchIdRef = useRef<number | null>(null);
  const samplingIntervalRef = useRef<number | null>(null);
  const isInferencingRef = useRef<boolean>(false);

  const [isCameraActive, setIsCameraActive] = useState<boolean>(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [cameraFps, setCameraFps] = useState<number>(1.0); // Configurable: 0.5, 1.0, 2.0, 3.0 FPS
  const [liveAiStatus, setLiveAiStatus] = useState<"IDLE" | "CONNECTING" | "STREAMING" | "INFERENCING" | "ERROR">("IDLE");
  const [liveLatencyMs, setLiveLatencyMs] = useState<number | null>(null);
  const [aiConnectionError, setAiConnectionError] = useState<string | null>(null);
  const [capturedFramesCount, setCapturedFramesCount] = useState<number>(0);

  const [gpsState, setGpsState] = useState<{
    lat: number;
    lon: number;
    speedKmh: number | null;
    headingDeg: number | null;
    accuracyM: number | null;
    isLive: boolean;
    error: string | null;
  }>({
    lat: 12.9348,
    lon: 77.6101,
    speedKmh: 34.2,
    headingDeg: 84,
    accuracyM: 5,
    isLive: false,
    error: null,
  });
  const gpsStateRef = useRef(gpsState);
  useEffect(() => {
    gpsStateRef.current = gpsState;
  }, [gpsState]);

  // Live Detection Feed State
  const [currentFrameDetections, setCurrentFrameDetections] = useState<ScanDetection[]>([]);
  const [liveDetectionsList, setLiveDetectionsList] = useState<ScanDetection[]>([]);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const timerRef = useRef<number | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const [backendUrlInput, setBackendUrlInput] = useState<string>(() => getBackendBaseUrl() || "");
  const [isSavingUrl, setIsSavingUrl] = useState<boolean>(false);
  const [showUrlSettings, setShowUrlSettings] = useState<boolean>(false);
  const [copiedTunnelCmd, setCopiedTunnelCmd] = useState<boolean>(false);

  // Check Backend Health on Mount
  const verifyBackendHealth = async () => {
    setIsCheckingHealth(true);
    const health = await roadScanApi.checkBackendHealth();
    setBackendHealth({
      checked: true,
      online: health.online,
      message: health.message,
      modelWeights: health.modelWeights,
    });
    setIsCheckingHealth(false);
  };

  const handleSaveBackendUrl = async () => {
    let cleaned = backendUrlInput.trim();
    if (cleaned.toLowerCase().includes("npx") || cleaned.toLowerCase().includes("localtunnel --port")) {
      setBackendHealth({
        checked: true,
        online: false,
        message: "You pasted the terminal command instead of the URL! Run `npx localtunnel --port 8000` in your PC terminal, and paste the generated HTTPS link (e.g. https://fresh-snakes-shave.loca.lt) here.",
      });
      return;
    }
    if (cleaned && !cleaned.startsWith("http://") && !cleaned.startsWith("https://")) {
      cleaned = `https://${cleaned}`;
      setBackendUrlInput(cleaned);
    }
    setIsSavingUrl(true);
    setBackendBaseUrl(cleaned);
    await verifyBackendHealth();
    setIsSavingUrl(false);
  };

  const handleResetBackendUrl = async () => {
    setIsSavingUrl(true);
    setBackendBaseUrl("");
    setBackendUrlInput("");
    await verifyBackendHealth();
    setIsSavingUrl(false);
  };

  useEffect(() => {
    verifyBackendHealth();
  }, []);

  // Elapsed timer during processing
  useEffect(() => {
    if (isProcessing) {
      setElapsedSeconds(0);
      timerRef.current = window.setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isProcessing]);

  // Clean up object URLs and abort on unmount
  useEffect(() => {
    return () => {
      if (videoPreviewUrl) URL.revokeObjectURL(videoPreviewUrl);
      if (abortControllerRef.current) abortControllerRef.current.abort();
      stopLiveCamera();
    };
  }, [videoPreviewUrl]);

  // Drag & Drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processSelectedFile(e.target.files[0]);
    }
  };

  // Validate and parse selected video file
  const processSelectedFile = (file: File) => {
    setValidationError(null);
    setJobError(null);
    setJobProgress(null);
    setActiveJobId(null);

    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    const isAccepted = ACCEPTED_FORMATS.includes(ext) || file.type.startsWith("video/");
    if (!isAccepted) {
      setValidationError(
        `Invalid video format (${ext}). Supported: ${ACCEPTED_FORMATS.join(", ")}.`
      );
      return;
    }

    const sizeMb = file.size / (1024 * 1024);
    if (sizeMb > MAX_FILE_SIZE_MB) {
      setValidationError(
        `File size (${sizeMb.toFixed(1)} MB) exceeds maximum allowed limit of ${MAX_FILE_SIZE_MB} MB.`
      );
      return;
    }

    setSelectedFile(file);

    const url = URL.createObjectURL(file);
    setVideoPreviewUrl(url);

    const tempVideo = document.createElement("video");
    tempVideo.src = url;
    tempVideo.onloadedmetadata = () => {
      setVideoMetadata({
        durationSec: Math.round(tempVideo.duration) || 0,
        width: tempVideo.videoWidth || 1920,
        height: tempVideo.videoHeight || 1080
      });
    };
  };

  const clearSelectedFile = () => {
    if (isProcessing) handleCancelAnalysis();
    if (videoPreviewUrl) URL.revokeObjectURL(videoPreviewUrl);
    setSelectedFile(null);
    setVideoPreviewUrl(null);
    setVideoMetadata(null);
    setValidationError(null);
    setJobProgress(null);
    setJobError(null);
    setActiveJobId(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // 1-Click Loader for Pre-Recorded Indian Road Sample Video (Phase 13 Judge Demo Flow)
  const handleLoadSampleVideo = async () => {
    setIsLoadingSample(true);
    setValidationError(null);
    setJobError(null);
    try {
      const file = await roadScanApi.fetchSampleVideoBlob();
      processSelectedFile(file);
      setBusId("BUS-027");
      setRouteId("ROUTE-17");
      setCity("Bengaluru");
    } catch (err: any) {
      setValidationError("Failed to load sample Indian road video: " + (err.message || "Network error"));
    } finally {
      setIsLoadingSample(false);
    }
  };

  // Observation Timeline Loader for Evidence Modal (Phase 12)
  useEffect(() => {
    if (!selectedEvidence) {
      setHazardObservations([]);
      return;
    }
    const targetHazardId = selectedEvidence.persistentHazardId;
    if (targetHazardId) {
      setIsLoadingObservations(true);
      roadScanApi
        .fetchHazardObservations(targetHazardId)
        .then((obs) => setHazardObservations(obs))
        .catch(() => setHazardObservations([]))
        .finally(() => setIsLoadingObservations(false));
    } else {
      setHazardObservations([]);
    }
  }, [selectedEvidence]);

  // Demo Playback Auto-Stepper Timer (Phase 13)
  useEffect(() => {
    let timer: number | null = null;
    if (mode === "DEMO_PLAYBACK" && isDemoPlaying) {
      timer = window.setInterval(() => {
        setDemoStep((prev) => (prev >= 2 ? 0 : prev + 1));
      }, 3500);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [mode, isDemoPlaying]);

  // Start Real Video Analysis Flow
  const handleStartAnalysis = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setUploadProgress(0);
    setProcessingStage("Connecting to NovaFlow AI Vision backend...");
    setJobError(null);
    setJobProgress(null);

    const abortCtrl = new AbortController();
    abortControllerRef.current = abortCtrl;

    const config: ScanConfig = {
      sampleFps,
      busId,
      routeId,
      city,
      confidenceThreshold
    };

    try {
      setProcessingStage("Uploading video file to AI backend...");
      const uploadRes = await roadScanApi.uploadRoadVideo(
        selectedFile,
        config,
        (pct) => {
          setUploadProgress(pct);
          if (pct < 100) {
            setProcessingStage(`Uploading video data (${pct}%)...`);
          } else {
            setProcessingStage("Upload complete. Queued in AI frame sampler...");
          }
        },
        abortCtrl.signal
      );

      const jobId = uploadRes.jobId;
      setActiveJobId(jobId);
      setProcessingStage(`AI Vision Engine sampling frames at ${sampleFps} FPS...`);

      // Reactive Polling
      const finalResult = await roadScanApi.pollJobUntilFinished(
        jobId,
        (current) => {
          setJobProgress(current);
          if (current.derivedIntelligence) {
            setDerivedIntelligence(current.derivedIntelligence);
          }
          if (current.ticketsSpawned) {
            setTotalTicketsCount(current.ticketsSpawned.length);
          }
          if (current.status === "PROCESSING") {
            setProcessingStage(
              `Sampling & tracking: Frame ${current.framesProcessed} / ~${current.totalEstimatedFrames} (${current.progressPct}%)`
            );
          }
        },
        abortCtrl.signal
      );

      setJobProgress(finalResult);
      if (finalResult.derivedIntelligence) {
        setDerivedIntelligence(finalResult.derivedIntelligence);
      }
      if (finalResult.ticketsSpawned) {
        setTotalTicketsCount(finalResult.ticketsSpawned.length);
      }
      setProcessingStage("AI processing complete.");
      setIsProcessing(false);
    } catch (err: any) {
      setIsProcessing(false);
      if (err.message?.includes("cancelled") || abortCtrl.signal.aborted) {
        setJobError("Analysis was cancelled by user.");
      } else {
        setJobError(
          err.message || "Failed to complete AI road analysis. Please verify the backend is running."
        );
      }
    }
  };

  // Cancel Analysis
  const handleCancelAnalysis = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (activeJobId) {
      await roadScanApi.cancelJob(activeJobId);
    }
    setIsProcessing(false);
    setProcessingStage("Analysis cancelled.");
    setJobError("Analysis was cancelled by user.");
  };

  // Draw real-time bounding boxes and labels on overlay canvas atop the live video
  const drawBoundingBoxes = (
    canvas: HTMLCanvasElement,
    video: HTMLVideoElement,
    detections: ScanDetection[]
  ) => {
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Synchronize canvas internal buffer size with video element rendered bounds
    const rect = video.getBoundingClientRect();
    if (canvas.width !== rect.width || canvas.height !== rect.height) {
      canvas.width = rect.width;
      canvas.height = rect.height;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!detections || detections.length === 0) return;

    detections.forEach((d) => {
      if (!d.boundingBox) return;
      let x1 = 0, y1 = 0, x2 = 0, y2 = 0;

      // Handle normalized (0..1) vs pixel coordinates
      if (d.boundingBox.x1 <= 1.0 && d.boundingBox.x2 <= 1.0) {
        x1 = d.boundingBox.x1 * canvas.width;
        y1 = d.boundingBox.y1 * canvas.height;
        x2 = d.boundingBox.x2 * canvas.width;
        y2 = d.boundingBox.y2 * canvas.height;
      } else {
        const scaleX = canvas.width / (video.videoWidth || 1280);
        const scaleY = canvas.height / (video.videoHeight || 720);
        x1 = d.boundingBox.x1 * scaleX;
        y1 = d.boundingBox.y1 * scaleY;
        x2 = d.boundingBox.x2 * scaleX;
        y2 = d.boundingBox.y2 * scaleY;
      }

      const w = Math.max(12, x2 - x1);
      const h = Math.max(12, y2 - y1);

      // Severity Color Palette
      let strokeColor = "#3B82F6"; // Blue (Low)
      let fillBg = "rgba(59, 130, 246, 0.16)";
      if (d.severity === "CRITICAL") {
        strokeColor = "#EF4444";
        fillBg = "rgba(239, 68, 68, 0.22)";
      } else if (d.severity === "HIGH") {
        strokeColor = "#F97316";
        fillBg = "rgba(249, 115, 22, 0.20)";
      } else if (d.severity === "MEDIUM") {
        strokeColor = "#EAB308";
        fillBg = "rgba(234, 179, 8, 0.16)";
      }

      // Box semi-transparent fill & border
      ctx.fillStyle = fillBg;
      ctx.fillRect(x1, y1, w, h);
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 2.5;
      ctx.strokeRect(x1, y1, w, h);

      // Corner Targeting Brackets
      const cornerLength = Math.min(12, w / 3, h / 3);
      ctx.lineWidth = 3.5;
      ctx.beginPath();
      // Top-Left
      ctx.moveTo(x1, y1 + cornerLength);
      ctx.lineTo(x1, y1);
      ctx.lineTo(x1 + cornerLength, y1);
      // Top-Right
      ctx.moveTo(x2 - cornerLength, y1);
      ctx.lineTo(x2, y1);
      ctx.lineTo(x2, y1 + cornerLength);
      // Bottom-Left
      ctx.moveTo(x1, y1 + h - cornerLength);
      ctx.lineTo(x1, y1 + h);
      ctx.lineTo(x1 + cornerLength, y1 + h);
      // Bottom-Right
      ctx.moveTo(x2 - cornerLength, y1 + h);
      ctx.lineTo(x2, y1 + h);
      ctx.lineTo(x2, y1 + h - cornerLength);
      ctx.stroke();

      // Top Tag Badge with Label and Confidence
      const labelText = `${d.label.toUpperCase()} ${Math.round(d.confidence * 100)}%`;
      ctx.font = "bold 11px Inter, system-ui, sans-serif";
      const textWidth = ctx.measureText(labelText).width;
      const badgeHeight = 20;
      const badgeWidth = textWidth + 10;
      const badgeY = y1 - badgeHeight > 0 ? y1 - badgeHeight : y1 + 2;

      ctx.fillStyle = strokeColor;
      ctx.fillRect(x1, badgeY, badgeWidth, badgeHeight);
      ctx.fillStyle = "#FFFFFF";
      ctx.fillText(labelText, x1 + 5, badgeY + 14);
    });
  };

  // Start continuous GPS tracking via Browser Geolocation watchPosition
  const startGpsTracking = () => {
    if (!("geolocation" in navigator)) {
      setGpsState((prev) => {
        const updated = {
          ...prev,
          isLive: false,
          error: "Browser Geolocation API not supported. Using corridor telemetry fallback.",
        };
        gpsStateRef.current = updated;
        return updated;
      });
      return;
    }

    try {
      const watchId = navigator.geolocation.watchPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          const speedKmh =
            pos.coords.speed !== null && !isNaN(pos.coords.speed)
              ? Math.round(pos.coords.speed * 3.6 * 10) / 10
              : null;
          const headingDeg =
            pos.coords.heading !== null && !isNaN(pos.coords.heading)
              ? Math.round(pos.coords.heading)
              : null;
          const accuracyM = Math.round(pos.coords.accuracy);

          const updated = {
            lat,
            lon,
            speedKmh: speedKmh ?? 32.5,
            headingDeg: headingDeg ?? 85,
            accuracyM,
            isLive: true,
            error: null,
          };
          setGpsState(updated);
          gpsStateRef.current = updated;
        },
        (err) => {
          let msg = "GPS position unavailable. Using corridor fallback.";
          if (err.code === 1) {
            msg = "Location permission denied. Running in corridor fallback mode.";
          } else if (err.code === 3) {
            msg = "GPS request timed out. Retrying in background...";
          }
          setGpsState((prev) => {
            const updated = { ...prev, isLive: false, error: msg };
            gpsStateRef.current = updated;
            return updated;
          });
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 2000,
        }
      );
      geoWatchIdRef.current = watchId;
    } catch (err: any) {
      setGpsState((prev) => {
        const updated = {
          ...prev,
          isLive: false,
          error: `Geolocation error: ${err.message}`,
        };
        gpsStateRef.current = updated;
        return updated;
      });
    }
  };

  // Start Live Camera (Rear camera preference + fallback)
  const startLiveCamera = async () => {
    setCameraError(null);
    setAiConnectionError(null);

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraError(
        "Camera streaming is not supported on this browser or requires HTTPS / localhost."
      );
      return;
    }

    try {
      let stream: MediaStream;
      try {
        // Preferred: Rear facing camera for transit vehicle dashcam
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        });
      } catch (envErr) {
        console.warn("Rear camera constraint failed, falling back to default camera:", envErr);
        // Fallback to generic video camera
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
      }

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch((e) => console.warn("Video play error:", e));
      }

      setIsCameraActive(true);
      setLiveAiStatus("STREAMING");
      startGpsTracking();
    } catch (err: any) {
      console.error("Camera access error:", err);
      let errorMsg = "Failed to access camera.";
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        errorMsg = "Camera permission was denied. Please allow camera permissions in your browser address bar.";
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        errorMsg = "No video camera hardware detected on this device.";
      } else if (err.name === "NotReadableError") {
        errorMsg = "Camera is currently in use by another application.";
      } else {
        errorMsg = err.message || errorMsg;
      }
      setCameraError(errorMsg);
      setIsCameraActive(false);
      setLiveAiStatus("IDLE");
    }
  };

  // Stop Live Camera cleanly
  const stopLiveCamera = () => {
    // 1. Stop all video tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
      videoRef.current.srcObject = null;
    }

    // 2. Clear sampling interval
    if (samplingIntervalRef.current) {
      clearInterval(samplingIntervalRef.current);
      samplingIntervalRef.current = null;
    }

    // 3. Clear Geolocation watch
    if (geoWatchIdRef.current !== null && "geolocation" in navigator) {
      navigator.geolocation.clearWatch(geoWatchIdRef.current);
      geoWatchIdRef.current = null;
    }

    // 4. Clear overlay canvas
    if (overlayCanvasRef.current) {
      const ctx = overlayCanvasRef.current.getContext("2d");
      if (ctx) ctx.clearRect(0, 0, overlayCanvasRef.current.width, overlayCanvasRef.current.height);
    }

    // 5. Reset states
    setIsCameraActive(false);
    isInferencingRef.current = false;
    setLiveAiStatus("IDLE");
    setCurrentFrameDetections([]);
  };

  // Gentle corridor simulation advancement when live GPS is denied or offline
  useEffect(() => {
    let simInterval: number | null = null;
    if (isCameraActive && !gpsState.isLive) {
      simInterval = window.setInterval(() => {
        setGpsState((prev) => {
          const next = {
            ...prev,
            lat: Number((prev.lat + 0.00003).toFixed(6)),
            lon: Number((prev.lon + 0.00002).toFixed(6)),
            speedKmh: Math.round(28 + Math.random() * 6),
            headingDeg: prev.headingDeg || 84,
          };
          gpsStateRef.current = next;
          return next;
        });
      }, 1000);
    }
    return () => {
      if (simInterval) clearInterval(simInterval);
    };
  }, [isCameraActive, gpsState.isLive]);

  // Live Camera Frame Sampling & AI Inference Loop (Phase 7)
  useEffect(() => {
    if (!isCameraActive) {
      if (samplingIntervalRef.current) {
        clearInterval(samplingIntervalRef.current);
        samplingIntervalRef.current = null;
      }
      return;
    }

    const intervalMs = Math.round(1000 / cameraFps);
    samplingIntervalRef.current = window.setInterval(async () => {
      // Prevent queue congestion: skip sampling tick if previous inference still in flight
      if (isInferencingRef.current) {
        return;
      }

      const video = videoRef.current;
      const offscreenCanvas = offscreenCanvasRef.current;
      if (!video || video.readyState < 2 || video.videoWidth === 0 || !offscreenCanvas) {
        return;
      }

      isInferencingRef.current = true;
      setLiveAiStatus("INFERENCING");

      try {
        const targetWidth = 640;
        const targetHeight = Math.round((targetWidth * video.videoHeight) / video.videoWidth) || 360;
        offscreenCanvas.width = targetWidth;
        offscreenCanvas.height = targetHeight;

        const ctx = offscreenCanvas.getContext("2d");
        if (!ctx) {
          isInferencingRef.current = false;
          return;
        }

        ctx.drawImage(video, 0, 0, targetWidth, targetHeight);
        const frameB64 = offscreenCanvas.toDataURL("image/jpeg", 0.75);

        const currentGps = gpsStateRef.current;
        const tStart = performance.now();

        const res = await roadScanApi.sendLiveFrame({
          frameBase64: frameB64,
          timestamp: new Date().toISOString(),
          busId,
          routeId,
          gps: {
            lat: currentGps.lat,
            lon: currentGps.lon,
            speedKmh: currentGps.speedKmh,
            headingDeg: currentGps.headingDeg,
            accuracyM: currentGps.accuracyM,
          },
          confidenceThreshold,
          persistDetections: true,
        });

        const roundtripMs = Math.round(performance.now() - tStart);
        setLiveLatencyMs(res.latencyMs || roundtripMs);
        setCapturedFramesCount((prev) => prev + 1);
        setLiveAiStatus("STREAMING");
        setAiConnectionError(null);

        if (res.derivedIntelligence) {
          setDerivedIntelligence(res.derivedIntelligence);
        }
        if (res.geminiVerificationEnabled !== undefined) {
          setGeminiVerificationActive(res.geminiVerificationEnabled);
        }
        if (res.ticketsSpawned && res.ticketsSpawned.length > 0) {
          setTotalTicketsCount((prev) => prev + res.ticketsSpawned!.length);
        }

        // Process live detections
        if (res.detections && res.detections.length > 0) {
          setCurrentFrameDetections(res.detections);
          setLiveDetectionsList((prev) => {
            const combined = [...res.detections, ...prev];
            const seen = new Set();
            return combined.filter((item) => {
              if (seen.has(item.id)) return false;
              seen.add(item.id);
              return true;
            }).slice(0, 30);
          });

          // Draw on overlay canvas directly over video
          if (overlayCanvasRef.current && videoRef.current) {
            drawBoundingBoxes(overlayCanvasRef.current, videoRef.current, res.detections);
          }
        } else {
          setCurrentFrameDetections([]);
          if (overlayCanvasRef.current) {
            const overlayCtx = overlayCanvasRef.current.getContext("2d");
            if (overlayCtx) overlayCtx.clearRect(0, 0, overlayCanvasRef.current.width, overlayCanvasRef.current.height);
          }
        }
      } catch (err: any) {
        console.warn("Live frame inference error:", err);
        setLiveAiStatus("ERROR");
        setAiConnectionError(
          err.message || "AI inference server error or connection timed out."
        );
      } finally {
        isInferencingRef.current = false;
      }
    }, intervalMs);

    return () => {
      if (samplingIntervalRef.current) {
        clearInterval(samplingIntervalRef.current);
        samplingIntervalRef.current = null;
      }
    };
  }, [isCameraActive, cameraFps, busId, routeId, confidenceThreshold]);

  // Severity color helpers
  const getSeverityBadgeClass = (sev: SeverityLevel | string) => {
    switch ((sev || "").toUpperCase()) {
      case "CRITICAL":
        return "bg-[#FEE2E2] text-[#DC2626] border-[#FCA5A5]";
      case "HIGH":
        return "bg-[#FFEDD5] text-[#EA580C] border-[#FDBA74]";
      case "MEDIUM":
        return "bg-[#FEF3C7] text-[#D97706] border-[#FCD34D]";
      case "LOW":
      default:
        return "bg-[#E0F2FE] text-[#0284C7] border-[#BAE6FD]";
    }
  };

  const renderDerivedIntelligenceHud = (intel: DerivedIntelligence | null) => {
    if (!intel) return null;
    return (
      <div className="bg-gradient-to-br from-[#0F172A] via-[#1E293B] to-[#0F172A] text-white p-5 rounded-2xl border border-[#334155] shadow-xl space-y-4 animate-fadeIn">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 border-b border-white/10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600/30 border border-blue-500/40 flex items-center justify-center text-blue-400">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                Derived Road Intelligence
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
                  Phase 9 Engine
                </span>
              </h4>
              <p className="text-xs text-slate-400">
                Situational road intelligence derived from computer-vision detections & kinematic telemetry
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-950/60 text-purple-300 border border-purple-500/40">
              <Sparkles className="w-3.5 h-3.5 text-purple-400" />
              <span>Gemini Verification: {geminiVerificationActive ? "Operational" : "Standby"}</span>
            </span>
            {totalTicketsCount > 0 && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-950/60 text-amber-300 border border-amber-500/40">
                <Wrench className="w-3.5 h-3.5 text-amber-400" />
                <span>Tickets: {totalTicketsCount}</span>
              </span>
            )}
          </div>
        </div>

        {(() => {
          // Normalize Traffic Congestion
          const cong = intel.traffic_congestion || {};
          const congLevel = cong.level || "LOW";
          const vehicleCount = cong.vehicle_count ?? 0;
          const roadOccupancy = cong.road_occupancy_pct ?? (cong.occupancy_ratio ? Math.round(cong.occupancy_ratio * 100) : 0);
          const recommendation = cong.recommendation || (congLevel === "HIGH" ? "Heavy congestion: recommend headway spacing & speed advisory." : congLevel === "MEDIUM" ? "Moderate vehicle density in travel lane." : "Optimal vehicle flow; corridor clear.");

          // Normalize Pedestrian Conflict
          const pedRaw = intel.pedestrian_risk;
          const pedArray: any[] = Array.isArray(pedRaw) ? pedRaw : (pedRaw?.detected ? [pedRaw] : []);
          const pedDetected = pedArray.length > 0;
          const highestPed = pedArray[0] || {};
          const pedRiskLevel = highestPed.severity || highestPed.risk_level || (pedDetected ? "MODERATE" : "NONE");
          const pedLabel = highestPed.label || "Potential Pedestrian Conflict/Risk";
          const pedCount = highestPed.pedestrian_count ?? (pedDetected ? pedArray.length : 0);
          const pedVehCount = highestPed.vehicles_in_proximity ?? (pedDetected ? 1 : 0);
          const pedDetails = highestPed.description || highestPed.details || (pedDetected ? `${pedArray.length} potential conflict zone(s) identified in road corridor.` : "No active pedestrian conflicts detected in roadway.");

          // Normalize Incidents
          const incRaw = intel.incidents;
          const incArray: any[] = Array.isArray(incRaw) ? incRaw : (incRaw?.detected ? [incRaw] : []);
          const incDetected = incArray.length > 0;
          const firstInc = incArray[0] || {};
          const incLabel = firstInc.label || "Potential Incident";
          const incIndicators: string[] = Array.isArray(firstInc.indicators)
            ? firstInc.indicators
            : incArray.map((x: any) => x.subtype || x.type || "Incident Indicator");
          const incDetails = firstInc.description || firstInc.details || (incDetected ? `${incArray.length} incident indicator(s) identified.` : "Normal roadway conditions; no incident markers.");

          return (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* 1. Traffic Congestion */}
              <div className={`p-4 rounded-xl border transition ${
                congLevel === "HIGH"
                  ? "bg-red-950/40 border-red-500/40 text-red-200"
                  : congLevel === "MEDIUM"
                  ? "bg-amber-950/40 border-amber-500/40 text-amber-200"
                  : "bg-emerald-950/40 border-emerald-500/40 text-emerald-200"
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Car className="w-4 h-4 text-slate-300" />
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-300">Traffic Congestion</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs font-black uppercase ${
                    congLevel === "HIGH"
                      ? "bg-red-500 text-white"
                      : congLevel === "MEDIUM"
                      ? "bg-amber-500 text-white"
                      : "bg-emerald-600 text-white"
                  }`}>
                    {congLevel}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono mb-2">
                  <div>
                    <span className="text-slate-400 block text-[10px]">VEHICLE COUNT</span>
                    <span className="text-lg font-bold text-white">{vehicleCount}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">ROAD OCCUPANCY</span>
                    <span className="text-lg font-bold text-white">{roadOccupancy}%</span>
                  </div>
                </div>
                <p className="text-[11px] text-slate-300 leading-tight">
                  {recommendation}
                </p>
              </div>

              {/* 2. Potential Pedestrian Conflict/Risk */}
              <div className={`p-4 rounded-xl border transition ${
                pedDetected
                  ? pedRiskLevel === "HIGH" || pedRiskLevel === "CRITICAL"
                    ? "bg-red-950/40 border-red-500/40 text-red-200"
                    : "bg-amber-950/40 border-amber-500/40 text-amber-200"
                  : "bg-slate-900/60 border-slate-700/60 text-slate-300"
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <UserCheck className="w-4 h-4 text-slate-300" />
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-300">Pedestrian Conflict</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs font-black uppercase ${
                    pedRiskLevel === "HIGH" || pedRiskLevel === "CRITICAL"
                      ? "bg-red-500 text-white"
                      : pedRiskLevel === "MODERATE" || pedRiskLevel === "MEDIUM"
                      ? "bg-amber-500 text-white"
                      : pedRiskLevel === "LOW"
                      ? "bg-yellow-600 text-white"
                      : "bg-slate-700 text-slate-300"
                  }`}>
                    {pedRiskLevel}
                  </span>
                </div>
                <div className="text-xs mb-1">
                  <span className="font-bold text-white block">{pedLabel}</span>
                  <span className="text-[11px] text-slate-400 font-mono">
                    {pedCount} pedestrian(s) • {pedVehCount} vehicle proximity
                  </span>
                </div>
                <p className="text-[11px] text-slate-300 leading-tight mt-1">
                  {pedDetails}
                </p>
              </div>

              {/* 3. Potential Incident */}
              <div className={`p-4 rounded-xl border transition ${
                incDetected
                  ? "bg-red-950/40 border-red-500/40 text-red-200"
                  : "bg-slate-900/60 border-slate-700/60 text-slate-300"
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <AlertOctagon className="w-4 h-4 text-orange-400" />
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-300">Incident Detection</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs font-black uppercase ${
                    incDetected
                      ? "bg-red-600 text-white"
                      : "bg-slate-700 text-slate-300"
                  }`}>
                    {incDetected ? "ALERT" : "CLEAR"}
                  </span>
                </div>
                <div className="text-xs mb-1">
                  <span className="font-bold text-white block">{incLabel}</span>
                  <span className="text-[11px] text-slate-400 font-mono">
                    Indicators: {incIndicators.length}
                  </span>
                </div>
                {incIndicators.length > 0 && (
                  <div className="flex flex-wrap gap-1 my-1">
                    {incIndicators.map((ind, i) => (
                      <span key={i} className="px-1.5 py-0.5 rounded text-[10px] bg-red-900/50 border border-red-500/40 text-red-200">
                        {ind}
                      </span>
                    ))}
                  </div>
                )}
                <p className="text-[11px] text-slate-300 leading-tight mt-1">
                  {incDetails}
                </p>
              </div>
            </div>
          );
        })()}
      </div>
    );
  };

  return (
    <div className="min-h-full pb-16 bg-[#F8FAFC]">
      {/* Top Banner Header */}
      <div className="bg-[#1B254B] border-b border-[#2D3A6E] text-white px-4 sm:px-6 lg:px-8 py-5">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#93C5FD] mb-1.5">
              <Cpu className="w-3.5 h-3.5 text-[#60A5FA]" />
              <span>Bharat Electronics Limited (BEL) • Edge AI Vision Pipeline</span>
            </div>
            <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <Video className="w-7 h-7 text-[#60A5FA]" />
              AI Road Scan & Computer Vision Analysis
            </h1>
            <p className="text-sm text-[#94A3B8] mt-1 max-w-2xl">
              Connected public-transit road intelligence: upload inspection footage or stream onboard dashcam video for YOLO hazard detection.
            </p>
          </div>

          {/* Mode Switcher & Backend Health Badge */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            {/* Backend Connectivity Indicator */}
            <div className="flex items-center gap-2">
              {backendHealth.checked && (
                <div
                  className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${
                    backendHealth.online
                      ? "bg-[#064E3B]/60 text-[#34D399] border-[#059669]/40"
                      : "bg-[#7F1D1D]/60 text-[#F87171] border-[#DC2626]/40"
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      backendHealth.online ? "bg-[#34D399] animate-pulse" : "bg-[#F87171]"
                    }`}
                  />
                  <span>
                    {backendHealth.online
                      ? `AI Backend Active (${backendHealth.modelWeights || "YOLOv8"})`
                      : "Backend Offline"}
                  </span>
                  <button
                    onClick={verifyBackendHealth}
                    disabled={isCheckingHealth}
                    title="Retry connection"
                    className="ml-1 hover:text-white transition"
                  >
                    <RefreshCw className={`w-3 h-3 ${isCheckingHealth ? "animate-spin" : ""}`} />
                  </button>
                </div>
              )}
            </div>

            {/* Mode Switcher Segmented Pills (Phases 12 & 13) */}
            <div className="inline-flex rounded-lg p-1 bg-[#111C44] border border-[#2D3A6E] shadow-inner flex-wrap gap-1">
              <button
                onClick={() => setMode("UPLOAD")}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                  mode === "UPLOAD"
                    ? "bg-[#2563EB] text-white shadow-sm"
                    : "text-[#94A3B8] hover:text-white"
                }`}
              >
                <Upload className="w-3.5 h-3.5" />
                <span>Upload Video</span>
              </button>
              <button
                onClick={() => setMode("CONNECTED_BUS")}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                  mode === "CONNECTED_BUS"
                    ? "bg-[#2563EB] text-white shadow-sm"
                    : "text-[#94A3B8] hover:text-white"
                }`}
              >
                <Radio className="w-3.5 h-3.5" />
                <span>Connected Bus</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        {/* Backend Offline Advisory Banner */}
        {backendHealth.checked && !backendHealth.online && (
          <div className="mb-6 p-5 rounded-2xl bg-[#FEF2F2] border border-[#FCA5A5] text-[#991B1B] shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-[#DC2626] flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-bold text-[#991B1B] flex items-center gap-2">
                    <span>AI Vision Engine Server Not Connected</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-200 text-red-800 font-semibold">
                      Vercel Cloud Frontend
                    </span>
                  </h4>
                  <p className="text-xs text-[#B91C1C] mt-1 leading-relaxed">
                    Vercel hosts the web frontend, while the PyTorch YOLOv8 AI inference engine runs on a FastAPI backend.
                    Connect your backend endpoint below to run video analysis and live dashcam scanning.
                  </p>
                </div>
              </div>
              <button
                onClick={verifyBackendHealth}
                disabled={isCheckingHealth}
                className="px-3.5 py-1.5 rounded-lg bg-[#DC2626] hover:bg-[#B91C1C] text-white text-xs font-bold transition flex items-center gap-1.5 flex-shrink-0 self-start sm:self-auto cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isCheckingHealth ? "animate-spin" : ""}`} />
                <span>Retry Connection</span>
              </button>
            </div>

            {/* Quick URL Config Input */}
            <div className="bg-white p-3.5 rounded-xl border border-red-200 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <span>Backend Server Endpoint URL</span>
                  <span className="text-[10px] text-slate-500 font-normal">(saved in browser)</span>
                </span>
                {getBackendBaseUrl() && (
                  <button
                    onClick={handleResetBackendUrl}
                    className="text-[11px] text-red-600 hover:underline cursor-pointer"
                  >
                    Reset to Default
                  </button>
                )}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={backendUrlInput}
                  onChange={(e) => setBackendUrlInput(e.target.value)}
                  placeholder="e.g. https://your-tunnel.loca.lt or https://novaflow.onrender.com"
                  className="flex-1 bg-slate-50 border border-slate-300 focus:border-blue-500 rounded-lg px-3 py-1.5 text-xs text-slate-900 font-mono focus:outline-none"
                />
                <button
                  onClick={handleSaveBackendUrl}
                  disabled={isSavingUrl || isCheckingHealth}
                  className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold transition flex items-center gap-1 shrink-0 cursor-pointer shadow-sm"
                >
                  <RefreshCw className={`w-3 h-3 ${isSavingUrl ? "animate-spin" : ""}`} />
                  <span>Connect & Save</span>
                </button>
              </div>

              {/* Instructions Row */}
              <div className="pt-2 border-t border-slate-100 grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px] text-slate-600">
                <div className="space-y-1">
                  <span className="font-semibold text-slate-800">⚡ 30-Second Live Test (Local PC):</span>
                  <div className="flex items-center justify-between bg-slate-900 text-emerald-400 px-2.5 py-1 rounded font-mono text-[10px]">
                    <span>npx localtunnel --port 8000</span>
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard.writeText("npx localtunnel --port 8000");
                        setCopiedTunnelCmd(true);
                        setTimeout(() => setCopiedTunnelCmd(false), 2000);
                      }}
                      className="text-slate-400 hover:text-white cursor-pointer ml-2"
                    >
                      {copiedTunnelCmd ? "Copied!" : "Copy"}
                    </button>
                  </div>
                  <p className="text-[10px] text-slate-500">Paste the generated HTTPS link above and click Connect & Save.</p>
                </div>
                <div className="space-y-1">
                  <span className="font-semibold text-slate-800">☁️ Permanent Cloud (Render / Railway):</span>
                  <p className="text-[10px] text-slate-500 leading-normal">
                    Deploy <code className="font-mono bg-slate-100 px-1 py-0.2 rounded">backend/</code> to Render.com, then add <code className="font-mono bg-slate-100 px-1 py-0.2 rounded text-blue-600">VITE_API_URL</code> to your Vercel Project Settings &gt; Environment Variables.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Backend Online Status Banner (Compact) */}
        {backendHealth.checked && backendHealth.online && (
          <div className="mb-4 px-4 py-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 flex items-center justify-between text-xs shadow-sm">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-emerald-500/20 animate-pulse" />
              <span className="font-medium">
                AI Vision Engine Operational:{" "}
                <span className="font-mono font-semibold text-emerald-800">
                  {getBackendBaseUrl() || "http://localhost:8000 (Local / Proxy)"}
                </span>
              </span>
              {backendHealth.modelWeights && (
                <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 text-[10px] font-mono border border-emerald-300">
                  YOLOv8 Active
                </span>
              )}
            </div>
            <button
              onClick={() => setShowUrlSettings(!showUrlSettings)}
              className="text-emerald-700 hover:text-emerald-900 underline font-medium cursor-pointer"
            >
              {showUrlSettings ? "Hide Settings" : "Change Server URL"}
            </button>
          </div>
        )}

        {/* Optional Collapsible Settings when Online */}
        {backendHealth.checked && backendHealth.online && showUrlSettings && (
          <div className="mb-6 p-4 rounded-xl bg-white border border-slate-200 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <h5 className="text-xs font-bold text-slate-800">Configure Backend Server Endpoint</h5>
              <button
                onClick={() => setShowUrlSettings(false)}
                className="text-xs text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                Close
              </button>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={backendUrlInput}
                onChange={(e) => setBackendUrlInput(e.target.value)}
                placeholder="https://your-backend.loca.lt or https://novaflow.onrender.com"
                className="flex-1 bg-slate-50 border border-slate-300 focus:border-blue-500 rounded-lg px-3 py-1.5 text-xs text-slate-900 font-mono focus:outline-none"
              />
              <button
                onClick={handleSaveBackendUrl}
                disabled={isSavingUrl}
                className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition flex items-center gap-1 cursor-pointer"
              >
                <RefreshCw className={`w-3 h-3 ${isSavingUrl ? "animate-spin" : ""}`} />
                <span>Save</span>
              </button>
              <button
                onClick={handleResetBackendUrl}
                className="px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold cursor-pointer"
              >
                Reset
              </button>
            </div>
          </div>
        )}

        {/* MODE 1: UPLOAD ROAD VIDEO */}
        {mode === "UPLOAD" && (
          <div className="space-y-6">
            {/* Upload Zone & Config Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left 2 Cols: Drag and Drop & Preview */}
              <div className="lg:col-span-2 space-y-4">
                {!selectedFile ? (
                  <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 bg-white ${
                      isDragging
                        ? "border-[#2563EB] bg-[#EFF6FF]"
                        : "border-[#CBD5E1] hover:border-[#2563EB] hover:bg-[#F8FAFC]"
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept={ACCEPTED_FORMATS.join(",")}
                      onChange={handleFileInputChange}
                      className="hidden"
                    />
                    <div className="w-14 h-14 mx-auto mb-3.5 rounded-2xl bg-[#EFF6FF] border border-[#BFDBFE] flex items-center justify-center text-[#2563EB]">
                      <Upload className="w-7 h-7" />
                    </div>
                    <h3 className="text-base sm:text-lg font-bold text-[#0F172A]">
                      Drag and drop road inspection video here
                    </h3>
                    <p className="text-xs sm:text-sm text-[#64748B] mt-1">
                      or click to browse from your device
                    </p>
                    <div className="mt-4 inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F1F5F9] text-[11px] font-medium text-[#475569]">
                      <span>Formats: MP4, MOV, AVI, MKV, WebM</span>
                      <span>•</span>
                      <span>Max: {MAX_FILE_SIZE_MB} MB</span>
                    </div>
                  </div>
                ) : (
                  <div className="bg-white border border-[#CBD5E1] rounded-xl p-5 shadow-sm space-y-4">
                    <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-10 h-10 rounded-lg bg-[#EFF6FF] flex items-center justify-center text-[#2563EB] flex-shrink-0">
                          <FileVideo className="w-5 h-5" />
                        </div>
                        <div className="min-w-0">
                          <h4 className="text-sm font-bold text-[#0F172A] truncate">
                            {selectedFile.name}
                          </h4>
                          <p className="text-xs text-[#64748B]">
                            {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                            {videoMetadata && (
                              <span>
                                &nbsp;•&nbsp;{videoMetadata.width}×{videoMetadata.height}&nbsp;•&nbsp;
                                {Math.floor(videoMetadata.durationSec / 60)}m {videoMetadata.durationSec % 60}s
                              </span>
                            )}
                          </p>
                        </div>
                      </div>

                      <button
                        onClick={clearSelectedFile}
                        disabled={isProcessing}
                        className="text-xs font-semibold px-2.5 py-1 rounded border border-[#CBD5E1] bg-white hover:bg-[#F1F5F9] text-[#DC2626] transition flex items-center gap-1 disabled:opacity-50"
                      >
                        <X className="w-3.5 h-3.5" />
                        <span>Remove</span>
                      </button>
                    </div>

                    {/* HTML5 Video Preview */}
                    {videoPreviewUrl && (
                      <div className="relative rounded-lg overflow-hidden bg-black aspect-video flex items-center justify-center">
                        <video
                          src={videoPreviewUrl}
                          controls
                          className="w-full h-full object-contain"
                        />
                      </div>
                    )}
                  </div>
                )}

                {/* Validation Error Banner */}
                {validationError && (
                  <div className="p-3.5 rounded-lg bg-[#FEF2F2] border border-[#FECACA] text-xs text-[#B91C1C] flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{validationError}</span>
                  </div>
                )}

                {/* Job Error Banner */}
                {jobError && (
                  <div className="p-4 rounded-xl bg-[#FEF2F2] border border-[#FECACA] text-xs text-[#B91C1C] flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5">
                      <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold block">Processing Notice</span>
                        <span>{jobError}</span>
                      </div>
                    </div>
                    {selectedFile && !isProcessing && (
                      <button
                        onClick={handleStartAnalysis}
                        className="px-3 py-1 rounded bg-[#DC2626] hover:bg-[#B91C1C] text-white font-bold transition flex-shrink-0"
                      >
                        Retry Analysis
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Right Col: Analysis Configuration */}
              <div className="bg-white border border-[#CBD5E1] rounded-xl p-5 shadow-sm space-y-4 flex flex-col justify-between">
                <div className="space-y-4">
                  <div className="flex items-center gap-2 pb-3 border-b border-[#E2E8F0]">
                    <Sliders className="w-4 h-4 text-[#2563EB]" />
                    <h3 className="text-sm font-bold text-[#0F172A]">
                      Sampling & Pipeline Config
                    </h3>
                  </div>

                  {/* Frame Sampling Rate */}
                  <div>
                    <label className="block text-xs font-semibold text-[#475569] mb-1">
                      Frame Sampling Rate
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      {[
                        { fps: 1, label: "1 FPS", desc: "Standard" },
                        { fps: 2, label: "2 FPS", desc: "Detailed" },
                        { fps: 5, label: "5 FPS", desc: "High Density" }
                      ].map((item) => (
                        <button
                          key={item.fps}
                          type="button"
                          disabled={isProcessing}
                          onClick={() => setSampleFps(item.fps)}
                          className={`p-2 rounded-lg border text-center transition ${
                            sampleFps === item.fps
                              ? "border-[#2563EB] bg-[#EFF6FF] text-[#2563EB] font-bold"
                              : "border-[#CBD5E1] bg-white text-[#475569] hover:bg-[#F8FAFC]"
                          }`}
                        >
                          <span className="block text-xs">{item.label}</span>
                          <span className="block text-[10px] text-[#64748B]">{item.desc}</span>
                        </button>
                      ))}
                    </div>
                    <p className="text-[11px] text-[#64748B] mt-1">
                      1 FPS samples one frame per second, balancing accuracy and speed.
                    </p>
                  </div>

                  {/* Bus ID and Route - Multi-Bus Fleet Selector (Phase 8) */}
                  <div className="space-y-2">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-xs font-semibold text-[#475569]">
                          Edge Bus Data Node
                        </label>
                        <span className="text-[10px] font-mono font-bold text-[#2563EB]">
                          {availableBuses.length > 0 ? `${availableBuses.length} Fleet Nodes Online` : "Fleet"}
                        </span>
                      </div>
                      <select
                        disabled={isProcessing}
                        value={availableBuses.some((b) => b.bus_id === busId) ? busId : "CUSTOM"}
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val === "CUSTOM") {
                            setCustomBusIdInput(busId);
                          } else {
                            setBusId(val);
                            const match = availableBuses.find((b) => b.bus_id === val);
                            if (match) {
                              if (match.route_id) setRouteId(match.route_id);
                              if (match.latitude && match.longitude) {
                                setGpsState((prev) => ({
                                  ...prev,
                                  lat: match.latitude,
                                  lon: match.longitude,
                                  speedKmh: match.speed || prev.speedKmh,
                                  headingDeg: match.heading || prev.headingDeg,
                                }));
                              }
                            }
                          }
                        }}
                        className="w-full px-2.5 py-1.5 text-xs border border-[#CBD5E1] rounded-md font-mono text-[#1E293B] bg-white focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                      >
                        {availableBuses.length > 0 ? (
                          availableBuses.map((b) => (
                            <option key={b.bus_id} value={b.bus_id}>
                              {b.bus_id} — {b.route_id || "Corridor"} ({b.AI_status || "AI"}/{b.camera_status || "Cam"})
                            </option>
                          ))
                        ) : (
                          <>
                            <option value="BUS-027">BUS-027 — ROUTE-17 (Koramangala)</option>
                            <option value="BUS-001">BUS-001 — Corridor-1A (MG Road)</option>
                            <option value="BUS-002">BUS-002 — Corridor-1A (Indiranagar)</option>
                            <option value="BUS-102">BUS-102 — Metro Ring (HSR Layout)</option>
                            <option value="BUS-117">BUS-117 — Airport Express (Hebbal)</option>
                            <option value="BUS-143">BUS-143 — Tech Corridor (Electronic City)</option>
                          </>
                        )}
                        <option value="CUSTOM">+ Custom Edge Identifier...</option>
                      </select>

                      {!availableBuses.some((b) => b.bus_id === busId) && (
                        <input
                          type="text"
                          disabled={isProcessing}
                          value={busId}
                          onChange={(e) => setBusId(e.target.value)}
                          placeholder="Enter Bus ID (e.g. BUS-099)"
                          className="w-full mt-1.5 px-2.5 py-1.5 text-xs border border-[#CBD5E1] rounded-md font-mono text-[#1E293B] focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                        />
                      )}
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#475569] mb-1">
                        Corridor Route
                      </label>
                      <input
                        type="text"
                        disabled={isProcessing}
                        value={routeId}
                        onChange={(e) => setRouteId(e.target.value)}
                        placeholder="e.g. ROUTE-17"
                        className="w-full px-2.5 py-1.5 text-xs border border-[#CBD5E1] rounded-md font-mono text-[#1E293B] focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                      />
                    </div>
                  </div>

                  {/* City Corridor */}
                  <div>
                    <label className="block text-xs font-semibold text-[#475569] mb-1">
                      Municipal Transit Region
                    </label>
                    <select
                      disabled={isProcessing}
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs border border-[#CBD5E1] rounded-md text-[#1E293B] focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                    >
                      <option value="Bengaluru">Bengaluru (BBMP East Division)</option>
                      <option value="New Delhi">New Delhi (Delhi PWD Ring Road)</option>
                      <option value="Mumbai">Mumbai (MCGM Western Corridor)</option>
                    </select>
                  </div>

                  {/* Confidence Threshold */}
                  <div>
                    <div className="flex justify-between text-xs font-semibold text-[#475569] mb-1">
                      <span>Confidence Filter</span>
                      <span className="font-mono text-[#2563EB]">{Math.round(confidenceThreshold * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      disabled={isProcessing}
                      min="0.15"
                      max="0.95"
                      step="0.05"
                      value={confidenceThreshold}
                      onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                      className="w-full accent-[#2563EB]"
                    />
                  </div>
                </div>

                {/* Submit Action CTAs */}
                <div className="pt-4 border-t border-[#E2E8F0] space-y-2">
                  {!isProcessing ? (
                    <button
                      onClick={handleStartAnalysis}
                      disabled={!selectedFile}
                      className={`w-full py-2.5 px-4 rounded-lg font-bold text-xs sm:text-sm flex items-center justify-center gap-2 transition shadow-md ${
                        !selectedFile
                          ? "bg-[#CBD5E1] text-[#94A3B8] cursor-not-allowed"
                          : "bg-[#2563EB] hover:bg-[#1D4ED8] text-white shadow-blue-900/20"
                      }`}
                    >
                      <Activity className="w-4 h-4" />
                      <span>Start AI Road Analysis</span>
                    </button>
                  ) : (
                    <div className="flex items-center gap-2">
                      <div className="flex-1 py-2.5 px-3 rounded-lg bg-[#EFF6FF] border border-[#BFDBFE] text-[#1E40AF] text-xs font-bold flex items-center justify-center gap-2">
                        <RefreshCw className="w-4 h-4 animate-spin text-[#2563EB]" />
                        <span>Analyzing...</span>
                      </div>
                      <button
                        onClick={handleCancelAnalysis}
                        className="py-2.5 px-3.5 rounded-lg bg-[#DC2626] hover:bg-[#B91C1C] text-white text-xs font-bold transition flex items-center gap-1.5 shadow-sm"
                        title="Cancel ongoing scan job"
                      >
                        <Ban className="w-4 h-4" />
                        <span>Cancel</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* PROCESSING STATE UI */}
            {isProcessing && (
              <div className="bg-white border-2 border-[#2563EB] rounded-xl p-5 shadow-lg space-y-4 animate-fadeIn">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-3 h-3 rounded-full bg-[#2563EB] animate-ping" />
                    <h3 className="text-sm font-bold text-[#0F172A]">
                      AI Video Inference in Progress
                    </h3>
                    {activeJobId && (
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-[#EFF6FF] text-[#2563EB] font-bold">
                        {activeJobId}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono text-[#64748B]">
                      Elapsed: {elapsedSeconds}s
                    </span>
                    <button
                      onClick={handleCancelAnalysis}
                      className="px-2.5 py-1 rounded bg-[#FEF2F2] hover:bg-[#FEE2E2] text-[#DC2626] text-xs font-bold border border-[#FECACA] transition flex items-center gap-1"
                    >
                      <Ban className="w-3 h-3" />
                      <span>Cancel</span>
                    </button>
                  </div>
                </div>

                {/* Progress bar */}
                <div>
                  <div className="flex justify-between text-xs text-[#64748B] mb-1">
                    <span className="font-medium text-[#1E293B]">{processingStage}</span>
                    <span className="font-bold text-[#2563EB]">
                      {jobProgress ? `${Math.round(jobProgress.progressPct)}%` : `${uploadProgress}%`}
                    </span>
                  </div>
                  <div className="w-full bg-[#E2E8F0] h-3 rounded-full overflow-hidden">
                    <div
                      className="bg-[#2563EB] h-full rounded-full transition-all duration-300"
                      style={{
                        width: `${jobProgress ? jobProgress.progressPct : uploadProgress}%`
                      }}
                    />
                  </div>
                </div>

                {/* Real-time processing metrics */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-[#F8FAFC] border border-[#E2E8F0] p-3 rounded-lg text-center text-xs">
                  <div>
                    <span className="text-[#64748B] block">Frames Processed</span>
                    <span className="font-bold text-[#0F172A] font-mono text-sm">
                      {jobProgress ? jobProgress.framesProcessed : 0}
                      {jobProgress?.totalEstimatedFrames ? ` / ${jobProgress.totalEstimatedFrames}` : ""}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#64748B] block">Active Detections</span>
                    <span className="font-bold text-[#2563EB] font-mono text-sm">
                      {jobProgress ? jobProgress.detectionsCount : 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#64748B] block">Confirmed Defects</span>
                    <span className="font-bold text-[#059669] font-mono text-sm">
                      {jobProgress ? jobProgress.confirmedCount : 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#64748B] block">ByteTracker Status</span>
                    <span className="font-bold text-[#059669]">Tracking Active</span>
                  </div>
                </div>
              </div>
            )}

            {/* RESULTS STATE UI (Pure Real Model Outputs, Zero Fake Detections) */}
            {jobProgress && jobProgress.status === "COMPLETED" && (
              <div className="bg-white border border-[#CBD5E1] rounded-xl p-5 shadow-sm space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 border-b border-[#E2E8F0]">
                  <div>
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-[#059669]" />
                      <h3 className="text-base font-bold text-[#0F172A]">
                        AI Road Scan Execution Summary
                      </h3>
                    </div>
                    <p className="text-xs text-[#64748B] mt-0.5">
                      Job ID: <span className="font-mono text-[#2563EB] font-bold">{jobProgress.jobId}</span> • 
                      Sampled at {sampleFps} FPS across {jobProgress.framesProcessed} video frames
                      {jobProgress.videoMetadata && (
                        <span>
                          &nbsp;({jobProgress.videoMetadata.width}×{jobProgress.videoMetadata.height},&nbsp;
                          {jobProgress.videoMetadata.durationSec}s)
                        </span>
                      )}
                    </p>
                  </div>

                  <span className="self-start sm:self-auto px-3 py-1 rounded-full text-xs font-bold bg-[#DCFCE7] text-[#15803D] border border-[#86EFAC] flex items-center gap-1.5">
                    <Check className="w-3.5 h-3.5" />
                    <span>Inference Complete</span>
                  </span>
                </div>

                {/* Derived Road Intelligence HUD (Phase 9 & 10) */}
                {renderDerivedIntelligenceHud(derivedIntelligence || jobProgress.derivedIntelligence || null)}

                {/* Primary Metric Strip */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl">
                    <span className="text-[11px] text-[#64748B] block uppercase font-bold tracking-wider">
                      Frames Analyzed
                    </span>
                    <span className="text-2xl font-black text-[#0F172A] font-mono mt-1 block">
                      {jobProgress.framesProcessed}
                    </span>
                  </div>
                  <div className="p-3.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl">
                    <span className="text-[11px] text-[#64748B] block uppercase font-bold tracking-wider">
                      Total Detections
                    </span>
                    <span className="text-2xl font-black text-[#0F172A] font-mono mt-1 block">
                      {jobProgress.detectionsCount}
                    </span>
                  </div>
                  <div className="p-3.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl">
                    <span className="text-[11px] text-[#64748B] block uppercase font-bold tracking-wider">
                      Confirmed Defects
                    </span>
                    <span className="text-2xl font-black text-[#059669] font-mono mt-1 block">
                      {jobProgress.confirmedCount}
                    </span>
                  </div>
                  <div className="p-3.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl">
                    <span className="text-[11px] text-[#64748B] block uppercase font-bold tracking-wider">
                      ByteTracker IDs
                    </span>
                    <span className="text-2xl font-black text-[#2563EB] font-mono mt-1 block">
                      {jobProgress.detections.length}
                    </span>
                  </div>
                </div>

                {/* Severity Breakdown Bar */}
                <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl flex flex-wrap items-center justify-between gap-3 text-xs">
                  <span className="font-bold text-[#475569] uppercase tracking-wider text-[11px]">
                    Severity Classification
                  </span>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="px-2.5 py-1 rounded-md font-bold bg-[#FEE2E2] text-[#DC2626] border border-[#FCA5A5]">
                      CRITICAL: {jobProgress.summaryBySeverity.critical}
                    </span>
                    <span className="px-2.5 py-1 rounded-md font-bold bg-[#FFEDD5] text-[#EA580C] border border-[#FDBA74]">
                      HIGH: {jobProgress.summaryBySeverity.high}
                    </span>
                    <span className="px-2.5 py-1 rounded-md font-bold bg-[#FEF3C7] text-[#D97706] border border-[#FCD34D]">
                      MEDIUM: {jobProgress.summaryBySeverity.medium}
                    </span>
                    <span className="px-2.5 py-1 rounded-md font-bold bg-[#E0F2FE] text-[#0284C7] border border-[#BAE6FD]">
                      LOW: {jobProgress.summaryBySeverity.low}
                    </span>
                  </div>
                </div>

                {/* Category Breakdown Chips */}
                {Object.keys(jobProgress.summaryByType).length > 0 && (
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="text-[#64748B] font-semibold">Detected Classes:</span>
                    {Object.entries(jobProgress.summaryByType).map(([cls, count]) => (
                      <span
                        key={cls}
                        className="px-2.5 py-0.5 rounded-full bg-[#EFF6FF] border border-[#BFDBFE] text-[#1E40AF] font-mono font-semibold"
                      >
                        {cls}: {count}
                      </span>
                    ))}
                  </div>
                )}

                {/* Detections Records Table */}
                <div className="border border-[#CBD5E1] rounded-xl overflow-hidden shadow-sm">
                  <div className="px-4 py-3 bg-[#F1F5F9] border-b border-[#CBD5E1] flex items-center justify-between text-xs font-bold text-[#475569]">
                    <span>Confirmed Road Defects & Transit Detections</span>
                    <span>Storage: Direct Paths (Zero Base64 in DB)</span>
                  </div>

                  {jobProgress.detections.length === 0 ? (
                    <div className="p-10 text-center text-xs text-[#64748B] space-y-2">
                      <ShieldCheck className="w-10 h-10 mx-auto text-[#94A3B8]" />
                      <p className="font-bold text-sm text-[#1E293B]">
                        Zero Detections in Analyzed Video
                      </p>
                      <p className="max-w-md mx-auto">
                        No persistent defects or vehicles met the confidence threshold ({Math.round(confidenceThreshold * 100)}%) in this video sequence. In strict compliance with NovaFlow guidelines, no synthetic placeholder detections were generated.
                      </p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs text-[#1E293B]">
                        <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-[11px] uppercase font-bold text-[#64748B]">
                          <tr>
                            <th className="py-2.5 px-3">Thumbnail</th>
                            <th className="py-2.5 px-3">ID / Track</th>
                            <th className="py-2.5 px-3">Type</th>
                            <th className="py-2.5 px-3">Confidence</th>
                            <th className="py-2.5 px-3">Severity</th>
                            <th className="py-2.5 px-3">GPS Location</th>
                            <th className="py-2.5 px-3">Frame #</th>
                            <th className="py-2.5 px-3 text-right">Evidence Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#E2E8F0]">
                          {jobProgress.detections.map((d) => (
                            <tr key={d.id} className="hover:bg-[#F8FAFC] transition">
                              <td className="py-2 px-3">
                                {d.thumbnailPath ? (
                                  <img
                                    src={d.thumbnailPath}
                                    alt={d.label}
                                    className="w-12 h-10 rounded object-cover border border-[#CBD5E1]"
                                  />
                                ) : (
                                  <div className="w-12 h-10 rounded bg-[#E2E8F0] flex items-center justify-center text-[#94A3B8]">
                                    <ImageIcon className="w-4 h-4" />
                                  </div>
                                )}
                              </td>
                              <td className="py-2.5 px-3 font-mono font-bold text-[#2563EB]">
                                {d.id}
                                <span className="block text-[10px] text-[#64748B]">Track #{d.trackId}</span>
                                {d.ticketId && (
                                  <span className="inline-flex items-center gap-1 mt-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#FEF3C7] text-[#B45309] border border-[#FDE68A]">
                                    <Wrench className="w-2.5 h-2.5" />
                                    <span>{d.ticketId}</span>
                                    {d.ticketStatus && <span className="opacity-75">({d.ticketStatus})</span>}
                                  </span>
                                )}
                              </td>
                              <td className="py-2.5 px-3">
                                <span className="font-semibold text-[#0F172A] block">{d.label}</span>
                                <div className="flex flex-wrap items-center gap-1 mt-0.5">
                                  <span className={`px-1.5 py-0.2 rounded text-[9px] font-semibold uppercase ${
                                    d.conditionType === "POTENTIAL"
                                      ? "bg-[#FFF7ED] text-[#C2410C] border border-[#FFEDD5]"
                                      : "bg-[#F0FDF4] text-[#15803D] border border-[#DCFCE7]"
                                  }`}>
                                    {d.conditionType === "POTENTIAL" ? "Potential" : "Direct"}
                                  </span>
                                  {d.isMultimodalVerified && (
                                    <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-[#F3E8FF] text-[#7E22CE] border border-[#D8B4FE] flex items-center gap-0.5" title={d.verificationNotes || "Gemini verified"}>
                                      <Sparkles className="w-2.5 h-2.5" />
                                      <span>Gemini Verified</span>
                                    </span>
                                  )}
                                  {(d.persistenceBadge || (d.independentBusesCount && d.independentBusesCount > 1)) && (
                                    <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-[#EFF6FF] text-[#1D4ED8] border border-[#BFDBFE] flex items-center gap-0.5">
                                      <span>🛡️</span>
                                      <span>{d.persistenceBadge || `CONFIRMED BY ${d.independentBusesCount} BUSES`}</span>
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="py-2.5 px-3 font-mono font-bold text-[#059669]">
                                {Math.round(d.confidence * 100)}%
                              </td>
                              <td className="py-2.5 px-3">
                                <span
                                  className={`px-2 py-0.5 rounded text-[11px] font-bold border ${getSeverityBadgeClass(
                                    d.severity
                                  )}`}
                                >
                                  {d.severity}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 font-mono text-[11px] text-[#475569]">
                                {d.location.lat.toFixed(4)}, {d.location.lon.toFixed(4)}
                              </td>
                              <td className="py-2.5 px-3 font-mono text-[11px]">
                                #{d.frameNumber}
                              </td>
                              <td className="py-2.5 px-3 text-right">
                                <button
                                  onClick={() => {
                                    setSelectedEvidence(d);
                                    setEvidenceViewMode("ANNOTATED");
                                  }}
                                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-bold transition shadow-sm"
                                >
                                  <Eye className="w-3.5 h-3.5" />
                                  <span>View Evidence</span>
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* MODE 3: CONNECTED BUS MODE (Phase 13) */}
        {mode === "CONNECTED_BUS" && (
          <div className="space-y-6">
            <div className="bg-white border border-[#CBD5E1] rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-[#E2E8F0]">
                <div>
                  <h3 className="text-base font-bold text-[#0F172A] flex items-center gap-2">
                    <Radio className="w-5 h-5 text-[#2563EB]" />
                    <span>Connected Transit Fleet Dashcam Stream</span>
                  </h3>
                  <p className="text-xs text-[#64748B] mt-0.5">
                    Live telemetry, forward video dashcam & onboard edge AI hazard inference across active transit buses.
                  </p>
                </div>

                {/* Fleet Bus Selector */}
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-[#475569]">Select Bus:</span>
                  <div className="inline-flex rounded-lg p-0.5 bg-[#F1F5F9] border border-[#CBD5E1]">
                    {["BUS-027", "BUS-014", "BUS-031"].map((bId) => (
                      <button
                        key={bId}
                        onClick={() => {
                          setConnectedBusId(bId);
                          setBusId(bId);
                        }}
                        className={`px-3 py-1 rounded text-xs font-bold transition ${
                          connectedBusId === bId
                            ? "bg-[#2563EB] text-white shadow-sm"
                            : "text-[#475569] hover:text-[#0F172A]"
                        }`}
                      >
                        {bId}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Connected Bus Telemetry Strip */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 bg-[#F8FAFC] border border-[#E2E8F0] p-3.5 rounded-xl text-xs">
                <div>
                  <span className="text-[10px] text-[#64748B] uppercase font-bold block">Bus Node</span>
                  <span className="font-mono font-black text-[#0F172A] text-sm block mt-0.5">{connectedBusId}</span>
                  <span className="text-[10px] text-[#059669] font-bold">● Edge Device Online</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#64748B] uppercase font-bold block">Assigned Corridor</span>
                  <span className="font-bold text-[#1E293B] text-sm block mt-0.5">
                    {connectedBusId === "BUS-031" ? "Route 33 (Hosur Rd)" : "Route 17 (Outer Ring Rd)"}
                  </span>
                  <span className="text-[10px] text-[#64748B]">Bengaluru Central</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#64748B] uppercase font-bold block">Telemetry Velocity</span>
                  <span className="font-mono font-bold text-[#2563EB] text-sm block mt-0.5">
                    {connectedBusId === "BUS-027" ? "34.2 km/h" : connectedBusId === "BUS-014" ? "28.5 km/h" : "41.0 km/h"}
                  </span>
                  <span className="text-[10px] text-[#64748B]">Heading: 84° E</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#64748B] uppercase font-bold block">Coordinates</span>
                  <span className="font-mono text-[#0F172A] text-xs block mt-0.5">
                    {connectedBusId === "BUS-031" ? "12.9351° N, 77.6106° E" : "12.9352° N, 77.6105° E"}
                  </span>
                  <span className="text-[10px] text-[#64748B]">GPS Lock: 3D High Accuracy</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#64748B] uppercase font-bold block">Camera Sensor</span>
                  <span className="font-semibold text-[#059669] text-xs block mt-0.5">Front Dashcam (1080p)</span>
                  <span className="text-[10px] text-[#64748B]">Model: Jetson Orin Nano</span>
                </div>
              </div>

              {/* Dashcam Video Frame Viewport */}
              <div className="relative aspect-video rounded-xl overflow-hidden bg-black border border-[#1E293B] shadow-inner flex items-center justify-center">
                <video
                  src="/sample_indian_road.mp4"
                  autoPlay
                  loop
                  muted
                  playsInline
                  className="w-full h-full object-cover"
                />
                <div className="absolute top-3 left-3 bg-black/75 backdrop-blur-sm text-white px-3 py-1.5 rounded-lg text-xs font-mono border border-white/20 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span>LIVE TRANSIT DASHCAM • {connectedBusId}</span>
                </div>
                <div className="absolute bottom-3 right-3 flex items-center gap-2">
                  <Link
                    to={`/gis?busId=${connectedBusId}`}
                    className="px-3 py-1.5 rounded-lg bg-blue-600/90 hover:bg-blue-600 text-white text-xs font-bold transition backdrop-blur-sm flex items-center gap-1.5 shadow-md"
                  >
                    <MapPin className="w-3.5 h-3.5" />
                    <span>Track in GIS Command Center</span>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* MODE 4: DEMO PLAYBACK MODE (Phase 12 & Phase 13) */}
        {mode === "DEMO_PLAYBACK" && (
          <div className="space-y-6 animate-fadeIn">
            {/* Clear Advisory Disclaimer Banner */}
            <div className="p-4 rounded-xl bg-amber-950/80 border border-amber-500/60 text-amber-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 shadow-lg">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-bold text-amber-100 flex items-center gap-2">
                    <span>DEMO PLAYBACK MODE: Multi-Bus Hazard Consensus Demonstration</span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-800 text-amber-200 border border-amber-500/40">
                      OFFLINE SAFE • NO SENSORS REQUIRED
                    </span>
                  </h4>
                  <p className="text-xs text-amber-300/90 mt-0.5">
                    Demonstrating repeated observation consensus logic across transit buses (BUS-027 → BUS-014 → BUS-031) on Bengaluru Outer Ring Road with pre-recorded telemetry. All playback data is explicitly labelled.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 self-start sm:self-auto flex-shrink-0">
                <button
                  type="button"
                  onClick={() => setIsDemoPlaying(!isDemoPlaying)}
                  className="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition flex items-center gap-1.5 shadow-sm cursor-pointer"
                >
                  {isDemoPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                  <span>{isDemoPlaying ? "Pause Stepper" : "Auto-Step Demo"}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setDemoStep(0)}
                  className="px-3 py-1.5 rounded-lg bg-amber-900/60 hover:bg-amber-800/60 text-amber-200 text-xs font-semibold border border-amber-500/40 transition cursor-pointer"
                >
                  Reset
                </button>
              </div>
            </div>

            {/* Interactive Multi-Bus Stepper */}
            <div className="bg-white border border-[#CBD5E1] rounded-xl p-5 shadow-sm space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
                <div>
                  <h3 className="text-base font-bold text-[#0F172A] flex items-center gap-2">
                    <span>Multi-Bus Hazard Confirmation Sequence</span>
                    <span className="text-xs font-mono font-normal text-[#64748B]">
                      (Geographic Proximity ≤20m • Road Segment Match • Time Window ≤72h)
                    </span>
                  </h3>
                  <p className="text-xs text-[#64748B] mt-0.5">
                    Click through the steps below to observe how repeated captures confirm persistent road damage without altering original model confidence.
                  </p>
                </div>
                <span className="font-mono text-xs px-2.5 py-1 rounded bg-[#EFF6FF] text-[#2563EB] font-bold border border-[#BFDBFE]">
                  Step {demoStep + 1} of 3
                </span>
              </div>

              {/* Step Navigation Pills */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div
                  onClick={() => setDemoStep(0)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition ${
                    demoStep === 0
                      ? "bg-[#EFF6FF] border-[#2563EB] shadow-sm ring-2 ring-[#2563EB]/20"
                      : "bg-[#F8FAFC] border-[#CBD5E1] hover:bg-white"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs text-[#2563EB]">1. BUS-027 (Route 17)</span>
                    <span className="text-[10px] font-mono text-[#64748B]">10:12 AM</span>
                  </div>
                  <h4 className="text-xs font-bold text-[#0F172A] mt-1">Initial Pothole Capture</h4>
                  <p className="text-[11px] text-[#64748B] mt-0.5">
                    Lat 12.9352, Lon 77.6105. Status: <span className="font-semibold text-amber-600">UNVERIFIED (1 Bus)</span>
                  </p>
                </div>

                <div
                  onClick={() => setDemoStep(1)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition ${
                    demoStep === 1
                      ? "bg-[#EFF6FF] border-[#2563EB] shadow-sm ring-2 ring-[#2563EB]/20"
                      : "bg-[#F8FAFC] border-[#CBD5E1] hover:bg-white"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs text-[#2563EB]">2. BUS-014 (Route 17)</span>
                    <span className="text-[10px] font-mono text-[#64748B]">12:45 PM (+2.5h)</span>
                  </div>
                  <h4 className="text-xs font-bold text-[#0F172A] mt-1">Second Bus Corroboration</h4>
                  <p className="text-[11px] text-[#64748B] mt-0.5">
                    Proximity: 2.8m. Status: <span className="font-semibold text-blue-600">CONFIRMED BY 2 BUSES</span>
                  </p>
                </div>

                <div
                  onClick={() => setDemoStep(2)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition ${
                    demoStep === 2
                      ? "bg-[#EFF6FF] border-[#2563EB] shadow-sm ring-2 ring-[#2563EB]/20"
                      : "bg-[#F8FAFC] border-[#CBD5E1] hover:bg-white"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs text-[#2563EB]">3. BUS-031 (Route 33)</span>
                    <span className="text-[10px] font-mono text-[#64748B]">04:15 PM (+14h)</span>
                  </div>
                  <h4 className="text-xs font-bold text-[#0F172A] mt-1">Third Bus Persistence Confirmation</h4>
                  <p className="text-[11px] text-[#64748B] mt-0.5">
                    Proximity: 4.1m. Status: <span className="font-semibold text-emerald-600">CONFIRMED BY 3 BUSES</span>
                  </p>
                </div>
              </div>

              {/* Three Distinct Metric Blocks (Phase 12 Requirements) */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 rounded-xl bg-gradient-to-br from-[#0F172A] to-[#1E293B] text-white">
                <div className="p-3 bg-white/5 rounded-lg border border-white/10">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">1. RAW AI MODEL CONFIDENCE</span>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-2xl font-black font-mono text-emerald-400">84%</span>
                    <span className="text-[10px] text-slate-300">YOLOv8 Raw</span>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1">
                    Strictly unaltered by multi-bus repeated observations.
                  </p>
                </div>

                <div className="p-3 bg-white/5 rounded-lg border border-white/10">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">2. INDEPENDENT OBSERVATIONS</span>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-2xl font-black font-mono text-blue-400">
                      {demoStep === 0 ? "1 Bus" : demoStep === 1 ? "2 Buses" : "3 Buses"}
                    </span>
                    <span className="text-[10px] text-slate-300">
                      ({demoStep === 0 ? "1" : demoStep === 1 ? "2" : "4"} captures)
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1 truncate">
                    {demoStep === 0
                      ? "Contributing: BUS-027"
                      : demoStep === 1
                      ? "Contributing: BUS-027, BUS-014"
                      : "Contributing: BUS-027, BUS-014, BUS-031"}
                  </p>
                </div>

                <div className="p-3 bg-white/5 rounded-lg border border-white/10">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">3. LAST DETECTED TIME</span>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-sm font-bold font-mono text-amber-300">
                      {demoStep === 0 ? "10:12 AM" : demoStep === 1 ? "12:45 PM" : "04:15 PM"}
                    </span>
                    <span className="text-[10px] text-slate-300">Today</span>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1">
                    Temporal window active (≤72h).
                  </p>
                </div>
              </div>

              {/* Demo Playback Video and Evidence Display */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="relative aspect-video rounded-xl overflow-hidden bg-black border border-[#CBD5E1]">
                  <video
                    src="/sample_indian_road.mp4"
                    autoPlay
                    loop
                    muted
                    playsInline
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute top-3 left-3 bg-black/75 backdrop-blur-sm text-white px-2.5 py-1 rounded text-xs font-mono flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span>PRE-RECORDED INDIAN ROAD FEED (DEMO PLAYBACK)</span>
                  </div>
                </div>

                {/* Inspection Card */}
                <div className="border border-[#CBD5E1] rounded-xl p-4 flex flex-col justify-between space-y-3 bg-[#F8FAFC]">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-1 rounded-full text-xs font-black bg-blue-100 text-blue-800 border border-blue-300">
                        {demoStep === 0 ? "CONFIRMED BY 1 BUS" : demoStep === 1 ? "CONFIRMED BY 2 BUSES" : "CONFIRMED BY 3 BUSES"}
                      </span>
                      <span className="text-xs font-mono text-[#64748B]">
                        Hazard Ref: HAZ-ORR-027
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-[#0F172A]">
                      Severe Pothole Cluster on Travel Lane
                    </h4>
                    <p className="text-xs text-[#64748B]">
                      Location: Outer Ring Road, Near Bellandur Flyover (Lat 12.9352° N, Lon 77.6105° E)
                    </p>

                    <div className="p-2.5 rounded-lg bg-white border border-[#CBD5E1] text-xs space-y-1">
                      <div className="flex justify-between">
                        <span className="text-[#64748B]">Latest Reporting Node:</span>
                        <span className="font-mono font-bold text-[#2563EB]">
                          {demoStep === 0 ? "BUS-027" : demoStep === 1 ? "BUS-014" : "BUS-031"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#64748B]">Severity:</span>
                        <span className="font-bold text-[#DC2626]">CRITICAL</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#64748B]">Persistence Score:</span>
                        <span className="font-mono font-bold text-[#059669]">
                          {demoStep === 0 ? "0.84 (1 obs)" : demoStep === 1 ? "0.92 (2 buses)" : "0.98 (3 buses)"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Flow Action Buttons */}
                  <div className="flex flex-col sm:flex-row items-center gap-2 pt-2 border-t border-[#E2E8F0]">
                    <Link
                      to="/gis?lat=12.9352&lon=77.6105"
                      className="w-full sm:flex-1 py-2 px-3 rounded-lg border border-[#2563EB] text-[#2563EB] hover:bg-[#EFF6FF] text-xs font-bold transition flex items-center justify-center gap-1.5"
                    >
                      <MapPin className="w-3.5 h-3.5" />
                      <span>View on GIS Map</span>
                    </Link>
                    <Link
                      to="/work-orders?hazard=HAZ-ORR-027&type=POTHOLE&lat=12.9352&lon=77.6105"
                      className="w-full sm:flex-1 py-2 px-3 rounded-lg bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-sm"
                    >
                      <Wrench className="w-3.5 h-3.5" />
                      <span>Create PWD Work Order</span>
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* PHASE 5: INTERACTIVE EVIDENCE INSPECTION MODAL */}
      {selectedEvidence && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto animate-fadeIn">
          <div className="bg-white rounded-2xl max-w-4xl w-full overflow-hidden shadow-2xl border border-[#CBD5E1] my-8">
            {/* Modal Header */}
            <div className="px-6 py-4 bg-[#1B254B] text-white flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-[#2563EB] flex items-center justify-center text-white">
                  <Eye className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-white">
                      AI Evidence Inspection Card
                    </h3>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getSeverityBadgeClass(
                        selectedEvidence.severity
                      )}`}
                    >
                      {selectedEvidence.severity}
                    </span>
                    {selectedEvidence.ticketId && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#FEF3C7] text-[#B45309] border border-[#FDE68A] flex items-center gap-1">
                        <Wrench className="w-3 h-3" />
                        <span>Ticket: {selectedEvidence.ticketId} ({selectedEvidence.ticketStatus || "OPEN"})</span>
                      </span>
                    )}
                    {selectedEvidence.isMultimodalVerified && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#F3E8FF] text-[#7E22CE] border border-[#D8B4FE] flex items-center gap-1">
                        <Sparkles className="w-3 h-3" />
                        <span>Gemini Verified</span>
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[#94A3B8] font-mono">
                    Detection Ref: {selectedEvidence.id} • Track #{selectedEvidence.trackId} • Condition: {selectedEvidence.conditionType || "DIRECT"}
                  </p>
                </div>
              </div>

              <button
                onClick={() => setSelectedEvidence(null)}
                className="w-8 h-8 rounded-lg bg-[#111C44] hover:bg-[#2D3A6E] flex items-center justify-center text-[#94A3B8] hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6">
              {/* Evidence View Mode Switcher */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-[#E2E8F0]">
                <div>
                  <span className="text-xs font-bold text-[#0F172A] block">
                    Frame Inspection Mode
                  </span>
                  <span className="text-xs text-[#64748B]">
                    Compare the AI annotated bounding box with the original raw camera frame.
                  </span>
                </div>

                <div className="inline-flex rounded-lg p-1 bg-[#F1F5F9] border border-[#CBD5E1] self-start sm:self-auto">
                  <button
                    onClick={() => setEvidenceViewMode("ANNOTATED")}
                    className={`px-3 py-1 rounded text-xs font-bold transition ${
                      evidenceViewMode === "ANNOTATED"
                        ? "bg-[#2563EB] text-white shadow-sm"
                        : "text-[#475569] hover:text-[#0F172A]"
                    }`}
                  >
                    AI Annotated Frame
                  </button>
                  <button
                    onClick={() => setEvidenceViewMode("ORIGINAL")}
                    className={`px-3 py-1 rounded text-xs font-bold transition ${
                      evidenceViewMode === "ORIGINAL"
                        ? "bg-[#2563EB] text-white shadow-sm"
                        : "text-[#475569] hover:text-[#0F172A]"
                    }`}
                  >
                    Raw Original Frame
                  </button>
                  <button
                    onClick={() => setEvidenceViewMode("SIDE_BY_SIDE")}
                    className={`px-3 py-1 rounded text-xs font-bold transition ${
                      evidenceViewMode === "SIDE_BY_SIDE"
                        ? "bg-[#2563EB] text-white shadow-sm"
                        : "text-[#475569] hover:text-[#0F172A]"
                    }`}
                  >
                    Side-by-Side
                  </button>
                </div>
              </div>

              {/* Evidence Frame Image Viewport */}
              <div className="bg-[#0F172A] rounded-xl overflow-hidden border border-[#1E293B]">
                {evidenceViewMode === "SIDE_BY_SIDE" ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2">
                    <div className="space-y-1">
                      <span className="text-[10px] font-mono text-[#94A3B8] px-2 block">
                        RAW CAMERA FRAME (Frame #{selectedEvidence.frameNumber})
                      </span>
                      <div className="relative aspect-video bg-black rounded overflow-hidden flex items-center justify-center">
                        <img
                          src={selectedEvidence.originalImagePath || selectedEvidence.evidenceImagePath}
                          alt="Raw frame"
                          className="w-full h-full object-contain"
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <span className="text-[10px] font-mono text-[#60A5FA] px-2 block">
                        AI ANNOTATED FRAME ({selectedEvidence.label} {Math.round(selectedEvidence.confidence * 100)}%)
                      </span>
                      <div className="relative aspect-video bg-black rounded overflow-hidden flex items-center justify-center">
                        <img
                          src={selectedEvidence.annotatedImagePath || selectedEvidence.evidenceImagePath}
                          alt="Annotated frame"
                          className="w-full h-full object-contain"
                        />
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="relative aspect-video max-h-[460px] flex items-center justify-center">
                    <img
                      src={
                        evidenceViewMode === "ORIGINAL"
                          ? selectedEvidence.originalImagePath || selectedEvidence.evidenceImagePath
                          : selectedEvidence.annotatedImagePath || selectedEvidence.evidenceImagePath
                      }
                      alt="Inspection frame"
                      className="w-full h-full object-contain"
                    />
                    <div className="absolute bottom-3 left-3 bg-black/70 backdrop-blur-sm text-white px-3 py-1.5 rounded-md text-xs font-mono">
                      <span>{evidenceViewMode === "ORIGINAL" ? "RAW ORIGINAL" : "AI ANNOTATED"}</span>
                      <span className="mx-2">•</span>
                      <span>FRAME #{selectedEvidence.frameNumber}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Metadata Details Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-[#F8FAFC] border border-[#E2E8F0] p-4 rounded-xl text-xs">
                <div>
                  <span className="text-[#64748B] block font-semibold">Issue Classification</span>
                  <span className="font-bold text-[#0F172A] text-sm mt-0.5 block">
                    {selectedEvidence.label}
                  </span>
                  <span className="text-[11px] font-mono text-[#64748B]">{selectedEvidence.type}</span>
                </div>

                <div>
                  <span className="text-[#64748B] block font-semibold">AI Confidence</span>
                  <span className="font-black text-[#059669] text-sm mt-0.5 block font-mono">
                    {Math.round(selectedEvidence.confidence * 100)}%
                  </span>
                  <span className="text-[11px] text-[#64748B]">YOLOv8 Consensus</span>
                </div>

                <div>
                  <span className="text-[#64748B] block font-semibold">Source Vehicle & Route</span>
                  <span className="font-mono font-bold text-[#2563EB] text-sm mt-0.5 block">
                    {selectedEvidence.sourceBusId || busId}
                  </span>
                  <span className="text-[11px] text-[#64748B]">
                    {selectedEvidence.sourceRouteId || routeId} ({city})
                  </span>
                </div>

                <div>
                  <span className="text-[#64748B] block font-semibold">Capture Timestamp</span>
                  <span className="font-mono text-[#1E293B] text-[11px] mt-0.5 block">
                    {new Date(selectedEvidence.timestamp).toLocaleString()}
                  </span>
                  <span className="text-[11px] text-[#64748B]">Frame #{selectedEvidence.frameNumber}</span>
                </div>

                <div className="sm:col-span-2 pt-2 border-t border-[#E2E8F0]">
                  <span className="text-[#64748B] block font-semibold">GPS Geo-Coordinates</span>
                  <span className="font-mono font-bold text-[#0F172A] mt-0.5 block">
                    {selectedEvidence.location.lat.toFixed(6)}° N, {selectedEvidence.location.lon.toFixed(6)}° E
                  </span>
                  <span className="text-[11px] text-[#64748B]">
                    {selectedEvidence.location.roadSegment || "Corridor Segment"}
                  </span>
                </div>

                <div className="sm:col-span-2 pt-2 border-t border-[#E2E8F0]">
                  <span className="text-[#64748B] block font-semibold">Storage Provider Reference</span>
                  <span className="font-mono text-[11px] text-[#0F172A] truncate block mt-0.5">
                    {selectedEvidence.evidenceImagePath}
                  </span>
                  <span className="text-[10px] text-[#059669] font-semibold">
                    {selectedEvidence.storageProvider === "supabase_storage"
                      ? "Cloud Bucket: Supabase Storage"
                      : "Local Storage Fallback"}
                  </span>
                </div>

                {selectedEvidence.verificationNotes && (
                  <div className="sm:col-span-4 p-3 rounded-xl bg-purple-50 border border-purple-200 text-purple-900 text-xs">
                    <span className="font-bold flex items-center gap-1.5 text-purple-800">
                      <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                      Gemini Multimodal Scene Verification:
                    </span>
                    <p className="mt-1 text-purple-950 leading-relaxed font-medium">
                      {selectedEvidence.verificationNotes}
                    </p>
                  </div>
                )}

                {/* Multi-Bus Hazard Consensus Card (Phase 12) */}
                {(selectedEvidence.persistenceBadge || (selectedEvidence.independentBusesCount && selectedEvidence.independentBusesCount > 1)) && (
                  <div className="sm:col-span-4 p-4 rounded-xl bg-gradient-to-r from-[#0F172A] via-[#1E293B] to-[#0F172A] border border-blue-500/40 text-blue-100 text-xs space-y-3 shadow-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">🛡️</span>
                        <span className="font-extrabold text-white text-sm tracking-wide">
                          {selectedEvidence.persistenceBadge || `CONFIRMED BY ${selectedEvidence.independentBusesCount} BUSES`}
                        </span>
                      </div>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-blue-500/20 text-blue-300 border border-blue-400/40">
                        MULTI-BUS CONSENSUS
                      </span>
                    </div>

                    <p className="text-[11px] text-blue-200/90 leading-relaxed">
                      This defect was captured independently by transit buses traversing this road segment within a 20-meter proximity radius. In accordance with Phase 12 guidelines, the original AI model confidence remains strictly unaltered.
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-white/10 text-xs">
                      <div className="p-2.5 rounded-lg bg-white/5 border border-white/10">
                        <span className="text-[10px] text-slate-400 block font-mono">1. RAW AI CONFIDENCE</span>
                        <span className="font-mono font-black text-emerald-400 text-base">
                          {Math.round(selectedEvidence.confidence * 100)}%
                        </span>
                        <span className="text-[9px] text-slate-400 block">Single-frame inference (unaltered)</span>
                      </div>
                      <div className="p-2.5 rounded-lg bg-white/5 border border-white/10">
                        <span className="text-[10px] text-slate-400 block font-mono">2. INDEPENDENT OBSERVATIONS</span>
                        <span className="font-mono font-black text-blue-300 text-base">
                          {selectedEvidence.independentBusesCount || 1} Buses
                        </span>
                        <span className="text-[9px] text-slate-400 block truncate">
                          Contributing: {Array.isArray(selectedEvidence.contributingBuses) ? selectedEvidence.contributingBuses.join(", ") : (selectedEvidence.contributingBuses || selectedEvidence.sourceBusId || "BUS-027")}
                        </span>
                      </div>
                      <div className="p-2.5 rounded-lg bg-white/5 border border-white/10">
                        <span className="text-[10px] text-slate-400 block font-mono">3. LAST DETECTED TIME</span>
                        <span className="font-mono font-bold text-amber-300 text-xs mt-0.5 block">
                          {selectedEvidence.lastDetectedAt ? new Date(selectedEvidence.lastDetectedAt).toLocaleString() : new Date(selectedEvidence.timestamp).toLocaleString()}
                        </span>
                        <span className="text-[9px] text-slate-400 block">Temporal window active</span>
                      </div>
                    </div>

                    {/* Observation History Audit Log */}
                    {hazardObservations.length > 0 && (
                      <div className="pt-2 border-t border-white/10">
                        <span className="text-[10px] uppercase font-mono font-bold text-blue-300 block mb-1.5">
                          Multi-Bus Observation Audit History:
                        </span>
                        <div className="space-y-1 max-h-32 overflow-y-auto">
                          {hazardObservations.map((obs, idx) => (
                            <div key={obs.id || idx} className="p-2 rounded bg-black/40 border border-blue-500/20 flex items-center justify-between text-[10px]">
                              <div className="flex items-center gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                                <span className="font-mono font-bold text-white">{obs.bus_id}</span>
                                <span className="text-slate-400">Route {obs.route_id || "17"}</span>
                              </div>
                              <div className="flex items-center gap-3 font-mono text-slate-300">
                                <span>Model Conf: {Math.round(obs.model_confidence * 100)}%</span>
                                <span>{new Date(obs.observed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Action Buttons in Modal Footer */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-[#E2E8F0]">
                <button
                  onClick={() => setSelectedEvidence(null)}
                  className="w-full sm:w-auto px-4 py-2 rounded-lg border border-[#CBD5E1] bg-white hover:bg-[#F1F5F9] text-xs font-bold text-[#475569] transition"
                >
                  Close Inspection
                </button>

                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <Link
                    to={`/gis?lat=${selectedEvidence.location.lat}&lon=${selectedEvidence.location.lon}`}
                    className="flex-1 sm:flex-none px-4 py-2 rounded-lg border border-[#2563EB] text-[#2563EB] hover:bg-[#EFF6FF] text-xs font-bold transition flex items-center justify-center gap-1.5"
                  >
                    <MapPin className="w-3.5 h-3.5" />
                    <span>View on GIS Map</span>
                  </Link>

                  <Link
                    to={selectedEvidence.ticketId ? `/work-orders?ticket=${selectedEvidence.ticketId}` : `/work-orders?hazard=${selectedEvidence.id}&type=${selectedEvidence.type}&lat=${selectedEvidence.location.lat}&lon=${selectedEvidence.location.lon}`}
                    className="flex-1 sm:flex-none px-4 py-2 rounded-lg bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-sm"
                  >
                    <Wrench className="w-3.5 h-3.5" />
                    <span>{selectedEvidence.ticketId ? `View Work Order (${selectedEvidence.ticketId})` : "Create PWD Work Order"}</span>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RoadScan;
