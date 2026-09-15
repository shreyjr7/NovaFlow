# NovaFlow Transport — System Architecture and Implementation Guide

## 1. Executive Summary

NovaFlow Transport turns regular public municipal bus fleets into mobile urban perception sensors. By mounting intelligent edge AI camera hardware on transit buses, cities obtain high-frequency, passive environmental and traffic intelligence without installing thousands of static cameras.

---

## 2. End-to-End System Architecture

```
                    BUS
                     │
              ┌──────┴──────┐
              │   CAMERAS   │  (Front, Rear, Left, Right)
              └──────┬──────┘
                     ↓
               EDGE AI DEVICE  (NVIDIA Jetson AGX Orin / Xavier)
                     │
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
 Road Detection   Traffic       Safety
 (Potholes,      Detection     Detection
  Damage, Water) (ByteTrack)   (VRU, Incidents)
       │             │             │
       └─────────────┼─────────────┘
                     ↓
               EVENT ENGINE   (Temporal Confirmation, Quality Gate)
                     ↓
             LOCAL BUFFER     (Store-and-Forward SQLite ACID Queue)
                     ↓
               MQTT / HTTPS   (Payload Dedup & Idempotency Key)
                     ↓
              INGESTION API   (FastAPI High-Throughput Sub-5ms)
                     ↓
                REDIS QUEUE   (Stream Queues with In-Memory Fallback)
                     ↓
             EVENT PROCESSOR  (Background Workers, Deduplication)
                     ↓
       ┌─────────────┼──────────────┐
       ↓             ↓              ↓
 PostgreSQL       PostGIS       Object Storage
 (Relational)    (Centroids)    (Evidence Clips & SHA-256)
       │             │              │
       └─────────────┼──────────────┘
                     ↓
                 ANALYTICS     (Diurnal Baselines, Delay Scoring)
                     ↓
              AI INSIGHTS     (Explainable Operational Recommendations)
                     ↓
             GIS COMMAND CENTER (12-Layer Spatial Command Center)
                     ↓
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
   Transport      Traffic       Road
   Authority      Police       Authority
```

---

## 3. Quick Start & Execution

### Option A: One-Click Launcher (Windows)
Double-click:
```cmd
START_NOVAFLOW.bat
```
This automatically verifies dependencies, seeds 525+ events, and launches both Backend (`http://localhost:8000`) and Frontend (`http://localhost:3000`).

### Option B: Individual Service Launchers
- Backend: `run_backend.bat`
- Frontend: `run_frontend.bat`
- Seed Data: `seed_data.bat`
- Test System Health: `python test_system.py`

---

## 4. The 7 Core Operational Systems

### System 1: Edge AI Simulator
- **File**: `edge/src/edge/pipeline/manager.py` & `run_simulator.py`
- Multi-camera capture (FRONT, REAR, LEFT, RIGHT).
- Frame quality evaluation (Laplacian blur variance, luminance, optical lens obstruction).
- Object detection via YOLOv8 or deterministic test generator.
- GPS kinematic interpolation along metropolitan routes.

### System 2: Road Defect Detection
- **Files**: `edge/src/edge/road_defect/` & `backend/app/routers/road_defects.py`
- 7 defect classes: Potholes, Road Damage, Waterlogging, Missing Signs, Missing Dividers, Missing Zebra Crossings, Damaged Signs.
- Temporal 3-of-5 sliding window confirmation to eliminate optical false positives.
- DBSCAN spatial clustering with 25-meter centroid refinement.

### System 3: Traffic Intelligence
- **Files**: `edge/src/edge/vehicle/` & `backend/app/routers/congestion.py`
- ByteTrack Hungarian multi-object vehicle association.
- Virtual counting line tripwires and polygonal zone density calculation.
- Diurnal speed and density baseline modeling with single slow vehicle suppression.

### System 4: GIS Command Center
- **Files**: `backend/app/routers/gis.py` & `frontend/src/pages/GisCommandCenter/`
- Full-screen 12-layer spatial command center.
- Real-time bus fleet kinematics and route vector overlays.
- Interactive officer action dispatch: Confirm, Dismiss, Escalate, and Maintenance Work Order generation.

### System 5: Incident Intelligence & ANPR
- **Files**: `edge/src/edge/incident/`, `edge/src/edge/anpr/`, `backend/app/routers/incidents.py`
- 7 explainable kinematic trajectory signals (sudden deceleration, abrupt heading, trajectory jumps).
- Pre/post impact circular video buffer extraction.
- 9-stage Indian RTO plate recognition with human-in-the-loop quarantine gate for confidence < 0.85.

### System 6: Maintenance Workflow
- **Files**: `backend/app/services/defect_service.py` & `frontend/src/pages/RoadDefects/`
- 6-stage municipal repair lifecycle: AI Detected → Unverified → Confirmed → Assigned → Under Repair → Resolved.
- 6-factor priority scoring algorithm (Severity, Traffic, Detections, Location, Safety, Persistence).
- Autonomous watchdog redetection verification.

### System 7: Urban Analytics & Insights
- **Files**: `backend/app/services/urban_analytics_service.py`, `insights_engine.py`, `frontend/src/pages/UrbanAnalytics/`
- Diurnal traffic curves, modal split analysis, and corridor congestion rankings.
- Grounded, evidence-backed operational recommendations with strict anti-speculation checks.

---

## 5. Security, Privacy & Chain of Custody

1. **Edge Privacy by Design**: Raw video processed locally on bus; non-incident frames discarded after inference.
2. **Passenger Anonymization**: Passenger cabin processing strictly local with zero biometric transmission.
3. **Cryptographic Integrity**: SHA-256 evidence hashing with immutable custody logs (Created, Accessed, Downloaded, Reviewed, Exported) and tamper detection.
4. **Zero-PII Public Safety Portal**: Citizen-facing dashboard with verified aggregated alerts and zero private data exposure.
