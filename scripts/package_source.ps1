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

$relPaths = @()
try {
    $gitCmd = Get-Command git -ErrorAction Stop
    $tracked = & $gitCmd.Source -C $repoRoot ls-files
    if ($LASTEXITCODE -ne 0 -or -not $tracked) {
        throw "git ls-files failed"
    }
    $relPaths = $tracked | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
} catch {
    $excludeTop = @(".venv", ".venv_portable_cpu", ".git", "build", "dist", "release", "verify_1_0")
    $excludeFragment = @(
        "\__pycache__\",
        "\.pytest_cache\",
        "\.runtime_venv\",
        "\.tmp\",
        "\.pip_cache\"
    )
    $excludeFilePattern = @(
        "*.pt",
        "*.csv",
        "*.jsonl",
        "*.log",
        "*.spec"
    )
    $relPaths = Get-ChildItem -Path $repoRoot -Recurse -File | Where-Object {
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
    } | ForEach-Object { $_.FullName.Substring($repoRoot.Length).TrimStart("\") }
}

foreach ($rel in $relPaths) {
    $sourcePath = Join-Path $repoRoot $rel
    if (-not (Test-Path $sourcePath)) {
        continue
    }
    $dest = Join-Path $stageDir $rel
    $destDir = Split-Path -Parent $dest
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    Copy-Item -Path $sourcePath -Destination $dest -Force
}

Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $zipPath -CompressionLevel Optimal
Remove-Item -Recurse -Force $stageDir

Write-Host "Source package created: $zipPath" -ForegroundColor Green
