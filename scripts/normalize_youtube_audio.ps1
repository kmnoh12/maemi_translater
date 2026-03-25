<# YouTube 매니페스트 오디오 정규화 (16kHz mono WAV 변환)

기존 normalize_manifest_audio.ps1과 동일한 ffmpeg 변환을 수행하되,
YouTube 매니페스트 CSV 형식(local_raw_path, local_derived_path)에 맞춘다.

사용법:
  powershell -ExecutionPolicy Bypass -File .\scripts\normalize_youtube_audio.ps1
  powershell -ExecutionPolicy Bypass -File .\scripts\normalize_youtube_audio.ps1 -ManifestPath .\data-workspace\metadata\youtube_manifest.csv
#>

param(
    [string]$ManifestPath = "",
    [switch]$Overwrite
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

if (-not $ManifestPath) {
    $ManifestPath = Join-Path $root "data-workspace\metadata\youtube_manifest.csv"
}

if (-not (Test-Path $ManifestPath)) {
    throw "Manifest file not found: $ManifestPath"
}

$manifest = Resolve-Path $ManifestPath

# ffmpeg 찾기
$ffmpegCandidates = @(
    "ffmpeg",
    "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"
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

Write-Host "Manifest: $manifest" -ForegroundColor Cyan
Write-Host "ffmpeg: $ffmpeg" -ForegroundColor Cyan

$rows = Import-Csv $manifest
$normalized = 0
$skipped = 0
$failed = 0

foreach ($row in $rows) {
    if (-not $row.local_raw_path -or -not $row.local_derived_path) {
        continue
    }

    # status가 downloaded 아닌 항목은 스킵
    if ($row.status -and $row.status -ne "downloaded") {
        continue
    }

    $inputPath = Join-Path $root $row.local_raw_path
    $outputPath = Join-Path $root $row.local_derived_path

    if (-not (Test-Path -LiteralPath $inputPath)) {
        continue
    }

    $outputDir = Split-Path -Parent $outputPath
    if (-not (Test-Path -LiteralPath $outputDir)) {
        New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    }

    if ((Test-Path -LiteralPath $outputPath) -and -not $Overwrite) {
        $skipped++
        continue
    }

    Write-Host "Normalizing $($row.video_id) -> $($row.local_derived_path)" -ForegroundColor Yellow
    & $ffmpeg -hide_banner -loglevel error -y -i $inputPath -ac 1 -ar 16000 -sample_fmt s16 $outputPath
    if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $outputPath)) {
        $normalized++
    } else {
        $failed++
        Write-Host "  [ERR] ffmpeg failed for $($row.video_id)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Normalized: $normalized" -ForegroundColor Green
Write-Host "Skipped (already exists): $skipped" -ForegroundColor Gray
Write-Host "Failed: $failed" -ForegroundColor Red
Write-Host "Done." -ForegroundColor Green
