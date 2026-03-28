param(
    [ValidateSet("dry-run", "copy")]
    [string]$Mode = "dry-run",
    [ValidateSet("fast", "quality")]
    [string]$Preset = "fast",
    [string]$Source = "",
    [string]$OutputDir = "",
    [string]$LogPath = "",
    [int]$SampleLimit = 0,
    [switch]$NoPause = $false
)

$ErrorActionPreference = "Stop"

function Wait-ForExit {
    if (-not $NoPause) {
        Read-Host "按回车退出" | Out-Null
    }
}

function Read-WithDefault {
    param(
        [string]$Prompt,
        [string]$DefaultValue
    )
    $raw = Read-Host "$Prompt（直接回车使用默认值：$DefaultValue）"
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
        # 文件夹选择器不可用时，回退到手动输入。
    }

    return Read-WithDefault -Prompt $Title -DefaultValue $DefaultValue
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $scriptDir "bird-select.exe"
$modelPath = Join-Path $scriptDir "yolov8s-seg.pt"

if (-not (Test-Path $exePath)) {
    Write-Host "未找到可执行文件: $exePath" -ForegroundColor Red
    Wait-ForExit
    exit 1
}
if (-not (Test-Path $modelPath)) {
    Write-Host "未找到模型文件: $modelPath" -ForegroundColor Red
    Write-Host "请先完整解压 zip 再运行。" -ForegroundColor Yellow
    Wait-ForExit
    exit 1
}

if (-not [Environment]::Is64BitOperatingSystem) {
    Write-Host "该便携包仅支持 64 位 Windows。" -ForegroundColor Red
    Wait-ForExit
    exit 1
}

Write-Host ""
Write-Host "鸟类清晰度筛选器（CPU 便携版）" -ForegroundColor Cyan
$modeText = if ($Mode -eq "dry-run") { "仅预览（不复制）" } else { "正式复制" }
$presetText = if ($Preset -eq "fast") { "快速" } else { "高质量" }
Write-Host "运行模式: $modeText | 处理预设: $presetText"
Write-Host ""

if ([string]::IsNullOrWhiteSpace($Source)) {
    $Source = Select-Folder -Title "请选择源文件夹（RAW 根目录）" -DefaultValue "E:\100NZ7_2"
}
if (-not (Test-Path $Source)) {
    Write-Host "源文件夹不存在: $Source" -ForegroundColor Red
    Wait-ForExit
    exit 1
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$defaultOutput = Join-Path $Source "selected_birds_in_focus_$($Preset)_$timestamp"
$defaultLog = Join-Path $Source "bird_focus_selection_$($Mode.Replace('-', ''))_$($Preset)_$timestamp.csv"

if ($Mode -eq "copy" -and [string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Select-Folder -Title "请选择复制后的输出文件夹" -DefaultValue $defaultOutput
}
if ([string]::IsNullOrWhiteSpace($LogPath)) {
    $LogPath = Read-WithDefault -Prompt "日志文件路径" -DefaultValue $defaultLog
}

$args = @(
    "--source", $Source,
    "--exclude-dir-prefixes", "selected_birds_in_focus,raw",
    "--log-format", "csv",
    "--log-path", $LogPath,
    "--device", "cpu",
    "--cpu-workers", "0",
    "--model", $modelPath
)

if ($Mode -eq "dry-run") {
    $args += "--dry-run"
} else {
    $args += @("--output-dir", $OutputDir)
}
if ($SampleLimit -gt 0) {
    $args += @("--sample-limit", "$SampleLimit")
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
Write-Host "开始运行..." -ForegroundColor Green
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
    Write-Host "运行失败: $($_.Exception.Message)" -ForegroundColor Red
    Wait-ForExit
    exit 1
}

Write-Host ""
Write-Host "完成。日志文件: $LogPath" -ForegroundColor Green
Wait-ForExit
