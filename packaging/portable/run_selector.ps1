param(
    [ValidateSet("dry-run", "copy")]
    [string]$Mode = "dry-run",
    [ValidateSet("fast", "quality")]
    [string]$Preset = "fast"
)

$ErrorActionPreference = "Stop"

function Read-WithDefault {
    param(
        [string]$Prompt,
        [string]$DefaultValue
    )
    $raw = Read-Host "$Prompt (press Enter to use default: $DefaultValue)"
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return $DefaultValue
    }
    return $raw
}

function Select-Folder {
    param(
        [string]$Title,
        [string]$DefaultValue
    )

    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop | Out-Null
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = $Title
        if (-not [string]::IsNullOrWhiteSpace($DefaultValue) -and (Test-Path $DefaultValue)) {
            $dialog.SelectedPath = $DefaultValue
        }
        $result = $dialog.ShowDialog()
        if ($result -eq [System.Windows.Forms.DialogResult]::OK -and -not [string]::IsNullOrWhiteSpace($dialog.SelectedPath)) {
            return $dialog.SelectedPath
        }
    } catch {
        # GUI picker unavailable; fallback to typed input.
    }

    return Read-WithDefault -Prompt $Title -DefaultValue $DefaultValue
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $scriptDir "bird-select.exe"
$modelPath = Join-Path $scriptDir "yolov8s-seg.pt"

if (-not (Test-Path $exePath)) {
    Write-Host "Executable not found: $exePath" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
if (-not (Test-Path $modelPath)) {
    Write-Host "Model file not found: $modelPath" -ForegroundColor Red
    Write-Host "Please extract the full zip before running." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not [Environment]::Is64BitOperatingSystem) {
    Write-Host "This portable package requires 64-bit Windows." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Bird Focus Selector Portable Launcher" -ForegroundColor Cyan
Write-Host "Mode: $Mode | Preset: $Preset | Device: CPU"
Write-Host ""

$source = Select-Folder -Title "Select source folder (RAW root)" -DefaultValue "E:\100NZ7_2"
if (-not (Test-Path $source)) {
    Write-Host "Source folder does not exist: $source" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$defaultOutput = Join-Path $source "selected_birds_in_focus_$($Preset)_$timestamp"
$defaultLog = Join-Path $source "bird_focus_selection_$($Mode.Replace('-', ''))_$($Preset)_$timestamp.csv"

$outputDir = $null
if ($Mode -eq "copy") {
    $outputDir = Select-Folder -Title "Select output folder for copied RAW files" -DefaultValue $defaultOutput
}
$logPath = Read-WithDefault -Prompt "Log file path" -DefaultValue $defaultLog

$args = @(
    "--source", $source,
    "--exclude-dir-prefixes", "selected_birds_in_focus,raw",
    "--log-format", "csv",
    "--log-path", $logPath
)

if ($Mode -eq "dry-run") {
    $args += "--dry-run"
} else {
    $args += @("--output-dir", $outputDir)
}

$args += @("--cpu-workers", "0")

$args += @("--model", $modelPath)

if ($Preset -eq "fast") {
    $args += @(
        "--no-prefer-full-raw",
        "--analysis-max-side", "1600",
        "--max-infer-side", "1600",
        "--confidence-threshold", "0.45",
        "--min-bird-area-ratio", "0.004",
        "--min-bird-side", "100",
        "--laplacian-threshold", "2200",
        "--tenengrad-threshold", "36",
        "--tenengrad-p90-threshold", "80",
        "--strong-edge-ratio-threshold", "0.10",
        "--min-focus-pixels", "1200",
        "--min-focus-pixel-ratio", "0.12",
        "--min-mask-fill-ratio", "0.12"
    )
} else {
    $args += @(
        "--prefer-full-raw",
        "--analysis-max-side", "0",
        "--max-infer-side", "0",
        "--confidence-threshold", "0.45",
        "--min-bird-area-ratio", "0.004",
        "--min-bird-side", "120",
        "--laplacian-threshold", "2600",
        "--tenengrad-threshold", "42",
        "--tenengrad-p90-threshold", "100",
        "--strong-edge-ratio-threshold", "0.12",
        "--min-focus-pixels", "1400",
        "--min-focus-pixel-ratio", "0.12",
        "--min-mask-fill-ratio", "0.12"
    )
}

Write-Host ""
Write-Host "Running..." -ForegroundColor Green
Write-Host "$exePath $($args -join ' ')" -ForegroundColor DarkGray
Write-Host ""

try {
    Push-Location $scriptDir
    try {
        & $exePath @args
    } finally {
        Pop-Location
    }
} catch {
    Write-Host ""
    Write-Host "Run failed: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Done. Log file: $logPath" -ForegroundColor Green
Read-Host "Press Enter to exit"
