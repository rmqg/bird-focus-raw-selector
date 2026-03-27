param(
    [string]$ExePath = "E:\bird_select\dist\bird-select\bird-select.exe",
    [string]$SampleSource = "E:\100NZ7_2"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ExePath)) {
    throw "Executable not found: $ExePath"
}
if (-not (Test-Path $SampleSource)) {
    throw "Sample source not found: $SampleSource"
}

$logPath = Join-Path $SampleSource ("portable_check_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".csv")

Write-Host "Smoke-checking portable executable..." -ForegroundColor Cyan
& $ExePath --help | Out-Null
& $ExePath `
    --dry-run `
    --source $SampleSource `
    --sample-limit 1 `
    --log-format csv `
    --log-path $logPath | Out-Null

if (-not (Test-Path $logPath)) {
    throw "Smoke check failed: log not created."
}

Write-Host "Release check passed. Log: $logPath" -ForegroundColor Green
