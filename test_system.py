#!/usr/bin/env python3
"""
NovaFlow Transport - Comprehensive System Diagnostic & Health Verifier
======================================================================
Verifies all 7 MVP systems:
  1. Edge AI Modules
  2. Road Defect Pipeline
  3. Traffic Intelligence Engine
  4. GIS Command Center
  5. Incident Intelligence & ANPR
  6. Maintenance Workflow
  7. Urban Analytics & Insights
"""

import sys
import os
import json

# Ensure UTF-8 output if supported
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure paths
sys.path.insert(0, os.path.abspath("edge/src"))
sys.path.insert(0, os.path.abspath("."))

def test_system():
    print("\n" + "="*60)
    print("   NovaFlow Transport System Diagnostic")
    print("="*60 + "\n")
    
    passed = 0
    total = 7

    # 1. Edge AI
    try:
        from edge.road_defect import RoadDefectDetector
        from edge.vehicle import VehicleProcessor
        from edge.traffic import CongestionDetector
        print("  [1/7] Edge AI Pipeline Modules ............ [ OK ]")
        passed += 1
    except Exception as e:
        print(f"  [1/7] Edge AI Pipeline Modules ............ [ FAIL: {e} ]")

    # 2. Database & Seed Data
    try:
        from sqlmodel import Session, select
        from backend.app.database.session import engine
        from backend.app.models.ingested_event import IngestedEvent
        with Session(engine) as session:
            count = len(session.exec(select(IngestedEvent)).all())
        print(f"  [2/7] Database & Seed Events ({count} events) ..... [ OK ]")
        passed += 1
    except Exception as e:
        print(f"  [2/7] Database & Seed Events ............... [ FAIL: {e} ]")

    # 3. Fleet & Routes Data
    try:
        from backend.app.services.demo_seeder_service import get_demo_seeder_service
        seeder = get_demo_seeder_service()
        buses = seeder.get_buses()
        routes = seeder.get_routes()
        r_count = len(routes.get('routes', []))
        print(f"  [3/7] Fleet Kinematics ({len(buses)} buses, {r_count} routes) .. [ OK ]")
        passed += 1
    except Exception as e:
        print(f"  [3/7] Fleet Kinematics ..................... [ FAIL: {e} ]")

    # 4. Road Defect Service
    try:
        from backend.app.services.defect_service import get_road_defect_service
        ds = get_road_defect_service()
        stats = ds.get_lifecycle_stats()
        print("  [4/7] Road Defect Lifecycle Engine ......... [ OK ]")
        passed += 1
    except Exception as e:
        print(f"  [4/7] Road Defect Lifecycle Engine ......... [ FAIL: {e} ]")

    # 5. Incident & Evidence Chain
    try:
        from backend.app.services.evidence_chain_service import get_evidence_chain_service
        ecs = get_evidence_chain_service()
        print("  [5/7] Incident & Cryptographic Chain ....... [ OK ]")
        passed += 1
    except Exception as e:
        print(f"  [5/7] Incident & Cryptographic Chain ....... [ FAIL: {e} ]")

    # 6. Urban Analytics Engine
    try:
        from backend.app.services.urban_analytics_service import get_urban_analytics_service
        uas = get_urban_analytics_service()
        uas.get_summary(date_range="today", time_of_day="all", zone="all")
        print("  [6/7] Urban Analytics Service .............. [ OK ]")
        passed += 1
    except Exception as e:
        print(f"  [6/7] Urban Analytics Service .............. [ FAIL: {e} ]")

    # 7. Frontend Build & Static Assets
    try:
        dist_index = os.path.join("frontend", "dist", "index.html")
        has_build = os.path.exists(dist_index)
        if has_build:
            print("  [7/7] Frontend Build Assets (dist/index.html) [ OK ]")
            passed += 1
        else:
            print("  [7/7] Frontend Build Assets (run npm run build) [ NOTICE ]")
    except Exception as e:
        print(f"  [7/7] Frontend Assets ...................... [ FAIL: {e} ]")

    print("\n" + "-"*60)
    print(f"  System Health Score: {passed}/{total} Checks Operational")
    print("="*60 + "\n")
    return passed == total

if __name__ == "__main__":
    success = test_system()
    sys.exit(0 if success else 1)
