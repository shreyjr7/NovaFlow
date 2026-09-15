@echo off
title START NOVAFLOW TRANSPORT
color 0B

cls
echo  ===============================================================
echo  *                                                             *
echo  *             N O V A F L O W   T R A N S P O R T             *
echo  *                                                             *
echo  *      AI-Powered Mobile Urban Sensing Fleet Platform         *
echo  *                                                             *
echo  ===============================================================
echo.
echo  [1/4] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)
echo        Python is ready.

echo.
echo  [2/4] Verifying database and seeding demo data...
set PYTHONPATH=edge/src;.
python -c "from backend.app.database.session import init_db; init_db(); from backend.app.services.demo_seeder_service import get_demo_seeder_service; get_demo_seeder_service().seed_historical_events(525)" >nul 2>&1
echo        Database verified (novaflow.db initialized with 525+ events).

echo.
echo  [3/4] Launching Central Backend on http://localhost:8000 ...
start "NovaFlow Backend [8000]" cmd /k "call \"%~dp0run_backend.bat\""
timeout /t 3 /nobreak >nul

echo.
echo  [4/4] Launching Frontend Command Center on http://localhost:3000 ...
start "NovaFlow Frontend [3000]" cmd /k "call \"%~dp0run_frontend.bat\""

echo.
echo  ===============================================================
echo  *  SYSTEM IS RUNNING!                                         *
echo  *  - Command Center UI:  http://localhost:3000                *
echo  *  - GIS Live Map:       http://localhost:3000/gis            *
echo  *  - Fleet Dashboard:    http://localhost:3000/fleet          *
echo  *  - Testing Center:     http://localhost:3000/testing        *
echo  *  - Demo Flow Theater:  http://localhost:3000/demo           *
echo  *  - Backend API & Docs: http://localhost:8000/docs           *
echo  ===============================================================
echo.
echo  Keep the opened terminal windows running.
echo  Press any key to close this launcher window.
pause >nul
