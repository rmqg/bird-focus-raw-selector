# 小白朋友使用说明（双击版）

你拿到的是一个 zip 压缩包，解压后可以直接双击运行。

---

## 1. 你会看到这些启动文件

- `Run_DryRun_Fast_GPU.bat`：先预览结果，不复制，速度快（有 NVIDIA 显卡推荐）。
- `Run_Copy_Fast_GPU.bat`：正式复制，速度快（有 NVIDIA 显卡推荐）。
- `Run_DryRun_Fast_CPU.bat`：先预览结果，不复制，兼容模式。
- `Run_Copy_Fast_CPU.bat`：正式复制，兼容模式。

---

## 2. 建议使用顺序

1. 先双击 `Run_DryRun_Fast_GPU.bat`（没有 NVIDIA 显卡就用 CPU 版）。
2. 看终端末尾统计和日志是否符合预期。
3. 再双击 `Run_Copy_Fast_GPU.bat` 执行正式复制。

---

## 3. 运行过程中需要输入什么

启动后会让你输入：
- 源目录（待筛选 RAW 的目录）
- 输出目录（复制后的目标目录，回车可用默认）
- 日志路径（回车可自动生成）

不懂就直接回车用默认值。

---

## 4. 常见问题

- 双击闪退：用“以管理员身份运行”PowerShell 再启动 bat。
- 速度慢：优先用 GPU 版 bat；或使用 Fast 预设。
- 没选到图：先看 dry-run 日志里的 `failure_reason` 字段。

完整排错见：
- [故障排查](TROUBLESHOOTING_CN.md)
