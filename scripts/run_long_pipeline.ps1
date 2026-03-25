$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$logDir = Join-Path $root "ml-workspace\reports\ops_logs"
$logPath = Join-Path $logDir ("long_pipeline_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

if (-not (Test-Path $python)) {
    throw ".venv Python not found. Set up environment first."
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

Push-Location $root
try {
    "START $(Get-Date -Format o)" | Out-File -FilePath $logPath -Encoding UTF8
    & $python .\scripts\build_manifest_inventory.py .\data-workspace\metadata\inat_full_manifest.csv .\ml-workspace\reports\inat_full_inventory.csv 2>&1 | Tee-Object -FilePath $logPath -Append
    & $python .\scripts\build_dataset_health_report.py 2>&1 | Tee-Object -FilePath $logPath -Append
    & $python .\scripts\precompute_dashboard_predictions.py 2>&1 | Tee-Object -FilePath $logPath -Append
    & $python .\scripts\build_korea_prediction_report.py 2>&1 | Tee-Object -FilePath $logPath -Append
    & $python .\scripts\build_confusion_pair_report.py 2>&1 | Tee-Object -FilePath $logPath -Append
    powershell -ExecutionPolicy Bypass -File .\scripts\build_preview_clips.ps1 2>&1 | Tee-Object -FilePath $logPath -Append
    & $python .\scripts\build_dashboard_payload.py 2>&1 | Tee-Object -FilePath $logPath -Append
    "END $(Get-Date -Format o)" | Out-File -FilePath $logPath -Encoding UTF8 -Append
    Write-Host "Long pipeline completed."
    Write-Host "Log written to $logPath"
} finally {
    Pop-Location
}
