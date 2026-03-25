$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$dashboardDir = Join-Path $root "dashboard"
$pythonCmd = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonCmd)) {
    throw "Required venv python not found at $pythonCmd"
}

$port = 8765
Write-Host "Starting dashboard app at http://127.0.0.1:$port/dashboard/index.html"
Push-Location $root
try {
    $env:PYTHONIOENCODING = "utf-8"
    & $pythonCmd ".\scripts\run_dashboard_app.py"
} finally {
    Pop-Location
}
