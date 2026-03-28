鸟类 RAW 初筛工具（GPU 便携包）使用说明

这是 GPU 专用便携包，已内置 Python 运行环境。
本包不提供 CPU 启动入口。

使用步骤：
1) 解压整个 zip 到本地磁盘（不要在压缩包内直接运行）。
2) 按需执行：Run_DryRun_Fast_GPU.bat（预览结果，不复制）。
3) 按需执行：Run_Copy_Fast_GPU.bat（正式复制）。

提示：
- 首次运行会自动安装 GPU 依赖（会下载较大文件，耗时较长）。
- 若包内缺少模型文件，会自动下载 yolov8s-seg.pt。
- 需要本机有可用 NVIDIA GPU 环境（nvidia-smi 可用）。
