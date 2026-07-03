from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: dict[str, int]


class YoloDetector:
    def __init__(self, weights_path: str):
        from ultralytics import YOLO

        self.model = YOLO(weights_path)

    def detect(self, frame) -> list[Detection]:
        results = self.model.predict(frame, verbose=False)
        detections: list[Detection] = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                class_index = int(box.cls.item()) if hasattr(box.cls, "item") else int(box.cls)
                confidence = float(box.conf.item()) if hasattr(box.conf, "item") else float(box.conf)
                coords = box.xyxy[0].tolist()
                detections.append(
                    Detection(
                        class_name=self.model.names.get(class_index, str(class_index)),
                        confidence=confidence,
                        bbox={
                            "x": int(coords[0]),
                            "y": int(coords[1]),
                            "width": int(coords[2] - coords[0]),
                            "height": int(coords[3] - coords[1]),
                        },
                    )
                )
        return detections
