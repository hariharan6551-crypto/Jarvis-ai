@echo off
echo Removing J.A.R.V.I.S from Windows startup...
set SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS.lnk
if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo Removed from startup successfully.
) else (
    echo J.A.R.V.I.S was not in startup.
)
pause
