from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_service_status(settings: Any, session_manager: Any, *, started_at: datetime | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    started = started_at or now
    uptime_seconds = max(0, int((now - started).total_seconds()))
    active_sessions = session_manager.list_active_sessions()
    return {
        "status": "ok" if not active_sessions else "degraded",
        "ready": True,
        "environment": settings.environment,
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "active_sessions": active_sessions,
        "hybrid_enabled": settings.use_hybrid_model,
        "uptime_seconds": uptime_seconds,
    }
