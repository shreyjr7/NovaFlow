@echo off
title NovaFlow Transport - Data Seeder
color 0E

echo ===============================================================
echo   NovaFlow Transport - Seed Data & Simulation Synchronizer
echo ===============================================================
echo   Seeding 20 Connected Buses, 5 Routes, 115 Road Segments,
echo   and 525+ Historical Events into SQLite Database...
echo ===============================================================
echo.

set PYTHONPATH=edge/src;.

python -c "import os; os.environ['NOVAFLOW_DEV_MODE'] = 'true'; from backend.app.database.session import init_db; init_db(); from backend.app.services.demo_seeder_service import get_demo_seeder_service; svc = get_demo_seeder_service(); count = svc.seed_historical_events(target_count=525); print(f'\n[SUCCESS] Seeded {count} historical events across 20 buses and 115 road segments into novaflow.db.'); print(f'[INFO] System Status: {svc.get_status().get(\"banner_text\")}\n')"

pause
