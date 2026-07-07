"""Run inference on a recorded video clip (offline mode).

Usage:
    python run_inference.py --video data/raw_clips/milking_clip.mp4
    python run_inference.py --video data/raw_clips/milking_clip.mp4 --model path/to/best.pt
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2


TASK_SIGNALS = {
    "TASK-01": {"person", "spray_bottle"},
    "TASK-02": {"person", "stripping_cup"},
    "TASK-03": {"teat_cups_attached"},
    "TASK-04": {"teat_cups_attached"},
    "TASK-05": {"teat_cups_detached"},
    "TASK-06": {"person", "dip_applicator"},
}

TASK_NAMES = {
    "TASK-01": "Pre-cleaning",
    "TASK-02": "Stripping",
    "TASK-03": "Machine attachment",
    "TASK-04": "Milking",
    "TASK-05": "Detachment",
    "TASK-06": "Post-dip",
}


@dataclass
class FrameDetection:
    frame_index: int
    timestamp: float
    detections: list[dict]


def run_inference(video_path: Path, model_path: str, output_dir: Path, fps: float = 1.0):
    from ultralytics import YOLO

    model = YOLO(model_path)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval = int(video_fps / fps)
    if frame_interval < 1:
        frame_interval = 1

    output_dir.mkdir(parents=True, exist_ok=True)
    all_detections = []
    all_events = []
    completed_tasks = set()

    frame_idx = 0
    print(f"Processing {video_path.name}...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            timestamp = frame_idx / video_fps
            results = model.predict(frame, verbose=False)

            frame_dets = []
            class_names = set()
            for r in results:
                for box in r.boxes:
                    cls_name = model.names[int(box.cls[0])]
                    conf = float(box.conf[0])
                    xyxy = box.xyxy[0].tolist()
                    frame_dets.append({
                        "class": cls_name,
                        "confidence": round(conf, 3),
                        "bbox": [int(x) for x in xyxy],
                    })
                    class_names.add(cls_name)

            all_detections.append({
                "frame": frame_idx,
                "timestamp": round(timestamp, 2),
                "detections": frame_dets,
            })

            for task_id, required in TASK_SIGNALS.items():
                if required.issubset(class_names) and task_id not in completed_tasks:
                    event = {
                        "task_id": task_id,
                        "task_name": TASK_NAMES[task_id],
                        "status": "completed",
                        "timestamp": round(timestamp, 2),
                        "confidence": min(d["confidence"] for d in frame_dets if d["class"] in required),
                    }
                    all_events.append(event)
                    completed_tasks.add(task_id)
                    print(f"  {task_id} ({TASK_NAMES[task_id]}): completed at {timestamp:.1f}s")

            if frame_idx % 50 == 0:
                print(f"  Frame {frame_idx}...")

        frame_idx += 1

    cap.release()

    output = {
        "video": video_path.name,
        "total_frames": frame_idx,
        "detections": all_detections,
        "events": all_events,
    }

    output_path = output_dir / f"{video_path.stem}_results.json"
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nDone. {len(all_events)} events detected. Results: {output_path}")
    return output


def main():
    parser = argparse.ArgumentParser(description="Run inference on recorded clip")
    parser.add_argument("--video", type=Path, required=True, help="Video file path")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="YOLO weights path")
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--fps", type=float, default=1.0, help="Analysis frame rate")
    args = parser.parse_args()

    run_inference(args.video, args.model, args.output, args.fps)


if __name__ == "__main__":
    main()
