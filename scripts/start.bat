@echo off
echo ============================================
echo   J.A.R.V.I.S - Starting Systems
echo ============================================
echo.

echo Starting backend server...
start "JARVIS-Backend" cmd /k "cd /d %~dp0..\backend && python main.py"

timeout /t 3 /nobreak >nul

echo Starting frontend...
start "JARVIS-Frontend" cmd /k "cd /d %~dp0..\frontend && npm run dev"

echo.
echo J.A.R.V.I.S is starting up!
echo Backend: http://127.0.0.1:8765
echo Frontend: http://localhost:5173
echo.
timeout /t 3 /nobreak >nul
start http://localhost:5173
