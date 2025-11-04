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

