from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass
class StreamHealth:
    max_consecutive_failures: int = 0
    frames_received: int = 0
    dropped_frames: int = 0
    consecutive_failures: int = 0
    last_frame_at: float | None = None

    def record_frame(self, now: float | None = None) -> None:
        self.frames_received += 1
        self.consecutive_failures = 0
        self.last_frame_at = time.monotonic() if now is None else now

    def record_failure(self) -> None:
        self.dropped_frames += 1
        self.consecutive_failures += 1
        self.max_consecutive_failures = max(self.max_consecutive_failures, self.consecutive_failures)

    @property
    def is_degraded(self) -> bool:
        return self.consecutive_failures > 0 or self.frames_received == 0

    def snapshot(self, now: float | None = None) -> dict[str, int | float | bool | None]:
        current_time = time.monotonic() if now is None else now
        frame_age = None if self.last_frame_at is None else max(0.0, current_time - self.last_frame_at)
        return {
            "frames_received": self.frames_received,
            "dropped_frames": self.dropped_frames,
            "consecutive_failures": self.consecutive_failures,
            "max_consecutive_failures": self.max_consecutive_failures,
            "last_frame_age_seconds": frame_age,
            "degraded": self.is_degraded,
        }