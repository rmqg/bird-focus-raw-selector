param(
    [ValidateSet("dry-run", "copy")]
    [string]$Mode = "dry-run",
    [ValidateSet("fast", "quality")]
    [string]$Preset = "fast",
    [ValidateSet("gpu", "cpu")]
    [string]$DevicePreset = "cpu"
)

$ErrorActionPreference = "Stop"

function Read-WithDefault {
    param(
        [string]$Prompt,
        [string]$DefaultValue
    )
    $raw = Read-Host "$Prompt (直接回车使用默认: $DefaultValue)"
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return $DefaultValue
    }
    return $raw
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $scriptDir "bird-select.exe"

if (-not (Test-Path $exePath)) {
    Write-Host "未找到可执行文件: $exePath" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

Write-Host ""
Write-Host "Bird Focus Selector 便携启动器" -ForegroundColor Cyan
Write-Host "模式: $Mode | 预设: $Preset | 设备: $DevicePreset"
Write-Host ""

$source = Read-WithDefault -Prompt "请输入源目录" -DefaultValue "E:\100NZ7_2"
if (-not (Test-Path $source)) {
    Write-Host "源目录不存在: $source" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$defaultOutput = Join-Path $source "selected_birds_in_focus_$($Preset)_$timestamp"
$defaultLog = Join-Path $source "bird_focus_selection_$($Mode.Replace('-', ''))_$($Preset)_$timestamp.csv"

$outputDir = $null
if ($Mode -eq "copy") {
    $outputDir = Read-WithDefault -Prompt "请输入输出目录" -DefaultValue $defaultOutput
}
$logPath = Read-WithDefault -Prompt "请输入日志文件路径" -DefaultValue $defaultLog

$args = @(
    "--source", $source,
    "--log-format", "csv",
    "--log-path", $logPath
)

if ($Mode -eq "dry-run") {
    $args += "--dry-run"
} else {
    $args += @("--output-dir", $outputDir)
}

if ($DevicePreset -eq "gpu") {
    $args += @("--device", "0")
} else {
    $args += @("--device", "cpu")
}

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
Write-Host "开始执行..." -ForegroundColor Green
Write-Host "$exePath $($args -join ' ')" -ForegroundColor DarkGray
Write-Host ""

try {
    & $exePath @args
} catch {
    Write-Host ""
    Write-Host "运行失败: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

Write-Host ""
Write-Host "执行完成。日志路径: $logPath" -ForegroundColor Green
Read-Host "按回车退出"
