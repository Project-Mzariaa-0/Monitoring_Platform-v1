from __future__ import annotations

from src.config.settings import settings
from src.services.session_manager import SessionManager
from src.services.session_runtime_service import SessionRuntimeService


def test_runtime_service_can_start_session_when_idle():
    service = SessionRuntimeService(settings, SessionManager(settings))
    assert service.can_start_session("alpha") is True


def test_runtime_service_rejects_duplicate_and_busy_session():
    manager = SessionManager(settings)
    manager.register("alpha", object(), object())
    service = SessionRuntimeService(settings, manager)
    assert service.can_start_session("alpha") is False
    assert service.can_start_session("beta") is False
