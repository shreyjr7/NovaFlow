# 🚍 NovaFlow Transport — AI-Powered Mobile Urban Intelligence Platform

NovaFlow Transport turns public municipal bus fleets into mobile urban sensors. By deploying computer vision at the edge, public transport vehicles passively and continuously monitor road defects, traffic congestion, pedestrian safety risks, and infrastructure degradation across metropolitan networks.

---

## ⚡ Quick Start (Windows One-Click)

Simply double-click:
```cmd
START_NOVAFLOW.bat
```
This automatically verifies dependencies, seeds 525+ demo events across 20 buses, and launches both:
- **Frontend Command Center**: [http://localhost:3000](http://localhost:3000)
- **Central Backend API**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📁 Repository Structure

```text
NovaFlow_Transport/
├── ai/                     # Edge AI models, YOLO pipelines, ANPR & detectors
├── backend/                # FastAPI backend, spatial clustering & database
│   ├── app/                # Routers, services, models, schemas & queue
│   └── tests/              # Comprehensive backend test suites
├── data/                   # Seed JSON files (buses, routes, segments, status)
├── edge/                   # Edge device runtime, local SQLite queue, camera simulator
│   ├── src/edge/           # Onboard inference & store-and-forward engine
│   └── tests/              # Edge unit & failure tests
├── frontend/               # React 18 + TypeScript + Vite + Tailwind UI
│   ├── src/pages/          # 25 command center dashboards
│   └── src/components/     # Shared GIS maps, cards, and banners
├── scratch/                # Experimental & analysis workspace
├── tests/                  # Root test runner
├── novaflow.db             # SQLite database with 525+ historical events
├── requirements.txt        # Unified Python dependencies
├── run_all.bat             # Starts backend & frontend concurrently
├── run_backend.bat         # Starts FastAPI backend (port 8000)
├── run_frontend.bat        # Starts React frontend (port 3000)
├── seed_data.bat           # Re-seeds demo buses, routes, and events
├── START_NOVAFLOW.bat      # Master one-click platform launcher
└── test_system.py          # System diagnostic & health verifier
```

---

## 🎯 The 7 Core Systems

| # | System | Dashboard Route | Key Features |
|---|---|---|---|
| **1** | **Edge AI Simulator** | `/offline-buffer` / Port 7000 | 4 camera streams, frame quality, YOLO inference, store-and-forward |
| **2** | **Road Defect Detection** | `/road-defects` | 7 defect classes, temporal 3-of-5 confirmation, 25m DBSCAN clustering |
| **3** | **Traffic Intelligence** | `/traffic`, `/congestion` | ByteTrack tracking, speed estimation, bottleneck alerts |
| **4** | **GIS Command Center** | `/gis`, `/command-center` | 12 interactive map layers, 20 live buses, 5 routes, officer actions |
| **5** | **Incident Intelligence** | `/incidents`, `/anpr` | 7 kinematic signals, video buffer, Indian RTO plate recognition |
| **6** | **Maintenance Workflow** | `/road-defects` | 6-stage lifecycle, 6-factor priority score, post-closure watchdog |
| **7** | **Urban Analytics** | `/urban-analytics` | Diurnal curves, modal split, safety indices, explainable insights |

---

## 🧪 System Diagnostics & Testing

To verify all 7 systems and run diagnostics:
```cmd
python test_system.py
```

To run the complete automated test suite (187 passing tests):
```cmd
python tests/test_runner.py
```
*(Or via pytest directly: `pytest backend/tests edge/tests -q`)*

---

## 🔐 Security & Privacy Architecture

- **Edge Privacy by Design**: Normal frames are processed in RAM and discarded; raw footage is never continuously streamed to the cloud.
- **Zero-PII Public Safety Portal**: Accessible at `/public`, citizens view safety notices without passenger or driver identifying information.
- **Cryptographic Evidence Chain of Custody**: Accessible at `/evidence-custody`, every clip is sealed with a SHA-256 hash and immutable audit log.
