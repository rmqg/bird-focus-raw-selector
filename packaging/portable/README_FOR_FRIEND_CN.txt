鸟类 RAW 初筛工具（综合便携包）使用说明

这是综合便携包，包含 GPU 与 CPU 两个启动入口。

使用步骤：
1) 解压整个 zip 到本地磁盘（不要在压缩包内直接运行）。
2) 按需执行预览（不复制）：
   - Run_DryRun_Fast_GPU.bat（优先）
   - 若 GPU 不可用，可改用 Run_DryRun_Fast_CPU.bat
3) 按需执行正式复制：
   - Run_Copy_Fast_GPU.bat
   - 或 Run_Copy_Fast_CPU.bat

运行时会提示你：
- 选择源文件夹（RAW 根目录）
- 选择输出文件夹（回车可用默认）
- 设置日志路径（回车可自动生成）

如果遇到问题：
- 先查看同目录 `docs` 下的排错文档；
- 或改用 CPU 启动入口重试。
