$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$manifest = Join-Path $root "data-workspace\\metadata\\public_seed_manifest.csv"
$ffmpegCandidates = @(
    "ffmpeg",
    "$env:LOCALAPPDATA\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\ffmpeg-8.0.1-full_build\\bin\\ffmpeg.exe"
)

$ffmpeg = $null
foreach ($candidate in $ffmpegCandidates) {
    try {
        if ($candidate -eq "ffmpeg") {
            & $candidate -version *> $null
            $ffmpeg = $candidate
            break
        }
        if (Test-Path $candidate) {
            $ffmpeg = $candidate
            break
        }
    } catch {
    }
}

if (-not $ffmpeg) {
    throw "ffmpeg executable not found."
}

Write-Host "Using ffmpeg: $ffmpeg" -ForegroundColor Cyan

$rows = Import-Csv $manifest
foreach ($row in $rows) {
    if (-not $row.local_raw_path -or -not $row.local_derived_path) {
        continue
    }

    $inputPath = Join-Path $root $row.local_raw_path
    $outputPath = Join-Path $root $row.local_derived_path

    if (-not (Test-Path $inputPath)) {
        continue
    }

    $outputDir = Split-Path -Parent $outputPath
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    }

    if (Test-Path $outputPath) {
        continue
    }

    Write-Host "Normalizing $($row.sound_id) -> $($row.local_derived_path)" -ForegroundColor Yellow
    & $ffmpeg -hide_banner -loglevel error -y -i $inputPath -ac 1 -ar 16000 -sample_fmt s16 $outputPath
}

Write-Host "Normalization finished." -ForegroundColor Green
