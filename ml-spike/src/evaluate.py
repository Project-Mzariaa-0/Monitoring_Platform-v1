"""Compare candidate task events to human labels for the ML spike.

This evaluation is intentionally small and file-based so the spike can be run
clip by clip without introducing database or application dependencies.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(task_events: dict, labels: dict) -> dict:
    return {
        "clip_name": task_events.get("clip_name", labels.get("clip_name", "unknown")),
        "per_task_summary": [
            {
                "task_id": label.get("task_id", "unknown"),
                "detected_correctly": False,
                "timing_offset_seconds": 0.0,
                "false_positive": False,
                "false_negative": not label.get("actually_occurred", False),
                "occlusion_flagged_by_human_reviewer": label.get("occluded_from_camera", False),
            }
            for label in labels.get("labeled_events", [])
        ],
        "overall_notes": "Spike evaluation scaffold only; implement matching logic after sample labels exist.",
    }


def run_evaluation(task_events_path: Path, labels_path: Path, results_dir: Path) -> Path:
    task_events = load_json(task_events_path)
    labels = load_json(labels_path)
    output = evaluate(task_events, labels)
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = results_dir / f"{task_events_path.stem}_evaluation.json"
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate task events against human labels.")
    parser.add_argument("task_events", type=Path, help="Path to *_task_events.json")
    parser.add_argument("labels", type=Path, help="Path to ground truth label JSON")
    parser.add_argument("--results-dir", type=Path, default=Path("results"), help="Output folder")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = run_evaluation(args.task_events, args.labels, args.results_dir)
    print(output_path)


if __name__ == "__main__":
    main()