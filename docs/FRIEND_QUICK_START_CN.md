# 快速上手（给普通用户）

## 1. 先选对压缩包

- `bird-select-portable-win64_cpu_*.zip`
  适合所有 64 位 Windows，CPU 专用，已内置 Python。
- `bird-select-portable-win64_gpu-online_*.zip`
  适合有 NVIDIA GPU 的机器，GPU 专用，已内置 Python，首次自动安装 GPU 依赖。

如果你的电脑没有 NVIDIA 环境，请直接用 CPU 包。

## 2. 使用顺序

1. 完整解压 zip（不要在压缩包里直接运行）。
2. 按需执行 `Run_DryRun_Fast_*.bat`（预览结果，不复制）。
3. 按需执行 `Run_Copy_Fast_*.bat`（正式复制）。

## 3. 运行时输入

程序会依次让你输入：
- 源目录（RAW 根目录）
- 输出目录（复制目标目录，可回车用默认）
- 日志路径（可回车自动生成）

## 4. 结果说明

- 只复制命中的 RAW，不会移动或修改原始文件。
- 自动递归扫描。
- 自动跳过 `selected_birds_in_focus*` 与 `raw*` 子目录。

## 5. 遇到问题

请先看：
- [故障排查](TROUBLESHOOTING_CN.md)
