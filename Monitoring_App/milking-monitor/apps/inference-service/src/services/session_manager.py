from __future__ import annotations

import threading
from typing import Any


class SessionManager:
    """Thread-safe session registry for the inference service."""

    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self._lock = threading.Lock()
        self._active_runners: dict[str, Any] = {}
        self._active_threads: dict[str, Any] = {}

    def register(self, session_id: str, runner: Any, thread: Any) -> None:
        with self._lock:
            self._active_runners[session_id] = runner
            self._active_threads[session_id] = thread

    def unregister(self, session_id: str) -> None:
        with self._lock:
            self._active_runners.pop(session_id, None)
            self._active_threads.pop(session_id, None)

    def is_session_active(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._active_runners

    def has_active_session(self) -> bool:
        with self._lock:
            return bool(self._active_runners)

    def list_active_sessions(self) -> list[str]:
        with self._lock:
            return list(self._active_runners.keys())

    def latest_active_session(self) -> str | None:
        with self._lock:
            if not self._active_runners:
                return None
            return next(iter(self._active_runners.keys()))

    @property
    def active_runners(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._active_runners)

    @property
    def active_threads(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._active_threads)
