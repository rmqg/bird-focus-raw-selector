Bird Focus Selector 便携包说明

这是完整便携包（内置可执行文件与模型）。

使用步骤：
1) 解压整个 zip 到本地磁盘（不要在压缩包内直接运行）。
2) 建议先运行：
   - Run_DryRun_Fast_GPU.bat（优先）
   - 若 GPU 不可用，可改用 Run_DryRun_Fast_CPU.bat
3) 检查结果后再运行正式复制：
   - Run_Copy_Fast_GPU.bat
   - 或 Run_Copy_Fast_CPU.bat

运行时会提示你：
- 选择源文件夹（RAW 根目录）
- 选择输出文件夹（回车可用默认）
- 设置日志路径（回车可自动生成）

如果遇到问题：
- 可先查看同目录 `docs` 下的排错文档；
- 或改用 CPU 启动入口重试。
