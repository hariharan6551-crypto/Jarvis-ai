@echo off
title J.A.R.V.I.S. Phase 1
echo.
echo  ===================================================
echo   J.A.R.V.I.S. - Phase 1: Core Voice Assistant
echo  ===================================================
echo.
echo  Step 1: Testing TTS...
python "%~dp0test_tts.py"
echo.
echo  Step 2: Testing Microphone...  
python "%~dp0test_mic.py"
echo.
echo  ===================================================
echo  If both tests passed, JARVIS will start now.
echo  Press Ctrl+C at any time to stop.
echo  ===================================================
echo.
pause
python "%~dp0jarvis_core.py"
pause
