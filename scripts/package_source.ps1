param(
    [string]$OutputName = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$releaseDir = Join-Path $repoRoot "release"
$stageDir = Join-Path $releaseDir "_source_stage"

if (-not (Test-Path $releaseDir)) {
    New-Item -ItemType Directory -Path $releaseDir | Out-Null
}
if (Test-Path $stageDir) {
    Remove-Item -Recurse -Force $stageDir
}
New-Item -ItemType Directory -Path $stageDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
if ([string]::IsNullOrWhiteSpace($OutputName)) {
    $OutputName = "bird-select-source-$timestamp.zip"
}
$zipPath = Join-Path $releaseDir $OutputName
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

$excludeTop = @(".venv", ".venv_portable_cpu", ".git", "build", "dist", "release")
$excludeFragment = @(
    "\__pycache__\",
    "\.pytest_cache\"
)
$excludeFilePattern = @(
    "*.pt",
    "*.csv",
    "*.jsonl",
    "*.log",
    "*.spec"
)

$files = Get-ChildItem -Path $repoRoot -Recurse -File | Where-Object {
    $full = $_.FullName
    $rel = $full.Substring($repoRoot.Length).TrimStart("\")
    $top = ($rel -split "\\")[0]
    if ($excludeTop -contains $top) { return $false }
    foreach ($frag in $excludeFragment) {
        if ($full -like "*$frag*") { return $false }
    }
    foreach ($pat in $excludeFilePattern) {
        if ($_.Name -like $pat) { return $false }
    }
    return $true
}

foreach ($file in $files) {
    $rel = $file.FullName.Substring($repoRoot.Length).TrimStart("\")
    $dest = Join-Path $stageDir $rel
    $destDir = Split-Path -Parent $dest
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    Copy-Item -Path $file.FullName -Destination $dest -Force
}

Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $zipPath -CompressionLevel Optimal
Remove-Item -Recurse -Force $stageDir

Write-Host "Source package created: $zipPath" -ForegroundColor Green
