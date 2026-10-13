from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

TASK_IDS = tuple(f"TASK-{index:02d}" for index in range(1, 7))


@dataclass(frozen=True)
class TaskMetrics:
    task_id: str
    support: int
    predicted: int
    true_positive: int
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class BenchmarkReport:
    sample_count: int
    correct_count: int
    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    tasks: tuple[TaskMetrics, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_predictions(records: Iterable[dict], task_ids: Iterable[str] = TASK_IDS) -> BenchmarkReport:
    labels = tuple(task_ids)
    counts = {
        task_id: {"support": 0, "predicted": 0, "true_positive": 0}
        for task_id in labels
    }
    sample_count = 0
    correct_count = 0

    for record in records:
        expected = record.get("expected_task")
        predicted = record.get("predicted_task")
        if expected not in counts:
            raise ValueError(f"Unknown expected_task: {expected!r}")
        if predicted not in counts:
            raise ValueError(f"Unknown predicted_task: {predicted!r}")

        sample_count += 1
        counts[expected]["support"] += 1
        counts[predicted]["predicted"] += 1
        if expected == predicted:
            counts[expected]["true_positive"] += 1
            correct_count += 1

    metrics: list[TaskMetrics] = []
    for task_id in labels:
        values = counts[task_id]
        precision = _safe_ratio(values["true_positive"], values["predicted"])
        recall = _safe_ratio(values["true_positive"], values["support"])
        f1 = _safe_ratio(2 * precision * recall, precision + recall)
        metrics.append(TaskMetrics(task_id, values["support"], values["predicted"], values["true_positive"], precision, recall, f1))

    return BenchmarkReport(
        sample_count=sample_count,
        correct_count=correct_count,
        accuracy=_safe_ratio(correct_count, sample_count),
        macro_precision=sum(metric.precision for metric in metrics) / len(metrics),
        macro_recall=sum(metric.recall for metric in metrics) / len(metrics),
        macro_f1=sum(metric.f1 for metric in metrics) / len(metrics),
        tasks=tuple(metrics),
    )


def load_predictions(path: str | Path) -> list[dict]:
    input_path = Path(path)
    if input_path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Prediction JSON must contain an array of records")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate labeled task predictions.")
    parser.add_argument("input", type=Path, help="JSON or JSONL with expected_task and predicted_task fields")
    parser.add_argument("--output", type=Path, help="Optional JSON report output path")
    args = parser.parse_args()

    report = evaluate_predictions(load_predictions(args.input))
    encoded = json.dumps(report.to_dict(), indent=2)
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()