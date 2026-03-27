Bird Focus Selector GPU 轻量联网包说明

这个包为了减小体积，不内置 Python 依赖和模型权重。
首次运行会自动联网安装依赖，并在缺少模型时自动下载 yolov8s-seg.pt。

使用步骤：
1) 解压整个 zip 到本地磁盘（不要在压缩包内直接运行）。
2) 首次建议运行：Run_DryRun_Fast_GPU.bat（无 NVIDIA 可用 CPU 版）。
3) 检查结果后运行：Run_Copy_Fast_GPU.bat 或 Run_Copy_Fast_CPU.bat。

注意事项：
- 首次运行需要联网，耗时会比较长（会下载 PyTorch CUDA 包）。
- 需要系统已安装 Python 3.10+（推荐 3.11）。
- 后续再次运行会复用 `.runtime_venv`，速度会快很多。
