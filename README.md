# Bird Focus RAW Selector

本项目是一个本地 Windows CLI 工具，用于从 RAW 文件中自动筛出“有鸟且鸟主体清晰”的照片，并复制到输出目录。

当前重点是实用可落地：
- 支持 Nikon / Sony / Canon RAW。
- 支持 dry-run（只看结果不复制）。
- 每张文件都有结构化日志。
- 默认支持“速度优先”和“质量优先”两类运行方式。
- 可产出“小白可双击运行”的便携包（无需手动敲命令）。

---

## 1. 功能概览

- 递归扫描源目录中的 RAW 文件。
- 使用预训练检测模型判断是否有鸟。
- 在鸟 ROI 内做清晰度评估（不是只看整张图）。
- 至少一只鸟清晰则判定该 RAW 入选。
- 只复制原始 RAW，不移动、不修改源文件。
- 对每个文件输出日志字段：检测、清晰度、阈值、最终决策、失败原因等。

默认支持扩展名：
- Nikon: `.nef`, `.nrw`
- Canon: `.cr2`, `.cr3`, `.crw`
- Sony: `.arw`, `.sr2`, `.srf`

---

## 2. 仓库结构

```text
bird_select/
├─ bird_select/                     # 核心代码
├─ docs/                            # 完整文档
├─ packaging/portable/              # 小白启动脚本模板
├─ scripts/                         # 打包脚本
├─ pyproject.toml
├─ requirements.txt
├─ requirements-cpu.txt
├─ requirements-gpu-cu128.txt
├─ yolov8s-seg.pt
└─ README.md
```

---

## 3. 开发者快速运行

```powershell
cd E:\bird_select
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

运行（默认源目录 `E:\100NZ7_2`）：
```powershell
python -m bird_select --dry-run
```

常用：
```powershell
python -m bird_select --help
```

---

## 4. 两类推荐预设

### A) 速度优先（推荐先筛）
- `--no-prefer-full-raw`
- `--analysis-max-side 1600`
- `--max-infer-side 1600`

### B) 质量优先（更慢）
- `--prefer-full-raw`
- `--analysis-max-side 0`
- `--max-infer-side 0`

详细参数见：
- [参数手册](docs/PARAMETERS_REFERENCE_CN.md)

---

## 5. 打包与交付

### 5.1 生成可上传 GitHub 的源码包

```powershell
cd E:\bird_select
powershell -ExecutionPolicy Bypass -File .\scripts\package_source.ps1
```

输出在 `release/` 目录。

### 5.2 生成小白可用的 Windows 便携包

```powershell
cd E:\bird_select
powershell -ExecutionPolicy Bypass -File .\scripts\build_portable.ps1
```

输出 zip 在 `release/`，解压后直接双击 `.bat` 即可使用。

---

## 6. 文档导航

- [小白使用说明](docs/FRIEND_QUICK_START_CN.md)
- [参数手册](docs/PARAMETERS_REFERENCE_CN.md)
- [故障排查](docs/TROUBLESHOOTING_CN.md)
- [GitHub 发布流程](docs/GITHUB_RELEASE_GUIDE_CN.md)

---

## 7. License

默认建议 MIT（如需商业/闭源条款请自行替换）。
