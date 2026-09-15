-- Phase 3 – PostgreSQL + PostGIS schema for NovaFlow Transport

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Authentication & Authorization
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email         TEXT NOT NULL UNIQUE,
    full_name     TEXT,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE roles (
    id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- 2. Fleet Assets
CREATE TABLE bus_routes (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE bus_devices (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    serial_number TEXT NOT NULL UNIQUE,
    hardware_type TEXT NOT NULL,
    firmware_ver  TEXT,
    installed_at  TIMESTAMPTZ,
    status        TEXT
);

CREATE TABLE buses (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fleet_number TEXT NOT NULL UNIQUE,
    route_id     UUID REFERENCES bus_routes(id),
    device_id    UUID REFERENCES bus_devices(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cameras (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bus_id     UUID NOT NULL REFERENCES buses(id) ON DELETE CASCADE,
    position   TEXT NOT NULL,
    interface  TEXT NOT NULL,
    model      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE camera_health (
    camera_id   UUID PRIMARY KEY REFERENCES cameras(id) ON DELETE CASCADE,
    last_seen   TIMESTAMPTZ NOT NULL,
    status      TEXT NOT NULL,
    error_code  TEXT,
    metrics_json JSONB
);

-- 3. GPS Tracking
CREATE TABLE gps_tracks (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bus_id      UUID NOT NULL REFERENCES buses(id) ON DELETE CASCADE,
    timestamp   TIMESTAMPTZ NOT NULL,
    location    GEOMETRY(Point, 4326) NOT NULL,
    speed_kmh   NUMERIC,
    heading_deg NUMERIC
);
CREATE INDEX idx_gps_tracks_location ON gps_tracks USING GIST (location);

-- 4. Core Event Table (generic)
CREATE TABLE road_events (
    event_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bus_id        UUID NOT NULL REFERENCES buses(id) ON DELETE CASCADE,
    camera_id     UUID NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    event_type    TEXT NOT NULL,
    confidence    NUMERIC CHECK (confidence BETWEEN 0 AND 1),
    timestamp     TIMESTAMPTZ NOT NULL,
    location      GEOMETRY(Point, 4326) NOT NULL,
    route_id      UUID REFERENCES bus_routes(id),
    frame_reference TEXT,
    clip_reference TEXT,
    status        TEXT DEFAULT 'NEW',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_road_events_timestamp ON road_events (timestamp);
CREATE INDEX idx_road_events_event_type ON road_events (event_type);
CREATE INDEX idx_road_events_bus_id ON road_events (bus_id);
CREATE INDEX idx_road_events_route_id ON road_events (route_id);
CREATE INDEX idx_road_events_location ON road_events USING GIST (location);

-- Specialized event tables via inheritance
CREATE TABLE potholes      (depth NUMERIC) INHERITS (road_events);
CREATE TABLE waterlogging  (water_depth NUMERIC) INHERITS (road_events);
CREATE TABLE road_damage   (damage_type TEXT) INHERITS (road_events);
CREATE TABLE missing_infrastructure (infra_type TEXT) INHERITS (road_events);
CREATE TABLE road_defects  (description TEXT) INHERITS (road_events);

-- 5. Vehicle Detection & Tracking
CREATE TABLE vehicle_detections (
    detection_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id     UUID NOT NULL REFERENCES road_events(event_id) ON DELETE CASCADE,
    vehicle_type TEXT NOT NULL,
    confidence   NUMERIC CHECK (confidence BETWEEN 0 AND 1),
    bbox         GEOMETRY(Polygon, 4326) NOT NULL,
    plate_number TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE vehicle_tracks (
    track_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id  UUID NOT NULL,
    start_time  TIMESTAMPTZ NOT NULL,
    end_time    TIMESTAMPTZ,
    path        GEOMETRY(LineString, 4326) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE traffic_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    route_id    UUID NOT NULL REFERENCES bus_routes(id),
    timestamp   TIMESTAMPTZ NOT NULL,
    image_uri   TEXT,
    congestion_level NUMERIC,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE congestion_events (
    event_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    route_id    UUID NOT NULL REFERENCES bus_routes(id),
    start_time  TIMESTAMPTZ NOT NULL,
    end_time    TIMESTAMPTZ,
    severity    TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. Pedestrian & School Zones
CREATE TABLE pedestrian_events (
    event_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bus_id     UUID NOT NULL REFERENCES buses(id),
    camera_id  UUID NOT NULL REFERENCES cameras(id),
    timestamp  TIMESTAMPTZ NOT NULL,
    location   GEOMETRY(Point, 4326) NOT NULL,
    count      INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE school_zones (
    zone_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name      TEXT NOT NULL,
    geometry  GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_school_zones_geom ON school_zones USING GIST (geometry);

-- 7. Incident Management
CREATE TABLE incidents (
    incident_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reported_by UUID NOT NULL REFERENCES users(id),
    description TEXT,
    severity    TEXT,
    status      TEXT DEFAULT 'OPEN',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE incident_vehicles (
    incident_id UUID NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    vehicle_id  UUID NOT NULL,
    PRIMARY KEY (incident_id, vehicle_id)
);

CREATE TABLE license_plates (
    plate_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plate_text TEXT NOT NULL UNIQUE,
    vehicle_type TEXT,
    owner_info JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE incident_evidence (
    evidence_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    s3_uri      TEXT NOT NULL,
    mime_type   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 8. GIS Layers
CREATE TABLE gis_layers (
    layer_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name       TEXT NOT NULL,
    layer_type TEXT NOT NULL,
    geojson    JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE road_segments (
    segment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name       TEXT,
    geometry   GEOMETRY(LineString, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_road_segments_geom ON road_segments USING GIST (geometry);

CREATE TABLE landmarks (
    landmark_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    geometry    GEOMETRY(Point, 4326) NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_landmarks_geom ON landmarks USING GIST (geometry);

-- 9. Maintenance & Ticketing
CREATE TABLE maintenance_tickets (
    ticket_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    defect_id   UUID NOT NULL REFERENCES road_defects(event_id) ON DELETE CASCADE,
    assigned_to UUID REFERENCES users(id),
    priority    TEXT,
    status      TEXT DEFAULT 'OPEN',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ticket_status_history (
    ticket_id   UUID NOT NULL REFERENCES maintenance_tickets(ticket_id) ON DELETE CASCADE,
    status      TEXT NOT NULL,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    changed_by  UUID REFERENCES users(id),
    PRIMARY KEY (ticket_id, changed_at)
);

-- 10. Analytics & Reporting
CREATE TABLE analytics_results (
    result_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_type TEXT NOT NULL,
    payload     JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE route_delays (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    route_id    UUID NOT NULL REFERENCES bus_routes(id),
    avg_delay   INTERVAL,
    measured_at TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE od_patterns (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    origin_zone      UUID NOT NULL REFERENCES school_zones(zone_id),
    destination_zone UUID NOT NULL REFERENCES school_zones(zone_id),
    count            INTEGER,
    period_start     TIMESTAMPTZ,
    period_end       TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 11. Alerts & Notifications
CREATE TABLE alerts (
    alert_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL REFERENCES users(id),
    alert_type TEXT NOT NULL,
    message    TEXT NOT NULL,
    is_read    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notifications (
    notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id),
    channel         TEXT NOT NULL,
    payload         JSONB,
    sent_at         TIMESTAMPTZ,
    status          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 12. AI Model Management
CREATE TABLE ai_model_versions (
    model_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name       TEXT NOT NULL,
    version    TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ai_detections (
    detection_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id    UUID NOT NULL REFERENCES ai_model_versions(model_id),
    event_id    UUID NOT NULL REFERENCES road_events(event_id),
    confidence  NUMERIC CHECK (confidence BETWEEN 0 AND 1),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 13. Research & Reporting
CREATE TABLE research_datasets (
    dataset_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title      TEXT NOT NULL,
    description TEXT,
    source_uri TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reports (
    report_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title       TEXT NOT NULL,
    content     TEXT,
    author_id   UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 14. Auditing
CREATE TABLE audit_logs (
    log_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id),
    action      TEXT NOT NULL,
    target_table TEXT,
    target_id   UUID,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(),
    details     JSONB
);
