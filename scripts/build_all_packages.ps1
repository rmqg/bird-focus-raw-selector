param(
    [switch]$BuildCpuPortable = $true,
    [switch]$BuildGpuPortable = $false,
    [switch]$BuildGpuOnlinePortable = $true
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Generating source package..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File (Join-Path $scriptDir "package_source.ps1")

if ($BuildGpuPortable) {
    Write-Host "Generating GPU portable package..." -ForegroundColor Cyan
    powershell -ExecutionPolicy Bypass -File (Join-Path $scriptDir "build_portable_gpu.ps1")
}

if ($BuildGpuOnlinePortable) {
    Write-Host "Generating GPU online portable package..." -ForegroundColor Cyan
    powershell -ExecutionPolicy Bypass -File (Join-Path $scriptDir "build_portable_gpu_online.ps1")
}

if ($BuildCpuPortable) {
    Write-Host "Generating CPU portable package..." -ForegroundColor Cyan
    powershell -ExecutionPolicy Bypass -File (Join-Path $scriptDir "build_portable_cpu.ps1")
}

Write-Host "All requested packages built successfully." -ForegroundColor Green
