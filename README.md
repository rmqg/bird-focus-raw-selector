# 鸟类清晰对焦 RAW 初筛工具

这是一个本地 Windows 工具，用来从大量 RAW 照片里自动初筛：
- 画面里有鸟；
- 至少有一只鸟主体清晰；
- 命中后复制原始 RAW 到新目录（不改动原文件）。

## 支持格式

- Nikon：`.nef`、`.nrw`
- Canon：`.cr2`、`.cr3`、`.crw`
- Sony：`.arw`、`.sr2`、`.srf`

## 下载与使用（普通用户）

请在 GitHub Releases 下载便携包：  
[https://github.com/rmqg/bird-focus-raw-selector/releases](https://github.com/rmqg/bird-focus-raw-selector/releases)

### 1) CPU 便携包

- 文件名：`bird-select-portable-win64_cpu_*.zip`
- 适用：任何 64 位 Windows
- 特点：CPU 专用、离线可用、已内置 Python

### 2) GPU 便携包

- 文件名：`bird-select-portable-win64_gpu-online_*.zip`
- 适用：有 NVIDIA GPU 且 `nvidia-smi` 可用的机器
- 特点：GPU 专用、已内置 Python、首次运行自动安装 GPU 依赖
- 说明：若缺少模型，会自动下载 `yolov8s-seg.pt`

## 使用步骤

1. 下载 zip 后先完整解压，不要在压缩包内直接运行。
2. 先运行 `Run_DryRun_Fast_*.bat`（只预览，不复制）。
3. 确认结果后运行 `Run_Copy_Fast_*.bat`（正式复制）。
4. 按提示选择源目录、输出目录、日志路径。

## 输出日志

每张 RAW 都会记录到 CSV/JSONL，包含：
- 文件路径
- 是否检测到鸟
- 检测置信度
- 清晰度分数
- 使用阈值
- 最终决策
- 失败原因（若有）

默认会自动跳过 `selected_birds_in_focus*` 与 `raw*` 子目录，避免重复扫描历史输出。

## 源码运行（开发者）

```powershell
cd E:\bird_select
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-cpu.txt
python -m bird_select --help
```

示例（全量预览，不复制）：

```powershell
python -m bird_select `
  --source E:\100NZ7_2 `
  --dry-run `
  --log-format csv `
  --log-path E:\100NZ7_2\bird_focus_log.csv `
  --device auto
```

## 文档

- [普通用户快速上手](docs/FRIEND_QUICK_START_CN.md)
- [参数说明](docs/PARAMETERS_REFERENCE_CN.md)
- [故障排查](docs/TROUBLESHOOTING_CN.md)
- [GitHub 发布流程](docs/GITHUB_RELEASE_GUIDE_CN.md)

## 开源协议

MIT
