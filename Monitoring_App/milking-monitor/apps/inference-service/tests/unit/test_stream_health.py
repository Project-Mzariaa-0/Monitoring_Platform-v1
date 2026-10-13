from src.ingestion.stream_health import StreamHealth


def test_stream_health_tracks_frames_and_recovers_after_a_failure():
    health = StreamHealth()

    health.record_frame(now=10.0)
    health.record_failure()
    health.record_frame(now=12.0)

    snapshot = health.snapshot(now=15.0)
    assert snapshot["frames_received"] == 2
    assert snapshot["dropped_frames"] == 1
    assert snapshot["max_consecutive_failures"] == 1
    assert snapshot["consecutive_failures"] == 0
    assert snapshot["last_frame_age_seconds"] == 3.0
    assert snapshot["degraded"] is False


def test_empty_stream_is_degraded():
    health = StreamHealth()

    assert health.is_degraded is True
    assert health.snapshot(now=5.0)["last_frame_age_seconds"] is None