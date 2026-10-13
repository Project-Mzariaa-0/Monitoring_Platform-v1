from __future__ import annotations

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone

_request_id = contextvars.ContextVar("request_id", default="system")


def set_request_id(request_id: str):
    return _request_id.set(request_id)


def clear_request_id(token) -> None:
    _request_id.reset(token)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id.get(),
        }
        for field in ("session_id", "event_type", "attempt"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)