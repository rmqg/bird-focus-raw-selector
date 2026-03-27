# 故障排查

---

## 1) `ModuleNotFoundError` 或 `No module named ...`

现象：
- 启动时提示缺少 `tqdm`、`torch`、`ultralytics` 等依赖。

处理：
```powershell
pip install -r requirements.txt
pip install -r requirements-cpu.txt
```

如果你要启用 GPU：
```powershell
pip install -r requirements-gpu-cu128.txt
```

---

## 2) `No space left on device`

现象：
- pip 下载依赖时提示磁盘空间不足。

处理：
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
- 是否 64 位 Windows 10/11
- 是否完整解压了整个 zip（不要在压缩包内直接运行）
- 是否有读写权限（建议放在普通目录，如 `D:\tools\bird-select`）

如果报 DLL 或运行库相关错误：
- 安装/修复 Microsoft Visual C++ 2015-2022 Redistributable（x64）

---

## 5) 把历史输出目录或 RAW 参考目录也扫进去了

确保参数包含：
- `--exclude-dir-prefixes selected_birds_in_focus,raw`

这样会自动跳过 `selected_birds_in_focus*` 与 `raw*` 子目录。

---

## 6) CPU 并行后内存占用变高

说明：
- CPU 并行会为多个进程各自加载模型与依赖，内存会明显上升。

处理：
- 降低并行度，例如：`--cpu-workers 2`
- 或临时禁用并行：`--cpu-workers 1`

---

## 7) 想用 GPU 但实际跑在 CPU

现象：
- 日志里看到 `+cpu`
- 或启动器提示回退到 CPU

处理：
- 确认 `nvidia-smi` 可用
- 源码运行时显式传 `--device 0`
- 便携包请使用 `Run_*_GPU.bat`
- 若驱动/运行时不完整，启动器会自动降级到 CPU

---

## 8) decode error

现象：
- `failure_reason` 包含 `decode_error:*`

说明：
- 机型/压缩格式兼容差异，或 RAW 文件损坏。

处理：
- 保留日志并给出样例文件，后续可单独做解码兼容分支。

---

## 9) 为什么输出目录里出现 `__dup001` 这类文件名

说明：
- 源目录不同子文件夹可能有同名 RAW 文件。
- 为了不覆盖旧文件，复制阶段会自动重命名为 `原名__dup001.ext`、`__dup002.ext`。
