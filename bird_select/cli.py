from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import BirdFocusSelector, SelectorConfig, summarize_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="筛选包含鸟且至少一只鸟清晰对焦的 RAW 文件。",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(r"E:\100NZ7_2"),
        help="源目录：会递归扫描支持的 RAW 文件。",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="输出目录：保存命中的 RAW 文件。默认 <source>/selected_birds_in_focus。",
    )
    parser.add_argument(
        "--extensions",
        default=".nef,.nrw,.cr2,.cr3,.crw,.arw,.sr2,.srf",
        help="递归扫描的 RAW 扩展名，逗号分隔。",
    )
    parser.add_argument(
        "--exclude-dir-prefixes",
        default="selected_birds_in_focus,raw",
        help="递归扫描时跳过的目录名前缀，逗号分隔。",
    )
    parser.add_argument(
        "--model",
        default="yolov8s-seg.pt",
        help="预训练鸟类检测模型名称或本地路径，建议使用分割模型以提高精度。",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="推理设备（传给 Ultralytics），如 auto、cpu 或 0。",
    )
    parser.add_argument(
        "--cpu-workers",
        type=int,
        default=0,
        help="CPU 并行 worker 数。0 表示自动（约为逻辑核心数的一半）。",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.40,
        help="鸟检测最小置信度阈值。",
    )
    parser.add_argument(
        "--iou-threshold",
        type=float,
        default=0.45,
        help="检测器 NMS 的 IoU 阈值。",
    )
    parser.add_argument(
        "--max-infer-side",
        type=int,
        default=0,
        help="检测推理边长上限。0 表示直接使用图像最大边。",
    )
    parser.add_argument(
        "--analysis-max-side",
        type=int,
        default=0,
        help="检测前先缩放到此最大边长。0 表示不缩放。",
    )
    parser.add_argument(
        "--min-preview-side",
        type=int,
        default=1200,
        help="若内嵌预览图小于该阈值，则回退到半尺寸 RAW 解码。",
    )
    parser.add_argument(
        "--allow-full-raw-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="当优先 RAW 解码失败时，允许回退到其他解码策略。",
    )
    parser.add_argument(
        "--prefer-full-raw",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="优先使用 full RAW 解码，再尝试内嵌预览图。",
    )
    parser.add_argument(
        "--full-raw-half-size",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="full RAW 是否半尺寸解码。关闭时使用原始分辨率。",
    )
    parser.add_argument(
        "--min-bird-area-ratio",
        type=float,
        default=0.0015,
        help="鸟框最小面积占比（bbox 面积 / 全图面积）。",
    )
    parser.add_argument(
        "--min-bird-side",
        type=int,
        default=70,
        help="鸟框最小宽高（分析图像像素）。",
    )
    parser.add_argument(
        "--laplacian-threshold",
        type=float,
        default=1100.0,
        help="鸟 ROI 内 Laplacian 方差最小阈值。",
    )
    parser.add_argument(
        "--tenengrad-threshold",
        type=float,
        default=28.0,
        help="鸟 ROI 内 Tenengrad 分数最小阈值。",
    )
    parser.add_argument(
        "--tenengrad-p90-threshold",
        type=float,
        default=70.0,
        help="聚焦区域 Tenengrad 90 分位数最小阈值。",
    )
    parser.add_argument(
        "--strong-edge-ratio-threshold",
        type=float,
        default=0.06,
        help="聚焦区域强梯度像素占比最小阈值。",
    )
    parser.add_argument(
        "--center-crop-ratio",
        type=float,
        default=0.72,
        help="仅使用鸟 ROI 中央区域参与清晰度评估。",
    )
    parser.add_argument(
        "--min-focus-pixels",
        type=int,
        default=900,
        help="聚焦评估区域最小像素数。",
    )
    parser.add_argument(
        "--min-focus-pixel-ratio",
        type=float,
        default=0.10,
        help="聚焦评估区域最小面积占比（相对鸟框）。",
    )
    parser.add_argument(
        "--min-mask-fill-ratio",
        type=float,
        default=0.10,
        help="存在分割掩码时，要求掩码覆盖鸟框的最小比例。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅输出命中结果，不执行复制。",
    )
    parser.add_argument(
        "--log-format",
        choices=("csv", "jsonl"),
        default="csv",
        help="处理日志格式。",
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        default=None,
        help="日志输出路径（可选）。如父目录不存在会自动创建。",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=None,
        help="仅处理前 N 张 RAW（调参时使用）。",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="输出目录中存在同名文件时允许覆盖。",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    source_dir = args.source.resolve()
    output_dir = args.output_dir.resolve() if args.output_dir else source_dir / "selected_birds_in_focus"
    model_name: str = args.model
    model_path_candidate = Path(model_name)
    if model_path_candidate.exists():
        model_name = str(model_path_candidate.resolve())
    raw_extensions = tuple(
        item.strip().lower() if item.strip().startswith(".") else f".{item.strip().lower()}"
        for item in args.extensions.split(",")
        if item.strip()
    )
    exclude_dir_prefixes = tuple(
        item.strip().lower()
        for item in args.exclude_dir_prefixes.split(",")
        if item.strip()
    )
    if not raw_extensions:
        raise SystemExit("未提供有效的扩展名。")

    config = SelectorConfig(
        source_dir=source_dir,
        output_dir=output_dir,
        dry_run=args.dry_run,
        raw_extensions=raw_extensions,
        exclude_dir_prefixes=exclude_dir_prefixes,
        model_name=model_name,
        device=args.device,
        cpu_workers=args.cpu_workers,
        confidence_threshold=args.confidence_threshold,
        iou_threshold=args.iou_threshold,
        max_infer_side=args.max_infer_side,
        analysis_max_side=args.analysis_max_side,
        min_preview_side=args.min_preview_side,
        allow_full_raw_fallback=args.allow_full_raw_fallback,
        prefer_full_raw=args.prefer_full_raw,
        full_raw_half_size=args.full_raw_half_size,
        min_bird_area_ratio=args.min_bird_area_ratio,
        min_bird_side=args.min_bird_side,
        laplacian_threshold=args.laplacian_threshold,
        tenengrad_threshold=args.tenengrad_threshold,
        tenengrad_p90_threshold=args.tenengrad_p90_threshold,
        strong_edge_ratio_threshold=args.strong_edge_ratio_threshold,
        center_crop_ratio=args.center_crop_ratio,
        min_focus_pixels=args.min_focus_pixels,
        min_focus_pixel_ratio=args.min_focus_pixel_ratio,
        min_mask_fill_ratio=args.min_mask_fill_ratio,
        log_format=args.log_format,
        log_path=args.log_path.resolve() if args.log_path else None,
        sample_limit=args.sample_limit,
        overwrite=args.overwrite,
    )

    selector = BirdFocusSelector(config)
    results, log_path = selector.run()
    summary = summarize_results(results)

    print("")
    print("运行摘要")
    print(f"  处理总数: {summary['processed']}")
    print(f"  检测到鸟: {summary['bird_detected']}")
    print(f"  入选数量: {summary['selected']}")
    print(f"  已复制数量: {summary['copied']}")
    print(f"  解码错误: {summary['decode_errors']}")
    print(f"  日志路径: {log_path}")
    if args.dry_run:
        print("  模式: 仅预览（不复制文件）")

    return 0
