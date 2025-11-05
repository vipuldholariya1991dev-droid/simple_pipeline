# PowerShell script to restart the backend server

Write-Host "`n🔄 RESTARTING BACKEND SERVER`n" -ForegroundColor Cyan

# Navigate to backend directory
$backendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $backendDir

# Check if virtual environment exists
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "   Please run: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Set Exa API Key if not already set (for PDF search)
if (-not $env:EXA_API_KEY) {
    $env:EXA_API_KEY = "ab2d74f4-77d7-4c23-a223-96a67c2075e3"
    Write-Host "✅ Exa API Key set for PDF search" -ForegroundColor Green
}

# Set Oxylabs credentials if not already set (for YouTube scraping)
if (-not $env:OXYLABS_USERNAME) {
    $env:OXYLABS_USERNAME = "usrsh10151"
    Write-Host "✅ Oxylabs Username set for YouTube scraping" -ForegroundColor Green
}
if (-not $env:OXYLABS_PASSWORD) {
    $env:OXYLABS_PASSWORD = "5vheo3r2m71rmoxkp0suwj82"
    Write-Host "✅ Oxylabs Password set for YouTube scraping" -ForegroundColor Green
}
if (-not $env:OXYLABS_ENDPOINT) {
    $env:OXYLABS_ENDPOINT = "nam1bd158a6d4buib42a7xdx.hbproxy.net"
    Write-Host "✅ Oxylabs Endpoint set for YouTube scraping" -ForegroundColor Green
}

# Set R2 credentials if not already set
if (-not $env:R2_ACCESS_KEY_ID) {
    $env:R2_ACCESS_KEY_ID = "5068efe15645d5f08368a5b22a811746"
    Write-Host "✅ R2 Access Key ID set" -ForegroundColor Green
}
if (-not $env:R2_SECRET_ACCESS_KEY) {
    $env:R2_SECRET_ACCESS_KEY = "f87a4caf85c89ada324027f17911e49dd66ea3e0953ce3c313960373d7a6a3a9"
    Write-Host "✅ R2 Secret Access Key set" -ForegroundColor Green
}

# Check R2 credentials (informational only)
if (-not $env:R2_ACCESS_KEY_ID -or -not $env:R2_SECRET_ACCESS_KEY) {
    Write-Host "⚠️  R2 credentials not set. R2 upload will be disabled." -ForegroundColor Yellow
    Write-Host "   Set R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY to enable Cloudflare R2 storage." -ForegroundColor Yellow
    Write-Host "   See R2_SETUP.md for instructions." -ForegroundColor Yellow
} else {
    Write-Host "✅ R2 credentials found - Cloudflare R2 storage enabled" -ForegroundColor Green
}

# Check if port 8001 is in use
Write-Host "`nChecking port 8001..." -ForegroundColor Yellow
$portInUse = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "⚠️  Port 8001 is in use" -ForegroundColor Yellow
    Write-Host "   Killing existing process..." -ForegroundColor Yellow
    Stop-Process -Id $portInUse.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Start the backend server
Write-Host "`n✅ Starting backend server on port 8001..." -ForegroundColor Green
Write-Host "   Server will be available at: http://localhost:8001" -ForegroundColor Cyan
Write-Host "   Press CTRL+C to stop the server`n" -ForegroundColor Yellow

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

