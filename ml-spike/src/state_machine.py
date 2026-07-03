"""Convert raw detections into experimental task events.

Maps detected object classes to milking tasks based on the production
task_signals mapping. This is still a spike-level implementation but
now produces real results from the detection data.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


TASK_ORDER = ["TASK-01", "TASK-02", "TASK-03", "TASK-04", "TASK-05", "TASK-06"]

TASK_SIGNALS = {
    "TASK-01": {"person", "spray_bottle"},
    "TASK-02": {"person", "stripping_cup"},
    "TASK-03": {"teat_cups_attached"},
    "TASK-04": {"teat_cups_attached"},
    "TASK-05": {"teat_cups_detached"},
    "TASK-06": {"person", "dip_applicator"},
}

TASK_CONFIDENCE_DEFAULTS = {
    "TASK-01": 0.82,
    "TASK-02": 0.78,
    "TASK-03": 0.96,
    "TASK-04": 0.91,
    "TASK-05": 0.95,
    "TASK-06": 0.80,
}


@dataclass
class Event:
    task_id: str
    detected_start_seconds: float
    detected_end_seconds: float
    confidence_score: float
    status_guess: str
    note: str


def load_raw_detections(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_classes_for_frame(frame: dict) -> set[str]:
    return {det["class"] for det in frame.get("detections", [])}


def infer_events(raw_detections: dict) -> dict:
    candidate_events_per_roi = []

    for roi_data in raw_detections.get("rois", []):
        roi_name = roi_data.get("roi", "unknown")
        frames = roi_data.get("frames", [])
        completed_tasks: set[str] = set()
        events: list[dict] = []

        first_frame_time = frames[0]["timestamp_seconds"] if frames else 0.0
        last_frame_time = frames[-1]["timestamp_seconds"] if frames else 0.0
        active_start: dict[str, float] = {}

        for frame in frames:
            classes = _collect_classes_for_frame(frame)
            t = frame["timestamp_seconds"]

            for task_id, required_signals in TASK_SIGNALS.items():
                if task_id in completed_tasks:
                    continue
                if required_signals.issubset(classes):
                    if task_id not in active_start:
                        active_start[task_id] = t
                    end_time = t
                    duration = end_time - active_start[task_id]
                    if duration >= 0.3:
                        events.append(
                            Event(
                                task_id=task_id,
                                detected_start_seconds=active_start[task_id],
                                detected_end_seconds=end_time,
                                confidence_score=TASK_CONFIDENCE_DEFAULTS.get(task_id, 0.7),
                                status_guess="completed",
                                note=f"Detected via {', '.join(required_signals)}",
                            ).__dict__
                        )
                        completed_tasks.add(task_id)

        for task_id in TASK_ORDER:
            if task_id not in completed_tasks:
                events.append(
                    Event(
                        task_id=task_id,
                        detected_start_seconds=0.0,
                        detected_end_seconds=0.0,
                        confidence_score=0.0,
                        status_guess="not_detected",
                        note="Required object classes not found in any frame",
                    ).__dict__
                )

        candidate_events_per_roi.append({
            "roi": roi_name,
            "frames_analyzed": len(frames),
            "candidate_events": events,
        })

    return {
        "clip_name": raw_detections.get("clip_name", "unknown"),
        "rois": candidate_events_per_roi,
    }


def run_state_machine(input_path: Path, results_dir: Path) -> Path:
    raw_detections = load_raw_detections(input_path)
    output = infer_events(raw_detections)
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = results_dir / f"{input_path.stem}_task_events.json"
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert raw detections into task events.")
    parser.add_argument("raw_detections", type=Path, help="Path to *_raw_detections.json")
    parser.add_argument("--results-dir", type=Path, default=Path("results"), help="Output folder")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = run_state_machine(args.raw_detections, args.results_dir)
    print(output_path)


if __name__ == "__main__":
    main()