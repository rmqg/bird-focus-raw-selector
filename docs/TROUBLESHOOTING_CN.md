# 故障排查

---

## 1) `torch ... +cpu`，GPU 没启用

现象：
- 日志里显示 `torch-xxx+cpu`
- 跑得很慢

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

## 4) 把历史输出目录也扫进去了

确保：
- `--exclude-dir-prefixes selected_birds_in_focus`

这样会自动跳过 `selected_birds_in_focus*` 子目录。

---

## 5) decode error

现象：
- `failure_reason` 包含 `decode_error:*`

说明：
- 机型/压缩格式兼容差异，或 RAW 文件损坏。

处理：
- 保留日志并给出样例文件，后续可单独做解码分支兼容。
