from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_task_payload():
    """Sample task event payload for testing."""
    return {
        "task_id": "TASK-01",
        "session_id": "test-session-001",
        "cow_position": 1,
        "confidence_score": 0.85,
        "status": "completed",
        "detected_start_time": "2026-07-03T12:00:00Z",
        "detected_end_time": "2026-07-03T12:00:10Z",
        "duration_seconds": 10,
    }


@pytest.fixture
def sample_thresholds():
    """Sample thresholds config for testing."""
    return {
        "default_missed_task_seconds": 180,
        "default_unverifiable_confidence": 0.5,
        "default_completeness_confidence": 0.7,
        "TASK-01": {"confidence": 0.82},
        "TASK-02": {"confidence": 0.78},
        "TASK-03": {"confidence": 0.96},
        "TASK-04": {"confidence": 0.91},
        "TASK-05": {"confidence": 0.95},
        "TASK-06": {"confidence": 0.80},
    }


@pytest.fixture
def sample_rois():
    """Sample ROI config for testing."""
    return {
        "row_position_1": {"x": 0, "y": 0, "width": 640, "height": 720},
        "row_position_2": {"x": 640, "y": 0, "width": 640, "height": 720},
    }
