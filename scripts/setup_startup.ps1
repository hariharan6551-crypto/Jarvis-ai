$ws = New-Object -ComObject WScript.Shell
$startup = [Environment]::GetFolderPath('Startup')
$shortcut = $ws.CreateShortcut("$startup\JARVIS.lnk")
$shortcut.TargetPath = "C:\Users\harih\Desktop\Jarvis\JARVIS.bat"
$shortcut.WorkingDirectory = "C:\Users\harih\Desktop\Jarvis"
$shortcut.Description = "JARVIS AI Assistant"
$shortcut.WindowStyle = 7
$shortcut.Save()
Write-Host "JARVIS added to Windows Startup!"
Write-Host "Location: $startup\JARVIS.lnk"
