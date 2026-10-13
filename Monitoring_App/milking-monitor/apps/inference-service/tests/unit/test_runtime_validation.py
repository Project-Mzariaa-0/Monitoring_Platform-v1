from pathlib import Path

from src.config.settings import Settings
from src.services.runtime_validation import validate_runtime_configuration


def test_runtime_configuration_accepts_valid_settings(tmp_path):
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"fake-model")
    roi_file = tmp_path / "rois.json"
    roi_file.write_text('{"1": {"x": 0, "y": 0, "width": 10, "height": 10}}', encoding="utf-8")
    thresholds_file = tmp_path / "thresholds.json"
    thresholds_file.write_text('{"task_threshold": 0.5}', encoding="utf-8")

    settings = Settings(
        rtsp_stream_url="rtsp://example/stream",
        fallback_video_path=None,
        web_app_ingest_url="http://example/api",
        web_app_ingest_token="token",
        model_weights_path=model_path,
        rois_file=roi_file,
        thresholds_file=thresholds_file,
    )

    report = validate_runtime_configuration(settings)
    assert report["ready"] is True
    assert report["errors"] == []


def test_runtime_configuration_flags_missing_required_values():
    settings = Settings(
        rtsp_stream_url="",
        web_app_ingest_url=None,
        web_app_ingest_token=None,
        model_weights_path=Path("/missing/model.pt"),
        rois_file=Path("/missing/rois.json"),
        thresholds_file=Path("/missing/thresholds.json"),
    )

    report = validate_runtime_configuration(settings)
    assert report["ready"] is False
    assert any("RTSP_STREAM_URL" in message for message in report["errors"])
    assert any("WEB_APP_INGEST_URL" in message for message in report["errors"])
