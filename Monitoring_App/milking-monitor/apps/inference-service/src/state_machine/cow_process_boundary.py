from __future__ import annotations

from datetime import datetime, timezone


class CowProcessBoundaryDetector:
    def __init__(self, thresholds: dict):
        self.thresholds = thresholds
        self.active_sessions: dict[tuple[str, int], dict[str, object]] = {}

    def update(self, session_id: str, cow_position: int, detections: list) -> list[dict]:
        class_names = {getattr(detection, "class_name", "") for detection in detections}
        key = (session_id, cow_position)
        events: list[dict] = []
        now = datetime.now(timezone.utc).isoformat()

        state = self.active_sessions.get(key, {"active": False, "start_time": None})

        if "teat_cups_attached" in class_names and not state["active"]:
            state["active"] = True
            state["start_time"] = now
            events.append(self._event(session_id, cow_position, "started", now))

        if "teat_cups_detached" in class_names and state["active"]:
            state["active"] = False
            events.append(self._event(session_id, cow_position, "completed", now))

        self.active_sessions[key] = state
        return events

    def _event(self, session_id: str, cow_position: int, event_type: str, detected_time: str) -> dict:
        return {
            "session_id": session_id,
            "cow_position": cow_position,
            "event_type": event_type,
            "detected_time": detected_time,
        }
