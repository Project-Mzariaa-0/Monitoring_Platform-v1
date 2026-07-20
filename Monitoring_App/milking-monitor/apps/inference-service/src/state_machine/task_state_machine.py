from __future__ import annotations

from datetime import datetime, timezone


class TaskStateMachine:
    def __init__(self, thresholds: dict):
        self.thresholds = thresholds
        self.active_tasks: dict[tuple[str, int], dict[str, object]] = {}
        self.process_start_task = "TASK-01"
        self.process_end_task = "TASK-06"

    TASK_SIGNALS: dict[str, set[str]] = {
        "TASK-01": {"person", "spray_bottle"},
        "TASK-02": {"person", "stripping_cup"},
        "TASK-03": {"teat_cups_attached"},
        "TASK-04": {"teat_cups_attached"},
        "TASK-05": {"teat_cups_detached"},
        "TASK-06": {"person", "dip_applicator"},
    }

    TASK_CONFIDENCE_DEFAULTS: dict[str, float] = {
        "TASK-01": 0.82,
        "TASK-02": 0.78,
        "TASK-03": 0.96,
        "TASK-04": 0.91,
        "TASK-05": 0.95,
        "TASK-06": 0.80,
    }

    def update(self, session_id: str, cow_position: int, detections: list) -> list[dict]:
        class_names = {getattr(detection, "class_name", "") for detection in detections}
        events: list[dict] = []
        key = (session_id, cow_position)
        state = self.active_tasks.get(key, {"completed": set(), "active": False, "start_times": {}, "first_seen": {}})

        now = datetime.now(timezone.utc).isoformat()

        for task_id, required_signals in self.TASK_SIGNALS.items():
            signals_present = required_signals.issubset(class_names)

            if signals_present and task_id not in state["completed"]:
                if task_id not in state["first_seen"]:
                    state["first_seen"][task_id] = now

                first_seen: dict = state.get("first_seen", {})
                start_time = first_seen.get(task_id) or now
                confidence = self._confidence_for_task(task_id)

                events.append(self._event(session_id, cow_position, task_id, "completed", confidence, start_time, now))
                state["completed"].add(task_id)
                state["active"] = True

        if "teat_cups_attached" not in class_names and state["active"] and self.process_end_task not in state["completed"]:
            missed_confidence = self.thresholds.get("default_unverifiable_confidence", 0.5)
            if self.process_start_task not in state["completed"]:
                events.append(self._event(session_id, cow_position, self.process_start_task, "missed", missed_confidence, now, now))
            if "TASK-03" in state["completed"] and "TASK-05" not in state["completed"]:
                events.append(self._event(session_id, cow_position, self.process_end_task, "missed", missed_confidence, now, now))
            state["active"] = False

        self.active_tasks[key] = state

        return events

    def _event(self, session_id: str, cow_position: int, task_id: str, status: str, confidence: float, start_time: str, end_time: str) -> dict:
        duration = 0
        if start_time and end_time and start_time != end_time:
            try:
                t_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                t_end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                duration = max(0, int((t_end - t_start).total_seconds()))
            except (ValueError, TypeError):
                duration = 0

        return {
            "task_id": task_id,
            "session_id": session_id,
            "cow_position": cow_position,
            "confidence_score": confidence,
            "status": status,
            "detected_start_time": start_time,
            "detected_end_time": end_time,
            "duration_seconds": duration,
        }

    def _confidence_for_task(self, task_id: str) -> float:
        task_config = self.thresholds.get(task_id)
        if isinstance(task_config, dict):
            return float(task_config.get("confidence", self.TASK_CONFIDENCE_DEFAULTS.get(task_id, 0.8)))
        return float(self.TASK_CONFIDENCE_DEFAULTS.get(task_id, 0.8))
