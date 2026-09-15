@echo off
title NovaFlow Transport - Central Backend
color 0A

echo ===============================================================
echo   NovaFlow Transport - Central Backend Service
echo ===============================================================
echo   Port:      http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo   Health:    http://localhost:8000/health
echo ===============================================================
echo.

set PYTHONPATH=edge/src;.
set NOVAFLOW_DEV_MODE=true

python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

pause
