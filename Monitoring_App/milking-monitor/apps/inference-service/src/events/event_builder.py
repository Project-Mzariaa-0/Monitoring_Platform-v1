from __future__ import annotations

from datetime import datetime, timezone

CONTRACT_VERSION = "1.0"


def _now_iso() -> str:
    # Canonical UTC with 'Z' suffix: the web ingest contract only accepts
    # Z-suffixed datetimes, and CPython emits '+00:00' by default.
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_iso(value: str | None) -> str | None:
    if value is None:
        return None
    if value.endswith("+00:00"):
        return value[:-6] + "Z"
    return value


def build_task_event(payload: dict) -> dict:
    completion_percentage = payload.get("completion_percentage")
    if completion_percentage is None:
        completion_percentage = 0.0

    return {
        "contract_version": CONTRACT_VERSION,
        "session_id": payload["session_id"],
        "event_type": "task_event",
        "task_id": payload["task_id"],
        "cow_position": payload["cow_position"],
        "status": payload["status"],
        "completion_percentage": float(completion_percentage),
        "confidence_score": payload.get("confidence_score", 0.0),
        "detected_start_time": _canonical_iso(payload.get("detected_start_time")) or _now_iso(),
        "detected_end_time": _canonical_iso(payload.get("detected_end_time")),
        "duration_seconds": payload.get("duration_seconds", 0),
    }


def build_cow_process_event(payload: dict) -> dict:
    return {
        "contract_version": CONTRACT_VERSION,
        "session_id": payload["session_id"],
        "event_type": "cow_process",
        "cow_position": payload["cow_position"],
        "process_status": payload["event_type"],
        "detected_time": _canonical_iso(payload.get("detected_time")) or _now_iso(),
    }
