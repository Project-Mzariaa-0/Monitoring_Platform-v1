from __future__ import annotations

from dataclasses import dataclass

from src.utils.label_aliases import normalize_class_name


@dataclass(frozen=True)
class ConfidenceDecision:
    accepted: bool
    minimum_signal_confidence: float
    required_signal_count: int
    accepted_signal_count: int


def evaluate_task_signals(
    task_id: str,
    required_signals: set[str],
    detections: list,
    thresholds: dict,
) -> ConfidenceDecision:
    task_config = thresholds.get(task_id)
    task_config = task_config if isinstance(task_config, dict) else {}
    minimum_confidence = float(
        task_config.get(
            "min_detection_confidence",
            thresholds.get("default_detection_confidence", 0.5),
        ),
    )
    minimum_confidence = min(max(minimum_confidence, 0.0), 1.0)

    signal_confidences: dict[str, float] = {}
    for detection in detections:
        signal = normalize_class_name(getattr(detection, "class_name", ""))
        confidence = float(getattr(detection, "confidence", 1.0))
        signal_confidences[signal] = max(signal_confidences.get(signal, 0.0), confidence)

    accepted_signals = [
        signal for signal in required_signals
        if signal_confidences.get(signal, 0.0) >= minimum_confidence
    ]
    minimum_signal_confidence = min(
        (signal_confidences.get(signal, 0.0) for signal in required_signals),
        default=0.0,
    )

    return ConfidenceDecision(
        accepted=len(accepted_signals) == len(required_signals),
        minimum_signal_confidence=minimum_signal_confidence,
        required_signal_count=len(required_signals),
        accepted_signal_count=len(accepted_signals),
    )