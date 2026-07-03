"""Convert raw detections into experimental task events.

The logic here is intentionally simple and threshold-driven. It exists to answer
the spike's go/no-go question, not to serve as the final production inference layer.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


TASK_ORDER = ["TASK-01", "TASK-02", "TASK-03", "TASK-04", "TASK-05", "TASK-06"]


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


def infer_events(raw_detections: dict) -> dict:
    candidate_events = []
    for task_id in TASK_ORDER:
        candidate_events.append(
            Event(
                task_id=task_id,
                detected_start_seconds=0.0,
                detected_end_seconds=0.0,
                confidence_score=0.0,
                status_guess="unverifiable",
                note="Placeholder spike implementation; refine once sample clips and labels exist.",
            )
        )

    return {
        "clip_name": raw_detections.get("clip_name", "unknown"),
        "rois": [
            {
                "roi": roi.get("roi", "unknown"),
                "candidate_events": [event.__dict__ for event in candidate_events],
            }
            for roi in raw_detections.get("rois", [])
        ],
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