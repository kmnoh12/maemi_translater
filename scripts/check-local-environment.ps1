$ErrorActionPreference = "Stop"

Write-Host "== Local Environment Check ==" -ForegroundColor Cyan

$pythonEntries = & py -0p 2>$null
if ($LASTEXITCODE -eq 0 -and $pythonEntries) {
    Write-Host ""
    Write-Host "[Python installs]" -ForegroundColor Yellow
    $pythonEntries | ForEach-Object { Write-Host $_ }
} else {
    Write-Host "Python launcher output not available." -ForegroundColor Red
}

Write-Host ""
Write-Host "[Current python]" -ForegroundColor Yellow
try {
    python --version
} catch {
    Write-Host "python command not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "[Node]" -ForegroundColor Yellow
try {
    node --version
} catch {
    Write-Host "node command not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "[Git]" -ForegroundColor Yellow
try {
    git --version
} catch {
    Write-Host "git command not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "[winget]" -ForegroundColor Yellow
try {
    winget --version
} catch {
    Write-Host "winget command not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "[ffmpeg]" -ForegroundColor Yellow
try {
    ffmpeg -version | Select-Object -First 1
} catch {
    Write-Host "ffmpeg not found in PATH" -ForegroundColor Red
}

Write-Host ""
Write-Host "[Recommendation]" -ForegroundColor Green
Write-Host "- Install Python 3.12 for ML/audio compatibility."
Write-Host "- Install ffmpeg and add it to PATH."
Write-Host "- Keep raw audio immutable and log every recording session."
