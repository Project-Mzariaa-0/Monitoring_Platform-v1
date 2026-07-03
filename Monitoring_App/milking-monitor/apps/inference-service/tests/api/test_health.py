from __future__ import annotations

import pytest


class TestHealthEndpoint:
    def test_health_check_returns_ok(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_active_sessions_returns_list(self, client):
        response = client.get("/active-sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_stop_nonexistent_session_returns_404(self, client):
        response = client.post("/session-window/nonexistent/stop")
        assert response.status_code == 404

    def test_session_window_missing_stream_url_returns_400(self, client):
        response = client.post(
            "/session-window",
            json={
                "session_id": "test-001",
                "start_time": "2026-07-03T12:00:00Z",
                "end_time": "2026-07-03T13:00:00Z",
            },
        )
        assert response.status_code == 400
