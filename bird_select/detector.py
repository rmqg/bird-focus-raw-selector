from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from ultralytics import YOLO


@dataclass(slots=True)
class BirdDetection:
    confidence: float
    bbox_xyxy: tuple[int, int, int, int]
    class_id: int
    class_name: str
    mask: np.ndarray | None


class BirdDetector:
    def __init__(
        self,
        model_name: str = "yolov8s-seg.pt",
        device: str = "cpu",
        confidence_threshold: float = 0.45,
        iou_threshold: float = 0.45,
        max_infer_side: int = 0,
    ) -> None:
        self.model = YOLO(model_name)
        self.device = device
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.max_infer_side = max_infer_side
        self.bird_class_ids = self._resolve_bird_class_ids()
        if not self.bird_class_ids:
            raise RuntimeError("The detection model does not expose a 'bird' class.")

    def _resolve_bird_class_ids(self) -> list[int]:
        names = self.model.names
        if isinstance(names, list):
            return [index for index, name in enumerate(names) if name == "bird"]
        return [int(index) for index, name in names.items() if name == "bird"]

    def detect(self, image_rgb: np.ndarray) -> list[BirdDetection]:
        image_height, image_width = image_rgb.shape[:2]
        infer_side = max(image_height, image_width)
        if self.max_infer_side > 0:
            infer_side = min(infer_side, self.max_infer_side)
        infer_side = max(640, int(round(infer_side / 32.0) * 32))

        results = self._predict_with_fallback(image_rgb, infer_side)
        if not results:
            return []

        result = results[0]
        if result.boxes is None or len(result.boxes) == 0:
            return []

        detections: list[BirdDetection] = []
        names = result.names
        mask_data = None
        if result.masks is not None and result.masks.data is not None:
            mask_data = result.masks.data.detach().cpu().numpy()

        for index, box in enumerate(result.boxes):
            class_id = int(box.cls.item())
            confidence = float(box.conf.item())
            x1, y1, x2, y2 = [int(round(value)) for value in box.xyxy[0].tolist()]
            mask = None
            if mask_data is not None and index < len(mask_data):
                raw_mask = mask_data[index]
                if raw_mask.shape[:2] != (image_height, image_width):
                    raw_mask = cv2.resize(
                        raw_mask.astype(np.float32),
                        (image_width, image_height),
                        interpolation=cv2.INTER_NEAREST,
                    )
                mask = raw_mask > 0.5
            detections.append(
                BirdDetection(
                    confidence=confidence,
                    bbox_xyxy=(x1, y1, x2, y2),
                    class_id=class_id,
                    class_name=names[class_id],
                    mask=mask,
                )
            )

        detections.sort(key=lambda item: item.confidence, reverse=True)
        return detections

    def _predict_with_fallback(self, image_rgb: np.ndarray, infer_side: int):
        current = infer_side
        last_error: Exception | None = None
        while current >= 640:
            try:
                return self.model.predict(
                    source=image_rgb,
                    device=self.device,
                    verbose=False,
                    conf=self.confidence_threshold,
                    iou=self.iou_threshold,
                    classes=self.bird_class_ids,
                    max_det=20,
                    imgsz=current,
                )
            except RuntimeError as exc:
                last_error = exc
                current = int(current * 0.75)
                current = max(640, int(round(current / 32.0) * 32))
                if current == 640:
                    break
        if last_error is not None:
            try:
                return self.model.predict(
                    source=image_rgb,
                    device=self.device,
                    verbose=False,
                    conf=self.confidence_threshold,
                    iou=self.iou_threshold,
                    classes=self.bird_class_ids,
                    max_det=20,
                    imgsz=640,
                )
            except RuntimeError as exc:
                raise RuntimeError(f"detector_failed_after_fallback:{exc}") from exc
        return self.model.predict(
            source=image_rgb,
            device=self.device,
            verbose=False,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            classes=self.bird_class_ids,
            max_det=20,
            imgsz=640,
        )
