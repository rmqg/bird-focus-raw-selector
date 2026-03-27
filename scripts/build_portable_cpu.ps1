$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$cpuVenv = Join-Path $repoRoot ".venv_portable_cpu"
$cpuPython = Join-Path $cpuVenv "Scripts\python.exe"

if (-not (Test-Path $cpuPython)) {
    Write-Host "Creating CPU build venv..." -ForegroundColor Cyan
    python -m venv $cpuVenv
}

Write-Host "Installing CPU dependencies..." -ForegroundColor Cyan
& $cpuPython -m pip install --upgrade pip
& $cpuPython -m pip install -r (Join-Path $repoRoot "requirements-cpu.txt")

Write-Host "Building CPU portable package..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "build_portable.ps1") `
    -PythonExe $cpuPython `
    -PackageSuffix "cpu"
