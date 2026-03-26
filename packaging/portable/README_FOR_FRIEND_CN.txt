Bird Focus Selector 便携包说明

1) 解压整个压缩包到本地磁盘（不要在压缩包里直接双击运行）。
2) 先运行：
   Run_DryRun_Fast_GPU.bat
   如果没有 NVIDIA 显卡，运行：
   Run_DryRun_Fast_CPU.bat
3) 观察结果没问题后，再运行 Copy 对应 bat。

文件说明：
- Run_DryRun_Fast_GPU.bat: 预览，不复制
- Run_Copy_Fast_GPU.bat: 正式复制
- Run_DryRun_Fast_CPU.bat: 预览（兼容）
- Run_Copy_Fast_CPU.bat: 正式复制（兼容）
- run_selector.ps1: 启动器核心脚本

提示：
- 首先输入源目录（你的 RAW 所在目录）
- 然后输入输出目录（回车可用默认）
- 最后输入日志路径（回车可自动生成）

如果报错：
- 右键 PowerShell 以管理员身份运行后再双击 bat
- 查看同目录下 docs 或 README 的故障排查章节
