from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from tqdm import tqdm

from .detector import BirdDetection, BirdDetector
from .raw_decoder import DecodeResult, RawDecodeError, RawDecoder
from .sharpness import SharpnessAnalyzer, SharpnessMetrics


@dataclass(slots=True)
class SelectorConfig:
    source_dir: Path
    output_dir: Path
    dry_run: bool
    raw_extensions: tuple[str, ...]
    exclude_dir_prefixes: tuple[str, ...]
    model_name: str
    device: str
    cpu_workers: int
    confidence_threshold: float
    iou_threshold: float
    max_infer_side: int
    analysis_max_side: int
    min_preview_side: int
    allow_full_raw_fallback: bool
    prefer_full_raw: bool
    full_raw_half_size: bool
    min_bird_area_ratio: float
    min_bird_side: int
    laplacian_threshold: float
    tenengrad_threshold: float
    tenengrad_p90_threshold: float
    strong_edge_ratio_threshold: float
    center_crop_ratio: float
    min_focus_pixels: int
    min_focus_pixel_ratio: float
    min_mask_fill_ratio: float
    log_format: str
    log_path: Path | None
    sample_limit: int | None
    overwrite: bool


@dataclass(slots=True)
class CandidateDecision:
    bbox_xyxy: tuple[int, int, int, int]
    confidence: float
    area_ratio: float
    laplacian_variance: float
    tenengrad_score: float
    tenengrad_p90: float
    strong_edge_ratio: float
    focus_pixels: int
    focus_pixel_ratio: float
    mask_fill_ratio: float
    focus_region: str
    sharp_enough: bool
    rejection_reason: str | None


@dataclass(slots=True)
class FileDecision:
    file_path: str
    bird_detected: bool
    detection_confidence: float | None
    sharpness_score: float | None
    threshold_used: str
    final_decision: bool
    failure_reason: str | None
    decode_method: str | None
    original_width: int | None
    original_height: int | None
    analysis_width: int | None
    analysis_height: int | None
    num_birds_detected: int
    num_candidate_birds: int
    laplacian_variance: float | None
    tenengrad_score: float | None
    tenengrad_p90: float | None
    strong_edge_ratio: float | None
    focus_pixels: int | None
    focus_pixel_ratio: float | None
    mask_fill_ratio: float | None
    focus_region: str | None
    selected_bbox: str | None
    copy_status: str
    copied_to: str | None
    details_json: str


_PROCESS_SELECTOR: BirdFocusSelector | None = None


def _init_process_selector(config: SelectorConfig) -> None:
    global _PROCESS_SELECTOR
    _PROCESS_SELECTOR = BirdFocusSelector(config)


def _process_file_in_worker(file_path_str: str) -> FileDecision:
    if _PROCESS_SELECTOR is None:
        raise RuntimeError("worker_selector_not_initialized")
    return _PROCESS_SELECTOR.process_file(Path(file_path_str))


def _worker_ready_signal() -> bool:
    # Worker initializer already loads model/decoder. Returning from this task
    # means one worker is ready to receive real file tasks.
    return True


