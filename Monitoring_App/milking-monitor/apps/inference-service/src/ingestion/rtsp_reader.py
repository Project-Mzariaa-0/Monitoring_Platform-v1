from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from dataclasses import dataclass, field

import cv2

from src.ingestion.stream_health import StreamHealth

logger = logging.getLogger(__name__)


@dataclass
class RtspReader:
    stream_url: str
    fallback_video_path: str | None = None
    health: StreamHealth = field(default_factory=StreamHealth, init=False)

    def _open_fallback(self):
        if self.fallback_video_path and Path(self.fallback_video_path).exists():
            logger.warning("Falling back to video: %s", self.fallback_video_path)
            capture = cv2.VideoCapture(self.fallback_video_path)
            if capture.isOpened():
                return capture
        return None

    def read_frames(self, limit: int | None = None):
        capture = cv2.VideoCapture(self.stream_url)

        if capture.isOpened():
            success, test_frame = capture.read()
            if success:
                frame_index = 0
                self.health.record_frame()
                yield frame_index, test_frame
                frame_index = 1
                try:
                    while True:
                        success, frame = capture.read()
                        if not success:
                            self.health.record_failure()
                            logger.warning("RTSP frame read failed after %d frames: %s", frame_index, self.stream_url)
                            break
                        self.health.record_frame()
                        yield frame_index, frame
                        frame_index += 1
                        if limit is not None and frame_index >= limit:
                            break
                finally:
                    capture.release()
                return
            else:
                self.health.record_failure()
                logger.warning("RTSP opened but first read failed: %s", self.stream_url)
                capture.release()
        else:
            capture.release()

        fallback = self._open_fallback()
        if fallback is None:
            raise RuntimeError("Unable to open RTSP stream or fallback video")

        total_frames = int(fallback.get(cv2.CAP_PROP_FRAME_COUNT))
        logger.info("Fallback video: %d frames, looping until session ends", total_frames)

        frame_index = 0
        try:
            while True:
                success, frame = fallback.read()
                if not success:
                    # Video ended — loop back to start
                    fallback.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    success, frame = fallback.read()
                    if not success:
                        self.health.record_failure()
                        break
                self.health.record_frame()
                yield frame_index, frame
                frame_index += 1
                if limit is not None and frame_index >= limit:
                    break
        finally:
            fallback.release()
