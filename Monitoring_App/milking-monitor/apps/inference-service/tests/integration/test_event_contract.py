from src.events.event_builder import build_cow_process_event, build_task_event


def test_task_event_builder_returns_payload():
    payload = {
        "task_id": "TASK-03",
        "session_id": "session-1",
        "cow_position": 1,
        "confidence_score": 0.95,
        "status": "completed",
        "detected_start_time": None,
        "detected_end_time": None,
    }

    assert build_task_event(payload) == payload


def test_cow_process_event_builder_returns_payload():
    payload = {
        "session_id": "session-1",
        "cow_position": 1,
        "event_type": "started",
        "detected_time": None,
    }

    assert build_cow_process_event(payload) == payload
