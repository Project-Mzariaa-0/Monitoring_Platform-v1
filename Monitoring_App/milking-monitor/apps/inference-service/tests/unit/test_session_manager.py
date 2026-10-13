from __future__ import annotations

from src.config.settings import settings
from src.services.session_manager import SessionManager


def test_session_manager_tracks_active_sessions():
    manager = SessionManager(settings)
    assert manager.list_active_sessions() == []
    assert manager.has_active_session() is False


def test_session_manager_rejects_duplicate_session_ids():
    manager = SessionManager(settings)
    manager._active_runners.clear()
    manager._active_runners["alpha"] = object()
    assert manager.has_active_session() is True
    assert manager.is_session_active("alpha") is True
    assert manager.is_session_active("beta") is False
