param(
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$releaseDir = Join-Path $repoRoot "release"
$templateDir = Join-Path $repoRoot "packaging\gpu_online"

if (-not (Test-Path $templateDir)) {
    throw "GPU template directory not found: $templateDir"
}

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        throw "Python command not found. Please install Python 3.10+ or pass -PythonExe."
    }
    $PythonExe = $pythonCmd.Source
}
if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}

$pythonBase = (& $PythonExe -c "import sys; print(sys.base_prefix)").Trim()
if (-not $pythonBase) {
    throw "Cannot detect Python base prefix from: $PythonExe"
}
if (-not (Test-Path (Join-Path $pythonBase "python.exe"))) {
    throw "Python base directory is invalid: $pythonBase"
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

# App source files
Copy-Item -Path (Join-Path $repoRoot "bird_select") -Destination (Join-Path $portableDir "bird_select") -Recurse -Force
Copy-Item -Path (Join-Path $repoRoot "pyproject.toml") -Destination (Join-Path $portableDir "pyproject.toml") -Force
Copy-Item -Path (Join-Path $repoRoot "requirements.txt") -Destination (Join-Path $portableDir "requirements.txt") -Force
Copy-Item -Path (Join-Path $repoRoot "requirements-gpu-cu128.txt") -Destination (Join-Path $portableDir "requirements-gpu-cu128.txt") -Force
Copy-Item -Path (Join-Path $repoRoot "LICENSE") -Destination (Join-Path $portableDir "LICENSE") -Force

# Template launcher files
Copy-Item -Path (Join-Path $templateDir "*") -Destination $portableDir -Recurse -Force

# Bundle Python runtime
$pythonRuntimeDir = Join-Path $portableDir "python_runtime"
Copy-Item -Path $pythonBase -Destination $pythonRuntimeDir -Recurse -Force

# Bundle model if present (script can auto-download if missing)
$modelPath = Join-Path $repoRoot "yolov8s-seg.pt"
if (Test-Path $modelPath) {
    Copy-Item -Path $modelPath -Destination (Join-Path $portableDir "yolov8s-seg.pt") -Force
}

# Copy docs from GPU template docs if present; otherwise fallback to root docs
$templateDocsDir = Join-Path $templateDir "docs"
if (Test-Path $templateDocsDir) {
    Copy-Item -Path $templateDocsDir -Destination $portableDir -Recurse -Force
} else {
    $docsDir = Join-Path $portableDir "docs"
    New-Item -ItemType Directory -Path $docsDir -Force | Out-Null
    Copy-Item -Path (Join-Path $repoRoot "docs\FRIEND_QUICK_START_CN.md") -Destination $docsDir -Force
    Copy-Item -Path (Join-Path $repoRoot "docs\TROUBLESHOOTING_CN.md") -Destination $docsDir -Force
}

Compress-Archive -Path (Join-Path $portableDir "*") -DestinationPath $zipPath -CompressionLevel Optimal
Write-Host "GPU online portable package created: $zipPath" -ForegroundColor Green
