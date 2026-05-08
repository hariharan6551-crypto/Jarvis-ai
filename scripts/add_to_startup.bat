@echo off
echo ============================================
echo   J.A.R.V.I.S — Add to Windows Startup
echo   Uses Task Scheduler with 15-second delay
echo ============================================
echo.

:: Determine project root dynamically
set "PROJECT_DIR=%~dp0.."

:: Create the scheduled task
echo Creating scheduled task with 15-second logon delay...
schtasks /Create /F /TN "JARVIS_Startup" /TR "\"%PROJECT_DIR%\JARVIS.bat\"" /SC ONLOGON /DELAY 0000:15 /RL HIGHEST

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ J.A.R.V.I.S added to Windows startup successfully!
    echo   Task Name: JARVIS_Startup
    echo   Trigger: On user logon
    echo   Delay: 15 seconds after login
    echo   Priority: Highest
    echo.
    echo To remove: Run scripts\remove_from_startup.bat
) else (
    echo.
    echo ✗ Failed to create scheduled task.
    echo   Try running this script as Administrator.
)
echo.
pause
