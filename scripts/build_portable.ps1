param(
    [string]$PythonExe = "",
    [switch]$SkipBuild = $false,
    [string]$PackageSuffix = "default",
    [string]$TemplateDir = "",
    [switch]$EmbedPython = $false
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$releaseDir = Join-Path $repoRoot "release"
$distDir = Join-Path $repoRoot "dist\bird-select"
if ([string]::IsNullOrWhiteSpace($TemplateDir)) {
    $portableTemplateDir = Join-Path $repoRoot "packaging\portable"
} else {
    if ([System.IO.Path]::IsPathRooted($TemplateDir)) {
        $portableTemplateDir = $TemplateDir
    } else {
        $portableTemplateDir = Join-Path $repoRoot $TemplateDir
    }
}

if (-not (Test-Path $portableTemplateDir)) {
    throw "Template directory not found: $portableTemplateDir"
}

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $PythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
}
if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}
if (-not (Test-Path (Join-Path $repoRoot "yolov8s-seg.pt"))) {
    throw "Model weight not found: yolov8s-seg.pt"
}

if (-not (Test-Path $releaseDir)) {
    New-Item -ItemType Directory -Path $releaseDir | Out-Null
}

if (-not $SkipBuild) {
    Write-Host "Installing/updating PyInstaller..." -ForegroundColor Cyan
    & $PythonExe -m pip install --upgrade pyinstaller

    Write-Host "Building Windows portable executable (onedir)..." -ForegroundColor Cyan
    Push-Location $repoRoot
    try {
        $buildArgs = @(
            "-m", "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--name", "bird-select",
            "--collect-all", "ultralytics",
            "--collect-all", "rawpy",
            "--collect-all", "cv2",
            "--collect-all", "numpy",
            "--hidden-import", "torch",
            "--hidden-import", "torchvision",
            "--hidden-import", "torchaudio",
            "--add-data", "yolov8s-seg.pt:.",
            "portable_entry.py"
        )
        & $PythonExe @buildArgs
    } finally {
        Pop-Location
    }
}

if (-not (Test-Path (Join-Path $distDir "bird-select.exe"))) {
    throw "Portable executable was not built successfully: $distDir\bird-select.exe"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$safeSuffix = if ([string]::IsNullOrWhiteSpace($PackageSuffix)) { "default" } else { $PackageSuffix }
$portableDirName = "bird-select-portable-win64_$safeSuffix" + "_$timestamp"
$portableDir = Join-Path $releaseDir $portableDirName
$zipPath = "$portableDir.zip"

if (Test-Path $portableDir) {
    Remove-Item -Recurse -Force $portableDir
}
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

New-Item -ItemType Directory -Path $portableDir | Out-Null
Copy-Item -Path (Join-Path $distDir "*") -Destination $portableDir -Recurse -Force
Copy-Item -Path (Join-Path $portableTemplateDir "*") -Destination $portableDir -Recurse -Force
Copy-Item -Path (Join-Path $repoRoot "yolov8s-seg.pt") -Destination (Join-Path $portableDir "yolov8s-seg.pt") -Force

if ($EmbedPython) {
    Write-Host "Embedding Python runtime..." -ForegroundColor Cyan
    $pythonBase = (& $PythonExe -c "import sys; print(sys.base_prefix)").Trim()
    if (-not $pythonBase) {
        throw "Cannot detect Python base prefix from: $PythonExe"
    }
    if (-not (Test-Path (Join-Path $pythonBase "python.exe"))) {
        throw "Python base directory is invalid: $pythonBase"
    }
    $pythonRuntimeDir = Join-Path $portableDir "python_runtime"
    Copy-Item -Path $pythonBase -Destination $pythonRuntimeDir -Recurse -Force
}

$docsDir = Join-Path $portableDir "docs"
$templateDocsDir = Join-Path $portableTemplateDir "docs"
if (Test-Path $templateDocsDir) {
    Copy-Item -Path $templateDocsDir -Destination $portableDir -Recurse -Force
} else {
    New-Item -ItemType Directory -Path $docsDir -Force | Out-Null
    Copy-Item -Path (Join-Path $repoRoot "docs\FRIEND_QUICK_START_CN.md") -Destination $docsDir -Force
    Copy-Item -Path (Join-Path $repoRoot "docs\TROUBLESHOOTING_CN.md") -Destination $docsDir -Force
}

Compress-Archive -Path (Join-Path $portableDir "*") -DestinationPath $zipPath -CompressionLevel Optimal
Write-Host "Portable package created: $zipPath" -ForegroundColor Green
