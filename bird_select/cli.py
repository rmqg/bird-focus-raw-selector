from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import BirdFocusSelector, SelectorConfig, summarize_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select RAW files that contain at least one bird in focus.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(r"E:\100NZ7_2"),
        help="Source directory that will be scanned recursively for supported RAW files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for matched RAW files. Defaults to <source>/selected_birds_in_focus.",
    )
    parser.add_argument(
        "--extensions",
        default=".nef,.nrw,.cr2,.cr3,.crw,.arw,.sr2,.srf",
        help="Comma-separated RAW file extensions to scan recursively.",
    )
    parser.add_argument(
        "--exclude-dir-prefixes",
        default="selected_birds_in_focus,raw",
        help="Comma-separated directory-name prefixes to skip during recursive scan.",
    )
    parser.add_argument(
        "--model",
        default="yolov8s-seg.pt",
        help="Pretrained bird detection model name or local path. Segmentation models are preferred for higher precision.",
    )
    parser.add_argument(
        "--cpu-workers",
        type=int,
        default=0,
        help="CPU parallel worker count. 0 means auto (about half of logical CPU cores).",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.40,
        help="Minimum bird detection confidence.",
    )
    parser.add_argument(
        "--iou-threshold",
        type=float,
        default=0.45,
        help="NMS IoU threshold for the detector.",
    )
    parser.add_argument(
        "--max-infer-side",
        type=int,
        default=0,
        help="Detector inference side length cap. 0 means use image max side directly.",
    )
    parser.add_argument(
        "--analysis-max-side",
        type=int,
        default=0,
        help="Resize decoded images to this max side before detection. 0 means no resize.",
    )
    parser.add_argument(
        "--min-preview-side",
        type=int,
        default=1200,
        help="If the embedded preview is smaller than this, fall back to half-size RAW decoding.",
    )
    parser.add_argument(
        "--allow-full-raw-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Allow fallback decoding strategy when preferred full RAW decode fails.",
    )
    parser.add_argument(
        "--prefer-full-raw",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Prefer full RAW decode before trying embedded preview.",
    )
    parser.add_argument(
        "--full-raw-half-size",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Decode full RAW at half-size. Keep disabled to use full resolution.",
    )
    parser.add_argument(
        "--min-bird-area-ratio",
        type=float,
        default=0.0015,
        help="Minimum bird bounding-box area divided by full image area.",
    )
    parser.add_argument(
        "--min-bird-side",
        type=int,
        default=70,
        help="Minimum bird bounding-box width and height in analysis pixels.",
    )
    parser.add_argument(
        "--laplacian-threshold",
        type=float,
        default=1100.0,
        help="Minimum Laplacian variance required inside the bird ROI.",
    )
    parser.add_argument(
        "--tenengrad-threshold",
        type=float,
        default=28.0,
        help="Minimum Tenengrad score required inside the bird ROI.",
    )
    parser.add_argument(
        "--tenengrad-p90-threshold",
        type=float,
        default=70.0,
        help="Minimum 90th percentile Tenengrad score inside the focus region.",
    )
    parser.add_argument(
        "--strong-edge-ratio-threshold",
        type=float,
        default=0.06,
        help="Minimum ratio of strong gradients inside the focus region.",
    )
    parser.add_argument(
        "--center-crop-ratio",
        type=float,
        default=0.72,
        help="Only the central portion of the bird ROI is used for sharpness evaluation.",
    )
    parser.add_argument(
        "--min-focus-pixels",
        type=int,
        default=900,
        help="Minimum number of pixels in the evaluated focus region.",
    )
    parser.add_argument(
        "--min-focus-pixel-ratio",
        type=float,
        default=0.10,
        help="Minimum evaluated focus-region area divided by bird bounding-box area.",
    )
    parser.add_argument(
        "--min-mask-fill-ratio",
        type=float,
        default=0.10,
        help="When a segmentation mask exists, require at least this much of the bbox to be covered by the mask.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected files but do not copy them.",
    )
    parser.add_argument(
        "--log-format",
        choices=("csv", "jsonl"),
        default="csv",
        help="Structured log format for all processed files.",
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        default=None,
        help="Optional explicit log path. The parent directory will be created if needed.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=None,
        help="Only process the first N RAW files after recursive discovery. Useful for threshold tuning.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite files in the output directory if they already exist.",
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
        raise SystemExit("No valid extensions were provided.")

    config = SelectorConfig(
        source_dir=source_dir,
        output_dir=output_dir,
        dry_run=args.dry_run,
        raw_extensions=raw_extensions,
        exclude_dir_prefixes=exclude_dir_prefixes,
        model_name=model_name,
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
    print("Run summary")
    print(f"  Processed: {summary['processed']}")
    print(f"  Bird detected: {summary['bird_detected']}")
    print(f"  Selected: {summary['selected']}")
    print(f"  Copied: {summary['copied']}")
    print(f"  Decode errors: {summary['decode_errors']}")
    print(f"  Log: {log_path}")
    if args.dry_run:
        print("  Mode: dry-run (no files copied)")

    return 0
