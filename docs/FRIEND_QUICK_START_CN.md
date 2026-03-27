# 小白朋友使用说明（双击版）

你拿到的是一个 zip 压缩包，解压后可以直接双击运行。

---

## 1. 启动文件说明

- `Run_DryRun_Fast_GPU.bat`：先预览结果，不复制，优先推荐（有 NVIDIA）。
- `Run_Copy_Fast_GPU.bat`：正式复制，优先推荐（有 NVIDIA）。
- `Run_DryRun_Fast_CPU.bat`：先预览结果，不复制。
- `Run_Copy_Fast_CPU.bat`：正式复制。

启动器默认行为：
- 递归扫描源目录。
- 自动跳过 `selected_birds_in_focus*` 和 `raw*` 子目录。
- CPU 自动多核并行（`--cpu-workers 0`）。
- GPU 启动失败时自动回退到 CPU。
- 默认使用包内 `yolov8s-seg.pt`，不依赖在线下载。

如果你下载的是 `gpu-online` 轻量包：
- 首次运行会自动联网安装依赖（时间较长）。
- 如果本地没有模型，会自动下载 `yolov8s-seg.pt`。

---

## 2. 建议使用顺序

1. 先双击 `Run_DryRun_Fast_GPU.bat`（没有 NVIDIA 再用 CPU 版）。
2. 看终端末尾统计和日志是否符合预期。
3. 再双击 `Run_Copy_Fast_GPU.bat` 或 `Run_Copy_Fast_CPU.bat` 执行正式复制。

---

## 3. 运行时需要输入什么

启动后会让你输入：
- 源目录（待筛选 RAW 的目录）
- 输出目录（复制后的目标目录，回车可用默认）
- 日志路径（回车可自动生成）

不懂就直接回车使用默认值。
如果系统支持图形界面，会先弹出文件夹选择窗口，直接点选目录即可。

---

## 4. 常见问题

- 双击闪退：右键 PowerShell 以管理员身份运行后再执行 bat。
- 速度慢：优先使用 GPU Fast 预设（默认 1600 分辨率分析）。
- 没选到图：先看 dry-run 日志里的 `failure_reason` 字段。

完整排错见：
- [故障排查](TROUBLESHOOTING_CN.md)
