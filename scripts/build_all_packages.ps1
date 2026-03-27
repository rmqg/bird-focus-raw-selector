param(
    [switch]$BuildCpuPortable = $true
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Generating source package..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File (Join-Path $scriptDir "package_source.ps1")

if ($BuildCpuPortable) {
    Write-Host "Generating CPU portable package..." -ForegroundColor Cyan
    powershell -ExecutionPolicy Bypass -File (Join-Path $scriptDir "build_portable_cpu.ps1")
}

Write-Host "All requested packages built successfully." -ForegroundColor Green
