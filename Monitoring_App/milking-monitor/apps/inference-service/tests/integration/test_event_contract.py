from src.events.event_builder import build_cow_process_event, build_task_event


def test_task_event_builder_returns_payload():
    payload = {
        "task_id": "TASK-03",
        "session_id": "session-1",
        "cow_position": 1,
        "confidence_score": 0.95,
        "status": "completed",
        "detected_start_time": "2026-07-03T12:00:00Z",
        "detected_end_time": "2026-07-03T12:00:10Z",
    }

    result = build_task_event(payload)
    assert result["task_id"] == "TASK-03"
    assert result["session_id"] == "session-1"
    assert result["cow_position"] == 1
    assert result["confidence_score"] == 0.95
    assert result["status"] == "completed"
    assert result["detected_start_time"] == "2026-07-03T12:00:00Z"
    assert result["detected_end_time"] == "2026-07-03T12:00:10Z"


def test_task_event_builder_fills_missing_times():
    payload = {
        "task_id": "TASK-01",
        "session_id": "session-2",
        "cow_position": 2,
        "confidence_score": 0.82,
        "status": "completed",
    }

    result = build_task_event(payload)
    assert result["task_id"] == "TASK-01"
    assert result["detected_start_time"] is not None
    assert result["detected_end_time"] is None


def test_cow_process_event_builder_returns_payload():
    payload = {
        "session_id": "session-1",
        "cow_position": 1,
        "event_type": "started",
        "detected_time": "2026-07-03T12:00:00Z",
    }

    result = build_cow_process_event(payload)
    assert result["session_id"] == "session-1"
    assert result["cow_position"] == 1
    assert result["process_status"] == "started"
    assert result["detected_time"] == "2026-07-03T12:00:00Z"


def test_cow_process_event_builder_fills_missing_time():
    payload = {
        "session_id": "session-2",
        "cow_position": 2,
        "event_type": "completed",
    }

    result = build_cow_process_event(payload)
    assert result["session_id"] == "session-2"
    assert result["process_status"] == "completed"
    assert result["detected_time"] is not None
