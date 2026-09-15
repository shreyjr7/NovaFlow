@echo off
title NovaFlow Transport - Full Stack Launcher
color 0D

echo ===============================================================
echo   NovaFlow Transport - Launching Full Stack in Parallel
echo ===============================================================
echo   1. Starting Central Backend on port 8000...
echo   2. Starting Frontend Command Center on port 3000...
echo ===============================================================
echo.

start "NovaFlow Backend (8000)" cmd /k "%~dp0run_backend.bat"
timeout /t 3 /nobreak >nul
start "NovaFlow Frontend (3000)" cmd /k "%~dp0run_frontend.bat"

echo.
echo All services launched!
echo Access the application at: http://localhost:3000
echo Access the API docs at:     http://localhost:8000/docs
echo.
