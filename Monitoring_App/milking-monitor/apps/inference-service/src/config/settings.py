from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODEL_PATH = SERVICE_ROOT / "models" / "yolov8_milking_custom.pt"


def _coerce_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _resolve_path(raw_value: str | None, default: Path) -> Path:
    if raw_value is None or raw_value == "":
        return default.resolve()
    candidate = Path(raw_value)
    if candidate.is_absolute():
        return candidate.resolve()
    return (SERVICE_ROOT / candidate).resolve()


@dataclass(frozen=True)
class Settings:
    app_name: str = "milking-monitor-inference-service"
    app_version: str = "0.1.0"
    environment: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    web_app_url: str = field(default_factory=lambda: os.getenv("WEB_APP_URL", "http://localhost:3000"))
    rtsp_stream_url: str | None = field(default_factory=lambda: os.getenv("RTSP_STREAM_URL"))
    fallback_video_path: str | None = field(default_factory=lambda: os.getenv("FALLBACK_VIDEO_PATH"))
    web_app_ingest_url: str | None = field(default_factory=lambda: os.getenv("WEB_APP_INGEST_URL"))
    web_app_ingest_token: str | None = field(default_factory=lambda: os.getenv("WEB_APP_INGEST_TOKEN"))
    model_weights_path: Path = field(default_factory=lambda: _resolve_path(os.getenv("MODEL_WEIGHTS_PATH"), DEFAULT_MODEL_PATH))
    cors_origins: list[str] = field(default_factory=lambda: [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()])
    use_hybrid_model: bool = field(default_factory=lambda: _coerce_bool(os.getenv("USE_HYBRID_MODEL"), False))
    hybrid_model_weights: Path = field(default_factory=lambda: _resolve_path(os.getenv("HYBRID_MODEL_WEIGHTS"), SERVICE_ROOT.parent.parent / "hybrid-model" / "models" / "checkpoints" / "best_model.pt"))
    hybrid_sequence_length: int = field(default_factory=lambda: int(os.getenv("HYBRID_SEQUENCE_LENGTH", "30")))
    hybrid_threshold: float = field(default_factory=lambda: float(os.getenv("HYBRID_THRESHOLD", "0.15")))
    hybrid_yolo_skip: int = field(default_factory=lambda: int(os.getenv("HYBRID_YOLO_SKIP", "5")))
    rois_file: Path = field(default_factory=lambda: (Path(__file__).resolve().parent / "rois.json"))
    thresholds_file: Path = field(default_factory=lambda: (Path(__file__).resolve().parent / "thresholds.json"))


settings = Settings()

__all__ = ["Settings", "settings"]
