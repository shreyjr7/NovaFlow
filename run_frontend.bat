@echo off
title NovaFlow Transport - Frontend Command Center
color 0B

echo ===============================================================
echo   NovaFlow Transport - Frontend Command Center
echo ===============================================================
echo   Local UI:  http://localhost:3000
echo   GIS Map:   http://localhost:3000/gis
echo   Fleet:     http://localhost:3000/fleet
echo ===============================================================
echo.

cd /d "%~dp0frontend"

if not exist node_modules (
    echo Installing frontend dependencies...
    cmd /c "npm install"
)

cmd /c "npm run dev"

pause
