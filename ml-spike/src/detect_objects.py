"""Run YOLOv8 on clips and save raw per-frame detections for each ROI.

This file is intentionally lightweight. It is the first step of the spike and
is designed to work on short sample clips once the real footage and ROIs exist.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass
class BBox:
    x: int
    y: int
    width: int
    height: int


@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: BBox


def load_rois(rois_path: Path) -> dict[str, dict[str, int]]:
    return json.loads(rois_path.read_text(encoding="utf-8"))


def build_output_path(results_dir: Path, clip_path: Path) -> Path:
    return results_dir / f"{clip_path.stem}_raw_detections.json"


def try_import_model() -> Any:
    try:
        from ultralytics import YOLO
    except Exception as exc:  # pragma: no cover - import guard for spike setup
        raise RuntimeError(
            "ultralytics is not available. Install requirements before running the spike."
        ) from exc
    return YOLO


def detect_on_roi(frame: Any, roi: dict[str, int], model: Any) -> list[Detection]:
    import cv2

    frame_h, frame_w = frame.shape[:2]
    x = roi["x"]
    y = roi["y"]
    width = roi["width"]
    height = roi["height"]

    sx = frame_w / 1280
    sy = frame_h / 720
    x = int(x * sx)
    y = int(y * sy)
    width = int(width * sx)
    height = int(height * sy)

    x = max(0, min(x, frame_w - 1))
    y = max(0, min(y, frame_h - 1))
    width = max(1, min(width, frame_w - x))
    height = max(1, min(height, frame_h - y))

    cropped = frame[y : y + height, x : x + width]
    if cropped.size == 0:
        return []

    results = model.predict(cropped, verbose=False)
    detections: list[Detection] = []
    for result in results:
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        for box in boxes:
            class_index = int(box.cls.item()) if hasattr(box.cls, "item") else int(box.cls)
            class_name = model.names.get(class_index, str(class_index))
            confidence = float(box.conf.item()) if hasattr(box.conf, "item") else float(box.conf)
            coords = box.xyxy[0].tolist()
            detections.append(
                Detection(
                    class_name=class_name,
                    confidence=confidence,
                    bbox=BBox(
                        x=int(coords[0]),
                        y=int(coords[1]),
                        width=int(coords[2] - coords[0]),
                        height=int(coords[3] - coords[1]),
                    ),
                )
            )
    return detections


def iter_video_frames(video_path: Path) -> Iterable[tuple[int, float, Any]]:
    import cv2

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
    frame_index = 0
    while True:
        success, frame = capture.read()
        if not success:
            break
        timestamp_seconds = frame_index / fps if fps else float(frame_index)
        yield frame_index, timestamp_seconds, frame
        frame_index += 1

    capture.release()


def iter_webcam_frames(webcam_index: int = 0, limit: int = 300) -> Iterable[tuple[int, float, Any]]:
    import cv2

    capture = cv2.VideoCapture(webcam_index)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open webcam index {webcam_index}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    frame_index = 0
    try:
        while frame_index < limit:
            success, frame = capture.read()
            if not success:
                break
            timestamp_seconds = frame_index / fps
            yield frame_index, timestamp_seconds, frame
            frame_index += 1
    finally:
        capture.release()


def run_detection(clip_path: Path | None, rois_path: Path, model_path: str, results_dir: Path, webcam_index: int | None = None, frame_limit: int = 300) -> Path:
    import cv2  # noqa: F401  # imported for side effect of validating dependency availability

    YOLO = try_import_model()
    model = YOLO(model_path)
    rois = load_rois(rois_path)

    if webcam_index is not None:
        source_label = f"webcam_{webcam_index}"
        frame_cache = list(iter_webcam_frames(webcam_index, limit=frame_limit))
    else:
        source_label = clip_path.stem if clip_path else "unknown"
        frame_cache = list(iter_video_frames(clip_path))

    output = {"clip_name": source_label, "rois": []}

    for roi_name, roi in rois.items():
        roi_frames = []
        for frame_number, timestamp_seconds, frame in frame_cache:
            detections = detect_on_roi(frame, roi, model)
            roi_frames.append(
                {
                    "frame_number": frame_number,
                    "timestamp_seconds": timestamp_seconds,
                    "detections": [
                        {
                            "class": detection.class_name,
                            "confidence": detection.confidence,
                            "bbox": asdict(detection.bbox),
                        }
                        for detection in detections
                    ],
                }
            )
        output["rois"].append({"roi": roi_name, "frames": roi_frames})

    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = build_output_path(results_dir, Path(source_label))
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run raw object detection on a clip or webcam.")
    parser.add_argument("clip", nargs="?", type=Path, help="Path to a sample video clip (omit for webcam mode)")
    parser.add_argument("--webcam", type=int, default=None, help="Webcam index (e.g. 0) to capture live frames")
    parser.add_argument("--frames", type=int, default=300, help="Max frames to capture from webcam (default 300)")
    parser.add_argument("--rois", type=Path, default=Path("data/rois.json"), help="ROI config JSON")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="YOLOv8 weights path or name")
    parser.add_argument("--results-dir", type=Path, default=Path("results"), help="Output folder")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.webcam is not None:
        output_path = run_detection(None, args.rois, args.model, args.results_dir, webcam_index=args.webcam, frame_limit=args.frames)
    elif args.clip is not None:
        output_path = run_detection(args.clip, args.rois, args.model, args.results_dir)
    else:
        print("Error: provide a clip path or use --webcam <index>")
        return
    print(output_path)


if __name__ == "__main__":
    main()