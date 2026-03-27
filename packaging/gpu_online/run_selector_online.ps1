param(
    [ValidateSet("dry-run", "copy")]
    [string]$Mode = "dry-run",
    [ValidateSet("fast", "quality")]
    [string]$Preset = "fast",
    [ValidateSet("gpu", "cpu")]
    [string]$DevicePreset = "gpu",
    [string]$Source = "",
    [string]$OutputDir = "",
    [string]$LogPath = "",
    [int]$SampleLimit = 0,
    [switch]$ForceInstall = $false,
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

function Ensure-PythonCommand {
    $python = Get-Command "python" -ErrorAction SilentlyContinue
    if (-not $python) {
        throw "未找到 Python 3.10+。请先安装 Python：https://www.python.org/downloads/windows/"
    }
    return $python.Source
}

function Invoke-Checked {
    param(
        [string]$StepName,
        [string]$FilePath,
        [string[]]$Arguments
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$StepName 执行失败（退出码: $LASTEXITCODE）"
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $scriptDir ".runtime_venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"
$requirementsGpuPath = Join-Path $scriptDir "requirements-gpu-cu128.txt"
$requirementsCpuPath = Join-Path $scriptDir "requirements-cpu.txt"

if (-not [Environment]::Is64BitOperatingSystem) {
    Write-Host "该便携包仅支持 64 位 Windows。" -ForegroundColor Red
    Wait-ForExit
    exit 1
}

if (-not (Test-Path $requirementsGpuPath)) {
    Write-Host "缺少依赖文件: $requirementsGpuPath" -ForegroundColor Red
    Wait-ForExit
    exit 1
}
if (-not (Test-Path $requirementsCpuPath)) {
    Write-Host "缺少依赖文件: $requirementsCpuPath" -ForegroundColor Red
    Wait-ForExit
    exit 1
}

Write-Host ""
Write-Host "鸟类清晰度筛选器（GPU 轻量联网版）" -ForegroundColor Cyan
$modeText = if ($Mode -eq "dry-run") { "仅预览（不复制）" } else { "正式复制" }
$presetText = if ($Preset -eq "fast") { "快速" } else { "高质量" }
$deviceText = if ($DevicePreset -eq "gpu") { "自动优先显卡" } else { "仅使用CPU" }
Write-Host "运行模式: $modeText | 处理预设: $presetText | 设备策略: $deviceText"
Write-Host ""

if ([string]::IsNullOrWhiteSpace($Source)) {
    $Source = Select-Folder -Title "请选择源文件夹（RAW 根目录）" -DefaultValue "E:\100NZ7_2"
}
if (-not (Test-Path $Source)) {
    Write-Host "源文件夹不存在: $Source" -ForegroundColor Red
    Wait-ForExit
    exit 1
}

$gpuReady = $false
if ($DevicePreset -eq "gpu") {
    try {
        $nvidia = Get-Command "nvidia-smi" -ErrorAction Stop
        if ($nvidia) { $gpuReady = $true }
    } catch {
        $gpuReady = $false
    }
}

$effectiveDevicePreset = if ($DevicePreset -eq "gpu" -and $gpuReady) { "gpu" } else { "cpu" }
if ($DevicePreset -eq "gpu" -and -not $gpuReady) {
    Write-Host "未检测到 NVIDIA 运行环境，安装与运行策略自动回退到 CPU。" -ForegroundColor Yellow
}

$requirementsPath = if ($effectiveDevicePreset -eq "gpu") { $requirementsGpuPath } else { $requirementsCpuPath }
$depsMarker = Join-Path $venvDir ".deps_installed_$($effectiveDevicePreset)_v1"
Write-Host "依赖安装方案: $effectiveDevicePreset" -ForegroundColor DarkGray

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$defaultOutput = Join-Path $Source "selected_birds_in_focus_$($Preset)_$timestamp"
$defaultLog = Join-Path $Source "bird_focus_selection_$($Mode.Replace('-', ''))_$($Preset)_$timestamp.csv"

if ($Mode -eq "copy" -and [string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Select-Folder -Title "请选择复制后的输出文件夹" -DefaultValue $defaultOutput
}
if ([string]::IsNullOrWhiteSpace($LogPath)) {
    $LogPath = Read-WithDefault -Prompt "日志文件路径" -DefaultValue $defaultLog
}

try {
    $pythonHost = Ensure-PythonCommand
} catch {
    Write-Host "$($_.Exception.Message)" -ForegroundColor Red
    Wait-ForExit
    exit 1
}

if (-not (Test-Path $pythonExe)) {
    Write-Host "正在创建运行时虚拟环境..." -ForegroundColor Cyan
    Invoke-Checked -StepName "创建虚拟环境" -FilePath $pythonHost -Arguments @("-m", "venv", $venvDir)
}

$needInstall = $ForceInstall -or -not (Test-Path $depsMarker)
if ($needInstall) {
    Write-Host "正在安装运行依赖（首次运行可能较慢）..." -ForegroundColor Cyan
    Invoke-Checked -StepName "升级 pip" -FilePath $pythonExe -Arguments @("-m", "pip", "install", "--upgrade", "pip")
    $stepName = if ($effectiveDevicePreset -eq "gpu") { "安装 GPU 依赖" } else { "安装 CPU 依赖" }
    Invoke-Checked -StepName $stepName -FilePath $pythonExe -Arguments @("-m", "pip", "install", "-r", $requirementsPath)
    Set-Content -Path $depsMarker -Value "ok" -Encoding ASCII
} else {
    Write-Host "复用已安装的运行依赖。" -ForegroundColor DarkGray
}

$args = @(
    "--source", $Source,
    "--exclude-dir-prefixes", "selected_birds_in_focus,raw",
    "--log-format", "csv",
    "--log-path", $LogPath
)

if ($Mode -eq "dry-run") {
    $args += "--dry-run"
} else {
    $args += @("--output-dir", $OutputDir)
}
if ($SampleLimit -gt 0) {
    $args += @("--sample-limit", "$SampleLimit")
}

if ($effectiveDevicePreset -eq "gpu") {
    $args += @("--device", "0")
} else {
    $args += @("--device", "cpu", "--cpu-workers", "0")
}

$modelPath = Join-Path $scriptDir "yolov8s-seg.pt"
if (Test-Path $modelPath) {
    $args += @("--model", $modelPath)
} else {
    Write-Host "本地未找到模型文件，首次运行会自动下载 yolov8s-seg.pt。" -ForegroundColor Yellow
    $args += @("--model", "yolov8s-seg.pt")
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
Write-Host "$pythonExe -m bird_select $($args -join ' ')" -ForegroundColor DarkGray
Write-Host ""

try {
    Push-Location $scriptDir
    try {
        Invoke-Checked -StepName "执行筛选" -FilePath $pythonExe -Arguments (@("-m", "bird_select") + $args)
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
