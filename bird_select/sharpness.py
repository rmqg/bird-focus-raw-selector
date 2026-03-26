from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(slots=True)
class SharpnessMetrics:
    laplacian_variance: float
    tenengrad_score: float
    tenengrad_p90: float
    strong_edge_ratio: float
    focus_pixels: int
    focus_pixel_ratio: float
    mask_fill_ratio: float
    focus_region: str


class SharpnessAnalyzer:
    def __init__(
        self,
        laplacian_threshold: float = 1100.0,
        tenengrad_threshold: float = 28.0,
        tenengrad_p90_threshold: float = 70.0,
        strong_edge_ratio_threshold: float = 0.06,
        center_crop_ratio: float = 0.72,
        min_focus_pixels: int = 900,
        min_focus_pixel_ratio: float = 0.10,
        min_mask_fill_ratio: float = 0.10,
    ) -> None:
        self.laplacian_threshold = laplacian_threshold
        self.tenengrad_threshold = tenengrad_threshold
        self.tenengrad_p90_threshold = tenengrad_p90_threshold
        self.strong_edge_ratio_threshold = strong_edge_ratio_threshold
        self.center_crop_ratio = center_crop_ratio
        self.min_focus_pixels = min_focus_pixels
        self.min_focus_pixel_ratio = min_focus_pixel_ratio
        self.min_mask_fill_ratio = min_mask_fill_ratio

    def analyze(
        self,
        image_rgb: np.ndarray,
        bbox_xyxy: tuple[int, int, int, int],
        mask: np.ndarray | None = None,
    ) -> SharpnessMetrics:
        x1, y1, x2, y2 = bbox_xyxy
        roi = image_rgb[y1:y2, x1:x2]
        if roi.size == 0:
            return self._empty_metrics()

        gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
        gray_f32 = gray.astype(np.float32)
        roi_height, roi_width = gray.shape
        bbox_pixels = int(roi_height * roi_width)
        if bbox_pixels <= 0:
            return self._empty_metrics()

        focus_mask = self._build_focus_mask(mask, bbox_xyxy, roi_width, roi_height)
        focus_pixels = int(focus_mask.sum())
        focus_pixel_ratio = focus_pixels / float(bbox_pixels)
        if focus_pixels <= 0:
            return SharpnessMetrics(
                laplacian_variance=0.0,
                tenengrad_score=0.0,
                tenengrad_p90=0.0,
                strong_edge_ratio=0.0,
                focus_pixels=0,
                focus_pixel_ratio=0.0,
                mask_fill_ratio=0.0,
                focus_region="empty",
            )

        laplacian = cv2.Laplacian(gray_f32, cv2.CV_32F, ksize=3)
        sobel_x = cv2.Sobel(gray_f32, cv2.CV_32F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray_f32, cv2.CV_32F, 0, 1, ksize=3)
        gradient_magnitude = cv2.magnitude(sobel_x, sobel_y)

        laplacian_values = laplacian[focus_mask]
        gradient_values = gradient_magnitude[focus_mask]

        laplacian_variance = float(laplacian_values.var())
        tenengrad_score = float(gradient_values.mean())
        tenengrad_p90 = float(np.percentile(gradient_values, 90))
        strong_edge_ratio = float((gradient_values >= 45.0).mean())

        mask_fill_ratio = 0.0
        focus_region = "bbox_center"
        if mask is not None:
            mask_roi = mask[y1:y2, x1:x2]
            if mask_roi.shape[:2] == (roi_height, roi_width):
                mask_fill_ratio = float(mask_roi.mean())
                focus_region = "mask_center"

        return SharpnessMetrics(
            laplacian_variance=laplacian_variance,
            tenengrad_score=tenengrad_score,
            tenengrad_p90=tenengrad_p90,
            strong_edge_ratio=strong_edge_ratio,
            focus_pixels=focus_pixels,
            focus_pixel_ratio=focus_pixel_ratio,
            mask_fill_ratio=mask_fill_ratio,
            focus_region=focus_region,
        )

    def is_sharp_enough(self, metrics: SharpnessMetrics) -> bool:
        return (
            metrics.laplacian_variance >= self.laplacian_threshold
            and metrics.tenengrad_score >= self.tenengrad_threshold
            and metrics.tenengrad_p90 >= self.tenengrad_p90_threshold
            and metrics.strong_edge_ratio >= self.strong_edge_ratio_threshold
            and metrics.focus_pixels >= self.min_focus_pixels
            and metrics.focus_pixel_ratio >= self.min_focus_pixel_ratio
            and (
                metrics.mask_fill_ratio == 0.0
                or metrics.mask_fill_ratio >= self.min_mask_fill_ratio
            )
        )

    def _build_focus_mask(
        self,
        mask: np.ndarray | None,
        bbox_xyxy: tuple[int, int, int, int],
        roi_width: int,
        roi_height: int,
    ) -> np.ndarray:
        center_mask = np.zeros((roi_height, roi_width), dtype=bool)
        inner_width = max(1, int(round(roi_width * self.center_crop_ratio)))
        inner_height = max(1, int(round(roi_height * self.center_crop_ratio)))
        start_x = max(0, (roi_width - inner_width) // 2)
        start_y = max(0, (roi_height - inner_height) // 2)
        end_x = min(roi_width, start_x + inner_width)
        end_y = min(roi_height, start_y + inner_height)
        center_mask[start_y:end_y, start_x:end_x] = True

        if mask is None:
            return center_mask

        x1, y1, x2, y2 = bbox_xyxy
        mask_roi = mask[y1:y2, x1:x2]
        if mask_roi.shape[:2] != (roi_height, roi_width):
            return center_mask

        binary_mask = mask_roi.astype(bool)
        if binary_mask.any():
            kernel_size = max(1, min(7, min(roi_width, roi_height) // 30))
            kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
            eroded = cv2.erode(binary_mask.astype(np.uint8), kernel, iterations=1).astype(bool)
            if eroded.any():
                binary_mask = eroded
        focus_mask = center_mask & binary_mask
        if focus_mask.any():
            return focus_mask
        return center_mask

    @staticmethod
    def _empty_metrics() -> SharpnessMetrics:
        return SharpnessMetrics(
            laplacian_variance=0.0,
            tenengrad_score=0.0,
            tenengrad_p90=0.0,
            strong_edge_ratio=0.0,
            focus_pixels=0,
            focus_pixel_ratio=0.0,
            mask_fill_ratio=0.0,
            focus_region="empty",
        )
