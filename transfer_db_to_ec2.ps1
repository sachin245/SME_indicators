# transfer_db_to_ec2.ps1
# One-time transfer of the local SQLite database to EC2.
# Run from the project root: .\transfer_db_to_ec2.ps1

$PEM      = "C:\Users\ResolveWave\Documents\GitHub\ec2-access.pem"
$EC2_USER = "ubuntu"
$EC2_HOST = "98.81.94.194"
$LOCAL_DB = "$PSScriptRoot\data\sme_indicators.db"
$REMOTE_DB = "~/SME_indicators/data/sme_indicators.db"

# ── Pre-flight checks ─────────────────────────────────────────────────────────

if (-not (Test-Path $PEM)) {
    Write-Error "PEM file not found: $PEM"
    exit 1
}

if (-not (Test-Path $LOCAL_DB)) {
    Write-Error "Local database not found: $LOCAL_DB"
    exit 1
}

$dbSize = (Get-Item $LOCAL_DB).Length
$dbSizeMB = [math]::Round($dbSize / 1MB, 1)
Write-Host ""
Write-Host "=== EC2 Database Transfer ===" -ForegroundColor Cyan
Write-Host "  Source : $LOCAL_DB ($dbSizeMB MB)"
Write-Host "  Target : ${EC2_USER}@${EC2_HOST}:$REMOTE_DB"
Write-Host ""

# ── Confirm ───────────────────────────────────────────────────────────────────

$confirm = Read-Host "Proceed? This will OVERWRITE the remote database. (y/N)"
if ($confirm -notmatch '^[Yy]$') {
    Write-Host "Aborted." -ForegroundColor Yellow
    exit 0
}

# ── Stop remote service so SQLite is not locked during transfer ───────────────

Write-Host ""
Write-Host "[1/4] Stopping sme-api on EC2..." -ForegroundColor Yellow
ssh -i $PEM -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_HOST}" "sudo systemctl stop sme-api"
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Could not stop sme-api (may not be running). Continuing."
}

# ── Backup existing remote DB ─────────────────────────────────────────────────

Write-Host "[2/4] Backing up remote database..." -ForegroundColor Yellow
$timestamp = (Get-Date -Format "yyyyMMdd_HHmmss")
ssh -i $PEM -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_HOST}" `
    "if [ -f ~/SME_indicators/data/sme_indicators.db ]; then cp ~/SME_indicators/data/sme_indicators.db ~/SME_indicators/data/sme_indicators.db.bak_$timestamp && echo 'Backup created: sme_indicators.db.bak_$timestamp'; else echo 'No existing DB to back up.'; fi"

# ── SCP transfer ──────────────────────────────────────────────────────────────

Write-Host "[3/4] Transferring database ($dbSizeMB MB)..." -ForegroundColor Yellow
scp -i $PEM -o StrictHostKeyChecking=no $LOCAL_DB "${EC2_USER}@${EC2_HOST}:$REMOTE_DB"
if ($LASTEXITCODE -ne 0) {
    Write-Error "SCP transfer failed. Remote database was NOT replaced."
    Write-Host "Restarting sme-api anyway..." -ForegroundColor Yellow
    ssh -i $PEM -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_HOST}" "sudo systemctl start sme-api"
    exit 1
}

# ── Verify remote file size ───────────────────────────────────────────────────

Write-Host "[4/4] Verifying transfer..." -ForegroundColor Yellow
$remoteSize = ssh -i $PEM -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_HOST}" `
    "stat -c%s ~/SME_indicators/data/sme_indicators.db 2>/dev/null || echo 0"
$remoteSizeMB = [math]::Round([long]$remoteSize / 1MB, 1)

if ([long]$remoteSize -ne $dbSize) {
    Write-Warning "Size mismatch — local: $dbSizeMB MB, remote: $remoteSizeMB MB"
} else {
    Write-Host "  Size verified: $dbSizeMB MB" -ForegroundColor Green
}

# ── Restart service ───────────────────────────────────────────────────────────

ssh -i $PEM -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_HOST}" "sudo systemctl start sme-api"
if ($LASTEXITCODE -eq 0) {
    Write-Host "  sme-api restarted." -ForegroundColor Green
} else {
    Write-Warning "Could not restart sme-api. Start it manually."
}

Write-Host ""
Write-Host "=== Transfer complete ===" -ForegroundColor Green
Write-Host "  Remote DB : ${EC2_USER}@${EC2_HOST}:$REMOTE_DB"
Write-Host "  Backup    : ~/SME_indicators/data/sme_indicators.db.bak_$timestamp"
Write-Host ""
