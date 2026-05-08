# J.A.R.V.I.S — Setup Windows Startup via Task Scheduler (PowerShell)
# Run as Administrator for best results

param(
    [switch]$Remove,
    [int]$DelaySeconds = 15
)

$TaskName = "JARVIS_Startup"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$LauncherPath = Join-Path $ProjectDir "JARVIS.bat"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  J.A.R.V.I.S — Startup Configuration"      -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if ($Remove) {
    Write-Host "Removing J.A.R.V.I.S from startup..." -ForegroundColor Yellow
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "✓ Removed scheduled task: $TaskName" -ForegroundColor Green
    } catch {
        Write-Host "  No scheduled task found." -ForegroundColor Gray
    }

    # Remove legacy shortcut
    $ShortcutPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS.lnk"
    if (Test-Path $ShortcutPath) {
        Remove-Item $ShortcutPath -Force
        Write-Host "✓ Removed legacy startup shortcut" -ForegroundColor Green
    }
    return
}

# Verify launcher exists
if (-not (Test-Path $LauncherPath)) {
    Write-Host "✗ JARVIS.bat not found at: $LauncherPath" -ForegroundColor Red
    Write-Host "  Please ensure JARVIS.bat exists in the project root." -ForegroundColor Yellow
    return
}

Write-Host "Project root: $ProjectDir"
Write-Host "Launcher:     $LauncherPath"
Write-Host "Delay:        ${DelaySeconds}s after logon"
Write-Host ""

# Create the scheduled task
try {
    $Action = New-ScheduledTaskAction -Execute $LauncherPath -WorkingDirectory $ProjectDir
    $Trigger = New-ScheduledTaskTrigger -AtLogOn
    $Trigger.Delay = "PT${DelaySeconds}S"
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest

    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force | Out-Null

    Write-Host "✓ J.A.R.V.I.S added to Windows startup!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Task Name:  $TaskName" -ForegroundColor White
    Write-Host "  Trigger:    On user logon" -ForegroundColor White
    Write-Host "  Delay:      ${DelaySeconds} seconds" -ForegroundColor White
    Write-Host "  Run Level:  Highest" -ForegroundColor White
    Write-Host ""
    Write-Host "To remove: .\setup_startup.ps1 -Remove" -ForegroundColor Yellow
} catch {
    Write-Host "✗ Failed to create scheduled task: $_" -ForegroundColor Red
    Write-Host "  Try running PowerShell as Administrator." -ForegroundColor Yellow
}