class BirdFocusSelector:
    def __init__(self, config: SelectorConfig) -> None:
        self.config = config
        self.resolved_device = self._resolve_device(config.device)
        self.decoder = RawDecoder(
            analysis_max_side=config.analysis_max_side,
            min_preview_side=config.min_preview_side,
            allow_full_raw_fallback=config.allow_full_raw_fallback,
            prefer_full_raw=config.prefer_full_raw,
            full_raw_half_size=config.full_raw_half_size,
        )
        self.detector = BirdDetector(
            model_name=config.model_name,
            device=self.resolved_device,
            confidence_threshold=config.confidence_threshold,
            iou_threshold=config.iou_threshold,
            max_infer_side=config.max_infer_side,
        )
        self.sharpness_analyzer = SharpnessAnalyzer(
            laplacian_threshold=config.laplacian_threshold,
            tenengrad_threshold=config.tenengrad_threshold,
            tenengrad_p90_threshold=config.tenengrad_p90_threshold,
            strong_edge_ratio_threshold=config.strong_edge_ratio_threshold,
            center_crop_ratio=config.center_crop_ratio,
            min_focus_pixels=config.min_focus_pixels,
            min_focus_pixel_ratio=config.min_focus_pixel_ratio,
            min_mask_fill_ratio=config.min_mask_fill_ratio,
        )

    @staticmethod
    def _resolve_device(raw_device: str) -> str:
        device = str(raw_device).strip().lower()
        if device != "auto":
            return str(raw_device)

        try:
            import torch
        except Exception:
            return "cpu"

        return "0" if torch.cuda.is_available() else "cpu"

    def run(self) -> tuple[list[FileDecision], Path]:
        files = list(self._iter_raw_files())
        if not files:
            raise RuntimeError(f"No supported RAW files were found under {self.config.source_dir}")

        if not self.config.dry_run:
            self.config.output_dir.mkdir(parents=True, exist_ok=True)

        results: list[FileDecision] = []
        progress = tqdm(total=len(files), desc="Scanning RAW files", unit="file")

        if self._use_parallel_cpu():
            decisions_iter = self._iter_decisions_parallel_cpu(files)
        else:
            decisions_iter = ((file_path, self.process_file(file_path)) for file_path in files)

        for file_path, decision in decisions_iter:
            if decision.final_decision:
                copy_status, copied_to = self._copy_if_needed(file_path)
                decision.copy_status = copy_status
                decision.copied_to = copied_to
            results.append(decision)
            progress.update(1)

            if self.config.dry_run and decision.final_decision:
                print(file_path)
        progress.close()

        log_path = self._resolve_log_path()
        self._write_log(results, log_path)
        return results, log_path

    def _use_parallel_cpu(self) -> bool:
        device = str(self.resolved_device).strip().lower()
        return device == "cpu" and self._resolved_cpu_workers() > 1

    def _resolved_cpu_workers(self) -> int:
        if self.config.cpu_workers > 0:
            return self.config.cpu_workers
        cpu_count = os.cpu_count() or 1
        # Keep auto mode conservative to avoid excessive RAM usage.
        return max(1, min(8, cpu_count // 2))

    def _iter_decisions_parallel_cpu(self, files: list[Path]) -> Iterable[tuple[Path, FileDecision]]:
        workers = self._resolved_cpu_workers()
        if workers <= 1:
            for file_path in files:
                yield file_path, self.process_file(file_path)
            return

        with ProcessPoolExecutor(
            max_workers=workers,
            initializer=_init_process_selector,
            initargs=(self.config,),
        ) as executor:
            warmup_futures = [executor.submit(_worker_ready_signal) for _ in range(workers)]
            warmup_bar = tqdm(total=workers, desc="Initializing workers", unit="worker", leave=False)
            for future in as_completed(warmup_futures):
                future.result()
                warmup_bar.update(1)
            warmup_bar.close()

            future_to_path = {
                executor.submit(_process_file_in_worker, str(path)): path
                for path in files
            }
            for future in as_completed(future_to_path):
                file_path = future_to_path[future]
                decision = future.result()
                yield file_path, decision

    def process_file(self, file_path: Path) -> FileDecision:
        threshold_used = (
            f"conf>={self.config.confidence_threshold:.2f};"
            f"laplacian>={self.config.laplacian_threshold:.1f};"
            f"tenengrad>={self.config.tenengrad_threshold:.1f};"
            f"tenengrad_p90>={self.config.tenengrad_p90_threshold:.1f};"
            f"strong_edge_ratio>={self.config.strong_edge_ratio_threshold:.3f};"
            f"min_area_ratio>={self.config.min_bird_area_ratio:.4f};"
            f"min_side>={self.config.min_bird_side};"
            f"center_crop_ratio={self.config.center_crop_ratio:.2f};"
            f"min_focus_pixels>={self.config.min_focus_pixels};"
            f"min_focus_pixel_ratio>={self.config.min_focus_pixel_ratio:.3f};"
            f"min_mask_fill_ratio>={self.config.min_mask_fill_ratio:.3f}"
        )
        try:
            decode_result = self.decoder.decode_for_analysis(file_path)
        except RawDecodeError as exc:
            return FileDecision(
                file_path=str(file_path),
                bird_detected=False,
                detection_confidence=None,
                sharpness_score=None,
                threshold_used=threshold_used,
                final_decision=False,
                failure_reason=f"decode_error:{exc}",
                decode_method=None,
                original_width=None,
                original_height=None,
                analysis_width=None,
                analysis_height=None,
                num_birds_detected=0,
                num_candidate_birds=0,
                laplacian_variance=None,
                tenengrad_score=None,
                tenengrad_p90=None,
                strong_edge_ratio=None,
                focus_pixels=None,
                focus_pixel_ratio=None,
                mask_fill_ratio=None,
                focus_region=None,
                selected_bbox=None,
                copy_status="not_selected",
                copied_to=None,
                details_json="[]",
            )

        try:
            detections = self.detector.detect(decode_result.image_rgb)
        except Exception as exc:
            return FileDecision(
                file_path=str(file_path),
                bird_detected=False,
                detection_confidence=None,
                sharpness_score=None,
                threshold_used=threshold_used,
                final_decision=False,
                failure_reason=f"detector_error:{exc}",
                decode_method=decode_result.decode_method,
                original_width=decode_result.original_width,
                original_height=decode_result.original_height,
                analysis_width=decode_result.analysis_width,
                analysis_height=decode_result.analysis_height,
                num_birds_detected=0,
                num_candidate_birds=0,
                laplacian_variance=None,
                tenengrad_score=None,
                tenengrad_p90=None,
                strong_edge_ratio=None,
                focus_pixels=None,
                focus_pixel_ratio=None,
                mask_fill_ratio=None,
                focus_region=None,
                selected_bbox=None,
                copy_status="not_selected",
                copied_to=None,
                details_json="[]",
            )
        if not detections:
            return self._make_decision_without_selection(
                file_path=file_path,
                decode_result=decode_result,
                threshold_used=threshold_used,
                failure_reason="no_bird_detected",
                detections=[],
            )

        try:
            candidates = self._evaluate_candidates(decode_result, detections)
        except Exception as exc:
            best_confidence = max((item.confidence for item in detections), default=None)
            return FileDecision(
                file_path=str(file_path),
                bird_detected=True,
                detection_confidence=best_confidence,
                sharpness_score=None,
                threshold_used=threshold_used,
                final_decision=False,
                failure_reason=f"sharpness_error:{exc}",
                decode_method=decode_result.decode_method,
                original_width=decode_result.original_width,
                original_height=decode_result.original_height,
                analysis_width=decode_result.analysis_width,
                analysis_height=decode_result.analysis_height,
                num_birds_detected=len(detections),
                num_candidate_birds=0,
                laplacian_variance=None,
                tenengrad_score=None,
                tenengrad_p90=None,
                strong_edge_ratio=None,
                focus_pixels=None,
                focus_pixel_ratio=None,
                mask_fill_ratio=None,
                focus_region=None,
                selected_bbox=None,
                copy_status="not_selected",
                copied_to=None,
                details_json="[]",
            )
        selectable = [item for item in candidates if item.rejection_reason is None]
        sharp_candidates = [item for item in selectable if item.sharp_enough]

        if sharp_candidates:
            winner = max(
                sharp_candidates,
                key=lambda item: (item.laplacian_variance, item.tenengrad_score, item.confidence),
            )
            return FileDecision(
                file_path=str(file_path),
                bird_detected=True,
                detection_confidence=winner.confidence,
                sharpness_score=winner.laplacian_variance,
                threshold_used=threshold_used,
                final_decision=True,
                failure_reason=None,
                decode_method=decode_result.decode_method,
                original_width=decode_result.original_width,
                original_height=decode_result.original_height,
                analysis_width=decode_result.analysis_width,
                analysis_height=decode_result.analysis_height,
                num_birds_detected=len(detections),
                num_candidate_birds=len(selectable),
                laplacian_variance=winner.laplacian_variance,
                tenengrad_score=winner.tenengrad_score,
                tenengrad_p90=winner.tenengrad_p90,
                strong_edge_ratio=winner.strong_edge_ratio,
                focus_pixels=winner.focus_pixels,
                focus_pixel_ratio=winner.focus_pixel_ratio,
                mask_fill_ratio=winner.mask_fill_ratio,
                focus_region=winner.focus_region,
                selected_bbox=json.dumps(winner.bbox_xyxy),
                copy_status="pending_copy" if not self.config.dry_run else "dry_run_selected",
                copied_to=None,
                details_json=self._serialize_candidates(candidates),
            )

        failure_reason = (
            "bird_detected_but_below_sharpness_threshold"
            if selectable
            else "bird_detected_but_boxes_too_small"
        )
        best_detection = max(detections, key=lambda item: item.confidence)
        best_candidate = max(candidates, key=lambda item: (item.laplacian_variance, item.tenengrad_score))
        return FileDecision(
            file_path=str(file_path),
            bird_detected=True,
            detection_confidence=best_detection.confidence,
            sharpness_score=best_candidate.laplacian_variance,
            threshold_used=threshold_used,
            final_decision=False,
            failure_reason=failure_reason,
            decode_method=decode_result.decode_method,
            original_width=decode_result.original_width,
            original_height=decode_result.original_height,
            analysis_width=decode_result.analysis_width,
            analysis_height=decode_result.analysis_height,
            num_birds_detected=len(detections),
            num_candidate_birds=len(selectable),
            laplacian_variance=best_candidate.laplacian_variance,
            tenengrad_score=best_candidate.tenengrad_score,
            tenengrad_p90=best_candidate.tenengrad_p90,
            strong_edge_ratio=best_candidate.strong_edge_ratio,
            focus_pixels=best_candidate.focus_pixels,
            focus_pixel_ratio=best_candidate.focus_pixel_ratio,
            mask_fill_ratio=best_candidate.mask_fill_ratio,
            focus_region=best_candidate.focus_region,
            selected_bbox=json.dumps(best_candidate.bbox_xyxy),
            copy_status="not_selected",
            copied_to=None,
            details_json=self._serialize_candidates(candidates),
        )

    def _make_decision_without_selection(
        self,
        file_path: Path,
        decode_result: DecodeResult,
        threshold_used: str,
        failure_reason: str,
        detections: list[BirdDetection],
    ) -> FileDecision:
        best_confidence = max((item.confidence for item in detections), default=None)
        return FileDecision(
            file_path=str(file_path),
            bird_detected=bool(detections),
            detection_confidence=best_confidence,
            sharpness_score=None,
            threshold_used=threshold_used,
            final_decision=False,
            failure_reason=failure_reason,
            decode_method=decode_result.decode_method,
            original_width=decode_result.original_width,
            original_height=decode_result.original_height,
            analysis_width=decode_result.analysis_width,
            analysis_height=decode_result.analysis_height,
            num_birds_detected=len(detections),
            num_candidate_birds=0,
            laplacian_variance=None,
            tenengrad_score=None,
            tenengrad_p90=None,
            strong_edge_ratio=None,
            focus_pixels=None,
            focus_pixel_ratio=None,
            mask_fill_ratio=None,
            focus_region=None,
            selected_bbox=None,
            copy_status="not_selected",
            copied_to=None,
            details_json="[]",
        )

    def _evaluate_candidates(
        self,
        decode_result: DecodeResult,
        detections: list[BirdDetection],
    ) -> list[CandidateDecision]:
        height, width = decode_result.image_rgb.shape[:2]
        image_area = float(height * width)
        candidates: list[CandidateDecision] = []

        for detection in detections:
            x1, y1, x2, y2 = self._clip_bbox(detection.bbox_xyxy, width, height)
            box_width = max(0, x2 - x1)
            box_height = max(0, y2 - y1)
            area_ratio = (box_width * box_height) / image_area if image_area else 0.0

            rejection_reason = None
            if box_width < self.config.min_bird_side or box_height < self.config.min_bird_side:
                rejection_reason = "bbox_side_below_min"
            elif area_ratio < self.config.min_bird_area_ratio:
                rejection_reason = "bbox_area_ratio_below_min"

            if rejection_reason is None:
                metrics = self.sharpness_analyzer.analyze(
                    decode_result.image_rgb,
                    (x1, y1, x2, y2),
                    mask=detection.mask,
                )
            else:
                metrics = SharpnessMetrics(
                    laplacian_variance=0.0,
                    tenengrad_score=0.0,
                    tenengrad_p90=0.0,
                    strong_edge_ratio=0.0,
                    focus_pixels=0,
                    focus_pixel_ratio=0.0,
                    mask_fill_ratio=0.0,
                    focus_region="rejected_before_focus",
                )

            candidates.append(
                CandidateDecision(
                    bbox_xyxy=(x1, y1, x2, y2),
                    confidence=detection.confidence,
                    area_ratio=area_ratio,
                    laplacian_variance=metrics.laplacian_variance,
                    tenengrad_score=metrics.tenengrad_score,
                    tenengrad_p90=metrics.tenengrad_p90,
                    strong_edge_ratio=metrics.strong_edge_ratio,
                    focus_pixels=metrics.focus_pixels,
                    focus_pixel_ratio=metrics.focus_pixel_ratio,
                    mask_fill_ratio=metrics.mask_fill_ratio,
                    focus_region=metrics.focus_region,
                    sharp_enough=self.sharpness_analyzer.is_sharp_enough(metrics) if rejection_reason is None else False,
                    rejection_reason=rejection_reason,
                )
            )

        return candidates

    def _copy_if_needed(self, file_path: Path) -> tuple[str, str | None]:
        if self.config.dry_run:
            return "dry_run_selected", None

        destination = self.config.output_dir / file_path.name
        copy_status = "copied"
        if destination.exists() and not self.config.overwrite:
            destination = self._next_available_destination(destination)
            copy_status = "copied_renamed"

        try:
            shutil.copy2(file_path, destination)
            return copy_status, str(destination)
        except Exception as exc:
            return f"copy_error:{exc}", None

    @staticmethod
    def _next_available_destination(destination: Path) -> Path:
        stem = destination.stem
        suffix = destination.suffix
        parent = destination.parent
        index = 1
        while True:
            candidate = parent / f"{stem}__dup{index:03d}{suffix}"
            if not candidate.exists():
                return candidate
            index += 1

    def _iter_raw_files(self) -> Iterable[Path]:
        source_dir = self.config.source_dir.resolve()
        output_dir = self.config.output_dir.resolve()
        exclude_prefixes = tuple(prefix.lower() for prefix in self.config.exclude_dir_prefixes if prefix.strip())
        count = 0
        for root, dirs, files in os.walk(source_dir, topdown=True):
            root_path = Path(root).resolve()

            # Prune folders early to avoid descending into output or excluded folders.
            kept_dirs: list[str] = []
            for dir_name in dirs:
                dir_path = (root_path / dir_name).resolve()
                dir_name_lower = dir_name.lower()
                if dir_path.is_relative_to(output_dir):
                    continue
                if exclude_prefixes and any(dir_name_lower.startswith(prefix) for prefix in exclude_prefixes):
                    continue
                kept_dirs.append(dir_name)
            dirs[:] = kept_dirs

            for file_name in files:
                path = root_path / file_name
                if path.suffix.lower() not in self.config.raw_extensions:
                    continue
                if path.resolve().is_relative_to(output_dir):
                    continue
                yield path
                count += 1
                if self.config.sample_limit is not None and count >= self.config.sample_limit:
                    return

    def _resolve_log_path(self) -> Path:
        extension = "csv" if self.config.log_format == "csv" else "jsonl"
        if self.config.log_path is not None:
            self.config.log_path.parent.mkdir(parents=True, exist_ok=True)
            return self.config.log_path

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.config.dry_run:
            log_dir = self.config.source_dir
        else:
            log_dir = self.config.output_dir
            log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / f"bird_focus_selection_{timestamp}.{extension}"

    def _write_log(self, results: list[FileDecision], log_path: Path) -> None:
        if self.config.log_format == "jsonl":
            with log_path.open("w", encoding="utf-8") as handle:
                for item in results:
                    handle.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
            return

        rows = [asdict(item) for item in results]
        fieldnames = list(FileDecision.__dataclass_fields__.keys())
        with log_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _serialize_candidates(self, candidates: list[CandidateDecision]) -> str:
        return json.dumps([asdict(item) for item in candidates], ensure_ascii=False)

    @staticmethod
    def _clip_bbox(
        bbox_xyxy: tuple[int, int, int, int],
        image_width: int,
        image_height: int,
    ) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = bbox_xyxy
        x1 = max(0, min(x1, image_width - 1))
        y1 = max(0, min(y1, image_height - 1))
        x2 = max(x1 + 1, min(x2, image_width))
        y2 = max(y1 + 1, min(y2, image_height))
        return x1, y1, x2, y2


def summarize_results(results: list[FileDecision]) -> dict[str, int]:
    return {
        "processed": len(results),
        "selected": sum(1 for item in results if item.final_decision),
        "copied": sum(1 for item in results if item.copy_status == "copied"),
        "decode_errors": sum(1 for item in results if item.failure_reason and item.failure_reason.startswith("decode_error")),
        "bird_detected": sum(1 for item in results if item.bird_detected),
    }
