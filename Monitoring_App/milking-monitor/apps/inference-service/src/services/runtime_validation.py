from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object JSON in {path}")
    return data


def validate_runtime_configuration(settings: Any) -> dict[str, Any]:
    """Return a structured report for readiness checks before a session starts."""
    errors: list[str] = []

    if not settings.rtsp_stream_url:
        errors.append("RTSP_STREAM_URL is not configured.")

    if not settings.web_app_ingest_url:
        errors.append("WEB_APP_INGEST_URL is not configured.")

    if not settings.web_app_ingest_token:
        errors.append("WEB_APP_INGEST_TOKEN is not configured.")

    if not settings.model_weights_path or not settings.model_weights_path.exists():
        errors.append(f"MODEL_WEIGHTS_PATH does not exist: {settings.model_weights_path}")

    for label, path in {
        "ROIS": settings.rois_file,
        "THRESHOLDS": settings.thresholds_file,
    }.items():
        if not path or not Path(path).exists():
            errors.append(f"{label}_FILE does not exist: {path}")
            continue
        try:
            _load_json(Path(path))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{label}_FILE is invalid JSON: {path} ({exc})")

    return {
        "ready": not errors,
        "errors": errors,
        "env": {
            "rtsp_stream_url": bool(settings.rtsp_stream_url),
            "web_app_ingest_url": bool(settings.web_app_ingest_url),
            "web_app_ingest_token": bool(settings.web_app_ingest_token),
            "model_weights_path": str(settings.model_weights_path),
        },
    }
