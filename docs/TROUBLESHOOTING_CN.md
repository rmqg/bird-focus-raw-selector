# 故障排查

---

## 1) `torch ... +cpu`，GPU 没启用

现象：
- 日志里显示 `torch-xxx+cpu`
- 跑得很慢

说明：
- 便携启动器当前版本默认回退 CPU 多核，这是预期行为（为了避免 GPU 初始化过慢）。
- 如果你要强制测试 GPU，请使用源码 CLI 并手工传 `--device 0`。

处理：
1. 确认 NVIDIA 驱动正常（`nvidia-smi`）。
2. 安装 CUDA 对应 PyTorch（示例 cu128）：
   ```powershell
   pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
   ```

---

## 2) `No space left on device`

现象：
- pip 下载大轮子时报磁盘空间不足。

处理：
- 把 `TEMP/TMP` 指到空间大的盘再安装：
  ```powershell
  $env:TEMP='E:\pip_temp'
  $env:TMP='E:\pip_temp'
  ```

---

## 3) 结果明显过少/过多

先看日志字段：
- `bird_detected`
- `failure_reason`
- `laplacian_variance`
- `tenengrad_score`
- `tenengrad_p90`

常见：
- `bird_detected_but_below_sharpness_threshold` 多：清晰度阈值太严。
- `bird_detected_but_boxes_too_small` 多：`min_bird_side` 或 `min_bird_area_ratio` 太高。

---

## 4) 换台电脑后跑不起来

先检查：
- 系统是否 64 位 Windows
- 是否完整解压了整个 zip（不要在压缩包内直接运行）
- 是否有读写权限（建议放在普通目录，如 `D:\tools\bird-select`）

如果报 DLL 或运行库相关错误：
- 安装/修复 Microsoft Visual C++ 2015-2022 Redistributable（x64）

---

## 5) 把历史输出目录或 RAW 参考目录也扫进去了

确保：
- `--exclude-dir-prefixes selected_birds_in_focus,raw`

这样会自动跳过 `selected_birds_in_focus*` 与 `raw*` 子目录。

---

## 6) GPU 版启动入口说明

- `Run_*_GPU.bat` 当前是兼容入口，实际会回退到 CPU 多核。
- 如果你希望固定 CPU，直接运行 CPU 版 bat。

---

## 7) CPU 并行后内存占用变高

说明：
- CPU 并行会为多个进程各自加载模型与依赖，内存会明显上升。

处理：
- 降低并行度，例如：`--cpu-workers 2`
- 或临时禁用并行：`--cpu-workers 1`

---

## 8) decode error

现象：
- `failure_reason` 包含 `decode_error:*`

说明：
- 机型/压缩格式兼容差异，或 RAW 文件损坏。

处理：
- 保留日志并给出样例文件，后续可单独做解码分支兼容。

---

## 9) 为什么输出目录里出现 `__dup001` 这类文件名

说明：
- 源目录不同子文件夹可能有同名 RAW 文件。
- 为了不覆盖旧文件，复制阶段会自动重命名为 `原名__dup001.ext`、`__dup002.ext`。
