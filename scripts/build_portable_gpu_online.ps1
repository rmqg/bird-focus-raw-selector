$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$releaseDir = Join-Path $repoRoot "release"
$templateDir = Join-Path $repoRoot "packaging\gpu_online"

if (-not (Test-Path $templateDir)) {
    throw "GPU online template directory not found: $templateDir"
}

if (-not (Test-Path $releaseDir)) {
    New-Item -ItemType Directory -Path $releaseDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$portableDirName = "bird-select-portable-win64_gpu-online_$timestamp"
$portableDir = Join-Path $releaseDir $portableDirName
$zipPath = "$portableDir.zip"

if (Test-Path $portableDir) {
    Remove-Item -Recurse -Force $portableDir
}
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

New-Item -ItemType Directory -Path $portableDir | Out-Null

Copy-Item -Path (Join-Path $repoRoot "bird_select") -Destination (Join-Path $portableDir "bird_select") -Recurse -Force
Copy-Item -Path (Join-Path $repoRoot "pyproject.toml") -Destination (Join-Path $portableDir "pyproject.toml") -Force
Copy-Item -Path (Join-Path $repoRoot "requirements.txt") -Destination (Join-Path $portableDir "requirements.txt") -Force
Copy-Item -Path (Join-Path $repoRoot "requirements-cpu.txt") -Destination (Join-Path $portableDir "requirements-cpu.txt") -Force
Copy-Item -Path (Join-Path $repoRoot "requirements-gpu-cu128.txt") -Destination (Join-Path $portableDir "requirements-gpu-cu128.txt") -Force
Copy-Item -Path (Join-Path $repoRoot "README.md") -Destination (Join-Path $portableDir "README.md") -Force
Copy-Item -Path (Join-Path $repoRoot "LICENSE") -Destination (Join-Path $portableDir "LICENSE") -Force

Copy-Item -Path (Join-Path $templateDir "*") -Destination $portableDir -Recurse -Force

$docsDir = Join-Path $portableDir "docs"
New-Item -ItemType Directory -Path $docsDir -Force | Out-Null
Copy-Item -Path (Join-Path $repoRoot "docs\FRIEND_QUICK_START_CN.md") -Destination $docsDir -Force
Copy-Item -Path (Join-Path $repoRoot "docs\TROUBLESHOOTING_CN.md") -Destination $docsDir -Force

Compress-Archive -Path (Join-Path $portableDir "*") -DestinationPath $zipPath -CompressionLevel Optimal
Write-Host "GPU online portable package created: $zipPath" -ForegroundColor Green
