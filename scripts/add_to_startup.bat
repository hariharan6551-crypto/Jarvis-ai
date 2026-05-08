@echo off
echo =============================================
echo   J.A.R.V.I.S - Auto Start Setup
echo =============================================
echo.
echo This will make J.A.R.V.I.S start automatically
echo when you turn on your PC.
echo.

:: Create a shortcut in the Windows Startup folder
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_FOLDER%\JARVIS.lnk
set TARGET_PATH=%~dp0JARVIS.bat
set ICON_PATH=%~dp0frontend\public\icon.ico

:: Use PowerShell to create shortcut
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%TARGET_PATH%'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'J.A.R.V.I.S AI Desktop Assistant'; $s.WindowStyle = 7; $s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo.
    echo SUCCESS! J.A.R.V.I.S will now auto-start with Windows.
    echo Shortcut created at: %SHORTCUT_PATH%
) else (
    echo.
    echo Failed to create startup shortcut.
    echo You can manually copy JARVIS.bat to:
    echo %STARTUP_FOLDER%
)

echo.
pause
