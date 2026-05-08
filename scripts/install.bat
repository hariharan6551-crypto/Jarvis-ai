@echo off
echo ============================================
echo   J.A.R.V.I.S - Installation Script
echo ============================================
echo.

echo [1/3] Installing Python dependencies...
cd /d "%~dp0..\backend"
pip install -r requirements.txt
echo.

echo [2/3] Installing Node.js dependencies...
cd /d "%~dp0..\frontend"
call npm install
echo.

echo [3/3] Creating data directories...
mkdir "%~dp0..\backend\data" 2>nul
mkdir "%~dp0..\backend\logs" 2>nul

echo.
echo ============================================
echo   Installation Complete!
echo   Run start.bat to launch J.A.R.V.I.S
echo ============================================
pause
