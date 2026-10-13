from src.state_machine.confidence_policy import evaluate_task_signals


def test_policy_uses_the_strictest_required_signal():
    detections = [
        type("Detection", (), {"class_name": "person", "confidence": 0.91})(),
        type("Detection", (), {"class_name": "spray_bottle", "confidence": 0.62})(),
    ]

    decision = evaluate_task_signals(
        "TASK-01",
        {"person", "spray_bottle"},
        detections,
        {"default_detection_confidence": 0.7},
    )

    assert decision.accepted is False
    assert decision.minimum_signal_confidence == 0.62
    assert decision.accepted_signal_count == 1


def test_policy_accepts_task_specific_threshold_override():
    detections = [
        type("Detection", (), {"class_name": "person", "confidence": 0.61})(),
        type("Detection", (), {"class_name": "spray_bottle", "confidence": 0.61})(),
    ]

    decision = evaluate_task_signals(
        "TASK-01",
        {"person", "spray_bottle"},
        detections,
        {"default_detection_confidence": 0.8, "TASK-01": {"min_detection_confidence": 0.6}},
    )

    assert decision.accepted is True