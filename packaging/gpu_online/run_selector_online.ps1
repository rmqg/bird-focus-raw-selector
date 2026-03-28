param(
    [ValidateSet("dry-run", "copy")]
    [string]$Mode = "dry-run",
    [ValidateSet("fast", "quality")]
    [string]$Preset = "fast",
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

function Ensure-ModelFile {
    param(
        [string]$ModelPath,
        [string]$PythonExe,
        [string]$WorkingDir
    )

    if (Test-Path $ModelPath) {
        return
    }

    try {
        [Net.ServicePointManager]::SecurityProtocol = `
            [Net.ServicePointManager]::SecurityProtocol -bor `
            [Net.SecurityProtocolType]::Tls12
    } catch {
        # 某些环境不支持修改 TLS 配置，忽略并继续。
    }

    $modelUrls = @(
        "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s-seg.pt",
        "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s-seg.pt"
    )
    $tmpPath = "$ModelPath.download"

    foreach ($url in $modelUrls) {
        for ($attempt = 1; $attempt -le 2; $attempt++) {
            try {
                if (Test-Path $tmpPath) {
                    Remove-Item -Force $tmpPath
                }
                Write-Host "正在下载模型（第 $attempt/2 次）..." -ForegroundColor Cyan
                Write-Host "$url" -ForegroundColor DarkGray
                Invoke-WebRequest -Uri $url -OutFile $tmpPath -UseBasicParsing -TimeoutSec 300
                if (-not (Test-Path $tmpPath)) {
                    throw "模型下载失败，未生成文件。"
                }
                $size = (Get-Item $tmpPath).Length
                if ($size -lt 10000000) {
                    throw "模型下载异常，文件过小（$size 字节）。"
                }
                Move-Item -Force $tmpPath $ModelPath
                Write-Host "模型下载完成: $ModelPath" -ForegroundColor Green
                return
            } catch {
                if (Test-Path $tmpPath) {
                    Remove-Item -Force $tmpPath -ErrorAction SilentlyContinue
                }
                if ($attempt -lt 2) {
                    Start-Sleep -Seconds 2
                }
            }
        }
    }

    Write-Host "HTTP 下载失败，尝试 Ultralytics 内置下载器..." -ForegroundColor Yellow
    try {
        Push-Location $WorkingDir
        try {
            Invoke-Checked -StepName "模型自动下载" -FilePath $PythonExe -Arguments @(
                "-c",
                "from ultralytics.utils.downloads import attempt_download_asset; attempt_download_asset('yolov8s-seg.pt')"
            )
        } finally {
            Pop-Location
        }
    } catch {
        throw "模型下载失败，请检查网络后重试。详细信息: $($_.Exception.Message)"
    }

    if (-not (Test-Path $ModelPath)) {
        throw "模型下载失败：未在 $ModelPath 发现模型文件。"
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bundledPythonExe = Join-Path $scriptDir "python_runtime\python.exe"
$venvDir = Join-Path $scriptDir ".runtime_venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"
$requirementsPath = Join-Path $scriptDir "requirements-gpu-cu128.txt"
$depsMarker = Join-Path $venvDir ".deps_installed_gpu_v110"
$modelPath = Join-Path $scriptDir "yolov8s-seg.pt"
$tmpDir = Join-Path $scriptDir ".tmp"
$pipCacheDir = Join-Path $scriptDir ".pip_cache"

if (-not [Environment]::Is64BitOperatingSystem) {
    Write-Host "该便携包仅支持 64 位 Windows。" -ForegroundColor Red
    Wait-ForExit
    exit 1
}

if (-not (Test-Path $bundledPythonExe)) {
    Write-Host "未找到内置 Python：$bundledPythonExe" -ForegroundColor Red
    Write-Host "请重新解压完整的 GPU 便携包后再运行。" -ForegroundColor Yellow
    Wait-ForExit
    exit 1
}

if (-not (Test-Path $requirementsPath)) {
    Write-Host "缺少依赖文件: $requirementsPath" -ForegroundColor Red
    Wait-ForExit
    exit 1
}

try {
    $nvidia = Get-Command "nvidia-smi" -ErrorAction Stop
    if (-not $nvidia) {
        throw "未检测到可用的 NVIDIA 环境。"
    }
} catch {
    Write-Host "当前机器未检测到 NVIDIA GPU 运行环境（nvidia-smi 不可用）。" -ForegroundColor Red
    Write-Host "GPU 便携包不包含 CPU 模式，请改用 CPU 便携包。" -ForegroundColor Yellow
    Wait-ForExit
    exit 1
}

Write-Host ""
Write-Host "鸟类清晰度筛选器（GPU 便携版）" -ForegroundColor Cyan
$modeText = if ($Mode -eq "dry-run") { "仅预览（不复制）" } else { "正式复制" }
$presetText = if ($Preset -eq "fast") { "快速" } else { "高质量" }
Write-Host "运行模式: $modeText | 处理预设: $presetText | 设备: GPU(0)"
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

New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
New-Item -ItemType Directory -Path $pipCacheDir -Force | Out-Null
$env:TEMP = $tmpDir
$env:TMP = $tmpDir
$env:PIP_CACHE_DIR = $pipCacheDir

if (-not (Test-Path $pythonExe)) {
    Write-Host "正在创建运行时虚拟环境..." -ForegroundColor Cyan
    Invoke-Checked -StepName "创建虚拟环境" -FilePath $bundledPythonExe -Arguments @("-m", "venv", $venvDir)
}

$needInstall = $ForceInstall -or -not (Test-Path $depsMarker)
if ($needInstall) {
    Write-Host "正在安装 GPU 运行依赖（首次运行耗时较长）..." -ForegroundColor Cyan
    Invoke-Checked -StepName "升级 pip" -FilePath $pythonExe -Arguments @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-Checked -StepName "安装 GPU 依赖" -FilePath $pythonExe -Arguments @("-m", "pip", "install", "-r", $requirementsPath)
    Set-Content -Path $depsMarker -Value "ok" -Encoding ASCII
} else {
    Write-Host "复用已安装的 GPU 运行依赖。" -ForegroundColor DarkGray
}

try {
    Ensure-ModelFile -ModelPath $modelPath -PythonExe $pythonExe -WorkingDir $scriptDir
} catch {
    Write-Host "$($_.Exception.Message)" -ForegroundColor Red
    Wait-ForExit
    exit 1
}

$args = @(
    "--source", $Source,
    "--exclude-dir-prefixes", "selected_birds_in_focus,raw",
    "--log-format", "csv",
    "--log-path", $LogPath,
    "--device", "0",
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
