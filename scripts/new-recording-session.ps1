param(
    [Parameter(Mandatory = $true)]
    [string]$SpeciesCode,

    [Parameter(Mandatory = $true)]
    [string]$LocationCode,

    [string]$DateString = (Get-Date -Format "yyyyMMdd")
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$speciesDir = Join-Path $root ("data-workspace\\raw_audio\\field_sessions\\" + $SpeciesCode)
if (-not (Test-Path $speciesDir)) {
    New-Item -ItemType Directory -Force -Path $speciesDir | Out-Null
}

$existing = Get-ChildItem $speciesDir -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "${SpeciesCode}_${DateString}_${LocationCode}_*" } |
    Select-Object -ExpandProperty Name

$nextSequence = 1
if ($existing) {
    $numbers = $existing | ForEach-Object {
        $parts = $_ -split "_"
        $parts[-1]
    } | Where-Object { $_ -match '^\d+$' } | ForEach-Object { [int]$_ }

    if ($numbers) {
        $nextSequence = (($numbers | Measure-Object -Maximum).Maximum + 1)
    }
}

$sequence = "{0:D3}" -f $nextSequence
$sessionId = "${SpeciesCode}_${DateString}_${LocationCode}_${sequence}"
$sessionPath = Join-Path $speciesDir $sessionId

New-Item -ItemType Directory -Force -Path $sessionPath | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $sessionPath "photos") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $sessionPath "notes") | Out-Null

$readmePath = Join-Path $sessionPath "README.txt"
if (-not (Test-Path $readmePath)) {
    @"
session_id=$sessionId
species_code=$SpeciesCode
location_code=$LocationCode
date=$DateString
todo=copy raw audio here and fill metadata CSV
"@ | Set-Content -Encoding UTF8 $readmePath
}

Write-Host "Created session: $sessionId" -ForegroundColor Green
Write-Host $sessionPath
