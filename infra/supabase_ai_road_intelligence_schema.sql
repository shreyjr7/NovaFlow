-- ==============================================================================
-- NovaFlow — AI Road Intelligence Supabase Data Model & Storage Configuration
-- Version: 3.0 (Bharat Electronics Limited • Smart Automation)
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================================
-- 2. Scan Jobs Table (Offline Video & Live Stream Job Lifecycle)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS scan_jobs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type                VARCHAR(32) NOT NULL DEFAULT 'OFFLINE_VIDEO', -- 'OFFLINE_VIDEO', 'LIVE_STREAM'
    status                  VARCHAR(32) NOT NULL DEFAULT 'QUEUED',        -- 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED'
    bus_id                  VARCHAR(64) NOT NULL DEFAULT 'BUS-027',
    route_id                VARCHAR(64) NOT NULL DEFAULT 'ROUTE-17',
    city                    VARCHAR(64) NOT NULL DEFAULT 'Bengaluru',
    video_file_name         VARCHAR(255),
    video_storage_path      TEXT,                                          -- Path in 'uploaded-videos' bucket
    video_duration_sec      NUMERIC(10, 2) DEFAULT 0.0,
    sample_fps              NUMERIC(4, 1) DEFAULT 1.0,                    -- 1.0, 2.0, or 5.0 FPS
    confidence_threshold    NUMERIC(4, 2) DEFAULT 0.70,                   -- 0.50 to 0.95
    total_frames            INTEGER DEFAULT 0,
    processed_frames        INTEGER DEFAULT 0,
    detections_count        INTEGER DEFAULT 0,
    confirmed_count         INTEGER DEFAULT 0,
    progress_pct            NUMERIC(5, 2) DEFAULT 0.0,
    error_message           TEXT,
    metadata_json           JSONB DEFAULT '{}'::jsonb,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at              TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_scan_jobs_status ON scan_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scan_jobs_bus_id ON scan_jobs(bus_id);
CREATE INDEX IF NOT EXISTS idx_scan_jobs_city ON scan_jobs(city);
CREATE INDEX IF NOT EXISTS idx_scan_jobs_created_at ON scan_jobs(created_at DESC);


