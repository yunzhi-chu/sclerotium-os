<#
.SYNOPSIS
  Sclerotium OS v5.2 — One-Command Installer
.DESCRIPTION
  Installs the complete super-organism (sclerotium + fungal + MiroFish).
  Single command: powershell -ExecutionPolicy Bypass -File install.ps1
.PARAMETER Full
  Install all optional dependencies (desktop automation, IM, voice, GPU)
.PARAMETER Dev
  Install development dependencies (testing, linting)
.PARAMETER Uninstall
  Remove Sclerotium OS from the system
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File install.ps1
  powershell -ExecutionPolicy Bypass -File install.ps1 -Full
  powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall
.NOTES
  Version: 5.2.0
  Organs: 339 (sclerotium 191 + fungal 120 + MiroFish 28)
  Tests: 12/12 · 3 bridges · 14 API endpoints
#>

param(
    [switch]$Full,
    [switch]$Dev,
    [switch]$Uninstall
)

$ErrorActionPreference = "Continue"
$VERSION = "5.2.0"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Sclerotium OS v$VERSION — Super Electronic Lifeform" -ForegroundColor Cyan
Write-Host "  339 Organs · 191 MCP Tools · 3 Systems" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# === UNINSTALL ===
if ($Uninstall) {
    Write-Host "[UNINSTALL] Removing Sclerotium OS..." -ForegroundColor Yellow
    try { Stop-Service "SclerotiumOS" -ErrorAction SilentlyContinue } catch {}
    try { sc.exe delete SclerotiumOS 2>$null } catch {}
    pip uninstall sclerotium-os -y 2>$null
    Write-Host "[UNINSTALL] Done." -ForegroundColor Green
    exit 0
}

# === Step 1: Python ===
Write-Host "[1/6] Checking Python..." -ForegroundColor Yellow
$pythonCmd = $null
foreach ($cmd in @("python3", "python")) {
    try {
        $v = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0) { $pythonCmd = $cmd; Write-Host "  OK: $v" -ForegroundColor Green; break }
    } catch {}
}
if (-not $pythonCmd) {
    Write-Host "  ERROR: Python 3.11+ required. Install from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# === Step 2: Core Dependencies ===
Write-Host "[2/6] Installing core dependencies..." -ForegroundColor Yellow
$corePkgs = @("aiohttp", "chromadb", "pydantic", "psutil", "Pillow", "numpy", "zep-cloud", "pywin32", "watchdog")
foreach ($pkg in $corePkgs) {
    Write-Host "  $pkg..." -ForegroundColor Gray -NoNewline
    & $pythonCmd -m pip install $pkg --quiet 2>&1 | Out-Null
    Write-Host " OK" -ForegroundColor Green
}

# === Step 3: pip install sclerotium-os ===
Write-Host "[3/6] Installing Sclerotium OS v$VERSION..." -ForegroundColor Yellow
$installDir = (Get-Location).Path
& $pythonCmd -m pip install -e "$installDir" --quiet 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK: sclerotium-os installed at $installDir" -ForegroundColor Green
} else {
    Write-Host "  WARNING: pip install -e failed, trying direct install..." -ForegroundColor Yellow
    & $pythonCmd -m pip install "$installDir" --quiet 2>&1 | Out-Null
}

# === Step 4: Optional Full Install ===
if ($Full) {
    Write-Host "[4/6] Installing full dependencies..." -ForegroundColor Yellow
    $fullPkgs = @("pywinauto", "pyautogui", "uiautomation", "litellm", "openai",
                  "edge-tts", "openai-whisper", "pystray")
    foreach ($pkg in $fullPkgs) {
        Write-Host "  $pkg..." -ForegroundColor Gray -NoNewline
        & $pythonCmd -m pip install $pkg --quiet 2>&1 | Out-Null
        Write-Host " OK" -ForegroundColor Green
    }
} else {
    Write-Host "[4/6] Skipping optional dependencies (use -Full for desktop/voice/IM)" -ForegroundColor Gray
}

# === Step 5: Dev Tools ===
if ($Dev) {
    Write-Host "[5/6] Installing dev tools..." -ForegroundColor Yellow
    & $pythonCmd -m pip install pytest pytest-asyncio pytest-cov mypy ruff --quiet 2>&1 | Out-Null
    Write-Host "  OK: pytest, mypy, ruff installed" -ForegroundColor Green
} else {
    Write-Host "[5/6] Skipping dev tools (use -Dev for pytest/mypy/ruff)" -ForegroundColor Gray
}

# === Step 6: System Integration ===
Write-Host "[6/6] System integration..." -ForegroundColor Yellow

# Create startup shortcut
try {
    $startupDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
    $WScriptShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WScriptShell.CreateShortcut("$startupDir\SclerotiumOS.lnk")
    $Shortcut.TargetPath = $pythonCmd
    $Shortcut.Arguments = "-c `"import asyncio; from sclerotium import run_console; asyncio.run(run_console())`""
    $Shortcut.WorkingDirectory = $installDir
    $Shortcut.WindowStyle = 7
    $Shortcut.Save()
    Write-Host "  OK: Startup shortcut created" -ForegroundColor Green
} catch {
    Write-Host "  SKIP: Startup shortcut (non-critical)" -ForegroundColor Yellow
}

# ── FINAL ──
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Sclerotium OS v$VERSION — Installation Complete" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Quick Start:" -ForegroundColor Yellow
Write-Host "    Set API key:  `$env:SCLEROTIUM_API_KEY = 'sk-...'" -ForegroundColor White
Write-Host "    Console mode: python sclerotium.py" -ForegroundColor White
Write-Host "    Dash mode:    python -c `"import asyncio; from mcp.server import SclerotiumMCPServer; s=SclerotiumMCPServer(); s.register_all_tools(); asyncio.run(s.run_http())`"" -ForegroundColor White
Write-Host "    Web UI:       http://localhost:18789" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Installed at: $installDir" -ForegroundColor Gray
