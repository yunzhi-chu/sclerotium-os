# Fungal Cortex v2.0 — One-Click Startup (PowerShell)
# Usage: .\start.ps1 [-NoFrontend] [-NoChroma] [-Seed] [-Check]
param(
    [switch]$NoFrontend,
    [switch]$NoChroma,
    [switch]$Seed,
    [switch]$Check,
    [switch]$SkipDeps
)

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$FRONTEND_DIR = "$ROOT\cortex-frontend"

Write-Host ""
Write-Host "  Fungal Cortex v2.0 — L6-Complete Agent OS" -ForegroundColor Cyan
Write-Host "  One-Click Startup Launcher" -ForegroundColor Cyan
Write-Host ""

# ── Prerequisites ──────────────────────────────────────────────────────
Write-Host "── Prerequisites ──"

try {
    $pyVer = python --version 2>&1
    Write-Host "  [OK] $pyVer" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] Python 3.10+ is required" -ForegroundColor Red
    exit 1
}

if (-not $NoFrontend) {
    try {
        $nodeVer = node --version 2>&1
        Write-Host "  [OK] Node.js $nodeVer" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Node.js 18+ is required" -ForegroundColor Red
        exit 1
    }
}

if ($Check) {
    Write-Host ""
    Write-Host "  All prerequisites satisfied" -ForegroundColor Green
    exit 0
}

# ── Dependencies ───────────────────────────────────────────────────────
if (-not $SkipDeps) {
    Write-Host ""
    Write-Host "── Python Dependencies ──"
    pip install -e $ROOT --quiet 2>$null
    Write-Host "  [OK] Python dependencies ready" -ForegroundColor Green

    if (-not $NoFrontend) {
        Write-Host ""
        Write-Host "── Node.js Dependencies ──"
        if (Test-Path "$FRONTEND_DIR\node_modules") {
            Write-Host "  [OK] Node modules already installed" -ForegroundColor Green
        } else {
            Write-Host "  [ .. ] Installing..." -ForegroundColor Gray
            Push-Location $FRONTEND_DIR
            npm install --legacy-peer-deps
            Pop-Location
            Write-Host "  [OK] Node dependencies installed" -ForegroundColor Green
        }
    }
}

# ── ChromaDB (optional) ────────────────────────────────────────────────
if (-not $NoChroma) {
    Write-Host ""
    Write-Host "── ChromaDB ──"
    try {
        $chromaRunning = docker ps --filter "name=cortex-chromadb" --format "{{.Names}}" 2>$null
        if ($chromaRunning) {
            Write-Host "  [OK] ChromaDB already running" -ForegroundColor Green
        } else {
            Start-Process docker -ArgumentList "run -d --rm --name cortex-chromadb -p 8001:8000 chromadb/chroma:latest" -NoNewWindow -Wait
            Write-Host "  [OK] ChromaDB started on port 8001" -ForegroundColor Green
        }
    } catch {
        Write-Host "  [WARN] Docker not available — skipping ChromaDB" -ForegroundColor Yellow
    }
}

# ── Start Services ─────────────────────────────────────────────────────
$backendJob = $null
$frontendJob = $null

Write-Host ""
Write-Host "── Backend (FastAPI) ──"
$backendJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location $root
    python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --log-level info
} -ArgumentList $ROOT
Write-Host "  [OK] Backend starting..." -ForegroundColor Green
Start-Sleep -Seconds 3

if (-not $NoFrontend) {
    Write-Host ""
    Write-Host "── Frontend (Next.js) ──"
    $frontendJob = Start-Job -ScriptBlock {
        param($dir)
        Set-Location $dir
        npm run dev -- --port 3000
    } -ArgumentList $FRONTEND_DIR
    Write-Host "  [OK] Frontend starting..." -ForegroundColor Green
}

# ── Seed skills ────────────────────────────────────────────────────────
if ($Seed) {
    Write-Host ""
    Write-Host "── Seed Skills ──"
    Start-Sleep -Seconds 3
    python "$FRONTEND_DIR\scripts\seed_skills.py" --api-url http://localhost:8000
    Write-Host "  [OK] 22 demo skills imported" -ForegroundColor Green
}

# ── Dashboard ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ===================================================" -ForegroundColor Green
Write-Host "    All Services Ready!" -ForegroundColor Green
Write-Host "  ===================================================" -ForegroundColor Green
Write-Host ""
Write-Host "    Backend API:  http://localhost:8000"
Write-Host "    API Docs:     http://localhost:8000/docs"
Write-Host "    Health:       http://localhost:8000/api/health"
if (-not $NoFrontend) {
Write-Host "    Frontend:     http://localhost:3000"
}
Write-Host ""
Write-Host "    Press Ctrl+C to stop all services"
Write-Host "  ==================================================="
Write-Host ""

# ── Wait for Ctrl+C ────────────────────────────────────────────────────
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host ""
    Write-Host "── Shutting Down ──"
    if ($backendJob) { Stop-Job $backendJob -ErrorAction SilentlyContinue; Remove-Job $backendJob -ErrorAction SilentlyContinue }
    if ($frontendJob) { Stop-Job $frontendJob -ErrorAction SilentlyContinue; Remove-Job $frontendJob -ErrorAction SilentlyContinue }
    docker stop cortex-chromadb 2>$null
    Write-Host "  All services stopped"
}
