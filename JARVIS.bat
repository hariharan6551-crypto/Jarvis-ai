@echo off
title J.A.R.V.I.S Launcher
echo =============================================
echo   J.A.R.V.I.S - AI Desktop Assistant
echo   Starting all systems...
echo =============================================
echo.

:: Start backend silently
start /B /MIN "JARVIS-Backend" cmd /c "cd /d %~dp0backend && python main.py"

:: Wait for backend to start
timeout /t 3 /nobreak >nul

:: Start frontend silently
start /B /MIN "JARVIS-Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"

:: Wait for frontend to start
timeout /t 4 /nobreak >nul

:: Launch Electron desktop app
echo Starting Electron desktop app...
cd /d %~dp0frontend
npx electron .

:: When Electron closes, kill background processes
echo Shutting down J.A.R.V.I.S...
taskkill /F /FI "WINDOWTITLE eq JARVIS-Backend" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS-Frontend" >nul 2>&1
