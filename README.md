# 鸟类清晰对焦 RAW 初筛工具

这是一个本地 Windows 工具，用来从大量 RAW 照片里自动初筛：
- 图里有鸟；
- 并且至少有一只鸟主体清晰；
- 命中后把原始 RAW 复制到新目录（不改动原文件）。

## 适用格式

- Nikon：`.nef`、`.nrw`
- Canon：`.cr2`、`.cr3`、`.crw`
- Sony：`.arw`、`.sr2`、`.srf`

## 给普通用户（推荐）

请直接在 GitHub 的 [Releases](https://github.com/rmqg/bird-focus-raw-selector/releases) 下载便携包：

- `bird-select-portable-win64_cpu_*.zip`
  适合所有 Windows 机器，稳定、离线可用。
- `bird-select-portable-win64_gpu-online_*.zip`
  适合有 NVIDIA 显卡的机器，首次运行会联网安装依赖并下载模型。

### 使用步骤

1. 下载 zip 后先完整解压，不要在压缩包内直接运行。
2. 先双击 `Run_DryRun_Fast_*.bat`（只预览，不复制）。
3. 确认结果后，再双击 `Run_Copy_Fast_*.bat`（正式复制）。
4. 按提示依次选择：
   - 源文件夹（RAW 根目录，例如 `E:\100NZ7_2`）
   - 输出文件夹（可回车使用默认）
   - 日志文件路径（可回车自动生成）

## 输出结果

程序会为每一张 RAW 记录日志（CSV 或 JSONL），包含：
- 文件路径
- 是否检测到鸟
- 检测置信度
- 清晰度分数
- 使用阈值
- 最终决策
- 失败原因（如有）

默认会自动跳过 `selected_birds_in_focus*` 和 `raw*` 子目录，避免重复扫描历史结果。

## 给开发者（源码运行）

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

## 项目文档

- [普通用户快速上手](docs/FRIEND_QUICK_START_CN.md)
- [参数说明](docs/PARAMETERS_REFERENCE_CN.md)
- [故障排查](docs/TROUBLESHOOTING_CN.md)
- [GitHub 发布流程](docs/GITHUB_RELEASE_GUIDE_CN.md)

## 开源协议

MIT