-- ==============================================================================
-- 3. Road Detections Table (Computer Vision Detections + ByteTracker IDs)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS road_detections (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id                 UUID REFERENCES scan_jobs(id) ON DELETE CASCADE,
    bus_id                  VARCHAR(64) NOT NULL DEFAULT 'BUS-027',
    type                    VARCHAR(64) NOT NULL,                         -- 'POTHOLE', 'DAMAGED_ROAD', 'WATERLOGGING', 'ROAD_DEBRIS', 'MISSING_SIGN', 'MISSING_DIVIDER', 'DAMAGED_ZEBRA', 'VEHICLE', 'PEDESTRIAN'
    confidence              NUMERIC(5, 4) NOT NULL,                       -- 0.0000 to 1.0000
    severity                VARCHAR(32) NOT NULL DEFAULT 'MEDIUM',        -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    latitude                DOUBLE PRECISION NOT NULL,
    longitude               DOUBLE PRECISION NOT NULL,
    location_accuracy       NUMERIC(6, 2) DEFAULT 2.50,                   -- In meters
    timestamp               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    frame_number            INTEGER NOT NULL DEFAULT 0,
    track_id                INTEGER NOT NULL DEFAULT 0,                   -- ByteTracker unique persistent ID across consecutive frames
    bounding_box            JSONB,                                        -- {"x1": 0.12, "y1": 0.34, "x2": 0.56, "y2": 0.78}
    segmentation            JSONB,                                        -- Optional polygon coordinate list [{"x":..., "y":...}]
    evidence_path           TEXT,                                         -- Storage path in 'evidence-frames' bucket
    annotated_evidence_path TEXT,                                         -- Storage path in 'annotated-frames' bucket
    thumbnail_path          TEXT,                                         -- Storage path in 'thumbnails' bucket
    source_model            VARCHAR(128) NOT NULL DEFAULT 'YOLOv8s-RDD2022',
    status                  VARCHAR(32) NOT NULL DEFAULT 'DETECTED',      -- 'DETECTED', 'CONFIRMED', 'DISMISSED', 'TICKET_CREATED'
    verification_notes      TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_road_detections_scan_id ON road_detections(scan_id);
CREATE INDEX IF NOT EXISTS idx_road_detections_bus_id ON road_detections(bus_id);
CREATE INDEX IF NOT EXISTS idx_road_detections_type ON road_detections(type);
CREATE INDEX IF NOT EXISTS idx_road_detections_severity ON road_detections(severity);
CREATE INDEX IF NOT EXISTS idx_road_detections_status ON road_detections(status);
CREATE INDEX IF NOT EXISTS idx_road_detections_lat_lon ON road_detections(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_road_detections_timestamp ON road_detections(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_road_detections_track_id ON road_detections(track_id);


-- ==============================================================================
-- 4. Maintenance Tickets Table (Municipal Repair Pipeline: PWD / BBMP / NHAI)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS maintenance_tickets (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_code             VARCHAR(64) UNIQUE NOT NULL,                  -- e.g. 'WO-BLR-2026-105'
    detection_id            UUID REFERENCES road_detections(id) ON DELETE SET NULL,
    hazard_type             VARCHAR(64) NOT NULL,
    title                   VARCHAR(255) NOT NULL,
    location_description    TEXT NOT NULL,
    latitude                DOUBLE PRECISION NOT NULL,
    longitude               DOUBLE PRECISION NOT NULL,
    city                    VARCHAR(64) NOT NULL DEFAULT 'Bengaluru',
    severity                VARCHAR(32) NOT NULL DEFAULT 'HIGH',          -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    priority                VARCHAR(32) NOT NULL DEFAULT 'P1',            -- 'P1', 'P2', 'P3'
    agency                  VARCHAR(128) NOT NULL DEFAULT 'BBMP Road Infrastructure Division',
    assigned_contractor     VARCHAR(128),
    assigned_crew           VARCHAR(128),
    status                  VARCHAR(32) NOT NULL DEFAULT 'PENDING',       -- 'PENDING', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'REOPENED', 'CANCELLED'
    estimated_cost_inr      NUMERIC(12, 2) DEFAULT 0.0,
    field_notes             TEXT,
    target_sla_hours        INTEGER DEFAULT 24,
    target_completion       TIMESTAMPTZ,
    resolved_at             TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_maintenance_tickets_code ON maintenance_tickets(ticket_code);
CREATE INDEX IF NOT EXISTS idx_maintenance_tickets_detection ON maintenance_tickets(detection_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_tickets_status ON maintenance_tickets(status);
CREATE INDEX IF NOT EXISTS idx_maintenance_tickets_city ON maintenance_tickets(city);
CREATE INDEX IF NOT EXISTS idx_maintenance_tickets_severity ON maintenance_tickets(severity);
CREATE INDEX IF NOT EXISTS idx_maintenance_tickets_created_at ON maintenance_tickets(created_at DESC);


-- ==============================================================================
-- 5. Evidence & Storage References Table
-- ==============================================================================
CREATE TABLE IF NOT EXISTS evidence_references (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    detection_id            UUID REFERENCES road_detections(id) ON DELETE CASCADE,
    scan_id                 UUID REFERENCES scan_jobs(id) ON DELETE CASCADE,
    bucket_name             VARCHAR(64) NOT NULL,                         -- 'uploaded-videos', 'evidence-frames', 'annotated-frames', 'thumbnails'
    storage_path            TEXT NOT NULL,
    public_url              TEXT,
    mime_type               VARCHAR(64) NOT NULL DEFAULT 'image/jpeg',
    file_size_bytes         BIGINT DEFAULT 0,
    sha256_hash             VARCHAR(64),
    captured_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata                JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_evidence_ref_detection ON evidence_references(detection_id);
CREATE INDEX IF NOT EXISTS idx_evidence_ref_scan ON evidence_references(scan_id);
CREATE INDEX IF NOT EXISTS idx_evidence_ref_bucket ON evidence_references(bucket_name);


-- ==============================================================================
-- 6. Bus Telemetry Table (Compatible Extension of Existing gps_telemetry)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS gps_telemetry (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bus_id                  VARCHAR(64) NOT NULL,
    timestamp               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    lat                     DOUBLE PRECISION NOT NULL,
    lon                     DOUBLE PRECISION NOT NULL,
    speed_kmh               NUMERIC(6, 2) DEFAULT 0.0,
    bearing_deg             NUMERIC(6, 2) DEFAULT 0.0,
    altitude_m              NUMERIC(8, 2) DEFAULT 0.0,
    hdop                    NUMERIC(4, 2) DEFAULT 1.0,
    road_segment            VARCHAR(128) DEFAULT 'UNKNOWN',
    scan_id                 UUID REFERENCES scan_jobs(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_gps_telemetry_bus_timestamp ON gps_telemetry(bus_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gps_telemetry_lat_lon ON gps_telemetry(lat, lon);


-- ==============================================================================
-- 7. Supabase Storage Buckets Setup
-- ==============================================================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES 
    (
        'uploaded-videos', 
        'uploaded-videos', 
        false, 
        524288000, -- 500 MB limit
        ARRAY['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska', 'video/webm']
    ),
    (
        'evidence-frames', 
        'evidence-frames', 
        true, 
        10485760,  -- 10 MB limit
        ARRAY['image/jpeg', 'image/png', 'image/webp']
    ),
    (
        'annotated-frames', 
        'annotated-frames', 
        true, 
        10485760,  -- 10 MB limit
        ARRAY['image/jpeg', 'image/png', 'image/webp']
    ),
    (
        'thumbnails', 
        'thumbnails', 
        true, 
        2097152,   -- 2 MB limit
        ARRAY['image/jpeg', 'image/png', 'image/webp']
    )
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;


-- ==============================================================================
-- 8. Row Level Security (RLS) Policies
-- ==============================================================================

-- Enable RLS on all tables
ALTER TABLE scan_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE road_detections ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_references ENABLE ROW LEVEL SECURITY;
ALTER TABLE gps_telemetry ENABLE ROW LEVEL SECURITY;

-- Scan Jobs Policies:
-- Anonymous / Public users can view completed job summaries
CREATE POLICY "Public read completed scan jobs" 
    ON scan_jobs FOR SELECT 
    USING (true);

-- Authenticated / Service Role can insert and update scan jobs
CREATE POLICY "Authenticated insert scan jobs" 
    ON scan_jobs FOR INSERT 
    WITH CHECK (true);

CREATE POLICY "Authenticated update scan jobs" 
    ON scan_jobs FOR UPDATE 
    USING (true);

-- Road Detections Policies:
-- Public read for verified or non-dismissed detections
CREATE POLICY "Public read detections" 
    ON road_detections FOR SELECT 
    USING (status != 'DISMISSED');

-- Authenticated / Service Role full write access for inference pipeline
CREATE POLICY "Pipeline manage road detections" 
    ON road_detections FOR ALL 
    USING (true);

-- Maintenance Tickets Policies:
-- Public read access for transparency
CREATE POLICY "Public read maintenance tickets" 
    ON maintenance_tickets FOR SELECT 
    USING (true);

-- Authenticated field engineers and backend dispatch can manage tickets
CREATE POLICY "Field engineers manage tickets" 
    ON maintenance_tickets FOR ALL 
    USING (true);

-- Storage Objects Policies:
-- Public can read evidence frames, annotated frames, and thumbnails
CREATE POLICY "Public read evidence objects" 
    ON storage.objects FOR SELECT 
    USING (bucket_id IN ('evidence-frames', 'annotated-frames', 'thumbnails'));

-- Authenticated / Service Role can upload to all buckets
CREATE POLICY "Service upload storage objects" 
    ON storage.objects FOR INSERT 
    WITH CHECK (bucket_id IN ('uploaded-videos', 'evidence-frames', 'annotated-frames', 'thumbnails'));
