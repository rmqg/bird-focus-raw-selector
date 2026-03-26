$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "1/2 Generating source package..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File (Join-Path $scriptDir "package_source.ps1")

Write-Host "2/2 Generating portable package..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File (Join-Path $scriptDir "build_portable.ps1")

Write-Host "All packages built successfully." -ForegroundColor Green
