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

    def _open_fallback(self):
        if self.fallback_video_path and Path(self.fallback_video_path).exists():
            logger.warning(
                "Falling back to video: %s", self.fallback_video_path,
            )
            capture = cv2.VideoCapture(self.fallback_video_path)
            if capture.isOpened():
                return capture
        return None

    def read_frames(self, limit: int | None = None):
        capture = cv2.VideoCapture(self.stream_url)

        if capture.isOpened():
            # Try one test read — RTSP may isOpened() but block for 30s on read()
            success, test_frame = capture.read()
            if success:
                # RTSP works — yield the test frame then continue
                frame_index = 0
                yield frame_index, test_frame
                frame_index = 1
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
                return
            else:
                logger.warning("RTSP opened but first read failed: %s", self.stream_url)
                capture.release()
        else:
            capture.release()

        # Fallback to video file
        fallback = self._open_fallback()
        if fallback is None:
            raise RuntimeError(f"Unable to open RTSP stream or fallback video")

        frame_index = 0
        try:
            while True:
                success, frame = fallback.read()
                if not success:
                    break
                yield frame_index, frame
                frame_index += 1
                if limit is not None and frame_index >= limit:
                    break
        finally:
            fallback.release()
