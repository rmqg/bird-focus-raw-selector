# 参数手册（核心）

---

## 基础路径

- `--source`
  - 源目录，递归扫描 RAW。
- `--output-dir`
  - 命中 RAW 复制目标目录。
- `--log-path`
  - 指定日志输出文件路径。

---

## 格式与扫描

- `--extensions`
  - RAW 扩展名白名单。
  - 默认：`.nef,.nrw,.cr2,.cr3,.crw,.arw,.sr2,.srf`
- `--exclude-dir-prefixes`
  - 扫描时跳过目录名前缀，避免把历史输出目录或参考 `raw` 目录再扫进去。
  - 默认：`selected_birds_in_focus,raw`

---

## 检测相关

- `--model`
  - 检测模型权重（默认 `yolov8s-seg.pt`）。
- `--cpu-workers`
  - CPU 并行 worker 数。
  - `0` 表示自动（约为逻辑核心数的一半，上限 8）。
- `--confidence-threshold`
  - 鸟检测置信度阈值。
- `--iou-threshold`
  - NMS IoU 阈值。
- `--max-infer-side`
  - 推理图像边长上限（0 = 不限，按当前图大小）。

---

## RAW 解码与分辨率

- `--prefer-full-raw / --no-prefer-full-raw`
  - 是否优先 full RAW 解码。
- `--analysis-max-side`
  - 分析前缩放上限（0 = 不缩放）。
- `--full-raw-half-size`
  - full RAW 是否半尺寸解码（提速但可能丢细节）。

---

## 清晰度判定

- `--laplacian-threshold`
- `--tenengrad-threshold`
- `--tenengrad-p90-threshold`
- `--strong-edge-ratio-threshold`
- `--min-focus-pixels`
- `--min-focus-pixel-ratio`
- `--min-mask-fill-ratio`

以上阈值越高，结果越严格；越低，召回越高。

---

## 目标尺寸过滤

- `--min-bird-side`
  - 最小 bbox 短边。
- `--min-bird-area-ratio`
  - 最小 bbox 面积占比。

---

## 运行模式

- `--dry-run`
  - 只输出结果不复制文件。
- `--sample-limit`
  - 仅处理前 N 张（调参用）。
- `--overwrite`
  - 复制时覆盖同名文件。

---

## 推荐预设（可直接抄）

### 速度优先
```text
--no-prefer-full-raw --analysis-max-side 1600 --max-infer-side 1600
```

### 质量优先
```text
--prefer-full-raw --analysis-max-side 0 --max-infer-side 0
```
