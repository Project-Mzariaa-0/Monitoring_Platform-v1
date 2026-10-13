from __future__ import annotations

import threading
from typing import Any

from src.runtime.session_runner import SessionRunner


class SessionRuntimeService:
    """Encapsulates runtime checks and coordination for starting inference sessions."""

    def __init__(self, settings: Any, session_manager: Any) -> None:
        self.settings = settings
        self.session_manager = session_manager
        self._lock = threading.Lock()

    def can_start_session(self, session_id: str) -> bool:
        with self._lock:
            if self.session_manager.is_session_active(session_id):
                return False
            if self.session_manager.has_active_session():
                return False
            return True

    def build_runner(self, session_id: str, end_time: str, *, stream_url: str, fallback_video_path: str | None, ingest_url: str, ingest_token: str, weights_path: str, rois: dict, thresholds: dict) -> SessionRunner:
        return SessionRunner(
            session_id=session_id,
            stream_url=stream_url,
            fallback_video_path=fallback_video_path,
            ingest_url=ingest_url,
            ingest_token=ingest_token,
            weights_path=weights_path,
            rois=rois,
            thresholds=thresholds,
            end_time=end_time,
            use_hybrid=self.settings.use_hybrid_model,
        )
