# Adds (or removes) a Startup shortcut so the tracker launches at login.
# Usage:
#   powershell -ExecutionPolicy Bypass -File install-startup.ps1          # install
#   powershell -ExecutionPolicy Bypass -File install-startup.ps1 -Remove  # uninstall
param([switch]$Remove)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$vbs       = Join-Path $scriptDir "start-tracker.vbs"
$startup   = [Environment]::GetFolderPath("Startup")
$lnkPath   = Join-Path $startup "Claude Usage Tracker.lnk"

if ($Remove) {
    if (Test-Path $lnkPath) { Remove-Item $lnkPath; Write-Host "Removed startup entry." }
    else { Write-Host "No startup entry found." }
    return
}

$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut($lnkPath)
$lnk.TargetPath       = "wscript.exe"
$lnk.Arguments        = "`"$vbs`""
$lnk.WorkingDirectory = $scriptDir
$lnk.Description      = "Claude Usage Tracker"
$lnk.Save()
Write-Host "Installed. The tracker will start automatically at login."
Write-Host "Shortcut: $lnkPath"
