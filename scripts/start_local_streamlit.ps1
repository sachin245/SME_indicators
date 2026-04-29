# Launches the Streamlit dashboard on http://localhost:8501.
# This is the original visualization. The React app on :8002 has the
# newer features but Streamlit is kept around as a backup.

# NOTE: see start_local_api.ps1 for why we don't set ErrorActionPreference=Stop.

$Repo       = Split-Path -Parent $PSScriptRoot
$Streamlit  = "C:\Users\sachi\AppData\Local\Programs\Python\Python312\Scripts\streamlit.exe"
$LogDir     = Join-Path $Repo "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Set-Location $Repo

while ($true) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content "$LogDir\streamlit.log" "[$stamp] starting streamlit on :8501"
    & $Streamlit run dashboard\app.py --server.port 8501 --server.headless true *>> "$LogDir\streamlit.log"
    Start-Sleep -Seconds 5
}
