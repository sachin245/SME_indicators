# Launches the FastAPI backend on http://localhost:8002.
# FastAPI also serves the built React UI at /, so this single process
# is enough to view the dashboard locally.
#
# Run manually:           powershell -ExecutionPolicy Bypass -File scripts\start_local_api.ps1
# Auto-start at logon:    scripts\install_autostart.ps1 (run once)

# NOTE: do NOT set $ErrorActionPreference = "Stop" here. It would make
# PowerShell raise NativeCommandError on uvicorn's stderr output (uvicorn
# writes its startup banner to stderr) and kill the watchdog loop.

$Repo   = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\sachi\AppData\Local\Programs\Python\Python312\python.exe"
$LogDir = Join-Path $Repo "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Set-Location $Repo

# Build the React frontend if dist is missing - first-run convenience
if (-not (Test-Path "$Repo\frontend\dist\index.html")) {
    Write-Output "frontend/dist missing - building React app first..."
    Push-Location "$Repo\frontend"
    npm install --silent
    npm run build
    Pop-Location
}

# Restart loop - if uvicorn dies, wait 5s and try again.
while ($true) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content "$LogDir\api.log" "[$stamp] starting uvicorn on :8002"
    & $Python -m uvicorn api.main:app --host 0.0.0.0 --port 8002 *>> "$LogDir\api.log"
    Start-Sleep -Seconds 5
}
