# 故障排查

## 1) 双击后无法启动 / 一闪而过

- 确认已经完整解压 zip，不要在压缩包内直接运行。
- 确认系统为 64 位 Windows 10/11。
- 右键 PowerShell 以管理员身份运行后再试一次。
- 如果提示运行库缺失，安装或修复 Microsoft Visual C++ 2015-2022 Redistributable（x64）。

## 2) 找不到 Python 或缺少依赖

- CPU 便携包和 GPU 便携包都已内置 Python。
- GPU 包首次运行会自动创建 `.runtime_venv` 并安装依赖，耗时较长是正常现象。
- 源码模式才需要手动安装依赖：

```powershell
pip install -r requirements.txt
pip install -r requirements-cpu.txt
# 如需 GPU
pip install -r requirements-gpu-cu128.txt
```

## 3) GPU 包提示未检测到 NVIDIA 环境

- GPU 包是 GPU 专用，不包含 CPU 入口。
- 先确认 `nvidia-smi` 在命令行可用。
- 如果机器没有 NVIDIA 环境，请使用 CPU 便携包。

## 4) GPU 包模型下载失败

- 先检查网络连接后重试（脚本会自动多次重试）。
- 可以手动将 `yolov8s-seg.pt` 放到程序根目录，再重新运行。
- 若网络受限，建议先在可联网环境完成首次运行，再拷贝整包到目标机器。

## 5) 安装依赖时提示空间不足

- 把程序放到剩余空间更大的分区（如 `E:\` / `D:\`）。
- GPU 包会把临时目录和 pip 缓存写到包目录下（`.tmp` / `.pip_cache`）。

## 6) 结果明显过少或过多

优先查看日志字段：
- `bird_detected`
- `detection_confidence`
- `laplacian_variance`
- `tenengrad_score`
- `failure_reason`

常见原因：
- `bird_detected_but_below_sharpness_threshold` 多：清晰度阈值偏严格。
- `bird_detected_but_boxes_too_small` 多：`min_bird_side` 或 `min_bird_area_ratio` 偏大。

## 7) 把历史输出目录也扫进去了

确保包含参数：

```text
--exclude-dir-prefixes selected_birds_in_focus,raw
```

这样会自动跳过 `selected_birds_in_focus*` 与 `raw*` 子目录。

## 8) `decode_error:*` 解码错误

- 表示某些 RAW 文件无法被当前解码链路正常读取，可能是兼容性差异或文件损坏。
- 程序会跳过失败文件并继续处理，不会中断全流程。
- 请保留日志，后续可针对样本做兼容增强。

## 9) 输出目录出现 `__dup001` 这类重命名

- 不同子目录里可能存在同名 RAW。
- 为防止覆盖，复制时会自动改名为 `原名__dup001.ext`、`__dup002.ext`。
