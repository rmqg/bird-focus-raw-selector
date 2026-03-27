# Bird Focus RAW Selector

一个本地 Windows 工具，用于从 RAW 照片中筛选“有鸟且鸟主体清晰”的文件并复制到新目录。

项目目标：
- GitHub 可发布（源码仓库规范化）
- 可直接发给不懂计算机的朋友使用（双击 bat 启动）
- 尽量减少目标机器环境差异带来的问题

---

## 核心能力

- 递归扫描 RAW 文件夹。
- 默认跳过 `selected_birds_in_focus*` 与 `raw*` 子目录，避免把已筛结果或参考目录重复扫入。
- 预训练模型检测鸟（不训练新模型）。
- 在鸟 ROI 内评估清晰度（Laplacian + Tenengrad）。
- 至少一只鸟清晰则入选。
- 支持 dry-run。
- 每个文件都输出结构化日志。
- 复制阶段遇到同名文件会自动重命名（`__dup001`...），避免漏拷。
- CPU 支持多进程并行（`--cpu-workers`，`0`=自动）。

默认支持 RAW 扩展名：
- Nikon: `.nef`, `.nrw`
- Canon: `.cr2`, `.cr3`, `.crw`
- Sony: `.arw`, `.sr2`, `.srf`

---

## 仓库结构

```text
bird_select/
├─ bird_select/                     # 核心代码
├─ docs/                            # 文档
├─ packaging/portable/              # 便携包启动器模板
├─ scripts/                         # 打包/检查脚本
├─ pyproject.toml
├─ requirements.txt
├─ requirements-cpu.txt
├─ requirements-gpu-cu128.txt
├─ yolov8s-seg.pt
└─ README.md
```

---

## 开发者快速运行

```powershell
cd E:\bird_select
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m bird_select --help
```

---

## 打包与交付

### 1) 源码包（上传 GitHub 或发给开发者）

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package_source.ps1
```

### 2) 便携包（小白可双击）

CPU 版（默认推荐，跨机器更稳）：
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_portable_cpu.ps1
```

GPU 版（可选，CUDA 12.8 环境）：
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_portable_gpu.ps1
```

统一入口（默认源码包 + CPU 便携包；需要时显式加 GPU）：
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_all_packages.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build_all_packages.ps1 -BuildGpuPortable
```

### 3) 发布前自检

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_release.ps1
```

### 4) 发布到 GitHub Release

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish_github_release.ps1 -Repo "<user>/<repo>"
```

---

## 便携包跨机器注意事项

- 仅支持 Windows 10/11 64 位。
- 建议先 dry-run 再 copy。
- 启动器支持目录弹窗选择。
- 当前便携启动器默认走 CPU 多核；GPU 入口为了兼容保留，但会回退为 CPU。
- 便携包内置模型文件，尽量避免首跑联网下载。

---

## 文档索引

- [小白使用说明](docs/FRIEND_QUICK_START_CN.md)
- [参数手册](docs/PARAMETERS_REFERENCE_CN.md)
- [故障排查](docs/TROUBLESHOOTING_CN.md)
- [GitHub 发布流程](docs/GITHUB_RELEASE_GUIDE_CN.md)

---

## License

Unlicense (Public Domain)
