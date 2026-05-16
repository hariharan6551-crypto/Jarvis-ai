@echo off
echo ============================================
echo   J.A.R.V.I.S - Installation Script v2.5
echo ============================================
echo.

echo [1/4] Installing Python dependencies...
cd /d "%~dp0..\backend"
pip install -r requirements.txt
if errorlevel 1 (
    echo [WARNING] Some Python packages failed. Trying individually...
    pip install SpeechRecognition
    pip install PyAudio
    pip install edge-tts
    pip install pyttsx3
    pip install sounddevice
    pip install psutil
    pip install fastapi uvicorn pydantic pydantic-settings
    pip install loguru
    pip install google-generativeai
    pip install chromadb
    pip install pyautogui pygetwindow
)
echo.

echo [2/4] Installing Node.js dependencies...
cd /d "%~dp0..\frontend"
call npm install
echo.

echo [3/4] Creating data directories...
mkdir "%~dp0..\backend\data" 2>nul
mkdir "%~dp0..\backend\logs" 2>nul
mkdir "%~dp0..\backend\data\chroma" 2>nul

echo [4/4] Verifying critical packages...
python -c "import speech_recognition; print('  [OK] SpeechRecognition')" 2>nul || echo   [MISSING] SpeechRecognition - run: pip install SpeechRecognition
python -c "import edge_tts; print('  [OK] edge-tts')" 2>nul || echo   [MISSING] edge-tts - run: pip install edge-tts
python -c "import sounddevice; print('  [OK] sounddevice')" 2>nul || echo   [MISSING] sounddevice - run: pip install sounddevice
python -c "import fastapi; print('  [OK] FastAPI')" 2>nul || echo   [MISSING] FastAPI - run: pip install fastapi
python -c "import psutil; print('  [OK] psutil')" 2>nul || echo   [MISSING] psutil - run: pip install psutil
python -c "import pyautogui; print('  [OK] pyautogui')" 2>nul || echo   [MISSING] pyautogui - run: pip install pyautogui

echo.
echo ============================================
echo   Installation Complete!
echo   Run: python launcher.py
echo   Or:  JARVIS.bat
echo ============================================
pause
