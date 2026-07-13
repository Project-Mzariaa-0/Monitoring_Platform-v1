from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2

logger = logging.getLogger(__name__)


@dataclass
class RtspReader:
    stream_url: str
    fallback_video_path: str | None = None

    def read_frames(self, limit: int | None = None):
        capture = cv2.VideoCapture(self.stream_url)
        if not capture.isOpened():
            if self.fallback_video_path and Path(self.fallback_video_path).exists():
                logger.warning(
                    "RTSP stream unreachable (%s), falling back to %s",
                    self.stream_url,
                    self.fallback_video_path,
                )
                capture = cv2.VideoCapture(self.fallback_video_path)
                if not capture.isOpened():
                    raise RuntimeError(
                        f"Unable to open fallback video: {self.fallback_video_path}"
                    )
            else:
                raise RuntimeError(f"Unable to open RTSP stream: {self.stream_url}")

        frame_index = 0
        try:
            while True:
                success, frame = capture.read()
                if not success:
                    break
                yield frame_index, frame
                frame_index += 1
                if limit is not None and frame_index >= limit:
                    break
        finally:
            capture.release()
