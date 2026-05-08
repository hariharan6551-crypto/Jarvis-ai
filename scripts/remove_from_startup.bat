@echo off
echo ============================================
echo   J.A.R.V.I.S — Remove from Startup
echo ============================================
echo.

:: Remove Task Scheduler entry
schtasks /Delete /TN "JARVIS_Startup" /F >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ Removed JARVIS_Startup scheduled task.
) else (
    echo   No scheduled task found.
)

:: Also remove old Startup folder shortcut if it exists
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS.lnk"
if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo ✓ Removed old startup shortcut.
) else (
    echo   No startup shortcut found.
)

echo.
echo J.A.R.V.I.S removed from Windows startup.
pause
