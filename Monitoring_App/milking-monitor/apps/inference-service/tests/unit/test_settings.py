from __future__ import annotations

from src.config.settings import settings


def test_settings_expose_runtime_configuration():
    assert settings.app_name == "milking-monitor-inference-service"
    assert isinstance(settings.cors_origins, list)
    assert settings.cors_origins
    assert isinstance(settings.use_hybrid_model, bool)


def test_model_path_defaults_to_service_model_dir():
    assert settings.model_weights_path.name.endswith(".pt")
    assert "models" in str(settings.model_weights_path)
