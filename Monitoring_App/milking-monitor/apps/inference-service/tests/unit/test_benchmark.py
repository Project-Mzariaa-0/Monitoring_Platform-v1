import pytest

from src.evaluation.benchmark import evaluate_predictions, load_predictions


def test_benchmark_reports_per_task_and_macro_metrics():
    report = evaluate_predictions([
        {"expected_task": "TASK-01", "predicted_task": "TASK-01"},
        {"expected_task": "TASK-01", "predicted_task": "TASK-02"},
        {"expected_task": "TASK-02", "predicted_task": "TASK-02"},
    ])

    task_one = report.tasks[0]
    assert report.sample_count == 3
    assert report.correct_count == 2
    assert report.accuracy == pytest.approx(2 / 3)
    assert task_one.support == 2
    assert task_one.predicted == 1
    assert task_one.precision == pytest.approx(1.0)
    assert task_one.recall == pytest.approx(0.5)
    assert task_one.f1 == pytest.approx(2 / 3)
    assert 0 < report.macro_f1 < 1


def test_benchmark_rejects_unknown_labels():
    with pytest.raises(ValueError, match="Unknown predicted_task"):
        evaluate_predictions([{"expected_task": "TASK-01", "predicted_task": "unknown"}])


def test_load_predictions_requires_an_array_for_json(tmp_path):
    path = tmp_path / "predictions.json"
    path.write_text('{"expected_task": "TASK-01"}', encoding="utf-8")

    with pytest.raises(ValueError, match="must contain an array"):
        load_predictions(path)