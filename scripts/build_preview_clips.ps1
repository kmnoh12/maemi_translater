$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$cachePath = Join-Path $root "dashboard\prediction_cache.json"
$outDir = Join-Path $root "dashboard\assets\preview_clips"

if (-not (Test-Path $cachePath)) {
    throw "prediction_cache.json not found. Run precompute_dashboard_predictions.py first."
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    $wingetPath = "C:\Users\kmnoh\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe"
    if (Test-Path $wingetPath) {
        $ffmpegExe = $wingetPath
    } else {
        throw "ffmpeg not found."
    }
} else {
    $ffmpegExe = $ffmpeg.Source
}

$json = Get-Content $cachePath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($item in $json.items) {
    $source = Join-Path $root $item.audio_path
    $target = Join-Path $outDir ("{0}_sound{1}_preview.mp3" -f $item.species_code, $item.sound_id)
    if (Test-Path $target) {
        continue
    }
    & $ffmpegExe -y -hide_banner -loglevel error -ss 0 -t 5 -i $source -ar 16000 -ac 1 -codec:a libmp3lame -b:a 96k $target
    Write-Host "Created preview clip $target"
}
