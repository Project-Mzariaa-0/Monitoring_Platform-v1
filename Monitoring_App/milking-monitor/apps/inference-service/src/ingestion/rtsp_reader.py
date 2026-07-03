from __future__ import annotations

from dataclasses import dataclass

import cv2


@dataclass
class RtspReader:
    stream_url: str

    def read_frames(self, limit: int | None = None):
        capture = cv2.VideoCapture(self.stream_url)
        if not capture.isOpened():
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
