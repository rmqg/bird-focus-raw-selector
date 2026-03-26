from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import rawpy


class RawDecodeError(RuntimeError):
    """Raised when a RAW file cannot be decoded for analysis."""


@dataclass(slots=True)
class DecodeResult:
    image_rgb: np.ndarray
    decode_method: str
    original_width: int
    original_height: int
    analysis_width: int
    analysis_height: int


class RawDecoder:
    def __init__(
        self,
        analysis_max_side: int = 0,
        min_preview_side: int = 1200,
        allow_full_raw_fallback: bool = True,
        prefer_full_raw: bool = True,
        full_raw_half_size: bool = False,
    ) -> None:
        self.analysis_max_side = analysis_max_side
        self.min_preview_side = min_preview_side
        self.allow_full_raw_fallback = allow_full_raw_fallback
        self.prefer_full_raw = prefer_full_raw
        self.full_raw_half_size = full_raw_half_size

    def decode_for_analysis(self, file_path: Path) -> DecodeResult:
        try:
            with rawpy.imread(str(file_path)) as raw:
                if self.prefer_full_raw:
                    full_result = self._try_decode_full_raw(raw)
                    if full_result is not None:
                        return full_result

                    preview_result = self._try_decode_preview(raw, decode_method="embedded_preview_fallback")
                    if preview_result is not None:
                        return preview_result
                    raise RawDecodeError("full_raw_and_preview_decode_failed")

                preview_result = self._try_decode_preview(raw, decode_method="embedded_preview")
                if preview_result is not None:
                    return preview_result

                if not self.allow_full_raw_fallback:
                    raise RawDecodeError("preview_too_small_or_missing")
                full_result = self._try_decode_full_raw(raw)
                if full_result is None:
                    raise RawDecodeError("full_raw_decode_failed")
                return full_result
        except RawDecodeError:
            raise
        except rawpy.LibRawError as exc:
            raise RawDecodeError(str(exc)) from exc
        except Exception as exc:
            raise RawDecodeError(str(exc)) from exc

    def _try_decode_full_raw(self, raw: rawpy.RawPy) -> DecodeResult | None:
        try:
            full_rgb = raw.postprocess(
                use_camera_wb=True,
                no_auto_bright=False,
                output_bps=8,
                half_size=self.full_raw_half_size,
            )
            resized = self._resize_for_analysis(full_rgb)
            return DecodeResult(
                image_rgb=resized,
                decode_method="half_size_raw" if self.full_raw_half_size else "full_raw",
                original_width=int(full_rgb.shape[1]),
                original_height=int(full_rgb.shape[0]),
                analysis_width=int(resized.shape[1]),
                analysis_height=int(resized.shape[0]),
            )
        except (rawpy.LibRawError, MemoryError, ValueError):
            if self.full_raw_half_size or not self.allow_full_raw_fallback:
                return None
            try:
                half_rgb = raw.postprocess(
                    use_camera_wb=True,
                    no_auto_bright=False,
                    output_bps=8,
                    half_size=True,
                )
                resized = self._resize_for_analysis(half_rgb)
                return DecodeResult(
                    image_rgb=resized,
                    decode_method="half_size_raw_fallback",
                    original_width=int(half_rgb.shape[1]),
                    original_height=int(half_rgb.shape[0]),
                    analysis_width=int(resized.shape[1]),
                    analysis_height=int(resized.shape[0]),
                )
            except (rawpy.LibRawError, MemoryError, ValueError):
                return None

    def _try_decode_preview(self, raw: rawpy.RawPy, decode_method: str) -> DecodeResult | None:
        preview_rgb = self._try_extract_preview(raw)
        if preview_rgb is None or max(preview_rgb.shape[:2]) < self.min_preview_side:
            return None
        resized = self._resize_for_analysis(preview_rgb)
        return DecodeResult(
            image_rgb=resized,
            decode_method=decode_method,
            original_width=int(preview_rgb.shape[1]),
            original_height=int(preview_rgb.shape[0]),
            analysis_width=int(resized.shape[1]),
            analysis_height=int(resized.shape[0]),
        )

    def _try_extract_preview(self, raw: rawpy.RawPy) -> np.ndarray | None:
        try:
            thumb = raw.extract_thumb()
        except (
            rawpy.LibRawNoThumbnailError,
            rawpy.LibRawUnsupportedThumbnailError,
            rawpy.LibRawError,
        ):
            return None

        if thumb.format == rawpy.ThumbFormat.JPEG:
            buffer = np.frombuffer(thumb.data, dtype=np.uint8)
            bgr = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
            if bgr is None:
                return None
            return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        if thumb.format == rawpy.ThumbFormat.BITMAP:
            bitmap = np.asarray(thumb.data)
            if bitmap.ndim == 2:
                return cv2.cvtColor(bitmap, cv2.COLOR_GRAY2RGB)
            if bitmap.ndim == 3 and bitmap.shape[2] == 4:
                return cv2.cvtColor(bitmap, cv2.COLOR_RGBA2RGB)
            return bitmap

        return None

    def _resize_for_analysis(self, image_rgb: np.ndarray) -> np.ndarray:
        if self.analysis_max_side <= 0:
            return image_rgb
        height, width = image_rgb.shape[:2]
        max_side = max(height, width)
        if max_side <= self.analysis_max_side:
            return image_rgb

        scale = self.analysis_max_side / float(max_side)
        resized = cv2.resize(
            image_rgb,
            (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
            interpolation=cv2.INTER_AREA,
        )
        return resized
