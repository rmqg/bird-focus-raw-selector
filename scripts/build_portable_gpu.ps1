$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "GPU build venv not found: $pythonExe"
}

Write-Host "Installing GPU dependencies..." -ForegroundColor Cyan
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r (Join-Path $repoRoot "requirements-gpu-cu128.txt")

Write-Host "Building GPU portable package..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "build_portable.ps1") `
    -PythonExe $pythonExe `
    -PackageSuffix "gpu-cu128"
