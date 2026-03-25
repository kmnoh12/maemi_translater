$ErrorActionPreference = "Stop"

$python = "py -3.12"
$venvPath = Join-Path $PSScriptRoot "..\\.venv"
$requirements = Join-Path $PSScriptRoot "..\\requirements\\core-ml.txt"

Write-Host "== Setup ML Environment ==" -ForegroundColor Cyan

if (-not (Test-Path $requirements)) {
    throw "Requirements file not found: $requirements"
}

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment with Python 3.12..." -ForegroundColor Yellow
    & py -3.12 -m venv $venvPath
} else {
    Write-Host "Virtual environment already exists: $venvPath" -ForegroundColor Yellow
}

$venvPython = Join-Path $venvPath "Scripts\\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Virtual environment python not found: $venvPython"
}

Write-Host "Upgrading pip..." -ForegroundColor Yellow
& $venvPython -m pip install --upgrade pip setuptools wheel

Write-Host "Installing core ML/audio packages..." -ForegroundColor Yellow
& $venvPython -m pip install -r $requirements

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Activate with: .\\.venv\\Scripts\\Activate.ps1"
