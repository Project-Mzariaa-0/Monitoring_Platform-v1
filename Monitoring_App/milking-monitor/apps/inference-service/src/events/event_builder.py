from __future__ import annotations

from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_task_event(payload: dict) -> dict:
    return {
        "session_id": payload["session_id"],
        "event_type": "task_event",
        "task_id": payload["task_id"],
        "cow_position": payload["cow_position"],
        "status": payload["status"],
        "confidence_score": payload.get("confidence_score", 0.0),
        "detected_start_time": payload.get("detected_start_time") or _now_iso(),
        "detected_end_time": payload.get("detected_end_time"),
        "duration_seconds": payload.get("duration_seconds", 0),
    }


def build_cow_process_event(payload: dict) -> dict:
    return {
        "session_id": payload["session_id"],
        "event_type": "cow_process",
        "cow_position": payload["cow_position"],
        "process_status": payload["event_type"],
        "detected_time": payload.get("detected_time") or _now_iso(),
    }
