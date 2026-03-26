from __future__ import annotations

import csv
import json
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


class BirdFocusSelector:
    def __init__(self, config: SelectorConfig) -> None:
        self.config = config
        self.decoder = RawDecoder(
            analysis_max_side=config.analysis_max_side,
            min_preview_side=config.min_preview_side,
            allow_full_raw_fallback=config.allow_full_raw_fallback,
            prefer_full_raw=config.prefer_full_raw,
            full_raw_half_size=config.full_raw_half_size,
        )
        self.detector = BirdDetector(
            model_name=config.model_name,
            device=config.device,
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

    def run(self) -> tuple[list[FileDecision], Path]:
        files = list(self._iter_raw_files())
        if not files:
            raise RuntimeError(f"No supported RAW files were found under {self.config.source_dir}")

        if not self.config.dry_run:
            self.config.output_dir.mkdir(parents=True, exist_ok=True)

        results: list[FileDecision] = []
        progress = tqdm(files, desc="Scanning RAW files", unit="file")
        for file_path in progress:
            decision = self.process_file(file_path)
            if decision.final_decision:
                copy_status, copied_to = self._copy_if_needed(file_path)
                decision.copy_status = copy_status
                decision.copied_to = copied_to
            results.append(decision)

            if self.config.dry_run and decision.final_decision:
                print(file_path)

        log_path = self._resolve_log_path()
        self._write_log(results, log_path)
        return results, log_path

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
        if destination.exists() and not self.config.overwrite:
            return "already_exists", str(destination)

        try:
            shutil.copy2(file_path, destination)
            return "copied", str(destination)
        except Exception as exc:
            return f"copy_error:{exc}", None

    def _iter_raw_files(self) -> Iterable[Path]:
        source_dir = self.config.source_dir.resolve()
        output_dir = self.config.output_dir.resolve()
        exclude_prefixes = tuple(prefix.lower() for prefix in self.config.exclude_dir_prefixes if prefix.strip())
        count = 0
        for path in source_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in self.config.raw_extensions:
                continue
            relative_parts = path.relative_to(source_dir).parts[:-1]
            if exclude_prefixes and any(
                part.lower().startswith(prefix)
                for part in relative_parts
                for prefix in exclude_prefixes
            ):
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
