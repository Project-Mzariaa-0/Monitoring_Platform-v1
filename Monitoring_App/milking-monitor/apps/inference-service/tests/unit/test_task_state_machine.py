from __future__ import annotations

import pytest
from src.state_machine.task_state_machine import TaskStateMachine


@pytest.fixture
def sm(sample_thresholds):
    return TaskStateMachine(sample_thresholds)


class TestTaskStateMachine:
    def test_completes_task_when_signal_matches(self, sm):
        detections = [type("Detection", (), {"class_name": "person"})(), type("Detection", (), {"class_name": "spray_bottle"})()]
        events = sm.update("s1", 1, detections)
        task_ids = [e["task_id"] for e in events]
        assert "TASK-01" in task_ids
        assert events[task_ids.index("TASK-01")]["status"] == "completed"

    def test_does_not_duplicate_completed_tasks(self, sm):
        detections = [type("Detection", (), {"class_name": "person"})(), type("Detection", (), {"class_name": "spray_bottle"})()]
        events1 = sm.update("s1", 1, detections)
        events2 = sm.update("s1", 1, detections)
        assert len([e for e in events1 if e["task_id"] == "TASK-01"]) == 1
        assert len([e for e in events2 if e["task_id"] == "TASK-01"]) == 0

    def test_different_positions_are_independent(self, sm):
        detections = [type("Detection", (), {"class_name": "person"})(), type("Detection", (), {"class_name": "spray_bottle"})()]
        events_pos1 = sm.update("s1", 1, detections)
        events_pos2 = sm.update("s1", 2, detections)
        assert len(events_pos1) == 1
        assert len(events_pos2) == 1
        assert events_pos1[0]["cow_position"] == 1
        assert events_pos2[0]["cow_position"] == 2

    def test_duration_computed_from_times(self, sm):
        detections = [type("Detection", (), {"class_name": "person"})(), type("Detection", (), {"class_name": "spray_bottle"})()]
        events = sm.update("s1", 1, detections)
        task_event = events[0]
        assert "duration_seconds" in task_event

    def test_confidence_comes_from_thresholds(self, sm):
        detections = [type("Detection", (), {"class_name": "person"})(), type("Detection", (), {"class_name": "spray_bottle"})()]
        events = sm.update("s1", 1, detections)
        task_event = events[0]
        assert task_event["confidence_score"] == 0.82

    def test_no_events_when_no_signals_match(self, sm):
        detections = [type("Detection", (), {"class_name": "cat"})()]
        events = sm.update("s1", 1, detections)
        assert len(events) == 0

    def test_missing_task_event_when_cups_absent(self, sm):
        sm.update("s1", 1, [type("Detection", (), {"class_name": "person"})(), type("Detection", (), {"class_name": "spray_bottle"})()])
        sm.update("s1", 1, [type("Detection", (), {"class_name": "teat_cups_attached"})()])
        events = sm.update("s1", 1, [])
        task_ids = [e["task_id"] for e in events]
        assert "TASK-06" in task_ids
        assert events[task_ids.index("TASK-06")]["status"] == "missed"
